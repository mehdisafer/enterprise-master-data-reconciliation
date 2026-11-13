"""Real PostgreSQL export contracts; no Snowflake connection is imitated here."""
from datetime import datetime, timezone
from uuid import UUID

import psycopg
import pytest

from mdm.demo import demonstrate
from mdm.snowflake import KEYS, TABLES, export_snapshot
from mdm.synthetic import demo_records

pytestmark = pytest.mark.integration


def exported(service, *, max_rows=100_000):
    # The application uses dict rows. The warehouse export intentionally uses a
    # dedicated connection with psycopg's default tuple rows.
    with psycopg.connect(service.db.dsn) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return export_snapshot(conn, max_rows=max_rows)


def test_demo_snapshot_preserves_uuid_time_roles_and_historical_provenance(service):
    report = demonstrate(service)
    snapshot = exported(service)
    assert set(snapshot.tables) == set(TABLES)
    assert len(snapshot.tables) == 16
    assert all(report["assertions"].values())
    assert snapshot.counts["source_records"] == len(demo_records())
    assert snapshot.counts["raw_records"] > snapshot.counts["source_records"]
    assert snapshot.counts["candidates"] > 0
    assert snapshot.counts["decision_events"] > 0
    assert snapshot.counts["run_sources"] == 3

    for table, rows in snapshot.tables.items():
        assert len({tuple(row[column] for column in KEYS[table]) for row in rows}) == len(rows)
        for row in rows:
            assert set(row) == set(TABLES[table])
            for column, kind in TABLES[table].items():
                value = row[column]
                if kind == "TIMESTAMP_TZ" and value is not None:
                    assert isinstance(value, str)
                    assert datetime.fromisoformat(value).utcoffset() is not None

    history = snapshot.tables["golden_history"]
    assert any(row["known_to"] is not None for row in history)
    assert any(row["valid_to"] is not None for row in history)
    assert any(row["attributes"].get("roles") == ["customer", "supplier"] for row in history)
    originals = snapshot.tables["raw_records"]
    for row in history:
        assert isinstance(row["golden_id"], str)
        assert str(UUID(row["golden_id"])) == row["golden_id"]
        assert str(UUID(row["history_id"])) == row["history_id"]
        for attribute, value in row["attributes"].items():
            provenance = row["provenance"][attribute]
            assert provenance["rule"] == "survivorship.v1"
            if value is None or value == []:
                continue
            source_key = provenance["source_key"]
            source_assertions = [original["payload"] for original in originals
                                 if original["source_key"] == source_key]
            assert source_assertions
            if attribute == "roles":
                for role in value:
                    contributor_keys = provenance["contributors"][role]
                    assert contributor_keys
                    assert all(any(original["source_key"] == key and
                                   role in original["payload"]["roles"]
                                   for original in originals) for key in contributor_keys)
            else:
                assert any(assertion.get(attribute) == value for assertion in source_assertions)
            assert datetime.fromisoformat(provenance["source_updated_at"]).utcoffset() is not None
            assert datetime.fromisoformat(provenance["valid_from"]).utcoffset() is not None

    corrected = report["stages"]["corrected"]
    expected = {row["source_key"]: str(row["golden_id"]) for row in corrected["crosswalk"]}
    actual = {row["source_key"]: row["golden_id"] for row in snapshot.tables["memberships"]}
    consumed = {row["source_key"]: row["golden_id"] for row in snapshot.tables["consumer_crosswalk"]
                if row["consumer"] == "reporting"}
    assert actual == expected == consumed
    assert exported(service).snapshot_id == snapshot.snapshot_id


def test_repeatable_read_export_keeps_one_generation_during_source_correction(service):
    record = next(record for record in demo_records() if record.source_id == "ORION-01")
    service.ingest([record])
    baseline = exported(service)
    with psycopg.connect(service.db.dsn) as reader:
        reader.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        # Acquire the MVCC snapshot before a separate writer commits a correction.
        assert reader.execute("SELECT count(*) FROM source_records").fetchone()[0] == 1
        changed = record.model_copy(update={
            "address": "Warehouse snapshot concurrent correction",
            "source_updated_at": datetime(2026, 10, 4, tzinfo=timezone.utc),
        })
        assert service.ingest([changed])["accepted"] == 1
        during = export_snapshot(reader)
        assert during.snapshot_id == baseline.snapshot_id
        assert during.tables["source_records"][0]["current_payload"]["address"] == record.address
    current = exported(service)
    assert current.snapshot_id != baseline.snapshot_id
    assert current.counts["raw_records"] == baseline.counts["raw_records"] + 1
    assert current.tables["source_records"][0]["revision"] == 2
    assert current.tables["source_records"][0]["current_payload"]["address"] == changed.address


def test_export_row_limit_fails_without_truncating_or_changing_the_authority(service):
    record = next(record for record in demo_records() if record.source_id == "ORION-01")
    service.ingest([record])
    before = exported(service)
    with pytest.raises(ValueError, match="exceeds configured row bound"):
        exported(service, max_rows=1)
    after = exported(service)
    assert after.snapshot_id == before.snapshot_id
    assert after.counts == before.counts
