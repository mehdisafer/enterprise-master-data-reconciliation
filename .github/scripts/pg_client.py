#!/usr/bin/env python3
"""CI-only transport for real PostgreSQL client binaries in the service container.

No mock database: stdio carries the actual archive, libpq environment selects the
database, and Docker executes only pg_dump or pg_restore. Credentials stay out of
the command arguments and logs. The runner can reach the service on localhost.
"""

import os
import re
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"pg_dump", "pg_restore"}:
        raise SystemExit("Expected pg_dump or pg_restore")
    container = os.environ.get("MDM_CI_POSTGRES_CONTAINER", "")
    if not re.fullmatch(r"[a-f0-9]{12,64}", container):
        raise SystemExit("Expected the exact CI service container ID")
    names = (
        "PGDATABASE", "PGUSER", "PGPASSWORD", "PGCONNECT_TIMEOUT", "PGOPTIONS",
        "PGSSLMODE", "PGAPPNAME", "PGCHANNELBINDING",
    )
    command = ["docker", "exec", "-i", "--env", "PGHOST=127.0.0.1", "--env", "PGPORT=5432"]
    for name in names:
        if name in os.environ:
            command.extend(["--env", name])
    command.extend([container, *sys.argv[1:]])
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
