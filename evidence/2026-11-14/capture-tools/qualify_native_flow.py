"""Execute the native, non-test PostgreSQL qualification with original evidence.

Run inside run_with_postgres.py after the project owner freezes the sources.
Only mdm, mdm_restore and mdm_load are used. No schema or database is reset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO = BASE.parent / "enterprise-master-data-reconciliation"
PYTHON = REPO / ".venv/bin/python"
MDM = REPO / ".venv/bin/mdm"
DBT = REPO / ".venv/bin/dbt"


class QualificationError(Exception):
    pass


def utc() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: Path, value) -> None:
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def probe(action: str, evidence: Path) -> None:
    import psycopg

    if action == "environment":
        databases = {}
        for database, variable in (("mdm", "MDM_DATABASE_URL"),
                                   ("mdm_restore", "MDM_RESTORE_DATABASE_URL"),
                                   ("mdm_load", "MDM_LOAD_DATABASE_URL")):
            with psycopg.connect(os.environ[variable], connect_timeout=5) as conn:
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                actual, address, port, server = conn.execute(
                    "SELECT current_database(),inet_server_addr(),inet_server_port(),version()"
                ).fetchone()
                if actual != database or str(address) != "127.0.0.1":
                    raise QualificationError("Unexpected database or server address")
                objects = conn.execute("""SELECT count(*) FROM pg_class c
                    JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'""").fetchone()[0]
                functions = conn.execute("""SELECT count(*) FROM pg_proc p
                    JOIN pg_namespace n ON n.oid=p.pronamespace
                    WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'""").fetchone()[0]
                if database == "mdm_restore" and (objects or functions):
                    raise QualificationError("Restore target already contains user objects; no reset is permitted")
                has_sources = conn.execute("SELECT to_regclass('public.source_records') IS NOT NULL").fetchone()[0]
                sources = conn.execute("SELECT count(*) FROM public.source_records").fetchone()[0] if has_sources else 0
                if database == "mdm_load" and sources:
                    raise QualificationError("Load target already has source records; no reset is permitted")
                databases[database] = {"address": str(address), "port": port, "version": server,
                                       "initial_user_objects": objects, "initial_user_functions": functions,
                                       "initial_source_records": sources}
        report = {"observed_at": utc(), "python": platform.python_version(), "platform": platform.platform(),
                  "databases": databases, "snowflake_live_executed": False,
                  "packages": {name: version(name) for name in
                               ("dbt-core", "dbt-postgres", "dbt-snowflake", "psycopg", "fastapi")}}
        write_json(evidence / "environment.json", report)
        print(json.dumps(report, sort_keys=True))
    elif action == "warehouse-export":
        from mdm.snowflake import export_snapshot

        with psycopg.connect(os.environ["MDM_DATABASE_URL"], connect_timeout=5) as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            snapshot = export_snapshot(conn)
        report = {"snapshot_id": snapshot.snapshot_id, "captured_at": snapshot.captured_at,
                  "counts": snapshot.counts, "postgres_export_executed": True,
                  "snowflake_load_executed": False}
        if len(snapshot.counts) != 16 or snapshot.counts["source_records"] == 0:
            raise QualificationError("Unexpected warehouse export contract or empty demonstration")
        write_json(evidence / "warehouse-export.json", report)
        print(json.dumps(report, sort_keys=True))
    else:
        raise QualificationError("Unknown read-only probe")


def source_manifest() -> dict:
    paths = []
    for prefix in ("src", "dbt", "scripts", "contracts"):
        paths.extend(path for path in (REPO / prefix).rglob("*") if path.is_file()
                     and not any(part in {"__pycache__", "target", "logs", "dbt_packages"}
                                 for part in path.relative_to(REPO).parts)
                     and path.suffix != ".pyc")
    paths.extend(REPO / name for name in
                 ("pyproject.toml", "uv.lock", ".github/workflows/quality.yml"))
    files = {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted(set(paths)) if path.is_file()}
    digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, text=True, capture_output=True, check=False)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, text=True, capture_output=True, check=False)
    return {"captured_at": utc(), "files": files, "content_sha256": digest,
            "git_commit": commit.stdout.strip() if commit.returncode == 0 else None,
            "git_status": status.stdout.splitlines() if status.returncode == 0 else None}


def execute(evidence: Path) -> int:
    os.umask(0o077)
    evidence.mkdir(parents=True, exist_ok=False)
    logs = evidence / "commands"
    logs.mkdir()
    initial_source = source_manifest()
    write_json(evidence / "source-before.json", initial_source)
    project = evidence / "dbt-project"
    shutil.copytree(REPO / "dbt", project,
                    ignore=shutil.ignore_patterns("target", "logs", "dbt_packages", "__pycache__", "*.pyc"))
    environment = os.environ.copy()
    environment.update({"PATH": str(REPO / ".venv/bin") + os.pathsep + environment.get("PATH", ""),
                        "MDM_PYTHON": str(PYTHON), "PYTHONDONTWRITEBYTECODE": "1",
                        "DBT_SEND_ANONYMOUS_USAGE_STATS": "false", "DO_NOT_TRACK": "1",
                        "DBT_UPLOAD_TO_ARTIFACTS_INGEST_API": "false",
                        "MDM_DBT_TARGET": "postgres", "MDM_SOURCE_SCHEMA": "public",
                        "MDM_ANALYTICS_SCHEMA": "analytics"})
    environment.pop("MDM_DATABASE_URL_FILE", None)
    environment.pop("MDM_RESTORE_DATABASE_URL_FILE", None)
    runtime = json.loads((BASE / "connection.json").read_text())
    bindir = Path(runtime["binary_directory"])
    environment["PG_DUMP"] = str(bindir / "pg_dump")
    environment["PG_RESTORE"] = str(bindir / "pg_restore")
    password = (BASE / "admin-password").read_bytes().strip()
    report = {"scope": "native_postgres_non_test_flow", "started_at": utc(),
              "evidence_directory": str(evidence), "source_content_sha256": initial_source["content_sha256"],
              "status": "running", "steps": [], "snowflake_live_executed": False,
              "container_execution_claimed": False}

    def step(name: str, command: list[str], *, updates: dict | None = None,
             expected: tuple[int, ...] = (0,), timeout: int = 300) -> tuple[bytes, bytes]:
        started_at = utc()
        started = time.monotonic()
        child_env = environment | (updates or {})
        print(json.dumps({"phase": name, "status": "started", "utc": started_at}), flush=True)
        process = subprocess.Popen(command, cwd=REPO, env=child_env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
        metadata = {"name": name, "command": command, "cwd": str(REPO),
                    "started_at": started_at, "finished_at": utc(),
                    "elapsed_seconds": round(time.monotonic() - started, 6),
                    "returncode": process.returncode, "timed_out": timed_out,
                    "expected_returncodes": list(expected),
                    "database": child_env.get("PGDATABASE"),
                    "stdout_path": str(logs / (name + ".stdout.log")),
                    "stderr_path": str(logs / (name + ".stderr.log"))}
        # Successful captures are original bytes. Unexpected password emission is
        # blocked before it reaches a persistent command log or the terminal.
        if password and (password in stdout or password in stderr):
            metadata["status"] = "failed_secret_capture_blocked"
            metadata["output_retained"] = False
            write_json(logs / (name + ".json"), metadata)
            report["steps"].append(metadata)
            raise QualificationError(name + " emitted a secret; output was not persisted")
        (logs / (name + ".stdout.log")).write_bytes(stdout)
        (logs / (name + ".stderr.log")).write_bytes(stderr)
        metadata["output_retained"] = True
        metadata["status"] = "passed" if process.returncode in expected and not timed_out else "failed"
        write_json(logs / (name + ".json"), metadata)
        report["steps"].append(metadata)
        print(json.dumps({"phase": name, "status": metadata["status"],
                          "returncode": process.returncode, "elapsed_seconds": metadata["elapsed_seconds"],
                          "stderr_path": metadata["stderr_path"]}), flush=True)
        if metadata["status"] != "passed":
            raise QualificationError(name + " failed; original outputs are retained")
        return stdout, stderr

    def dbt_args(command: list[str], name: str) -> list[str]:
        arguments = [str(DBT), *command, "--project-dir", str(project), "--profiles-dir", str(project),
                     "--target", "postgres", "--log-path", str(evidence / "dbt-logs" / name),
                     "--no-use-colors"]
        # deps has no --target-path option in the installed dbt Core CLI.
        if command != ["deps"]:
            arguments += ["--target-path", str(evidence / "dbt-target" / name)]
        return arguments

    try:
        step("01-environment", [str(PYTHON), str(Path(__file__).resolve()), "--probe", "environment",
                                 "--evidence", str(evidence)])
        step("02-pg-dump-version", [environment["PG_DUMP"], "--version"])
        step("03-pg-restore-version", [environment["PG_RESTORE"], "--version"])
        step("04-migrate", [str(MDM), "migrate"])
        step("05-demo", [str(MDM), "demo", "--output", str(evidence / "demo.json")])
        check_stdout, _ = step("06-business-check", [str(MDM), "check"])
        (evidence / "business-check.json").write_bytes(check_stdout)
        step("07-snapshot", [str(MDM), "snapshot", "--output", str(evidence / "postgres-snapshot.json")])
        step("08-warehouse-export", [str(PYTHON), str(Path(__file__).resolve()), "--probe", "warehouse-export",
                                      "--evidence", str(evidence)])
        step("09-dbt-deps", dbt_args(["deps"], "deps"))
        step("10-dbt-build", dbt_args(["build"], "build"))
        step("11-dbt-docs", dbt_args(["docs", "generate"], "docs"))
        archive = evidence / "reference.dump"
        step("12-backup", ["bash", str(REPO / "scripts/backup.sh"), str(archive), "--expect-db", "mdm"], timeout=600)
        step("13-restore", ["bash", str(REPO / "scripts/restore.sh"), str(archive), "--expect-db", "mdm_restore",
                            "--report", str(evidence / "restore.json")], timeout=600)
        forbidden = evidence / "forbidden-restore.json"
        _, rejection = step("14-reject-second-restore", ["bash", str(REPO / "scripts/restore.sh"), str(archive),
                            "--expect-db", "mdm_restore", "--report", str(forbidden)], expected=(1,))
        rejection_record = json.loads(rejection)
        if (forbidden.exists() or rejection_record.get("restore_verified") is not False
                or rejection_record.get("error_type") != "OperationError"
                or rejection_record.get("reason") != "Restore target is not empty and isolated"):
            raise QualificationError("Second restore did not fail for the expected populated-target reason")
        write_json(evidence / "second-restore-rejection.json", {"expected_rejection_observed": True,
                   "forbidden_report_created": False, "original_response": rejection_record})
        step("15-dbt-restored-test", dbt_args(["test"], "restored-test"), updates={"PGDATABASE": "mdm_restore"})
        step("16-benchmark-control", [str(MDM), "benchmark", "--size", "300", "--output",
                                       str(evidence / "benchmark-control.json")], timeout=300)
        step("17-benchmark-database", [str(MDM), "benchmark", "--size", "300", "--database", "--output",
                                        str(evidence / "benchmark-database.json")],
             updates={"MDM_DATABASE_URL": environment["MDM_LOAD_DATABASE_URL"], "PGDATABASE": "mdm_load"}, timeout=600)

        check = json.loads((evidence / "business-check.json").read_text())
        restore = json.loads((evidence / "restore.json").read_text())
        control = json.loads((evidence / "benchmark-control.json").read_text())
        load = json.loads((evidence / "benchmark-database.json").read_text())
        if (not check.get("passed") or not restore.get("snapshot_content_equal")
                or restore.get("business_check_exit_code") != 0
                or not control.get("thresholds_met") or not load.get("thresholds_met")
                or not load.get("database_executed") or load.get("records") != 300):
            raise QualificationError("One or more final business/restore/load assertions failed")
        dbt_results = {}
        for name in ("build", "restored-test"):
            result = json.loads((evidence / "dbt-target" / name / "run_results.json").read_text())
            statuses = Counter(row["status"] for row in result["results"])
            if not result["results"] or set(statuses) - {"pass", "success"}:
                raise QualificationError("dbt result contains failures, skipped nodes or warnings: " + name)
            dbt_results[name] = dict(statuses)
        catalog = json.loads((evidence / "dbt-target/docs/catalog.json").read_text())
        if len(catalog.get("nodes", {})) < 5:
            raise QualificationError("dbt catalog is missing expected model relations")
        report.update({"status": "passed", "business_check_passed": True,
                       "restore_content_equal": True, "second_restore_rejected_for_expected_reason": True,
                       "dbt_statuses": dbt_results, "dbt_catalog_model_count": len(catalog["nodes"]),
                       "control_thresholds_met": True, "database_thresholds_met": True})
    except (QualificationError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        report.update({"status": "failed", "error_type": type(exc).__name__,
                       "reason": str(exc) if isinstance(exc, QualificationError) else "Inspect retained command outputs"})
    finally:
        final_source = source_manifest()
        write_json(evidence / "source-after.json", final_source)
        report["source_unchanged_during_run"] = initial_source["files"] == final_source["files"]
        if not report["source_unchanged_during_run"]:
            report.update({"status": "failed", "reason": "Executable source files changed during qualification"})
        report["finished_at"] = utc()
        write_json(evidence / "qualification.json", report)
        print(json.dumps({"qualification_status": report["status"], "report": str(evidence / "qualification.json")}), flush=True)
    return 0 if report["status"] == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--probe", choices=("environment", "warehouse-export"))
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    if args.probe:
        if not args.evidence:
            parser.error("a read-only probe requires its evidence directory")
        probe(args.probe, args.evidence.resolve())
        return 0
    if not args.execute:
        parser.error("--execute is required; coordinate exclusive use of the runtime first")
    evidence = args.evidence or (BASE / "qualification" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    evidence = evidence.resolve()
    if not evidence.is_relative_to(BASE) or evidence == BASE:
        parser.error("evidence must be a new directory within this dedicated runtime")
    return execute(evidence)


if __name__ == "__main__":
    sys.exit(main())
