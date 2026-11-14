#!/usr/bin/env bash
# Run with: uv run --no-sync bash scripts/backup.sh /safe/mdm.dump --expect-db mdm
set -euo pipefail
exec "${MDM_PYTHON:-python3}" - "$@" <<'PY'
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

TABLES = (
    "raw_records", "source_records", "identity_groups", "memberships",
    "golden_history", "decisions", "outbox", "consumer_inbox", "consumer_records",
    "schema_migrations", "standard_records", "membership_history", "candidates",
    "decision_events", "consumer_crosswalk", "runs", "run_sources",
)


class OperationError(Exception):
    """A safe operator-facing error that contains no connection secrets."""


def main():
    parser = argparse.ArgumentParser(description="Create a consistent, non-overwriting MDM backup")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--expect-db", required=True)
    args = parser.parse_args()
    dsn = os.environ.get("MDM_DATABASE_URL", "")
    dsn_file = os.environ.get("MDM_DATABASE_URL_FILE")
    if dsn and dsn_file:
        raise OperationError("Use only one database secret mechanism")
    if dsn_file:
        dsn = Path(dsn_file).read_text().strip()
    if not dsn:
        raise OperationError("MDM_DATABASE_URL or MDM_DATABASE_URL_FILE is required")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,62}", args.expect_db):
        raise OperationError("Expected database name is invalid")
    archive = args.archive.absolute()
    manifest = Path(str(archive) + ".manifest.json")
    if archive.exists() or archive.is_symlink() or manifest.exists() or manifest.is_symlink():
        raise OperationError("Backup destination already exists; choose a new path")
    os.umask(0o077)
    archive.parent.mkdir(parents=True, exist_ok=True)
    client_env = os.environ.copy()
    mapping = {"dbname": "PGDATABASE", "password": "PGPASSWORD", "user": "PGUSER",
               "application_name": "PGAPPNAME", "connect_timeout": "PGCONNECT_TIMEOUT"}
    for key, value in conninfo_to_dict(dsn).items():
        client_env[mapping.get(key, "PG" + key.upper().replace("_", ""))] = str(value)
    client_env["PGCONNECT_TIMEOUT"] = "10"
    # pg_dump inherits the same resolved libpq connection, without a DSN in argv.
    client_env["PGOPTIONS"] = "-c lock_timeout=5000 -c statement_timeout=300000"
    pg_dump = os.environ.get("PG_DUMP", "pg_dump")
    client_version = subprocess.check_output([pg_dump, "--version"], env=client_env, text=True).strip()
    started = time.monotonic()
    tmp_path = None
    with psycopg.connect(dsn, connect_timeout=10) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        conn.execute("SET TIME ZONE 'UTC'")
        conn.execute("SET statement_timeout = '300s'")
        conn.execute("SET idle_in_transaction_session_timeout = '600s'")
        database, server_version = conn.execute(
            "SELECT current_database(), current_setting('server_version')"
        ).fetchone()
        if database != args.expect_db:
            raise OperationError("Connected database does not match --expect-db")
        snapshot = conn.execute("SELECT pg_export_snapshot()").fetchone()[0]
        fingerprints = {}
        for table in TABLES:
            digest = hashlib.sha256()
            count = 0
            query = sql.SQL("SELECT to_jsonb(t)::text FROM {} t ORDER BY to_jsonb(t)::text").format(
                sql.Identifier("public", table)
            )
            with conn.cursor(name="backup_" + table) as cursor:
                cursor.execute(query)
                for (row,) in cursor:
                    digest.update(row.encode() + b"\n")
                    count += 1
            fingerprints[table] = {"rows": count, "sha256": digest.hexdigest()}
        try:
            with tempfile.NamedTemporaryFile(dir=archive.parent, prefix=".mdm-backup-", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                subprocess.run(
                    [pg_dump, "--format=custom", "--no-owner", "--no-privileges", "--snapshot=" + snapshot],
                    env=client_env, stdout=tmp, check=True, timeout=600,
                )
                tmp.flush()
                os.fsync(tmp.fileno())
            file_digest = hashlib.sha256()
            with tmp_path.open("rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    file_digest.update(chunk)
            # Link is atomic and fails if a competing process claimed the destination.
            os.link(tmp_path, archive)
            tmp_path.unlink()
            tmp_path = None
            report = {
                "format_version": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source_database": database,
                "server_version": server_version,
                "client_version": client_version,
                "archive_sha256": file_digest.hexdigest(),
                "archive_bytes": archive.stat().st_size,
                "tables": fingerprints,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "restore_tested": False,
            }
            with manifest.open("x") as file:
                json.dump(report, file, indent=2, sort_keys=True)
                file.write("\n")
            print(json.dumps({"backup_created": True, "archive": str(archive), "manifest": str(manifest)}))
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)


try:
    main()
except Exception as exc:
    # PostgreSQL exception strings may carry connection details; do not echo them.
    print(json.dumps({"backup_created": False, "error_type": type(exc).__name__, "reason": str(exc) if isinstance(exc, OperationError) else "Inspect the failing stage; connection details are suppressed"}), file=sys.stderr)
    sys.exit(1)
PY
