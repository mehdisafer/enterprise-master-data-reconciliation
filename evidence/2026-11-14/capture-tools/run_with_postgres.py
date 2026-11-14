"""Run an authorized local qualification command with the isolated PostgreSQL.

Processes do not survive the executor call that launches them. Start the server
and execute the client command together, then stop the dedicated cluster cleanly.
Only this runtime's synthetic cluster is managed. No system service is modified.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone


BASE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not 10 <= args.timeout_seconds <= 3600:
        parser.error("timeout must be between 10 and 3600 seconds")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command

    configuration = json.loads((BASE / "connection.json").read_text())
    bindir = Path(configuration["binary_directory"])
    data = Path(configuration["data_directory"])
    if not data.is_relative_to(BASE) or not bindir.is_relative_to(BASE):
        raise RuntimeError("Runtime paths must remain inside this dedicated directory")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    logs = BASE / "logs" / run_id
    logs.mkdir()
    password = (BASE / "admin-password").read_text().strip()
    pgpass = BASE / "pgpass"
    if not pgpass.exists():
        with os.fdopen(os.open(pgpass, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as handle:
            handle.write(f"127.0.0.1:{configuration['port']}:*:mdm:{password}\n")
    dsn = f"postgresql://mdm@127.0.0.1:{configuration['port']}/mdm"
    environment = os.environ.copy()
    environment.pop("MDM_DATABASE_URL_FILE", None)
    environment.update({
        "LD_LIBRARY_PATH": configuration["library_directory"],
        "PATH": str(bindir) + os.pathsep + environment.get("PATH", ""),
        "PGHOST": "127.0.0.1",
        "PGPORT": str(configuration["port"]),
        "PGUSER": "mdm",
        "PGDATABASE": "mdm",
        "PGPASSFILE": str(pgpass),
        "PGCONNECT_TIMEOUT": "5",
        "DBT_ENV_SECRET_PG_PASSWORD": password,
        "MDM_DATABASE_URL": dsn,
        "MDM_TEST_DATABASE_URL": dsn + "_test",
        "MDM_RESTORE_DATABASE_URL": dsn + "_restore",
        "MDM_LOAD_DATABASE_URL": dsn + "_load",
        "PG_DUMP": str(bindir / "pg_dump"),
        "PG_RESTORE": str(bindir / "pg_restore"),
    })
    # A caller's unrelated libpq password must not override this cluster's passfile.
    environment.pop("PGPASSWORD", None)

    def captured(name: str, arguments: list[str], *, timeout: int = 40) -> subprocess.CompletedProcess:
        result = subprocess.run(arguments, env=environment, text=True, capture_output=True, timeout=timeout)
        (logs / name).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f"{name} failed with exit {result.returncode}; see {logs / name}")
        return result

    psql = [str(bindir / "psql"), "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1"]
    report = {"run_id": run_id, "dsn_without_password": dsn, "readiness": False,
              "command_executed": bool(command), "command_exit_code": None, "stop_exit_code": None}
    with (BASE / "qualification.lock").open("a+") as lease:
        try:
            fcntl.flock(lease.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another qualification owns the dedicated cluster") from exc
        started = False
        try:
            captured("start.log", [str(bindir / "pg_ctl"), "-D", str(data), "-l",
                                    str(logs / "postgres.log"), "-w", "-t", "30", "start"])
            started = True
            captured("pg-isready.log", [str(bindir / "pg_isready"), "-h", "127.0.0.1", "-p",
                                        str(configuration["port"]), "-U", "mdm", "-d", "postgres"])
            existing = set(captured("databases-before.txt", psql + ["-d", "postgres", "-c",
                "SELECT datname FROM pg_database ORDER BY datname"]).stdout.splitlines())
            for name in ("mdm", "mdm_test", "mdm_restore", "mdm_load"):
                if name not in existing:
                    captured(f"createdb-{name}.log", [str(bindir / "createdb"), "-O", "mdm", name])
            query = """SELECT json_build_object(
                'version', version(), 'server_version_num', current_setting('server_version_num'),
                'database', current_database(), 'user', current_user,
                'server_address', inet_server_addr(), 'server_port', inet_server_port(),
                'readiness_answer', 6*7, 'postmaster_started', pg_postmaster_start_time(),
                'settings', (SELECT json_object_agg(name,current_setting(name)) FROM pg_settings
                WHERE name IN ('listen_addresses','port','unix_socket_directories','max_connections',
                  'shared_buffers','work_mem','maintenance_work_mem','max_worker_processes',
                  'max_parallel_workers','max_parallel_workers_per_gather','dynamic_shared_memory_type',
                  'huge_pages','jit','temp_file_limit','min_wal_size','max_wal_size','wal_buffers',
                  'fsync','synchronous_commit','full_page_writes','statement_timeout','lock_timeout',
                  'idle_in_transaction_session_timeout','TimeZone','data_checksums'))
                )"""
            observed = json.loads(captured("readiness-query.json", psql + ["-d", "mdm", "-c", query]).stdout)
            if (observed["server_version_num"] != "170012" or observed["server_address"] != "127.0.0.1"
                    or observed["settings"]["unix_socket_directories"] != ""
                    or observed["readiness_answer"] != 42):
                raise RuntimeError("Observed server does not match the intended runtime")
            report["readiness"] = True
            report["server_version"] = observed["version"]
            print(json.dumps({"postgres_ready": True, "server_version": observed["version"],
                              "dsn_without_password": dsn, "evidence_directory": str(logs)}), flush=True)
            if command:
                result = subprocess.run(command, env=environment, timeout=args.timeout_seconds)
                report["command_exit_code"] = result.returncode
            else:
                report["command_exit_code"] = 0
        except subprocess.TimeoutExpired:
            report["command_exit_code"] = 124
            raise
        finally:
            if started:
                stopped = subprocess.run([str(bindir / "pg_ctl"), "-D", str(data), "-m", "fast",
                                          "-w", "-t", "30", "stop"], env=environment,
                                         text=True, capture_output=True, timeout=40)
                (logs / "stop.log").write_text(stopped.stdout + stopped.stderr)
                report["stop_exit_code"] = stopped.returncode
            (logs / "run.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({"qualification_runtime_report": str(logs / "run.json")}), flush=True)
    if report["stop_exit_code"] != 0:
        return 1
    return int(report["command_exit_code"] or 0)


if __name__ == "__main__":
    sys.exit(main())
