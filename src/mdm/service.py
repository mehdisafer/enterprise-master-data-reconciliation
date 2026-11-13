"""Transactional identity lifecycle, temporal golden records and durable outbox.

Every graph mutation uses one PostgreSQL advisory transaction lock. This is a
deliberate correctness boundary, not a claim of horizontal write scalability.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from itertools import combinations
from uuid import UUID, uuid4, uuid5

from psycopg.types.json import Jsonb

from mdm.config import Actor
from mdm.db import Database
from mdm.domain import NORMALIZATION_VERSION, RULE_VERSION, SourceRecord
from mdm.matching import compare, generate_candidates, group_conflicts, normalize, survive
from mdm.telemetry import correlated_operation, emit, metadata

NAMESPACE = UUID("7062f685-fb4a-48b7-b4f7-592af1a65930")


class Conflict(ValueError):
    """A stale version, incompatible identity or reused idempotency key."""


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def now(conn) -> datetime:
    return conn.execute("SELECT clock_timestamp() AS t").fetchone()["t"]


def _uuid(value) -> str:
    return str(UUID(str(value)))


class Service:
    def __init__(self, db: Database | None = None):
        self.db = db or Database()

    def records(self, conn=None) -> list[SourceRecord]:
        if conn is None:
            with self.db.connect() as connection:
                return self.records(connection)
        return [SourceRecord.model_validate(r["current_payload"])
                for r in conn.execute("SELECT current_payload FROM source_records ORDER BY source_key")]

    def _group_records(self, conn, group_ids) -> list[SourceRecord]:
        return [SourceRecord.model_validate(row["current_payload"]) for row in conn.execute(
            "SELECT s.current_payload FROM source_records s JOIN memberships m USING(source_key) WHERE m.golden_id=ANY(%s::uuid[]) ORDER BY s.source_key",
            (list(group_ids),))]

    @correlated_operation("service.ingest")
    def ingest(self, records: list[SourceRecord]) -> dict:
        if len(records) > 10000:
            raise ValueError("batch limit is 10,000 records")
        # Validate the entire batch before writing. A source failure never means
        # its absent rows have been deleted.
        records = [SourceRecord.model_validate(r) for r in records]
        accepted = 0
        changed: set[str] = set()
        with self.db.connect(write=True) as conn:
            timestamp = now(conn)
            for record in sorted(records, key=lambda r: (r.key, r.valid_from, r.source_updated_at)):
                if record.valid_from > timestamp or record.source_updated_at > timestamp:
                    raise ValueError("future-effective source assertions require a scheduled activation and are not accepted")
                payload = record.model_dump(mode="json")
                fingerprint = digest(payload)
                if conn.execute("SELECT 1 FROM raw_records WHERE source_key=%s AND payload_hash=%s", (record.key, fingerprint)).fetchone():
                    continue
                collision = conn.execute(
                    "SELECT 1 FROM raw_records WHERE source_key=%s AND effective_from=%s "
                    "AND (payload->>'source_updated_at')::timestamptz=%s LIMIT 1",
                    (record.key, record.valid_from, record.source_updated_at),
                ).fetchone()
                if collision:
                    raise Conflict("different payloads share one source validity/change coordinate; correct the source version")
                source = conn.execute("SELECT revision FROM source_records WHERE source_key=%s", (record.key,)).fetchone()
                if not source:
                    conn.execute("INSERT INTO source_records VALUES(%s,%s,%s,%s,%s,1,%s)",
                                 (record.key, record.source_system, record.entity_type, record.source_id, Jsonb(payload), timestamp))
                    group_id = str(uuid5(NAMESPACE, record.key))
                    conn.execute("INSERT INTO identity_groups VALUES(%s,%s,'active',0,%s)", (group_id, record.entity_type, timestamp))
                    conn.execute("INSERT INTO memberships VALUES(%s,%s)", (record.key, group_id))
                    conn.execute("INSERT INTO membership_history VALUES(%s,%s,%s,%s,NULL)", (uuid4(), record.key, group_id, timestamp))
                else:
                    group_id = str(conn.execute("SELECT golden_id FROM memberships WHERE source_key=%s", (record.key,)).fetchone()["golden_id"])
                    conn.execute("UPDATE source_records SET revision=revision+1, ingested_at=%s WHERE source_key=%s", (timestamp, record.key))
                conn.execute("INSERT INTO raw_records VALUES(%s,%s,%s,%s,%s,%s)",
                             (uuid4(), record.key, Jsonb(payload), fingerprint, record.valid_from, timestamp))
                # A late correction rewrites the interpretation of its business
                # interval, never the original row or a newer business interval.
                current = conn.execute("SELECT payload FROM raw_records WHERE source_key=%s ORDER BY effective_from DESC, (payload->>'source_updated_at')::timestamptz DESC, observed_at DESC, raw_id DESC LIMIT 1", (record.key,)).fetchone()["payload"]
                conn.execute("UPDATE source_records SET current_payload=%s WHERE source_key=%s", (Jsonb(current), record.key))
                revision = conn.execute("SELECT revision FROM source_records WHERE source_key=%s", (record.key,)).fetchone()["revision"]
                standard = normalize(SourceRecord.model_validate(current))
                conn.execute("INSERT INTO standard_records VALUES(%s,%s,%s,%s) ON CONFLICT(source_key) DO UPDATE SET revision=excluded.revision,normalization_version=excluded.normalization_version,attributes=excluded.attributes",
                             (record.key, revision, NORMALIZATION_VERSION, Jsonb(standard)))
                changed.add(group_id)
                accepted += 1
            for group_id in sorted(changed):
                conflicts = group_conflicts(self._group_records(conn, [group_id]))
                if conflicts:
                    raise Conflict("source correction would invalidate the current group; split it before ingesting: " + ";".join(conflicts))
                self._rebuild(conn, group_id, timestamp)
            return {"received": len(records), "accepted": accepted, "duplicates": len(records)-accepted,
                    "groups_rebuilt": len(changed), "trace": metadata()}

    def _rebuild(self, conn, group_id: str, timestamp: datetime, *, correction_for: str | None = None):
        group = conn.execute("UPDATE identity_groups SET version=version+1 WHERE golden_id=%s RETURNING *", (group_id,)).fetchone()
        conn.execute("UPDATE golden_history SET known_to=%s WHERE golden_id=%s AND known_to IS NULL", (timestamp, group_id))
        keys = [r["source_key"] for r in conn.execute("SELECT source_key FROM memberships WHERE golden_id=%s ORDER BY source_key", (group_id,))]
        event_id = uuid4()
        parent_trace = None
        if correction_for:
            parent = conn.execute("SELECT request->'trace' trace FROM decisions WHERE decision_id=%s",
                                  (correction_for,)).fetchone()
            parent_trace = parent["trace"] if parent else None
        payload = {"contract_version": "golden-event.v1", "golden_id": str(group_id), "group_version": group["version"],
                   "active": bool(keys), "source_keys": keys, "correction_for": correction_for,
                   "attributes": {}, "provenance": {}, "conflicts": [], "business_slices": [],
                   "trace": metadata(parent_trace, decision_id=correction_for, event_id=event_id)}
        if keys:
            originals = list(conn.execute("SELECT source_key,payload,effective_from,observed_at,raw_id FROM raw_records WHERE source_key=ANY(%s) ORDER BY effective_from,(payload->>'source_updated_at')::timestamptz,observed_at,raw_id", (keys,)))
            boundaries = sorted({row["effective_from"] for row in originals})
            for index, start in enumerate(boundaries):
                end = boundaries[index+1] if index+1 < len(boundaries) else None
                effective = {}
                for row in originals:
                    if row["effective_from"] <= start:
                        effective[row["source_key"]] = SourceRecord.model_validate(row["payload"])
                hard = group_conflicts(list(effective.values()))
                if hard:
                    raise Conflict("historical business interval contains incompatible identities: " + ";".join(hard))
                attributes, provenance, conflicts = survive(list(effective.values()))
                conn.execute("INSERT INTO golden_history VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL)",
                             (uuid4(), group_id, group["version"], Jsonb(attributes), Jsonb(provenance), Jsonb(conflicts), start, end, timestamp))
                segment = {"valid_from": start.isoformat(), "valid_to": end.isoformat() if end else None,
                           "attributes": attributes, "provenance": provenance, "conflicts": conflicts}
                payload["business_slices"].append(segment)
                if start <= timestamp and (end is None or end > timestamp):
                    payload.update(segment)
            conn.execute("UPDATE identity_groups SET status='active' WHERE golden_id=%s", (group_id,))
        else:
            conn.execute("UPDATE identity_groups SET status='retired' WHERE golden_id=%s", (group_id,))
        conn.execute("INSERT INTO outbox VALUES(%s,%s,%s,%s,%s,%s)",
                     (event_id, group_id, group["version"], "golden.changed" if keys else "golden.retired", Jsonb(payload), timestamp))
        return payload

    def _versions(self, conn, group_ids) -> dict[str, int]:
        group_ids = sorted({_uuid(g) for g in group_ids})
        rows = list(conn.execute("SELECT golden_id,version FROM identity_groups WHERE golden_id=ANY(%s::uuid[]) AND status='active'", (group_ids,)))
        result = {str(r["golden_id"]): r["version"] for r in rows}
        if len(result) != len(group_ids):
            raise Conflict("every referenced group must exist and be active")
        return result

    @staticmethod
    def _assert_versions(actual: dict, expected: dict):
        if actual != {_uuid(k): v for k, v in expected.items()}:
            raise Conflict("group version conflict; reload the records and request a new decision")

    @staticmethod
    def _canonical_versions(versions: dict) -> dict[str, int]:
        if any(type(value) is not int or value < 1 for value in versions.values()):
            raise ValueError("expected group versions must be positive integers")
        return {_uuid(key): value for key, value in sorted(versions.items())}

    def _basis(self, conn, group_ids) -> dict:
        rows = list(conn.execute(
            "SELECT m.source_key,m.golden_id,s.revision FROM memberships m "
            "JOIN source_records s USING(source_key) WHERE m.golden_id=ANY(%s::uuid[]) ORDER BY m.source_key",
            (list(group_ids),),
        ))
        return {
            "memberships": {row["source_key"]: str(row["golden_id"]) for row in rows},
            "source_revisions": {row["source_key"]: row["revision"] for row in rows},
        }

    def _replay(self, conn, kind: str, submission: dict, actor: Actor, reason: str, key: str):
        """Check the submitted operation before consulting mutable topology."""
        actor.require("requester")
        if not reason.strip() or len(reason) > 2000:
            raise ValueError("a reason of 1–2,000 characters is required")
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", key):
            raise ValueError("invalid idempotency key")
        old = conn.execute("SELECT * FROM decisions WHERE idempotency_key=%s", (key,)).fetchone()
        if old:
            saved = old["request"].get("submission")
            if saved is None:
                # Read compatibility for pre-submission decisions. The original
                # caller fields can still be reconstructed without live state.
                fields = {
                    "merge": ("group_ids", "expected_versions"),
                    "split": ("group_ids", "expected_versions", "partitions"),
                    "unmerge": ("expected_versions",),
                }[kind]
                saved = {field: old["request"].get(field) for field in fields}
                if kind == "unmerge":
                    saved["merge_decision_id"] = old["request"].get("undoes")
            if (old["kind"] != kind or saved != submission or old["request"]["reason"] != reason
                    or old["requested_by"] != actor.name):
                raise Conflict("idempotency key was used for another request")
            emit("decision.replayed", decision_id=old["decision_id"],
                 origin_correlation_id=old["request"].get("trace", {}).get("origin_correlation_id"))
        return old

    def _assert_restore_destinations(self, conn, current_group_ids, mapping: dict):
        """An old ID must not acquire unrelated members during an unmerge."""
        destinations = sorted(set(mapping.values()) - set(current_group_ids))
        for destination in destinations:
            row = conn.execute(
                "SELECT g.status,EXISTS(SELECT 1 FROM memberships m WHERE m.golden_id=g.golden_id) occupied "
                "FROM identity_groups g WHERE g.golden_id=%s", (destination,),
            ).fetchone()
            if not row or row["status"] != "retired" or row["occupied"]:
                raise Conflict("unmerge destination is occupied or no longer retired; request an explicit split")

    def _policy_events(self, conn) -> list[dict]:
        """Reconstruct source-pair policy from immutable human decision events.

        Policies survive source revisions. Only a later executed explicit human
        merge clears a separation; automatic merges never clear human decisions.
        Compact partition maps avoid expanding every policy into quadratic pairs.
        """
        rows = conn.execute(
            "SELECT e.event_id,e.decision_id,e.transition,e.payload,e.occurred_at,d.kind,d.created_at,"
            "COALESCE((SELECT r.payload FROM decision_events r WHERE r.decision_id=d.decision_id "
            "AND r.transition='requested' ORDER BY r.occurred_at,r.event_id LIMIT 1),d.request) request "
            "FROM decision_events e JOIN decisions d USING(decision_id) "
            "WHERE (e.transition='rejected' AND d.kind='merge') OR "
            "(e.transition='executed' AND d.kind IN ('merge','split','unmerge')) "
            "ORDER BY e.occurred_at,e.event_id"
        )
        events = []
        for row in rows:
            request = row["request"]
            basis = request.get("basis", {})
            if row["transition"] == "rejected":
                mapping = basis.get("memberships")
                if mapping is None:
                    mapping = {r["source_key"]: str(r["golden_id"]) for r in conn.execute(
                        "SELECT source_key,golden_id FROM membership_history WHERE golden_id=ANY(%s::uuid[]) "
                        "AND known_from<=%s AND (known_to IS NULL OR known_to>%s)",
                        (request["group_ids"], row["created_at"], row["created_at"]),
                    )}
                negative = True
            else:
                mapping = row["payload"]["after_memberships"]
                negative = row["kind"] in {"split", "unmerge"}
            events.append({
                "decision_id": str(row["decision_id"]), "transition": row["transition"],
                "kind": row["kind"], "occurred_at": row["occurred_at"].isoformat(),
                "mapping": mapping, "negative": negative,
                "source_revisions": basis.get("source_revisions", {}),
                "reason": request.get("reason", "Human identity decision"),
            })
        return events

    @staticmethod
    def _pair_policy(left: str, right: str, events: list[dict]) -> dict | None:
        for event in reversed(events):
            mapping = event["mapping"]
            if left not in mapping or right not in mapping:
                continue
            if event["negative"] and mapping[left] != mapping[right]:
                return {
                    "left_key": left, "right_key": right, "decision_id": event["decision_id"],
                    "kind": event["kind"], "transition": event["transition"],
                    "occurred_at": event["occurred_at"], "reason": event["reason"],
                    "left_revision_at_decision": event["source_revisions"].get(left),
                    "right_revision_at_decision": event["source_revisions"].get(right),
                    "requires_explicit_human_merge": True,
                }
            if not event["negative"] and mapping[left] == mapping[right]:
                return None
        return None

    def _group_policy_block(self, memberships: dict, events: list[dict]) -> dict | None:
        # A triggering A-C pair cannot hide an existing negative B-C link when
        # A and B already belong to one group. The first blocker is sufficient.
        for left, right in combinations(sorted(memberships), 2):
            if memberships[left] != memberships[right]:
                blocked = self._pair_policy(left, right, events)
                if blocked:
                    return blocked
        return None

    def preview_merge(self, group_ids: list[str]) -> dict:
        group_ids = sorted({_uuid(group) for group in group_ids})
        if not 2 <= len(group_ids) <= 20:
            raise ValueError("merge requires 2–20 distinct groups")
        with self.db.connect() as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            versions = self._versions(conn, group_ids)
            records = self._group_records(conn, group_ids)
            hard = group_conflicts(records)
            attributes, provenance, conflicts = (None, {}, hard) if hard else survive(records)
            block = self._group_policy_block(self._basis(conn, group_ids)["memberships"], self._policy_events(conn))
            return {"group_ids": group_ids, "expected_versions": versions,
                    "attributes": attributes, "provenance": provenance, "conflicts": conflicts,
                    "hard_conflicts": hard, "policy_blocks": [block] if block else [],
                    "source_keys": sorted(record.key for record in records)}

    def _audit(self, conn, decision_id, actor, transition, payload, timestamp):
        event_id = uuid4()
        parent = conn.execute("SELECT request->'trace' trace FROM decisions WHERE decision_id=%s",
                              (decision_id,)).fetchone()
        audited = {**payload, "trace": metadata(parent["trace"] if parent else None,
                                               decision_id=decision_id, event_id=event_id)}
        conn.execute("INSERT INTO decision_events VALUES(%s,%s,%s,%s,%s,%s)",
                     (event_id, decision_id, actor, transition, Jsonb(audited), timestamp))

    def _request(self, conn, kind: str, request: dict, actor: Actor, reason: str, key: str, *, submission: dict):
        old = self._replay(conn, kind, submission, actor, reason, key)
        if old:
            return old
        request = {**request, "reason": reason, "contract_version": "decision.v1", "rule_version": RULE_VERSION,
                   "submission": submission, "basis": self._basis(conn, request["group_ids"])}
        decision_id, timestamp = uuid4(), now(conn)
        request["trace"] = metadata(decision_id=decision_id)
        result = conn.execute("INSERT INTO decisions VALUES(%s,%s,%s,'pending',1,%s,NULL,NULL,%s,NULL,%s) RETURNING *",
                              (decision_id, key, kind, actor.name, Jsonb(request), timestamp)).fetchone()
        self._audit(conn, decision_id, actor.name, "requested", request, timestamp)
        return result

    @correlated_operation("service.request_merge")
    def request_merge(self, group_ids: list[str], expected_versions: dict, actor: Actor, reason: str, idempotency_key: str):
        group_ids = sorted({_uuid(g) for g in group_ids})
        if not 2 <= len(group_ids) <= 20:
            raise ValueError("merge requires 2–20 distinct groups")
        expected_versions = self._canonical_versions(expected_versions)
        submission = {"group_ids": group_ids, "expected_versions": expected_versions}
        with self.db.connect(write=True) as conn:
            replay = self._replay(conn, "merge", submission, actor, reason, idempotency_key)
            if replay:
                return replay
            versions = self._versions(conn, group_ids)
            self._assert_versions(versions, expected_versions)
            records = self._group_records(conn, group_ids)
            conflicts = group_conflicts(records)
            if conflicts:
                raise Conflict("merge blocked: " + ";".join(conflicts))
            return self._request(conn, "merge", {"group_ids": group_ids, "expected_versions": versions},
                                 actor, reason, idempotency_key, submission=submission)

    @correlated_operation("service.request_split")
    def request_split(self, group_id: str, partitions: list[list[str]], expected_version: int, actor: Actor,
                      reason: str, idempotency_key: str):
        group_id = _uuid(group_id)
        expected = self._canonical_versions({group_id: expected_version})
        flattened = [key for part in partitions for key in part]
        if (not 2 <= len(partitions) <= 20 or any(not part for part in partitions)
                or any(not isinstance(key, str) for key in flattened)
                or len(flattened) != len(set(flattened))):
            raise ValueError("split partitions must cover every current source identity exactly once in 2–20 nonempty groups")
        partitions = sorted([sorted(part) for part in partitions])
        submission = {"group_ids": [group_id], "expected_versions": expected, "partitions": partitions}
        with self.db.connect(write=True) as conn:
            replay = self._replay(conn, "split", submission, actor, reason, idempotency_key)
            if replay:
                return replay
            versions = self._versions(conn, [group_id])
            self._assert_versions(versions, expected)
            existing = {r.key for r in self._group_records(conn, [group_id])}
            if set(flattened) != existing:
                raise ValueError("split partitions must cover every current source identity exactly once in 2–20 nonempty groups")
            return self._request(conn, "split", {"group_ids": [group_id], "expected_versions": versions,
                                                  "partitions": partitions}, actor, reason, idempotency_key,
                                 submission=submission)

    @correlated_operation("service.request_unmerge")
    def request_unmerge(self, merge_decision_id: str, expected_versions: dict, actor: Actor, reason: str, idempotency_key: str):
        merge_decision_id = _uuid(merge_decision_id)
        expected_versions = self._canonical_versions(expected_versions)
        submission = {"merge_decision_id": merge_decision_id, "expected_versions": expected_versions}
        with self.db.connect(write=True) as conn:
            replay = self._replay(conn, "unmerge", submission, actor, reason, idempotency_key)
            if replay:
                return replay
            old = conn.execute("SELECT * FROM decisions WHERE decision_id=%s", (merge_decision_id,)).fetchone()
            if not old or old["kind"] not in {"merge", "automatic_merge"} or old["status"] != "executed":
                raise ValueError("unmerge needs an executed merge decision")
            mapping = old["result"]["before_memberships"]
            rows = list(conn.execute("SELECT source_key,golden_id FROM memberships WHERE source_key=ANY(%s)", (list(mapping),)))
            active = sorted({str(r["golden_id"]) for r in rows})
            if len(active) != 1 or {r.key for r in self._group_records(conn, active)} != set(mapping):
                raise Conflict("topology has changed since this merge; request an explicit split instead")
            self._assert_versions(self._versions(conn, active), expected_versions)
            self._assert_restore_destinations(conn, active, mapping)
            return self._request(conn, "unmerge", {"group_ids": active, "expected_versions": expected_versions,
                "restore_mapping": mapping, "undoes": str(old["decision_id"])}, actor, reason, idempotency_key,
                submission=submission)

    @correlated_operation("service.approve")
    def approve(self, decision_id: str, actor: Actor, expected_version: int, *, reject: bool = False):
        actor.require("approver")
        with self.db.connect(write=True) as conn:
            decision = conn.execute("SELECT * FROM decisions WHERE decision_id=%s", (_uuid(decision_id),)).fetchone()
            if not decision:
                raise KeyError("decision not found")
            if decision["requested_by"] == actor.name:
                raise PermissionError("requester and approver must be different people")
            status = "rejected" if reject else "approved"
            if decision["status"] == status and decision["approved_by"] == actor.name and decision["version"] == expected_version+1:
                return decision
            if decision["status"] != "pending" or decision["version"] != expected_version:
                raise Conflict("decision version or status conflict")
            result = conn.execute("UPDATE decisions SET status=%s,approved_by=%s,version=version+1 WHERE decision_id=%s RETURNING *",
                                  (status, actor.name, decision_id)).fetchone()
            self._audit(conn, decision_id, actor.name, status, {}, now(conn))
            return result

    @correlated_operation("service.execute")
    def execute(self, decision_id: str, actor: Actor, expected_version: int, *, failpoint: str | None = None):
        actor.require("executor")
        with self.db.connect(write=True) as conn:
            decision = conn.execute("SELECT * FROM decisions WHERE decision_id=%s", (_uuid(decision_id),)).fetchone()
            if not decision:
                raise KeyError("decision not found")
            if actor.name in {decision["requested_by"], decision["approved_by"]}:
                raise PermissionError("executor must differ from requester and approver")
            if decision["status"] == "executed" and decision["executed_by"] == actor.name and decision["version"] == expected_version+1:
                return decision
            if decision["status"] != "approved" or decision["version"] != expected_version:
                raise Conflict("decision version or status conflict")
            request = decision["request"]
            self._assert_versions(self._versions(conn, request["group_ids"]), request["expected_versions"])
            return self._execute_plan(conn, decision, actor.name, failpoint=failpoint)

    def _execute_plan(self, conn, decision, executor, *, failpoint=None):
        request = decision["request"]
        group_ids = request["group_ids"]
        timestamp = now(conn)
        before = {r["source_key"]: str(r["golden_id"]) for r in conn.execute(
            "SELECT source_key,golden_id FROM memberships WHERE golden_id=ANY(%s::uuid[])", (group_ids,))}
        if decision["kind"] in {"merge", "automatic_merge"}:
            conflicts = group_conflicts(self._group_records(conn, group_ids))
            if conflicts:
                raise Conflict("merge blocked: " + ";".join(conflicts))
            target = min(group_ids)
            after = {key: target for key in before}
        elif decision["kind"] == "unmerge":
            after = request["restore_mapping"]
            if set(before) != set(after):
                raise Conflict("source membership changed after unmerge request")
            self._assert_restore_destinations(conn, group_ids, after)
        else:
            # The partition containing the earliest lexical source keeps the old
            # ID. Every other partition receives a deterministic decision ID.
            after = {}
            for index, part in enumerate(request["partitions"]):
                target = group_ids[0] if index == 0 else str(uuid5(NAMESPACE, f"{decision['decision_id']}:{index}"))
                for key in part:
                    after[key] = target
        affected = sorted(set(before.values()) | set(after.values()))
        entity_type = self._group_records(conn, group_ids)[0].entity_type
        for target in sorted(set(after.values())):
            conn.execute("INSERT INTO identity_groups VALUES(%s,%s,'active',0,%s) ON CONFLICT(golden_id) DO NOTHING", (target, entity_type, timestamp))
        for key, target in sorted(after.items()):
            if before[key] != target:
                conn.execute("UPDATE memberships SET golden_id=%s WHERE source_key=%s", (target, key))
                conn.execute("UPDATE membership_history SET known_to=%s WHERE source_key=%s AND known_to IS NULL", (timestamp, key))
                conn.execute("INSERT INTO membership_history VALUES(%s,%s,%s,%s,NULL)", (uuid4(), key, target, timestamp))
        result = {"before_memberships": before, "after_memberships": after, "affected_groups": affected,
                  "consumers_must_apply_corrections": True,
                  "trace": metadata(request.get("trace"), decision_id=decision["decision_id"])}
        conn.execute("UPDATE decisions SET status='executed',executed_by=%s,result=%s,version=version+1 WHERE decision_id=%s",
                     (executor, Jsonb(result), decision["decision_id"]))
        self._audit(conn, decision["decision_id"], executor, "executed", result, timestamp)
        if failpoint == "before_outbox":
            raise RuntimeError("injected crash before outbox insert; transaction must roll back")
        for group_id in affected:
            self._rebuild(conn, group_id, timestamp, correction_for=str(decision["decision_id"]))
        return conn.execute("SELECT * FROM decisions WHERE decision_id=%s", (decision["decision_id"],)).fetchone()

    @correlated_operation("service.reconcile")
    def reconcile(self, *, mode: str = "hybrid", failpoint: str | None = None) -> dict:
        if mode not in {"deterministic", "hybrid"}:
            raise ValueError("unsupported matching mode")
        with self.db.connect(write=True) as conn:
            records = self.records(conn)
            by_key = {r.key: r for r in records}
            revisions = {r["source_key"]: r["revision"] for r in conn.execute("SELECT source_key,revision FROM source_records")}
            policies = self._policy_events(conn)
            pairs = generate_candidates(records)
            result = {"records": len(records), "candidates": len(pairs), "new_evidence": 0, "automatic_merges": 0,
                      "review": 0, "reject": 0, "group_conflicts": 0, "policy_blocked_candidates": 0,
                      "mode": mode, "trace": metadata()}
            for left, right in sorted(pairs):
                evidence = compare(by_key[left], by_key[right], mode=mode)
                candidate = conn.execute("INSERT INTO candidates VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING candidate_id",
                    (uuid4(), left, right, revisions[left], revisions[right], RULE_VERSION, mode,
                     Jsonb(evidence.model_dump(mode="json")), evidence.decision, now(conn))).fetchone()
                if candidate:
                    result["new_evidence"] += 1
                else:
                    candidate = conn.execute(
                        "SELECT candidate_id FROM candidates WHERE left_key=%s AND right_key=%s "
                        "AND left_revision=%s AND right_revision=%s AND rule_version=%s AND mode=%s",
                        (left, right, revisions[left], revisions[right], RULE_VERSION, mode),
                    ).fetchone()
                candidate_id = candidate["candidate_id"]
                group_ids = sorted({str(r["golden_id"]) for r in conn.execute(
                    "SELECT golden_id FROM memberships WHERE source_key=ANY(%s)", ([left, right],),
                )})
                if len(group_ids) == 1:
                    conn.execute("UPDATE candidates SET disposition='merged' WHERE candidate_id=%s", (candidate_id,))
                    continue
                if evidence.decision == "reject":
                    result["reject"] += 1
                    conn.execute("UPDATE candidates SET disposition='reject' WHERE candidate_id=%s", (candidate_id,))
                    continue
                if group_conflicts(self._group_records(conn, group_ids)):
                    result["group_conflicts"] += 1
                    conn.execute("UPDATE candidates SET disposition='group_conflict' WHERE candidate_id=%s", (candidate_id,))
                    continue
                basis = self._basis(conn, group_ids)
                blocked = self._group_policy_block(basis["memberships"], policies)
                if blocked:
                    # Persist a current review disposition while preserving the
                    # immutable comparison score and criteria in evidence.
                    result["policy_blocked_candidates"] += 1
                    result["review"] += 1
                    conn.execute("UPDATE candidates SET disposition='review' WHERE candidate_id=%s", (candidate_id,))
                    continue
                if evidence.decision == "review":
                    result["review"] += 1
                    conn.execute("UPDATE candidates SET disposition='review' WHERE candidate_id=%s", (candidate_id,))
                    continue
                versions = self._versions(conn, group_ids)
                decision_id = uuid4()
                request = {"group_ids": group_ids, "expected_versions": versions, "rule_version": RULE_VERSION,
                           "contract_version": "decision.v1", "basis": basis, "evidence": evidence.model_dump(mode="json"),
                           "trace": metadata(decision_id=decision_id)}
                decision = conn.execute("INSERT INTO decisions VALUES(%s,%s,'automatic_merge','approved',1,'system.rules','system.rules',NULL,%s,NULL,%s) RETURNING *",
                    (decision_id, f"auto:{digest([left,right,versions])}", Jsonb(request), now(conn))).fetchone()
                self._audit(conn, decision_id, "system.rules", "auto-authorized", request, now(conn))
                self._execute_plan(conn, decision, "system.rules", failpoint=failpoint)
                result["automatic_merges"] += 1
                conn.execute("UPDATE candidates SET disposition='merged' WHERE candidate_id=%s", (candidate_id,))
            return result

    def _current_candidates(self, conn, *, mode: str = "hybrid", policies: list[dict] | None = None) -> list[dict]:
        if mode not in {"deterministic", "hybrid"}:
            raise ValueError("unsupported matching mode")
        rows = list(conn.execute(
            "SELECT c.*,lm.golden_id left_golden_id,rm.golden_id right_golden_id FROM candidates c "
            "JOIN source_records l ON l.source_key=c.left_key AND l.revision=c.left_revision "
            "JOIN source_records r ON r.source_key=c.right_key AND r.revision=c.right_revision "
            "JOIN memberships lm ON lm.source_key=c.left_key JOIN memberships rm ON rm.source_key=c.right_key "
            "WHERE c.mode=%s AND c.rule_version=%s ORDER BY c.left_key,c.right_key", (mode, RULE_VERSION),
        ))
        policies = self._policy_events(conn) if policies is None else policies
        basis_cache, block_cache = {}, {}
        for row in rows:
            left_group, right_group = str(row["left_golden_id"]), str(row["right_golden_id"])
            row["policy_blocks"] = []
            if left_group == right_group:
                row["disposition"] = "merged"
                continue
            groups = tuple(sorted((left_group, right_group)))
            if policies and row["evidence"]["decision"] != "reject":
                if groups not in block_cache:
                    for group in groups:
                        if group not in basis_cache:
                            basis_cache[group] = self._basis(conn, [group])["memberships"]
                    block_cache[groups] = self._group_policy_block(
                        {**basis_cache[left_group], **basis_cache[right_group]}, policies,
                    )
                if block_cache[groups]:
                    row["policy_blocks"] = [block_cache[groups]]
                    if row["disposition"] != "group_conflict":
                        row["disposition"] = "review"
        return rows

    def _consumer_state(self, conn, consumer: str) -> dict:
        reference = {row["source_key"]: str(row["golden_id"]) for row in conn.execute("SELECT * FROM memberships")}
        expected_groups = {str(row["golden_id"]): row["version"] for row in conn.execute(
            "SELECT golden_id,version FROM identity_groups WHERE status='active'",
        )}
        snapshots = list(conn.execute(
            "SELECT golden_id,group_version,payload FROM consumer_records WHERE consumer=%s AND active", (consumer,),
        ))
        owners = {}
        versions = {}
        for row in snapshots:
            golden_id = str(row["golden_id"])
            versions[golden_id] = row["group_version"]
            for key in row["payload"]["source_keys"]:
                owners.setdefault(key, set()).add(golden_id)
        actual = {row["source_key"]: str(row["golden_id"]) for row in conn.execute(
            "SELECT source_key,golden_id FROM consumer_crosswalk WHERE consumer=%s", (consumer,),
        )}
        conflicts = sorted(key for key, ids in owners.items() if len(ids) != 1)
        projection_mismatches = sorted(
            key for key in set(owners) | set(actual)
            if key not in actual or owners.get(key) != {actual[key]}
        )
        missing = sorted(set(reference) - set(actual))
        unexpected = sorted(set(actual) - set(reference))
        mismatched = sorted(key for key in set(reference) & set(actual) if reference[key] != actual[key])
        stale_groups = sorted(group for group, version in expected_groups.items() if versions.get(group) != version)
        unexpected_groups = sorted(set(versions) - set(expected_groups))
        remaining = conn.execute(
            "SELECT count(*) n FROM outbox o WHERE NOT EXISTS(SELECT 1 FROM consumer_inbox i "
            "WHERE i.consumer=%s AND i.event_id=o.event_id)", (consumer,),
        ).fetchone()["n"]
        matched = len(set(reference) & set(actual)) - len(mismatched)
        return {
            "consumer": consumer, "remaining": remaining,
            "caught_up": remaining == 0 and not any((conflicts, projection_mismatches, missing, unexpected, mismatched, stale_groups, unexpected_groups)),
            "reference_sources": len(reference), "consumed_sources": len(owners), "consumed_crosswalks": len(actual),
            "reference_coverage": matched / len(reference) if reference else None,
            "consumed_coverage": sum(owners[key] == {actual.get(key)} for key in owners) / len(owners) if owners else None,
            "conflicting_sources": conflicts, "projection_mismatches": projection_mismatches,
            "missing_sources": missing, "unexpected_sources": unexpected,
            "mismatched_sources": mismatched, "stale_groups": stale_groups, "unexpected_active_groups": unexpected_groups,
        }

    def _consumer_states(self, conn) -> list[dict]:
        names = {row["consumer"] for row in conn.execute(
            "SELECT consumer FROM consumer_records UNION SELECT consumer FROM consumer_inbox",
        )} | {"reporting"}
        return [self._consumer_state(conn, name) for name in sorted(names)]

    @correlated_operation("service.consume")
    def consume(self, consumer: str = "reporting", *, limit: int = 10000, failpoint: str | None = None) -> dict:
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,39}", consumer):
            raise ValueError("invalid consumer identifier")
        if not 1 <= limit <= 10000:
            raise ValueError("consumer batch must contain 1–10,000 events")
        with self.db.connect(write=True) as conn:
            rows = list(conn.execute("SELECT o.* FROM outbox o WHERE NOT EXISTS(SELECT 1 FROM consumer_inbox i WHERE i.consumer=%s AND i.event_id=o.event_id) ORDER BY o.occurred_at,o.aggregate_id,o.aggregate_version LIMIT %s", (consumer, limit)))
            selected_count = len(rows)
            corrections = sorted({row["payload"].get("correction_for") for row in rows
                                  if row["payload"].get("correction_for")})
            if corrections:
                # A merge/split/unmerge publishes at most twenty affected IDs.
                # Finish the whole correction even if the requested limit is 1.
                excessive = conn.execute(
                    "SELECT payload->>'correction_for' correction FROM outbox "
                    "WHERE payload->>'correction_for'=ANY(%s) GROUP BY payload->>'correction_for' HAVING count(*)>20",
                    (corrections,),
                ).fetchone()
                if excessive:
                    raise Conflict("consumer correction exceeds the twenty-group operation contract")
                expanded = list(conn.execute(
                    "SELECT o.* FROM outbox o WHERE o.payload->>'correction_for'=ANY(%s) "
                    "AND NOT EXISTS(SELECT 1 FROM consumer_inbox i WHERE i.consumer=%s AND i.event_id=o.event_id)",
                    (corrections, consumer),
                ))
                rows = sorted({row["event_id"]: row for row in [*rows, *expanded]}.values(),
                              key=lambda row: (row["occurred_at"], str(row["aggregate_id"]), row["aggregate_version"]))
            for row in rows:
                p = row["payload"]
                existing = conn.execute("SELECT group_version FROM consumer_records WHERE consumer=%s AND golden_id=%s", (consumer, row["aggregate_id"])).fetchone()
                if not existing or existing["group_version"] < row["aggregate_version"]:
                    conn.execute("INSERT INTO consumer_records VALUES(%s,%s,%s,%s,%s) ON CONFLICT(consumer,golden_id) DO UPDATE SET group_version=excluded.group_version,payload=excluded.payload,active=excluded.active",
                        (consumer, row["aggregate_id"], row["aggregate_version"], Jsonb(p), p["active"]))
                conn.execute("INSERT INTO consumer_inbox VALUES(%s,%s,%s) ON CONFLICT DO NOTHING", (consumer, row["event_id"], now(conn)))
            # Derive pointers from consumed snapshots only. An ingestion batch
            # may be behind; an identity correction is consumed atomically.
            if rows:
                conn.execute("DELETE FROM consumer_crosswalk WHERE consumer=%s", (consumer,))
                current = list(conn.execute("SELECT golden_id,payload FROM consumer_records WHERE consumer=%s AND active ORDER BY golden_id", (consumer,)))
                owners = {}
                for row in current:
                    for key in row["payload"]["source_keys"]:
                        owners.setdefault(key, []).append(str(row["golden_id"]))
                for key, ids in owners.items():
                    if len(ids) == 1:
                        conn.execute("INSERT INTO consumer_crosswalk VALUES(%s,%s,%s)", (consumer, key, ids[0]))
                if failpoint == "before_ack":
                    raise RuntimeError("injected consumer crash; snapshot and inbox must roll back together")
            result = {**self._consumer_state(conn, consumer), "processed": len(rows), "requested_limit": limit,
                      "expanded_for_atomic_corrections": len(rows) - selected_count, "trace": metadata()}
        # These receipts are logged only after the inbox/projection transaction
        # commits. Durable receipt correlation is inbox.event_id -> outbox.trace.
        for row in rows:
            trace = row["payload"].get("trace", {})
            emit("consumer.acknowledged", consumer=consumer, event_id=row["event_id"],
                 aggregate_id=row["aggregate_id"], aggregate_version=row["aggregate_version"],
                 decision_id=trace.get("decision_id"), producer_correlation_id=trace.get("correlation_id"),
                 producer_run_id=trace.get("run_id"), origin_correlation_id=trace.get("origin_correlation_id"))
        return result

    def snapshot(self, *, mode: str = "hybrid") -> dict:
        with self.db.connect() as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            groups = list(conn.execute("SELECT g.golden_id,g.entity_type,g.status,g.version,h.attributes,h.provenance,h.conflicts,h.valid_from,h.valid_to,h.known_from FROM identity_groups g LEFT JOIN golden_history h ON h.golden_id=g.golden_id AND h.known_to IS NULL AND h.valid_from<=current_timestamp AND (h.valid_to IS NULL OR h.valid_to>current_timestamp) ORDER BY g.golden_id"))
            candidates = self._current_candidates(conn, mode=mode)
            return {"contract_version": "snapshot.v1", "groups": groups,
                "matching_mode": mode,
                "crosswalk": list(conn.execute("SELECT * FROM memberships ORDER BY source_key")),
                "sources": list(conn.execute("SELECT * FROM source_records ORDER BY source_key")),
                "candidates": candidates,
                "policy_blocks": [{"candidate_id": str(row["candidate_id"]), "left_key": row["left_key"],
                                   "right_key": row["right_key"], "reasons": row["policy_blocks"]}
                                  for row in candidates if row["policy_blocks"]],
                "decisions": list(conn.execute("SELECT * FROM decisions ORDER BY created_at")),
                "consumers": list(conn.execute("SELECT * FROM consumer_records ORDER BY consumer,golden_id")),
                "consumer_crosswalk": list(conn.execute("SELECT * FROM consumer_crosswalk ORDER BY consumer,source_key")),
                "consumer_status": self._consumer_states(conn),
                "runs": list(conn.execute("SELECT * FROM runs ORDER BY started_at")),
                "counts": {"raw_records": conn.execute("SELECT count(*) n FROM raw_records").fetchone()["n"],
                           "history_rows": conn.execute("SELECT count(*) n FROM golden_history").fetchone()["n"],
                           "outbox_events": conn.execute("SELECT count(*) n FROM outbox").fetchone()["n"]}}

    def history(self, group_id: str) -> list[dict]:
        with self.db.connect() as conn:
            return list(conn.execute("SELECT * FROM golden_history WHERE golden_id=%s ORDER BY known_from,valid_from", (_uuid(group_id),)))

    def quality(self, *, mode: str = "hybrid") -> dict:
        with self.db.connect() as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            counts = conn.execute("SELECT (SELECT count(*) FROM source_records) sources,(SELECT count(*) FROM memberships) crosswalks,(SELECT count(*) FROM identity_groups WHERE status='active') active_groups,(SELECT count(*) FROM decisions WHERE status='pending') pending_decisions,(SELECT count(*) FROM decisions WHERE status='executed' AND kind IN ('split','unmerge')) corrections,(SELECT count(*) FROM decisions WHERE status='executed') executed_decisions").fetchone()
            candidates = self._current_candidates(conn, mode=mode)
            counts["matching_mode"] = mode
            counts["suspected_duplicate_pairs"] = sum(
                row["disposition"] == "review" and not row["policy_blocks"]
                and row["left_golden_id"] != row["right_golden_id"] for row in candidates
            )
            counts["policy_blocked_candidates"] = sum(bool(row["policy_blocks"]) for row in candidates)
            counts["group_conflicting_candidates"] = sum(row["disposition"] == "group_conflict" for row in candidates)
            counts["crosswalk_coverage"] = counts["crosswalks"] / counts["sources"] if counts["sources"] else None
            counts["correction_rate"] = counts["corrections"] / counts["executed_decisions"] if counts["executed_decisions"] else None
            states = self._consumer_states(conn)
            counts["consumer_lag"] = [{**state, "pending_events": state["remaining"]} for state in states]
            counts["unconsumed_events"] = next(state["remaining"] for state in states if state["consumer"] == "reporting")
            return counts

    def check(self) -> dict:
        failures = []
        with self.db.connect() as conn:
            checks = {
                "source_crosswalk_coverage": "SELECT count(*) n FROM source_records s LEFT JOIN memberships m USING(source_key) WHERE m.source_key IS NULL",
                "active_memberships": "SELECT count(*) n FROM memberships m JOIN identity_groups g USING(golden_id) WHERE g.status<>'active'",
                "empty_active_groups": "SELECT count(*) n FROM identity_groups g WHERE status='active' AND NOT EXISTS(SELECT 1 FROM memberships m WHERE m.golden_id=g.golden_id)",
                "source_domains": "SELECT count(*) n FROM memberships m JOIN source_records s USING(source_key) JOIN identity_groups g USING(golden_id) WHERE s.entity_type<>g.entity_type",
                "nonoverlap": "SELECT count(*) n FROM golden_history a JOIN golden_history b ON a.golden_id=b.golden_id AND a.history_id<b.history_id WHERE tstzrange(a.valid_from,a.valid_to,'[)') && tstzrange(b.valid_from,b.valid_to,'[)') AND tstzrange(a.known_from,a.known_to,'[)') && tstzrange(b.known_from,b.known_to,'[)')",
                "attribute_provenance": "SELECT count(*) n FROM golden_history h CROSS JOIN LATERAL jsonb_each(h.attributes) a WHERE NOT h.provenance ? a.key OR (a.value NOT IN ('null'::jsonb,'[]'::jsonb) AND NOT coalesce(h.provenance->a.key ? 'source_key',false))",
                "ledger_outbox": "SELECT count(*) n FROM identity_groups g WHERE version>0 AND NOT EXISTS(SELECT 1 FROM outbox o WHERE o.aggregate_id=g.golden_id AND o.aggregate_version=g.version)",
                "membership_history": "SELECT count(*) n FROM memberships m WHERE NOT EXISTS(SELECT 1 FROM membership_history h WHERE h.source_key=m.source_key AND h.golden_id=m.golden_id AND h.known_to IS NULL)",
            }
            results = {name: conn.execute(sql).fetchone()["n"] for name, sql in checks.items()}
            failures.extend(name for name, count in results.items() if count)
            for row in conn.execute("SELECT golden_id FROM identity_groups WHERE status='active'"):
                if group_conflicts(self._group_records(conn, [str(row["golden_id"])])):
                    failures.append("group_compatibility")
            results["group_compatibility"] = failures.count("group_compatibility")
            return {"passed": not failures, "violations": results, "checks": len(results)}
