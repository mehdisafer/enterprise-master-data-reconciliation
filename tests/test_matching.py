"""Behavioral checks for the source, matching and survivorship contracts."""

from __future__ import annotations

import json
import unittest
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from mdm.domain import SourceRecord
from mdm.matching import (
    CandidateLimitExceeded,
    compare,
    evaluate,
    generate_candidates,
    group_conflicts,
    normalize,
    survive,
)
from mdm.synthetic import demo_records, late_record, scale_records, truth


def changed(record: SourceRecord, **values) -> SourceRecord:
    return SourceRecord.model_validate({**record.model_dump(mode="json"), **values})


class SourceContractTests(unittest.TestCase):
    def setUp(self):
        self.record = demo_records()[0]

    def test_unknown_fields_are_rejected_instead_of_silently_discarded(self):
        with self.assertRaises(ValidationError):
            changed(self.record, customer_secret="must not be accepted")

    def test_composite_keys_cannot_collide_through_delimiters(self):
        for value in ("ERP_BETA:organization:x", "x/y", "x;DROP TABLE raw", "", "x" * 101):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                changed(self.record, source_id=value)

    def test_timestamps_require_a_timezone(self):
        with self.assertRaises(ValidationError):
            changed(self.record, valid_from="2026-01-01T00:00:00")
        with self.assertRaises(ValidationError):
            changed(self.record, source_updated_at=datetime(2026, 1, 1))

    def test_source_systems_and_entity_types_are_closed_enumerations(self):
        for values in ({"source_system": "UNKNOWN"}, {"entity_type": "customer"}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                changed(self.record, **values)

    def test_role_can_be_customer_and_supplier_on_one_identity(self):
        record = changed(self.record, roles=["customer", "supplier"])
        self.assertEqual(record.entity_type, "organization")
        self.assertEqual(record.roles, ("customer", "supplier"))
        with self.assertRaises(ValidationError):
            changed(self.record, roles=["customer", "customer"])

    def test_self_parent_and_nonorganization_parent_are_rejected(self):
        for key in (self.record.key, "ERP_ALPHA:product:P01", "unsafe parent"):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                changed(self.record, parent_source_key=key)

    def test_product_and_organization_contracts_do_not_interchange(self):
        with self.assertRaises(ValidationError):
            changed(self.record, product_code="P01")
        with self.assertRaises(ValidationError):
            changed(self.record, entity_type="product")

    def test_whitespace_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            changed(self.record, name="   ")

    def test_source_assertions_are_immutable(self):
        with self.assertRaises(ValidationError):
            self.record.name = "Changed"  # type: ignore[misc]

    def test_comparison_projection_preserves_source_spelling_and_accents(self):
        record = changed(self.record, name="  Northstar Équipements SAS  ", country="fr", address="  18 Rue des Ateliers  ")
        original = record.model_dump(mode="json")
        normalized = normalize(record)
        self.assertEqual(normalized["name"], "northstar equipements")
        self.assertEqual(normalized["country"], "FR")
        self.assertEqual(record.model_dump(mode="json"), original)

    def test_identifier_normalization_preserves_zeroes_and_product_punctuation(self):
        normalized = normalize(changed(self.record, registration_id="FR-001.020"))
        self.assertEqual(normalized["registration_id"], "FR001020")
        products = [r for r in demo_records() if r.entity_type == "product"]
        a = changed(products[0], product_code=" AB-C-001 ")
        b = changed(products[1], product_code="A-BC-001")
        self.assertEqual(normalize(a)["product_code"], "AB-C-001")
        self.assertNotEqual(normalize(a)["product_code"], normalize(b)["product_code"])


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.records = demo_records()
        self.by_key = {record.key: record for record in self.records}
        self.truth = truth()

    def scenario(self, name):
        return [self.by_key[key] for key in self.truth["scenarios"][name]]

    def test_legal_identifier_matches_across_all_three_erps(self):
        a, b, c = self.scenario("automatic_duplicate")
        self.assertEqual({normalize(r)["name"] for r in (a, b, c)}, {"northstar equipements"})
        self.assertEqual(compare(a, b).decision, "auto")
        self.assertEqual(compare(b, c).decision, "auto")
        self.assertEqual(group_conflicts([a, b, c]), [])

    def test_conflicting_registration_blocks_a_high_similarity_pair(self):
        a, _, c = self.scenario("transitive_bridge")
        evidence = compare(a, c)
        self.assertGreaterEqual(evidence.score, 0.60)
        self.assertEqual(evidence.decision, "reject")
        self.assertIn("registration_id_conflict", evidence.conflicts)

    def test_same_identifier_in_two_jurisdictions_is_not_one_legal_entity(self):
        a, b, _ = self.scenario("automatic_duplicate")
        evidence = compare(a, changed(b, country="DE"))
        self.assertEqual(evidence.decision, "reject")
        self.assertIn("registration_jurisdiction_conflict", evidence.conflicts)

    def test_same_authority_same_time_conflicting_names_block_a_merge(self):
        a = self.by_key["ERP_BETA:organization:CYPRESS-01"]
        b = changed(a, source_id="OTHER", name="Completely Distinct Legal Entity")
        evidence = compare(a, b)
        self.assertEqual(evidence.decision, "reject")
        self.assertIn("equal_authority_current_name_conflict", evidence.conflicts)

    def test_parent_child_cannot_be_merged_even_with_missing_identifiers(self):
        parent = self.by_key["ERP_ALPHA:organization:ASTERIA-HOLDING"]
        child = self.by_key["ERP_BETA:organization:ASTERIA-PLANT"]
        evidence = compare(changed(parent, registration_id=None), changed(child, registration_id=None))
        self.assertEqual(evidence.decision, "reject")
        self.assertIn("parent_child_identity", evidence.conflicts)

    def test_establishment_is_not_the_legal_organization(self):
        parent = self.by_key["ERP_ALPHA:organization:ASTERIA-HOLDING"]
        site = self.by_key["ERP_GAMMA:establishment:ASTERIA-SITE"]
        evidence = compare(parent, site)
        self.assertEqual(evidence.decision, "reject")
        self.assertIn("entity_type_mismatch", evidence.conflicts)

    def test_two_establishments_do_not_match_on_a_shared_parent_registration(self):
        a = self.by_key["ERP_BETA:establishment:NOVA-LYON"]
        b = self.by_key["ERP_GAMMA:establishment:NOVA-NANTES"]
        evidence = compare(a, b)
        self.assertEqual(evidence.decision, "reject")
        self.assertNotIn("registration_exact", evidence.contributions)

    def test_product_unit_and_manufacturer_conflicts_are_strong(self):
        each = self.by_key["ERP_ALPHA:product:BOLT-M8"]
        box = self.by_key["ERP_GAMMA:product:BOLT-M8-BOX"]
        self.assertIn("unit_of_measure_conflict", compare(each, box).conflicts)
        ficta = self.by_key["ERP_ALPHA:product:THERMAL-S12"]
        altair = self.by_key["ERP_GAMMA:product:THERMAL-ALT"]
        self.assertIn("manufacturer_conflict", compare(ficta, altair).conflicts)

    def test_complete_product_signature_can_match_descriptions_in_different_languages(self):
        a = self.by_key["ERP_ALPHA:product:BOLT-M8"]
        b = self.by_key["ERP_BETA:product:B-008"]
        self.assertEqual(compare(a, b).decision, "auto")

    def test_transitive_connectivity_cannot_create_an_incompatible_group(self):
        a, b, c = self.scenario("transitive_bridge")
        self.assertEqual(compare(a, b).decision, "review")
        self.assertEqual(compare(b, c).decision, "review")
        self.assertEqual(group_conflicts([a, b]), [])
        self.assertEqual(group_conflicts([b, c]), [])
        self.assertTrue(group_conflicts([a, b, c]))
        with self.assertRaises(ValueError):
            survive([a, b, c])

    def test_group_checks_include_pairs_that_blocking_did_not_generate(self):
        a, b, c = self.scenario("transitive_bridge")
        a = changed(a, name="Quartz", address=None, postal_code=None, phone="1111")
        b = changed(b, name="Bridge", address=None, postal_code=None, phone="1111", email="bridge@example.invalid")
        c = changed(c, name="Zircon", address=None, postal_code=None, phone=None, email="bridge@example.invalid")
        pairs = generate_candidates([a, b, c])
        self.assertNotIn(tuple(sorted((a.key, c.key))), pairs)
        self.assertTrue(group_conflicts([a, b, c]))

    def test_ambiguous_same_name_same_address_requires_human_review(self):
        a, b = self.scenario("mistaken_merge_then_split")
        evidence = compare(a, b)
        self.assertEqual(evidence.decision, "review")
        self.assertEqual(evidence.conflicts, [])
        self.assertNotEqual(self.truth["identity_by_key"][a.key], self.truth["identity_by_key"][b.key])

    def test_fuzzy_name_is_review_only_and_adds_recall(self):
        a, b = self.scenario("manual_positive")
        self.assertEqual(compare(a, b, mode="deterministic").decision, "reject")
        hybrid = compare(a, b, mode="hybrid")
        self.assertEqual(hybrid.decision, "review")
        self.assertIn("name_fuzzy", hybrid.contributions)

    def test_comparison_is_order_independent(self):
        for first, second in list(generate_candidates(self.records)):
            a, b = self.by_key[first], self.by_key[second]
            self.assertEqual(compare(a, b).model_dump(), compare(b, a).model_dump())

    def test_same_source_duplicates_are_candidates(self):
        keys = ("ERP_BETA:organization:CYPRESS-01", "ERP_BETA:organization:CYPRESS-02")
        self.assertIn(keys, generate_candidates(self.records))
        self.assertEqual(compare(*(self.by_key[key] for key in keys)).decision, "auto")

    def test_duplicate_current_versions_are_rejected_before_scoring(self):
        record = self.records[0]
        for call in (generate_candidates, survive, group_conflicts):
            with self.subTest(call=call.__name__), self.assertRaises(ValueError):
                call([record, record])
        with self.assertRaises(ValueError):
            compare(record, record)

    def test_candidate_limits_stop_instead_of_hiding_candidates(self):
        records = self.scenario("automatic_duplicate")
        with self.assertRaises(CandidateLimitExceeded):
            generate_candidates(records, max_block_size=2)
        with self.assertRaises(CandidateLimitExceeded):
            generate_candidates(records, max_candidates=1)

    def test_matching_mode_is_not_an_executable_expression(self):
        with self.assertRaises(ValueError):
            compare(self.records[0], self.records[1], mode="exec('unsafe')")

    def test_candidate_recall_and_review_gain_are_measured_on_each_split(self):
        for split, spec in self.truth["splits"].items():
            with self.subTest(split=split):
                records = [r for r in self.records if r.key in spec["identity_by_key"]]
                deterministic = evaluate(records, spec["identity_by_key"], mode="deterministic")
                hybrid = evaluate(records, spec["identity_by_key"], mode="hybrid")
                self.assertEqual(hybrid["candidate_recall"], 1.0)
                self.assertEqual(hybrid["auto"]["false_positives"], 0)
                self.assertGreater(hybrid["suggestion"]["recall"], deterministic["suggestion"]["recall"])
                self.assertEqual(hybrid["suggestion"]["false_positives"], deterministic["suggestion"]["false_positives"])
                self.assertLess(hybrid["candidate_pairs"], hybrid["exhaustive_pairs"])

    def test_empty_metrics_do_not_claim_perfect_accuracy(self):
        record = self.records[0]
        metrics = evaluate([record], {record.key: "one"})
        self.assertIsNone(metrics["candidate_recall"])
        self.assertIsNone(metrics["auto"]["precision"])
        self.assertIsNone(metrics["auto"]["recall"])

    def test_exhaustive_evaluation_is_limited_to_a_control_corpus(self):
        with self.assertRaises(ValueError):
            evaluate(self.records, self.truth["identity_by_key"], max_exhaustive_records=10)

    def test_group_quality_detects_a_mistaken_merge_even_without_hard_conflicts(self):
        a, b = self.scenario("mistaken_merge_then_split")
        labels = {key: self.truth["identity_by_key"][key] for key in (a.key, b.key)}
        result = evaluate([a, b], labels, groups=[[a.key, b.key]])
        self.assertEqual(result["groups"]["impure_groups"], 1)
        self.assertEqual(result["groups"]["hard_conflicting_groups"], 0)
        self.assertEqual(result["groups"]["false_positives"], 1)
        with self.assertRaises(ValueError):
            evaluate([a, b], labels, groups=[[a.key], [a.key]])


class SurvivorshipAndFixtureTests(unittest.TestCase):
    def setUp(self):
        self.records = demo_records()
        self.by_key = {record.key: record for record in self.records}
        self.truth = truth()

    def test_late_less_authoritative_name_does_not_replace_legal_name(self):
        keys = self.truth["scenarios"]["automatic_duplicate"]
        records = [late_record() if key == late_record().key else self.by_key[key] for key in keys]
        attrs, provenance, conflicts = survive(records)
        self.assertEqual(attrs["name"], "Northstar Équipements SAS")
        self.assertEqual(provenance["name"]["source_key"], "ERP_ALPHA:organization:NORTHSTAR-01")
        self.assertEqual(attrs["address"], "22 Rue des Ateliers")
        self.assertEqual(provenance["address"]["source_key"], "ERP_BETA:organization:NS-44")
        self.assertIn("attribute_disagreement:name", conflicts)
        self.assertTrue(provenance["name"]["alternatives"])

    def test_survivorship_is_order_independent_and_each_value_has_provenance(self):
        records = [self.by_key[key] for key in self.truth["scenarios"]["automatic_duplicate"]]
        original = survive(records)
        self.assertEqual(original, survive(list(reversed(records))))
        attrs, provenance, _ = original
        self.assertEqual(set(attrs), set(provenance))
        for attribute, value in attrs.items():
            proof = provenance[attribute]
            self.assertIn("rule", proof)
            self.assertIn("reason", proof)
            if value is not None:
                self.assertIn(proof["source_key"], {r.key for r in records})

    def test_role_union_keeps_all_contributing_sources(self):
        records = [self.by_key[key] for key in self.truth["scenarios"]["automatic_duplicate"]]
        attrs, provenance, _ = survive(records)
        self.assertEqual(attrs["roles"], ["customer", "supplier"])
        self.assertEqual(len(provenance["roles"]["contributors"]["supplier"]), 2)
        self.assertEqual(len(provenance["roles"]["contributors"]["customer"]), 2)

    def test_missing_high_authority_value_does_not_erase_a_known_value(self):
        keys = self.truth["scenarios"]["automatic_duplicate"]
        records = [self.by_key[key] for key in keys]
        records = [changed(r, address="   ") if r.source_system == "ERP_BETA" else r for r in records]
        attrs, provenance, _ = survive(records)
        self.assertEqual(attrs["address"], "18 Rue des Ateliers")
        self.assertEqual(provenance["address"]["source_key"], keys[0])

    def test_freshness_breaks_equal_source_authority_without_erasing_alternatives(self):
        original = self.by_key["ERP_BETA:organization:CYPRESS-01"]
        newer = changed(original, source_id="CYPRESS-LATEST", name="Cypress Hydraulics Renamed", source_updated_at="2026-02-01T00:00:00Z")
        attrs, provenance, conflicts = survive([original, newer])
        self.assertEqual(attrs["name"], "Cypress Hydraulics Renamed")
        self.assertEqual(provenance["name"]["source_key"], newer.key)
        self.assertIn("attribute_disagreement:name", conflicts)

    def test_business_validity_and_source_change_timestamps_remain_distinct(self):
        record = late_record()
        self.assertLess(record.valid_from, record.source_updated_at)
        attrs, provenance, _ = survive([record])
        self.assertEqual(attrs["address"], "22 Rue des Ateliers")
        self.assertNotEqual(provenance["address"]["valid_from"], provenance["address"]["source_updated_at"])

    def test_heldout_and_development_split_by_entity_identity(self):
        development = self.truth["splits"]["development"]["identity_by_key"]
        heldout = self.truth["splits"]["heldout"]["identity_by_key"]
        self.assertFalse(set(development) & set(heldout))
        self.assertFalse(set(development.values()) & set(heldout.values()))
        self.assertEqual(set(development) | set(heldout), set(self.by_key))

    def test_versioned_fixture_files_match_the_generated_contract_corpus(self):
        root = Path(__file__).resolve().parents[1]
        from_files = []
        for path in sorted((root / "data/fixtures/v1").glob("erp_*.json")):
            from_files.extend(SourceRecord.model_validate(row) for row in json.loads(path.read_text()))
        self.assertEqual({r.key: r for r in from_files}, self.by_key)
        self.assertEqual(json.loads((root / "data/truth/v1/identity_truth.json").read_text()), self.truth)
        saved_late = SourceRecord.model_validate(json.loads((root / "data/fixtures/v1/late_correction.json").read_text()))
        self.assertEqual(saved_late, late_record())

    def test_scale_corpus_is_repeatable_and_keeps_candidate_recall(self):
        records, labels = scale_records(25, seed=7)
        again, same_labels = scale_records(25, seed=7)
        self.assertEqual(records, again)
        self.assertEqual(labels, same_labels)
        self.assertEqual(len(records), 75)
        result = evaluate(records, labels)
        self.assertEqual(result["candidate_recall"], 1.0)
        self.assertEqual(result["auto"]["precision"], 1.0)
        self.assertEqual(result["auto"]["recall"], 1.0)
        self.assertLess(result["candidate_pairs"], result["exhaustive_pairs"] / 10)


if __name__ == "__main__":
    unittest.main()

