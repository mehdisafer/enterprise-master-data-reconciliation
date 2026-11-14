"""Offline boundary/transaction unit tests. These do not qualify Snowflake."""

import copy
import json
import sys
from types import ModuleType
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from mdm.snowflake import (
    TABLES, Snapshot, SnowflakeConfig, SnowflakePublisher, canonical, connect, identifier, validate_snapshot,
)


@pytest.fixture
def config():
    return SnowflakeConfig("testorg-testaccount", "mdm_loader", "mdm_demo", "mdm_raw", "mdm_demo_xs", "mdm_loader", "/run/secrets/test-key")


@pytest.fixture
def snapshot():
    timestamp = "2026-01-01T00:00:00+00:00"
    tables = {table: [] for table in TABLES}
    tables["source_records"] = [{
        "source_key": "ERP_ALPHA:organization:1", "source_system": "ERP_ALPHA",
        "entity_type": "organization", "source_id": "1", "current_payload": {"name": "A"},
        "revision": 1, "ingested_at": timestamp,
    }]
    tables["identity_groups"] = [{"golden_id": "golden1", "entity_type": "organization", "status": "active", "version": 1, "created_at": timestamp}]
    tables["memberships"] = [{"source_key": "ERP_ALPHA:organization:1", "golden_id": "golden1"}]
    tables["golden_history"] = [{
        "history_id": "history1", "golden_id": "golden1", "group_version": 1,
        "attributes": {"name": "A' ; DROP TABLE x; --"},
        "provenance": {"name": {"source_key": "ERP_ALPHA:organization:1", "rule": "v1"}},
        "conflicts": [], "valid_from": timestamp, "valid_to": None,
        "known_from": timestamp, "known_to": None,
    }]
    return Snapshot(timestamp, tables)


@pytest.mark.parametrize("value", ['x.y', 'x;DROP TABLE y', 'x"', "x'", '', 'x--', 'x' * 64])
def test_rejects_untrusted_object_names(value):
    with pytest.raises(ValueError, match="simple identifiers"):
        identifier(value)


def test_contract_checks_relationships_provenance_and_duplicates(snapshot):
    validate_snapshot(snapshot)
    for table, mutate in [
        ("memberships", lambda rows: rows[0].update(golden_id="unknown")),
        ("golden_history", lambda rows: rows[0].update(provenance={})),
        ("source_records", lambda rows: rows.append(copy.deepcopy(rows[0]))),
        ("identity_groups", lambda rows: rows[0].update(status="retired")),
    ]:
        changed = copy.deepcopy(snapshot)
        mutate(changed.tables[table])
        with pytest.raises(ValueError):
            validate_snapshot(changed)


def test_snapshot_replay_id_excludes_capture_time_but_includes_payload(snapshot):
    later = replace(snapshot, captured_at="2026-02-01T00:00:00+00:00")
    assert later.snapshot_id == snapshot.snapshot_id
    changed = copy.deepcopy(snapshot)
    changed.tables["golden_history"][0]["attributes"]["name"] = "Changed"
    assert changed.snapshot_id != snapshot.snapshot_id


def test_timezone_and_unknown_columns_fail_closed(snapshot):
    with pytest.raises(ValueError, match="timezone"):
        canonical(datetime(2026, 1, 1))
    assert "2026-01-01" in canonical(datetime(2026, 1, 1, tzinfo=timezone.utc))
    snapshot.tables["source_records"][0]["sql"] = "DROP TABLE source_records"
    with pytest.raises(ValueError, match="Unexpected columns"):
        validate_snapshot(snapshot)


class CursorDouble:
    """A recording driver double; never presented as a database integration."""

    def __init__(self, connection):
        self.connection = connection
        self.sfqid = "offline-test-id"
        self.rowcount = 1
        self.answer = None

    def execute(self, sql, params=None):
        self.connection.calls.append((sql, params))
        if sql.startswith("INSERT INTO") and "_MDM_SNAPSHOT_DATA" in sql:
            self.connection.loaded.append((params[1], params[2], params[3]))
        if "SELECT count(*)" in sql and "_MDM_SNAPSHOT_MANIFEST" in sql:
            self.answer = self.connection.manifest_count
        elif sql.startswith("SELECT snapshot_id"):
            self.answer = self.connection.active
        elif "SELECT count(*)" in sql and "GROUP BY" in sql:
            self.answer = 0
        elif "SELECT count(*)" in sql and "table_name = %s" in sql:
            self.answer = self.connection.counts[params[1]]
        return self

    def fetchone(self):
        return (self.answer,)

    def fetchall(self):
        return self.connection.loaded

    def close(self):
        pass


class RecordingConnection:
    def __init__(self, counts, *, manifest_count=0, active=None):
        self.counts = counts
        self.calls = []
        self.commits = 0
        self.rollbacks = 0
        self.manifest_count = manifest_count
        self.active = active
        self.loaded = []

    def cursor(self):
        return CursorDouble(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_publish_binds_values_and_commits_after_pointer(config, snapshot):
    driver = RecordingConnection(snapshot.counts)
    publisher = SnowflakePublisher(driver, config)
    result = publisher.publish(snapshot)
    assert result["status"] == "published"
    assert driver.commits == 1 and driver.rollbacks == 0
    hostile_name = snapshot.tables["golden_history"][0]["attributes"]["name"]
    assert all(hostile_name not in sql for sql, _ in driver.calls)
    loaded = [params for sql, params in driver.calls if sql.startswith("INSERT INTO") and "_MDM_SNAPSHOT_DATA" in sql]
    assert any(hostile_name in json.loads(params[3]).get("attributes", {}).values() for params in loaded)
    assert driver.calls[-1][0].startswith("UPDATE MDM_DEMO.MDM_RAW._MDM_ACTIVE_SNAPSHOT")


def test_injected_crash_rolls_back_data_and_publication(config, snapshot):
    driver = RecordingConnection(snapshot.counts)
    with pytest.raises(RuntimeError, match="Injected failure"):
        SnowflakePublisher(driver, config).publish(snapshot, fail_before_commit=True)
    assert driver.rollbacks == 1 and driver.commits == 0


def test_uncertain_commit_retry_reconciles_and_refuses_historical_rewind(config, snapshot):
    driver = RecordingConnection(snapshot.counts, manifest_count=1, active=snapshot.snapshot_id)
    result = SnowflakePublisher(driver, config).publish(snapshot)
    assert result["status"] == "already_published"
    assert not any(sql.startswith(("INSERT", "UPDATE")) for sql, _ in driver.calls)
    driver.active = "newer-generation"
    with pytest.raises(ValueError, match="refusing to rewind"):
        SnowflakePublisher(driver, config).publish(snapshot)


def test_cloud_bound_and_count_mismatch_abort_before_commit(config, snapshot):
    driver = RecordingConnection(snapshot.counts)
    with pytest.raises(ValueError, match="row bound"):
        SnowflakePublisher(driver, replace(config, max_rows=1)).publish(snapshot)
    assert not driver.calls
    driver.counts = {**snapshot.counts, "source_records": 0}
    with pytest.raises(ValueError, match="row-count mismatch"):
        SnowflakePublisher(driver, config).publish(snapshot)
    assert driver.rollbacks == 1 and driver.commits == 0


def test_missing_authorization_configuration_does_not_connect(monkeypatch):
    for name in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_ROLE", "SNOWFLAKE_PRIVATE_KEY_PATH"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="Missing authorized"):
        SnowflakeConfig.from_env()


def test_corrupt_staged_content_never_advances_visibility(config, snapshot):
    class CorruptCursor(CursorDouble):
        def fetchall(self):
            rows = list(super().fetchall())
            table, key, document = rows[0]
            changed = json.loads(document)
            changed["source_id"] = "unexpected"
            rows[0] = (table, key, json.dumps(changed))
            return rows

    class CorruptConnection(RecordingConnection):
        def cursor(self):
            return CorruptCursor(self)

    driver = CorruptConnection(snapshot.counts)
    with pytest.raises(ValueError, match="document content differs"):
        SnowflakePublisher(driver, config).publish(snapshot)
    assert driver.rollbacks == 1 and driver.commits == 0
    assert not any(sql.startswith("UPDATE") for sql, _ in driver.calls)


def test_connector_factory_preserves_explicit_revocation_and_timeout_policy(config, monkeypatch):
    """Inspect actual factory arguments without opening a cloud connection."""
    package = ModuleType("snowflake")
    connector = ModuleType("snowflake.connector")
    captured = {}
    sentinel = object()

    def record_connection(**kwargs):
        captured.update(kwargs)
        return sentinel

    connector.connect = record_connection
    package.connector = connector
    monkeypatch.setitem(sys.modules, "snowflake", package)
    monkeypatch.setitem(sys.modules, "snowflake.connector", connector)
    assert connect(config) is sentinel
    assert captured["ocsp_fail_open"] is False
    assert not captured.get("insecure_mode", False)
    assert not captured.get("disable_ocsp_checks", False)
    assert captured["login_timeout"] <= 15
    assert captured["network_timeout"] <= 30
    assert captured["session_parameters"]["STATEMENT_TIMEOUT_IN_SECONDS"] <= 120
    assert captured["authenticator"] == "snowflake_jwt"
