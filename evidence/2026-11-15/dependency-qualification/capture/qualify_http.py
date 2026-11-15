#!/usr/bin/env python3
"""Bounded real-Uvicorn qualification against an already seeded local database.

Run with the tested interpreter: qualify_http.py --output NEW_DIRECTORY --expect-db mdm_demo
Database credentials come only from MDM_DATABASE_URL[_FILE]. Temporary actor
credentials never enter command arguments, result JSON or published logs.
This exercises reads and refused mutations; all 17 ledger fingerprints must match.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import http.client
from importlib.metadata import version
import ipaddress
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
from uuid import UUID, uuid4

TABLES = (
    "raw_records", "source_records", "identity_groups", "memberships",
    "golden_history", "decisions", "outbox", "consumer_inbox", "consumer_records",
    "schema_migrations", "standard_records", "membership_history", "candidates",
    "decision_events", "consumer_crosswalk", "runs", "run_sources",
)
ROLES = ("reader", "requester", "approver", "executor")
BODY_LIMIT = 10_000_000
BODY_MARKER = "qualification-private-body-sentinel"
QUERY_MARKER = "qualification-private-query-sentinel"
HEADER_MARKER = "qualification-untrusted-correlation-sentinel"


class QualificationFailure(Exception):
    """Failure messages are fixed labels and never include application payloads."""


def serve(fd: int) -> None:
    import uvicorn
    inherited = socket.socket(fileno=fd)
    config = uvicorn.Config("mdm.api:app", host="127.0.0.1", port=inherited.getsockname()[1],
                            access_log=False, log_level="info", timeout_graceful_shutdown=3)
    uvicorn.Server(config).run(sockets=[inherited])


def fingerprint(dsn: str, expected: str) -> tuple[dict, dict, str]:
    import psycopg
    from psycopg import sql
    with psycopg.connect(dsn, connect_timeout=3,
                         options="-c statement_timeout=5000 -c lock_timeout=2000") as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        conn.execute("SET TIME ZONE 'UTC'")
        database, server, address = conn.execute(
            "SELECT current_database(), current_setting('server_version'), inet_server_addr()::text"
        ).fetchone()
        if database != expected or database in {"postgres", "template0", "template1"}:
            raise QualificationFailure("dedicated_database_mismatch")
        if not address or not ipaddress.ip_interface(address).ip.is_loopback:
            raise QualificationFailure("database_must_use_loopback_tcp")
        tables = {}
        for table in TABLES:
            digest, count = hashlib.sha256(), 0
            query = sql.SQL("SELECT to_jsonb(t)::text FROM {} t ORDER BY to_jsonb(t)::text").format(
                sql.Identifier("public", table)
            )
            for (row,) in conn.execute(query):
                digest.update(row.encode() + b"\n")
                count += 1
            tables[table] = {"rows": count, "sha256": digest.hexdigest()}
        row = conn.execute(
            "SELECT golden_id FROM golden_history GROUP BY golden_id ORDER BY count(*) DESC,golden_id LIMIT 1"
        ).fetchone()
        if not row:
            raise QualificationFailure("seeded_golden_history_required")
        return tables, {"database": database, "server_version": server,
                        "address": str(ipaddress.ip_interface(address).ip)}, str(row[0])


def main() -> int:
    import httpx
    from mdm.config import database_url
    from psycopg.conninfo import conninfo_to_dict

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expect-db", default="mdm_demo")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    started = time.monotonic()
    report = {"format_version": 1, "started_at": datetime.now(timezone.utc).isoformat(),
              "qualification": "native_http_loopback", "database_writes_intended": False,
              "budget_seconds": 60, "requests": [], "assertions": [], "passed": False}
    process = listener = client = None
    temporary = tempfile.TemporaryDirectory(prefix="mdm-http-qualification-")
    temp = Path(temporary.name)
    stdout_path, stderr_path = temp / "server.stdout.log", temp / "server.stderr.log"
    stdout_file, stderr_file = stdout_path.open("wb"), stderr_path.open("wb")
    tokens = {role: secrets.token_urlsafe(48) for role in ROLES}
    forbidden = [*tokens.values(), BODY_MARKER, QUERY_MARKER, HEADER_MARKER]
    credential_file = temp / "actors.json"
    credential_file.write_text(json.dumps({token: {"name": f"http.{role}", "role": role}
                                         for role, token in tokens.items()}))
    credential_file.chmod(0o600)
    checks = report["assertions"]
    requests = report["requests"]
    correlations: set[str] = set()

    def check(condition: bool, label: str) -> None:
        checks.append({"check": label, "passed": bool(condition)})
        if not condition:
            raise QualificationFailure(label)

    def timeout_handler(signum, frame):
        raise QualificationFailure("55_second_execution_deadline")

    def capture(label, method, path, status, headers, body, expected, elapsed):
        headers = {key.lower(): value for key, value in headers.items()}
        item = {"label": label, "method": method, "path": path.split("?", 1)[0],
                "status": status, "expected_status": expected, "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_ms": round(elapsed * 1000, 3),
                "correlation_id": headers.get("x-correlation-id"),
                "content_type": headers.get("content-type")}
        requests.append(item)
        check(status == expected, label + ".status")
        identifier = headers.get("x-correlation-id", "")
        try:
            valid_uuid = str(UUID(identifier)) == identifier
        except ValueError:
            valid_uuid = False
        check(valid_uuid and identifier not in correlations, label + ".unique_server_correlation")
        correlations.add(identifier)
        check(headers.get("cache-control") == "no-store", label + ".no_store")
        check(headers.get("x-content-type-options") == "nosniff", label + ".nosniff")
        check(headers.get("referrer-policy") == "no-referrer", label + ".referrer")
        check("frame-ancestors 'none'" in headers.get("content-security-policy", ""), label + ".frame_policy")
        check(all(token.encode() not in body for token in tokens.values()), label + ".no_token_in_response")
        if expected == 401:
            check(headers.get("www-authenticate") == "Bearer", label + ".bearer_challenge")
        if "application/json" in headers.get("content-type", ""):
            return json.loads(body)
        return body.decode("utf-8")

    def request(label, method, path, expected=200, role=None, authorization=None, **kwargs):
        headers = {"X-Correlation-ID": HEADER_MARKER}
        if role:
            headers["Authorization"] = "Bearer " + tokens[role]
        if authorization:
            headers["Authorization"] = authorization
        headers.update(kwargs.pop("headers", {}))
        began = time.monotonic()
        response = client.request(method, path, headers=headers, **kwargs)
        return capture(label, method, path, response.status_code, response.headers,
                       response.content, expected, time.monotonic() - began)

    previous_alarm = signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, 55)
    try:
        dsn = database_url()
        forbidden.append(dsn)
        password = conninfo_to_dict(dsn).get("password")
        if password:
            forbidden.append(password)
        before, database, history_id = fingerprint(dsn, args.expect_db)
        report["database"] = database
        report["tables_before"] = before
        report["runtime"] = {"python": sys.version.split()[0],
                             **{name: version(name) for name in ("uvicorn", "fastapi", "pydantic", "psycopg", "httpx")}}
        report["harness_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        check(len(before) == 17 and before["source_records"]["rows"] > 0, "seeded_17_table_inventory")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        port = listener.getsockname()[1]
        child_env = os.environ.copy()
        child_env.pop("MDM_ACTORS_JSON", None)
        child_env["MDM_ACTORS_JSON_FILE"] = str(credential_file)
        child_env["PYTHONUNBUFFERED"] = "1"
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--serve-fd", str(listener.fileno())],
                                   env=child_env, pass_fds=(listener.fileno(),),
                                   stdout=stdout_file, stderr=stderr_file)
        listener.close()
        listener = None
        ready_by = time.monotonic() + 8
        while b"Application startup complete." not in stderr_path.read_bytes():
            if process.poll() is not None or time.monotonic() >= ready_by:
                raise QualificationFailure("uvicorn_startup_failed_or_timed_out")
            time.sleep(0.02)
        check(process.poll() is None, "uvicorn_started")
        report["server"] = {"host": "127.0.0.1", "port": port, "access_log": False,
                            "default_body_limit_bytes": BODY_LIMIT}
        client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=4, trust_env=False)
        check(request("health", "GET", "/healthz") == {"status": "ok"}, "health.database_ready")
        console = request("console", "GET", "/")
        check('id="login"' in console and '/assets/app.js' in console, "console.assets_and_login")
        check(len(request("javascript", "GET", "/assets/app.js")) > 100, "javascript.nonempty")
        check(len(request("stylesheet", "GET", "/assets/style.css")) > 100, "stylesheet.nonempty")
        for i, path in enumerate(("/api/me", "/api/overview", "/api/openapi.json", f"/api/golden/{history_id}/history", "/metrics")):
            request(f"unauthenticated_{i}", "GET", path, 401)
        request("invalid_bearer", "GET", "/api/me", 401, authorization="Bearer unknown-qualification-token")
        request("invalid_scheme", "GET", "/api/me", 401, authorization="Basic unknown-qualification-token")
        for role in ROLES:
            identity = request(f"identity_{role}", "GET", f"/api/me?role=executor&probe={QUERY_MARKER}", role=role)
            check(identity == {"name": f"http.{role}", "role": role}, f"identity_{role}.server_assigned")
        overview = request("overview", "GET", "/api/overview", role="reader")
        snapshot, quality = overview["snapshot"], overview["quality"]
        check(snapshot["contract_version"] == "snapshot.v1", "overview.contract")
        check(len(snapshot["sources"]) == before["source_records"]["rows"], "overview.source_count")
        check(len(snapshot["crosswalk"]) == before["memberships"]["rows"], "overview.crosswalk_count")
        check(quality["crosswalk_coverage"] == 1 and quality["unconsumed_events"] == 0, "overview.coverage_and_delivery")
        crosswalk = {row["source_key"]: row["golden_id"] for row in snapshot["crosswalk"]}
        check({row["source_key"]: row["golden_id"] for row in snapshot["consumer_crosswalk"]} == crosswalk,
              "overview.consumer_mapping")
        history = request("history", "GET", f"/api/golden/{history_id}/history", role="reader")
        check(bool(history) and all(row["golden_id"] == history_id for row in history), "history.identity")
        check(any(row["known_to"] is not None for row in history), "history.retained_revisions")
        check(all(datetime.fromisoformat(row["known_from"]).tzinfo is not None for row in history), "history.aware_timestamps")
        check(all(set(row["attributes"]) <= set(row["provenance"]) for row in history), "history.attribute_provenance_keys")
        check(all("source_key" in row["provenance"][key] for row in history
                  for key, value in row["attributes"].items() if value not in (None, [])), "history.nonempty_value_lineage")
        schema = request("openapi", "GET", "/api/openapi.json", role="reader")
        check(schema["openapi"].startswith("3.1."), "openapi.version")
        for model in ("MergeInput", "SplitInput", "UnmergeInput", "VersionInput", "IngestInput", "SourceRecord"):
            check(schema["components"]["schemas"][model]["additionalProperties"] is False, "openapi.strict." + model)
        check(schema["paths"]["/api/ingest"]["post"]["security"] == [{"HTTPBearer": []}], "openapi.bearer")
        metrics = request("metrics", "GET", "/metrics", role="reader")
        check(f"mdm_sources {before['source_records']['rows']}\n" in metrics, "metrics.source_count")
        check("mdm_crosswalk_coverage 1.0\n" in metrics, "metrics.coverage")
        request("docs_disabled", "GET", "/docs", 404)
        request("unprotected_openapi_disabled", "GET", "/openapi.json", 404)
        request("invalid_history_identifier", "GET", "/api/golden/not-a-uuid/history", 422, role="reader")
        request("refused_ingestion", "POST", "/api/ingest", 403, role="reader", json={"records": []})
        request("refused_reconciliation", "POST", "/api/reconcile", 403, role="requester", json={})
        request("refused_consumption", "POST", "/api/consume", 403, role="approver", json={})
        groups = sorted(set(crosswalk.values()))[:2]
        versions = {row["golden_id"]: row["version"] for row in snapshot["groups"] if row["golden_id"] in groups}
        merge = {"group_ids": groups, "expected_versions": versions,
                 "reason": BODY_MARKER, "idempotency_key": "qualification-refused-" + str(uuid4())}
        request("refused_merge", "POST", "/api/decisions/merge", 403, role="reader", json=merge)
        missing = str(uuid4())
        request("refused_approval", "POST", f"/api/decisions/{missing}/approve", 403, role="requester", json={"expected_version": 1})
        request("refused_execution", "POST", f"/api/decisions/{missing}/execute", 403, role="approver", json={"expected_version": 1})
        request("missing_decision", "POST", f"/api/decisions/{missing}/approve", 404, role="approver", json={"expected_version": 1})
        errors = request("actor_injection", "POST", "/api/decisions/merge", 422, role="requester",
                         json={**merge, "actor": {"name": BODY_MARKER, "role": "executor"}})
        check(any(error["type"] == "extra_forbidden" for error in errors["detail"]), "actor_injection.rejected_extra")
        malformed = request("malformed_json", "POST", "/api/ingest", 422, role="executor",
                            content=b'{"records": [', headers={"Content-Type": "application/json"})
        check(malformed["detail"][0]["type"] == "json_invalid", "malformed_json.contract")
        bad_source = {**snapshot["sources"][0]["current_payload"], "valid_from": "2026-01-01T00:00:00"}
        invalid = request("naive_timestamp", "POST", "/api/ingest", 422, role="executor", json={"records": [bad_source]})
        check(any(error["loc"][-1] == "valid_from" for error in invalid["detail"]), "naive_timestamp.location")
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=4)
        began = time.monotonic()
        try:
            connection.putrequest("POST", "/api/ingest")
            for name, value in {"Content-Length": str(BODY_LIMIT + 1), "Connection": "close",
                                "Content-Type": "application/json", "X-Correlation-ID": HEADER_MARKER}.items():
                connection.putheader(name, value)
            connection.endheaders()
            response = connection.getresponse()
            oversized = capture("oversized_declared_length", "POST", "/api/ingest", response.status,
                                dict(response.getheaders()), response.read(), 413, time.monotonic() - began)
            check(oversized["detail"] == "request body exceeds configured byte limit", "declared_length.bounded")
        finally:
            connection.close()
        chunk = b"x" * 1_000_000
        oversized = request("oversized_chunked_body", "POST", "/api/ingest", 413, role="executor",
                            content=iter([chunk] * 10 + [b"x"]), headers={"Content-Type": "application/json"})
        check(oversized["detail"] == "request body exceeds configured byte limit", "chunked_body.bounded")
        client.close()
        client = None
        process.send_signal(signal.SIGTERM)
        return_code = process.wait(timeout=4)
        report["shutdown"] = {"signal": "SIGTERM", "returncode": return_code, "forced_kill": False}
        # Uvicorn restores and re-raises SIGTERM after finishing lifespan shutdown.
        check(return_code in (0, -signal.SIGTERM), "shutdown.expected_exit_semantics")
        logs = stderr_path.read_text()
        check("Application shutdown complete." in logs and "Finished server process" in logs, "shutdown.completed_lifespan")
        try:
            connection = socket.create_connection(("127.0.0.1", port), timeout=0.2)
        except OSError:
            closed = True
        else:
            connection.close()
            closed = False
        check(closed, "shutdown.listener_closed")
        after, after_database, _ = fingerprint(dsn, args.expect_db)
        report["tables_after"] = after
        check(database == after_database, "same_database_before_after")
        for table in TABLES:
            check(before[table] == after[table], "unchanged." + table)
        structured = [json.loads(line) for line in logs.splitlines() if line.startswith("{")]
        events = [item for item in structured if item.get("event") == "http.request"]
        counts = Counter(item.get("correlation_id") for item in events)
        check(len(events) == len(requests) and set(counts) == correlations and set(counts.values()) == {1},
              "logs.exact_request_correlation_coverage")
        for entry in requests:
            event = next(item for item in events if item["correlation_id"] == entry["correlation_id"])
            check(event["method"] == entry["method"] and event["status"] == entry["status"], "logs.request." + entry["label"])
        allowed = {"event", "trace_version", "correlation_id", "origin_correlation_id", "run_id", "method",
                   "route", "status", "duration_ms", "error_type", "operation", "decision_id", "event_id"}
        check(all(set(item) <= allowed and item["trace_version"] == "correlation.v1" for item in structured),
              "logs.allowlisted_fields")
        check(all(item.get("correlation_id") in correlations for item in structured), "logs.nested_operations_correlated")
        report["structured_log_events"] = len(structured)
        report["http_log_events"] = len(events)
        report["passed"] = True
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc) if isinstance(exc, QualificationFailure) else "Unexpected failure; inspect the recorded stage and sanitized logs"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_alarm)
        if client is not None:
            client.close()
        if listener is not None:
            listener.close()
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)
                report["shutdown"] = {"forced_kill": True, "returncode": process.returncode}
                report["passed"] = False
        stdout_file.close()
        stderr_file.close()
        for path in (stdout_path, stderr_path):
            raw = path.read_bytes()
            safe = all(value.encode() not in raw for value in forbidden if value)
            checks.append({"check": "logs.no_secrets_or_untrusted_data." + path.name, "passed": safe})
            if safe:
                (args.output / path.name).write_bytes(raw)
            else:
                report["passed"] = False
                report["error"] = "Server log contains a forbidden value; raw log withheld"
        temporary.cleanup()
        clean = not credential_file.exists() and not temp.exists()
        checks.append({"check": "temporary_credentials_removed", "passed": clean})
        report["passed"] = report["passed"] and clean
        report["request_count"] = len(requests)
        report["assertion_count"] = len(checks)
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        if report["elapsed_seconds"] > 60:
            report["passed"] = False
            report["error"] = "Execution exceeded the declared 60-second budget"
        output = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if any(token in output for token in tokens.values()):
            raise RuntimeError("Token detected in result; output refused")
        (args.output / "qualification.json").write_text(output)
    print(json.dumps({"passed": report["passed"], "request_count": report["request_count"],
                      "assertion_count": report["assertion_count"], "elapsed_seconds": report["elapsed_seconds"]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--serve-fd":
        serve(int(sys.argv[2]))
    else:
        raise SystemExit(main())
