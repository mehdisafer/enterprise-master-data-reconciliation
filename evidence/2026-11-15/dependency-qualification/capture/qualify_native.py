"""Capture the combined P02 dependency qualification on a real isolated database.

Requires dedicated fresh mdm_demo/mdm_restore/mdm_load databases and mdm_test.
Credentials are supplied externally. No cloud service is contacted by this flow
except the explicitly recorded package advisory audit.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import tomllib
import xml.etree.ElementTree as ET

import psycopg

ROOT = Path(__file__).resolve().parent / "repo"
OUT = ROOT / "artifacts" / "qualification-20261115"
OUT.mkdir(parents=True, exist_ok=False)
ENV = os.environ.copy()
ENV.update(PATH=str(ROOT / ".venv/bin") + os.pathsep + ENV["PATH"],
           DBT_SEND_ANONYMOUS_USAGE_STATS="false", DO_NOT_TRACK="1", UV_LINK_MODE="copy",
           MDM_PYTHON=str(ROOT / ".venv/bin/python"))
COMMANDS = []


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + "\n")


def run(label, command, *, updates=None, expected=0, timeout=240):
    directory = OUT / "commands" / f"{len(COMMANDS) + 1:02}-{label}"
    directory.mkdir(parents=True)
    env = {**ENV, **(updates or {})}
    start = datetime.now(timezone.utc).isoformat()
    timer = time.monotonic()
    code = None
    try:
        with (directory / "stdout.txt").open("wb") as stdout, (directory / "stderr.txt").open("wb") as stderr:
            process = subprocess.run(command, env=env, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=timeout)
        code = process.returncode
    finally:
        report = {"label": label, "command": command, "cwd": str(ROOT), "started_at": start,
                  "ended_at": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": time.monotonic()-timer,
                  "returncode": code, "expected_returncode": expected, "timeout_seconds": timeout}
        write(directory / "execution.json", report)
        COMMANDS.append(report)
        print(f"{label}: exit {code} ({report['elapsed_seconds']:.2f}s)", flush=True)
    if code != expected:
        print((directory / "stderr.txt").read_text()[-5000:], file=sys.stderr)
        print((directory / "stdout.txt").read_text()[-5000:], file=sys.stderr)
        raise RuntimeError(f"{label} returned {code}, expected {expected}")
    return directory


def main():
    with psycopg.connect(ENV["MDM_DATABASE_URL"]) as conn:
        database, server = conn.execute("SELECT current_database(), version()").fetchone()
        assert database == "mdm_demo"
        assert conn.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'").fetchone()[0] == 0
    write(OUT / "environment.json", {"python": platform.python_version(), "platform": platform.platform(),
          "postgres": server, "database": database,
          "packages": {name: version(name) for name in ("fastapi", "pydantic", "pydantic-core", "dbt-core", "dbt-postgres", "dbt-snowflake", "psycopg", "uvicorn")},
          "remote_base_commit": "16f7325c5f8b16ce2c5259d2fba44f40e78bebe7",
          "scope": "native isolated workspace; not GitHub Actions, Docker or live Snowflake"})
    run("lock-check", ["uv", "lock", "--check"])
    run("editable-sync", ["uv", "sync", "--frozen", "--all-extras"])
    run("lint", ["ruff", "check", "src", "tests", "scripts", ".github/scripts"])
    run("editable-unit", ["pytest", "-q", "-m", "not integration", "--junitxml="+str(OUT / "editable-unit.xml")])
    run("build-sdist-and-wheel", ["uv", "build", "--no-sources", "--out-dir", str(OUT / "dist")])
    wheels = list((OUT / "dist").glob("*.whl"))
    assert len(wheels) == 1
    run("install-wheel", ["uv", "pip", "install", "--no-deps", "--reinstall", "--python", str(ROOT / ".venv/bin/python"), str(wheels[0])])
    run("verify-distribution", ["python", "scripts/verify_distribution.py", "--output", str(OUT / "distribution.json")])
    run("full-postgres-suite", ["pytest", "-q", "--junitxml="+str(OUT / "pytest.xml")])
    junit = ET.parse(OUT / "pytest.xml").getroot()
    assert not junit.findall(".//skipped") and not junit.findall(".//failure") and not junit.findall(".//error")
    run("migrate", ["mdm", "migrate"])
    run("demo", ["mdm", "demo", "--output", str(OUT / "demo.json")])
    check = run("business-check", ["mdm", "check"])
    shutil.copy2(check / "stdout.txt", OUT / "business-check.json")
    run("snapshot", ["mdm", "snapshot", "--output", str(OUT / "postgres-snapshot.json")])
    export = run("warehouse-export", ["python", "-c", "import json,os,psycopg; from mdm.snowflake import export_snapshot; c=psycopg.connect(os.environ['MDM_DATABASE_URL']); c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'); s=export_snapshot(c); print(json.dumps({'snapshot_id':s.snapshot_id,'counts':s.counts,'postgres_export_executed':True,'snowflake_load_executed':False})); c.close()"])
    shutil.copy2(export / "stdout.txt", OUT / "warehouse-export.json")
    dbt_project = OUT / "dbt-project"
    shutil.copytree(ROOT / "dbt", dbt_project, ignore=shutil.ignore_patterns("logs", "target*", "dbt_packages"))
    common = ["--project-dir", str(dbt_project), "--profiles-dir", str(dbt_project), "--target", "postgres"]
    run("dbt-build", ["dbt", "build", *common, "--target-path", str(OUT / "dbt/build"), "--log-path", str(OUT / "dbt/logs/build")])
    before = {name: hashlib.sha256((OUT / "dbt/build" / name).read_bytes()).hexdigest() for name in ("manifest.json", "run_results.json")}
    run("dbt-docs", ["dbt", "docs", "generate", *common, "--target-path", str(OUT / "dbt/docs"), "--log-path", str(OUT / "dbt/logs/docs")])
    assert before == {name: hashlib.sha256((OUT / "dbt/build" / name).read_bytes()).hexdigest() for name in before}
    run("backup", ["bash", "scripts/backup.sh", str(OUT / "reference.dump"), "--expect-db", "mdm_demo"])
    run("restore", ["bash", "scripts/restore.sh", str(OUT / "reference.dump"), "--expect-db", "mdm_restore", "--report", str(OUT / "restore.json")])
    rejected = run("second-restore-rejection", ["bash", "scripts/restore.sh", str(OUT / "reference.dump"), "--expect-db", "mdm_restore", "--report", str(OUT / "forbidden-restore.json")], expected=1)
    rejection = json.loads((rejected / "stderr.txt").read_text())
    assert rejection == {"restore_verified": False, "error_type": "OperationError", "reason": "Restore target is not empty and isolated"}
    assert not (OUT / "forbidden-restore.json").exists()
    write(OUT / "second-restore-rejection.json", {"passed": True, "returncode": 1, "response": rejection, "forbidden_report_absent": True})
    run("dbt-restored", ["dbt", "test", *common, "--target-path", str(OUT / "dbt/restored"), "--log-path", str(OUT / "dbt/logs/restored")], updates={"PGDATABASE": "mdm_restore"})
    run("benchmark-control", ["mdm", "benchmark", "--size", "300", "--output", str(OUT / "benchmark-control.json")])
    run("benchmark-database", ["mdm", "benchmark", "--size", "300", "--database", "--output", str(OUT / "benchmark-database.json")], updates={"MDM_DATABASE_URL": ENV["MDM_LOAD_DATABASE_URL"]})
    run("http-runtime", ["python", str(ROOT.parent / "qualify_http.py"), "--output", str(OUT / "http")], timeout=120)
    run("components", ["python", "scripts/component_inventory.py", "--check", "--output", str(OUT / "components.json")])
    run("export-audit-input", ["uv", "export", "--frozen", "--all-extras", "--no-emit-project", "--no-hashes", "--output-file", str(OUT / "audit-requirements.txt")])
    run("dependency-audit", ["pip-audit", "--strict", "--disable-pip", "--no-deps", "-r", str(OUT / "audit-requirements.txt"), "--progress-spinner", "off", "--timeout", "20", "--format", "json", "--output", str(OUT / "dependency-audit.json")], timeout=180)
    build = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["uv"]["build-constraint-dependencies"]
    (OUT / "audit-build-requirements.txt").write_text("\n".join(item["requirement"] for item in build) + "\n")
    run("build-dependency-audit", ["pip-audit", "--strict", "--disable-pip", "--no-deps", "-r", str(OUT / "audit-build-requirements.txt"), "--progress-spinner", "off", "--timeout", "20", "--format", "json", "--output", str(OUT / "build-dependency-audit.json")], timeout=180)
    source_paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
    files = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_paths
             if (ROOT/name).is_file() and not name.startswith("evidence/")}
    write(OUT / "source-files.json", {"remote_base_commit": "16f7325c5f8b16ce2c5259d2fba44f40e78bebe7", "files": files,
          "meaning": "content correspondence, not independent certification"})


if __name__ == "__main__":
    started = datetime.now(timezone.utc).isoformat()
    succeeded = False
    try:
        main()
        succeeded = True
    finally:
        write(OUT / "qualification.json", {"passed": succeeded, "started_at": started,
              "ended_at": datetime.now(timezone.utc).isoformat(), "commands": COMMANDS,
              "scope": "native Python/PostgreSQL; no container, rendered browser or live Snowflake qualification"})
