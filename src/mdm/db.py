"""Bounded PostgreSQL transactions and checksum-verified migrations."""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
from importlib.resources import files

import psycopg
from psycopg.rows import dict_row

from mdm.config import database_url

GRAPH_LOCK = 24022002


class Database:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or database_url()

    @contextmanager
    def connect(self, *, write: bool = False):
        with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=5,
                            options="-c statement_timeout=30000 -c lock_timeout=5000 -c idle_in_transaction_session_timeout=30000") as conn:
            if write:
                # Global graph serialization is intentional and measured. Matching
                # reads can run in parallel; mutations remain a single-writer lane.
                conn.execute("SELECT pg_advisory_xact_lock(%s)", (GRAPH_LOCK,))
            yield conn

    def migrate(self) -> dict:
        script = files("mdm").joinpath("sql/001.sql").read_text()
        digest = hashlib.sha256(script.encode()).hexdigest()
        with self.connect(write=True) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version integer PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT clock_timestamp())")
            row = conn.execute("SELECT checksum FROM schema_migrations WHERE version=1").fetchone()
            if row:
                if row["checksum"] != digest:
                    raise ValueError("applied migration checksum differs; add a new migration")
                return {"version": 1, "applied": False, "checksum": digest}
            conn.execute(script)
            conn.execute("INSERT INTO schema_migrations(version,checksum) VALUES(1,%s)", (digest,))
            return {"version": 1, "applied": True, "checksum": digest}

