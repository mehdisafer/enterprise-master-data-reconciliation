"""Integration tests fail closed unless their dedicated PostgreSQL is supplied."""
import os

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict

from mdm.db import Database
from mdm.service import Service


@pytest.fixture
def service():
    dsn = os.environ.get("MDM_TEST_DATABASE_URL")
    if not dsn:
        pytest.fail("real PostgreSQL integration requires MDM_TEST_DATABASE_URL (dedicated *_test database)")
    if not conninfo_to_dict(dsn).get("dbname", "").endswith("_test"):
        pytest.fail("test reset is allowed only in an explicitly supplied *_test database")
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    db = Database(dsn)
    db.migrate()
    return Service(db)
