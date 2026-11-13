"""Explainable matching, bounded candidate blocking and attribute survivorship.

This module never accepts executable rule expressions from metadata. Rules are
reviewed code and ``rules.v1.json`` records their fixed policy and version.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from itertools import combinations
from typing import Iterable, Literal

from mdm.domain import (
    NORMALIZATION_VERSION,
    RULE_VERSION,
    SURVIVORSHIP_VERSION,
    Evidence,
    SourceRecord,
)

Mode = Literal["deterministic", "hybrid"]
LEGAL_SUFFIXES = frozenset(
    {"sa", "sas", "sasu", "sarl", "ltd", "limited", "inc", "incorporated", "llc", "gmbh", "ag", "bv", "srl", "plc"}
)
NAME_STOPWORDS = frozenset({
    "industrial", "industries", "industry", "components", "manufacturing",
    "enterprises", "group", "international", "technology", "technologies",
    "services", "company", "corporation", "systems", "holdings", "holding",
    "equipment", "equipements", "engineering", "precision", "products",
})
MAX_BLOCK_SIZE = 1000
MAX_CANDIDATES = 1_000_000
REVIEW_THRESHOLD = 0.60
FUZZY_MIN_SIMILARITY = 0.86

_LEGAL_AUTHORITY = {"ERP_ALPHA": 300, "ERP_BETA": 200, "ERP_GAMMA": 100}
_ADDRESS_AUTHORITY = {"ERP_ALPHA": 200, "ERP_BETA": 300, "ERP_GAMMA": 100}
_CONTACT_AUTHORITY = {"ERP_ALPHA": 100, "ERP_BETA": 200, "ERP_GAMMA": 300}
AUTHORITY = {
    "name": _LEGAL_AUTHORITY,
    "country": _LEGAL_AUTHORITY,
    "registration_id": _LEGAL_AUTHORITY,
    "parent_source_key": _LEGAL_AUTHORITY,
    "address": _ADDRESS_AUTHORITY,
    "postal_code": _ADDRESS_AUTHORITY,
    "city": _ADDRESS_AUTHORITY,
    "email": _CONTACT_AUTHORITY,
    "phone": _CONTACT_AUTHORITY,
    "product_code": _LEGAL_AUTHORITY,
    "manufacturer": _LEGAL_AUTHORITY,
    "unit_of_measure": _LEGAL_AUTHORITY,
    "entity_type": _LEGAL_AUTHORITY,
}
ATTRIBUTES = tuple(AUTHORITY)


class CandidateLimitExceeded(ValueError):
    """The run must stop or be repartitioned; no candidate is silently discarded."""


def _text(value: str | None) -> str:
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]|_", " ", without_accents).split())


def _name(value: str) -> str:
    words = _text(value).split()
    for suffix in (("s", "a", "s", "u"), ("s", "a", "r", "l"), ("s", "a", "s"), ("s", "a")):
        if len(words) > len(suffix) and tuple(words[-len(suffix):]) == suffix:
            del words[-len(suffix):]
            break
    while len(words) > 1 and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words)


def normalize(record: SourceRecord) -> dict[str, str]:
    """Create a comparison projection without changing any original source value."""
    phone = re.sub(r"\D", "", record.phone or "")
    if phone.startswith("00"):
        phone = phone[2:]
    return {
        "key": record.key,
        "entity_type": record.entity_type,
        "name": _name(record.name),
        "country": (record.country or "").upper(),
        "registration_id": re.sub(r"[^\w]|_", "", (record.registration_id or "").upper()),
        "parent_source_key": record.parent_source_key or "",
        "address": _text(record.address),
        "postal_code": re.sub(r"\s", "", (record.postal_code or "").upper()),
        "city": _text(record.city),
        "email": (record.email or "").strip().casefold(),
        "phone": phone,
        # Manufacturer SKUs retain punctuation and leading zeroes.
        "product_code": (record.product_code or "").strip().upper(),
        "manufacturer": _name(record.manufacturer) if record.manufacturer else "",
        "unit_of_measure": (record.unit_of_measure or "").strip().upper(),
    }


def _unique(records: Iterable[SourceRecord]) -> list[SourceRecord]:
    records = list(records)
    keys = [record.key for record in records]
    if len(keys) != len(set(keys)):
        raise ValueError("matching needs one current source version per composite key")
    return records


def blocking_keys(record: SourceRecord) -> set[tuple[str, ...]]:
    """Union of exact identifier, name, contact, location and prefix blocks.

    Blocks have an identity-domain prefix. Roles never partition identity.
    Country is intentionally absent from name/contact blocks so an incomplete
    country does not silently lose a possible match. The comparator checks risk.
    """
    n = normalize(record)
    domain = record.entity_type
    keys: set[tuple[str, ...]] = set()
    if n["registration_id"]:
        keys.add((domain, "registration", n["registration_id"]))
    if n["product_code"]:
        keys.add((domain, "product_code", n["product_code"]))
    if n["name"]:
        keys.add((domain, "name", n["name"]))
        words = n["name"].split()
        # The two longest distinctive tokens tolerate a typo in either token.
        distinctive = sorted(
            set(words) - NAME_STOPWORDS, key=lambda token: (-len(token), token)
        )[:2]
        for token in distinctive:
            if len(token) >= 4:
                keys.add((domain, "name_prefix", token[:4]))
    for field in ("email", "phone"):
        if n[field]:
            keys.add((domain, field, n[field]))
    if n["address"] and n["postal_code"]:
        keys.add((domain, "address", n["postal_code"], n["address"]))
    if n["postal_code"] and n["name"]:
        keys.add((domain, "postal_name", n["postal_code"], n["name"][:3]))
    return keys


def generate_candidates(
    records: list[SourceRecord],
    *,
    max_block_size: int = MAX_BLOCK_SIZE,
    max_candidates: int = MAX_CANDIDATES,
) -> set[tuple[str, str]]:
    """Generate unique unordered pairs, with explicit resource limits.

    An oversized block aborts the run with its family and size, without logging
    source values. Same-source duplicates remain eligible. There is no top-K
    truncation, random sample or silent exhaustive fallback.
    """
    if max_block_size < 2 or max_candidates < 1:
        raise ValueError("candidate limits must allow at least one comparison")
    buckets: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for record in _unique(records):
        for block in blocking_keys(record):
            buckets[block].append(record.key)
    candidates: set[tuple[str, str]] = set()
    for block in sorted(buckets):
        members = sorted(buckets[block])
        if len(members) > max_block_size:
            raise CandidateLimitExceeded(
                f"block family {block[1]} has {len(members)} records; limit is {max_block_size}"
            )
        for pair in combinations(members, 2):
            candidates.add(pair)
            if len(candidates) > max_candidates:
                raise CandidateLimitExceeded(f"candidate count exceeds configured limit {max_candidates}")
    return candidates


def pair_conflicts(a: SourceRecord, b: SourceRecord) -> list[str]:
    """Hard contradictions cannot be overridden by similarity or human approval."""
    an, bn = normalize(a), normalize(b)
    conflicts: list[str] = []
    if a.entity_type != b.entity_type:
        conflicts.append("entity_type_mismatch")
    if a.parent_source_key == b.key or b.parent_source_key == a.key:
        conflicts.append("parent_child_identity")
    if (
        a.entity_type == b.entity_type == "organization"
        and a.source_system == b.source_system
        and a.source_updated_at == b.source_updated_at
        and an["name"] != bn["name"]
    ):
        conflicts.append("equal_authority_current_name_conflict")
    if an["registration_id"] and bn["registration_id"]:
        if an["registration_id"] != bn["registration_id"]:
            conflicts.append("registration_id_conflict")
        elif an["country"] and bn["country"] and an["country"] != bn["country"]:
            conflicts.append("registration_jurisdiction_conflict")
    if a.entity_type == b.entity_type == "product":
        for field in ("product_code", "manufacturer", "unit_of_measure"):
            if an[field] and bn[field] and an[field] != bn[field]:
                conflicts.append(f"{field}_conflict")
    return conflicts


def group_conflicts(records: list[SourceRecord]) -> list[str]:
    """Check every pair, including pairs not in the candidate graph.

    A-B and B-C evidence cannot overrule incompatible A-C endpoints. A parent
    reference is also checked against every source identity in the group.
    """
    members = sorted(_unique(records), key=lambda record: record.key)
    conflicts: list[str] = []
    for a, b in combinations(members, 2):
        for reason in pair_conflicts(a, b):
            conflicts.append(f"{reason}:{a.key}|{b.key}")
    return conflicts


def compare(a: SourceRecord, b: SourceRecord, mode: Mode = "hybrid") -> Evidence:
    """Produce bounded, interpretable evidence, not a calibrated probability.

    Only a jurisdiction-scoped registration identifier or a full product
    signature permits auto merge. Fuzzy names can propose review but never auto.
    """
    if mode not in ("deterministic", "hybrid"):
        raise ValueError("unknown matching mode")
    if a.key == b.key:
        raise ValueError("a source identity cannot be compared with itself")
    if a.key > b.key:
        a, b = b, a
    an, bn = normalize(a), normalize(b)
    conflicts = pair_conflicts(a, b)
    contributions: dict[str, float] = {}
    reasons: list[str] = []
    def exact(field: str) -> bool:
        return bool(an[field] and bn[field] and an[field] == bn[field])

    same_registration = exact("registration_id")
    authoritative_registration = (
        a.entity_type == b.entity_type == "organization"
        and same_registration and exact("country")
    )
    authoritative_product = (
        a.entity_type == b.entity_type == "product"
        and exact("product_code") and exact("manufacturer") and exact("unit_of_measure")
    )
    if same_registration and a.entity_type == b.entity_type == "organization":
        contributions["registration_exact"] = 0.98 if authoritative_registration else 0.65
    if authoritative_product:
        contributions["manufacturer_product_unit_exact"] = 0.98
    if not authoritative_registration and not authoritative_product:
        if exact("name"):
            contributions["name_exact"] = 0.45
        elif mode == "hybrid" and an["name"] and bn["name"]:
            # SequenceMatcher's ratio can depend on argument order. Use the
            # lower direction so renaming source keys cannot improve evidence.
            similarity = min(
                SequenceMatcher(None, an["name"], bn["name"], autojunk=False).ratio(),
                SequenceMatcher(None, bn["name"], an["name"], autojunk=False).ratio(),
            )
            if similarity >= FUZZY_MIN_SIMILARITY:
                contributions["name_fuzzy"] = round(0.45 * similarity, 6)
                reasons.append(f"normalized_name_similarity={similarity:.6f}")
        if exact("address") and exact("postal_code"):
            contributions["address_postal_exact"] = 0.25
        if exact("email"):
            contributions["email_exact"] = 0.15
        if exact("phone"):
            contributions["phone_exact"] = 0.15
        if a.entity_type == b.entity_type == "product" and exact("product_code"):
            contributions["product_code_exact"] = 0.45
    score = round(min(1.0, sum(contributions.values())), 6)
    if conflicts:
        decision = "reject"
        reasons.append("hard_conflict_blocks_merge_regardless_of_score")
    elif authoritative_registration or authoritative_product:
        decision = "auto"
        reasons.append("complete_authoritative_identifier")
    elif score >= REVIEW_THRESHOLD:
        decision = "review"
        reasons.append("supporting_evidence_requires_human_identity_decision")
    else:
        decision = "reject"
        reasons.append("insufficient_evidence")
    return Evidence(
        left_key=a.key, right_key=b.key, score=score, contributions=contributions,
        conflicts=conflicts, decision=decision, rule_version=RULE_VERSION,
        normalization_version=NORMALIZATION_VERSION, reasons=reasons, mode=mode,
    )


def survive(records: list[SourceRecord]) -> tuple[dict, dict, list[str]]:
    """Select each value by authority, then freshness, then completeness.

    Empty values cannot displace a known value. Ties use stable source keys.
    At equal authority and freshness, disagreement is exposed, never hidden.
    Hard-conflicting groups cannot produce a golden record.
    """
    records = _unique(records)
    if not records:
        raise ValueError("cannot consolidate an empty identity group")
    hard_conflicts = group_conflicts(records)
    if hard_conflicts:
        raise ValueError("cannot consolidate an incompatible identity group: " + "; ".join(hard_conflicts))
    attrs: dict = {}
    provenance: dict = {}
    conflicts: list[str] = []
    for attr in ATTRIBUTES:
        candidates = [
            r for r in records
            if getattr(r, attr) is not None and str(getattr(r, attr)).strip()
        ]
        if not candidates:
            attrs[attr] = None
            provenance[attr] = {
                "source_key": None, "source_updated_at": None, "valid_from": None,
                "rule": SURVIVORSHIP_VERSION, "reason": "no_source_asserts_a_value",
                "authority": None,
            }
            continue
        authority = AUTHORITY[attr]
        # Longest known string is only a final completeness tiebreaker; it never
        # overrules authority or source freshness. Lexical keys settle equal ranks.
        candidates.sort(key=lambda r: (
            -authority[r.source_system], -r.source_updated_at.timestamp(),
            -len(str(getattr(r, attr))), r.key,
        ))
        winner = candidates[0]
        attrs[attr] = getattr(winner, attr)
        provenance[attr] = {
            "source_key": winner.key,
            "source_updated_at": winner.source_updated_at.isoformat(),
            "valid_from": winner.valid_from.isoformat(),
            "rule": SURVIVORSHIP_VERSION,
            "reason": "nonempty_then_authority_then_freshness_then_completeness_then_source_key",
            "authority": authority[winner.source_system],
            "alternatives": [
                {"source_key": r.key, "value": getattr(r, attr), "authority": authority[r.source_system]}
                for r in candidates[1:] if getattr(r, attr) != getattr(winner, attr)
            ],
        }
        normalized_values = {
            normalize(r).get(attr, str(getattr(r, attr))) for r in candidates
        }
        if len(normalized_values) > 1:
            conflicts.append(f"attribute_disagreement:{attr}")
    roles = sorted({role for record in records for role in record.roles})
    attrs["roles"] = roles
    contributors = sorted((r for r in records if r.roles), key=lambda r: r.key)
    anchor = contributors[0] if contributors else None
    provenance["roles"] = {
        "source_key": anchor.key if anchor else None,
        "source_updated_at": anchor.source_updated_at.isoformat() if anchor else None,
        "valid_from": anchor.valid_from.isoformat() if anchor else None,
        "rule": SURVIVORSHIP_VERSION,
        "reason": "union_of_business_roles_does_not_create_a_new_legal_identity",
        "contributors": {
            role: [r.key for r in contributors if role in r.roles] for role in roles
        },
    }
    return attrs, provenance, conflicts


def evaluate(
    records: list[SourceRecord],
    identity_by_key: dict[str, str],
    *,
    mode: Mode = "hybrid",
    groups: list[list[str]] | None = None,
    max_exhaustive_records: int = 1000,
) -> dict:
    """Compare blocking and decisions with exhaustive labeled pairs.

    ``suggestion`` treats auto + review as retrieved evidence, not approved
    identities. ``auto`` measures only autonomous decisions. Empty denominators
    return null so an empty output cannot claim perfect precision or recall.
    """
    records = _unique(records)
    if max_exhaustive_records < 1 or len(records) > max_exhaustive_records:
        raise ValueError("exhaustive evaluation is restricted to the bounded control corpus")
    by_key = {r.key: r for r in records}
    if set(by_key) != set(identity_by_key):
        raise ValueError("truth labels must cover exactly the evaluated source identities")
    candidates = generate_candidates(records)
    all_pairs = set(combinations(sorted(by_key), 2))
    positives = {p for p in all_pairs if identity_by_key[p[0]] == identity_by_key[p[1]]}
    evidence = [compare(by_key[a], by_key[b], mode=mode) for a, b in sorted(candidates)]
    automatic = {(e.left_key, e.right_key) for e in evidence if e.decision == "auto"}
    suggested = {(e.left_key, e.right_key) for e in evidence if e.decision in {"auto", "review"}}
    review = {(e.left_key, e.right_key) for e in evidence if e.decision == "review"}

    def metrics(predicted: set[tuple[str, str]]) -> dict:
        tp, fp, fn = len(predicted & positives), len(predicted - positives), len(positives - predicted)
        return {
            "true_positives": tp, "false_positives": fp, "false_negatives": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
        }

    result = {
        "mode": mode, "rule_version": RULE_VERSION,
        "records": len(records), "exhaustive_pairs": len(all_pairs),
        "candidate_pairs": len(candidates), "truth_positive_pairs": len(positives),
        "candidate_recall": len(candidates & positives) / len(positives) if positives else None,
        "candidate_missed_pairs": [list(p) for p in sorted(positives - candidates)],
        "comparison_reduction": 1 - len(candidates) / len(all_pairs) if all_pairs else None,
        "auto": metrics(automatic), "suggestion": metrics(suggested),
        "review_pairs": len(review), "review_false_positives": len(review - positives),
        "review_share_of_candidates": len(review) / len(candidates) if candidates else None,
    }
    if groups is not None:
        flattened = [key for group in groups for key in group]
        if len(flattened) != len(set(flattened)) or set(flattened) != set(by_key):
            raise ValueError("evaluated groups must partition all source identities exactly once")
        if any(not group for group in groups):
            raise ValueError("identity groups must be nonempty")
        grouped_pairs = set().union(*(set(combinations(sorted(group), 2)) for group in groups))
        result["groups"] = {
            **metrics(grouped_pairs), "count": len(groups),
            "impure_groups": sum(len({identity_by_key[key] for key in group}) > 1 for group in groups),
            "hard_conflicting_groups": sum(bool(group_conflicts([by_key[key] for key in group])) for group in groups),
        }
    return result

