"""Capture the concurrent-main regression check without dependency resolution."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import mdm
import psycopg

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def utc():
    return datetime.now(timezone.utc).isoformat()


def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def run(label, command, timeout):
    folder = OUT / label
    folder.mkdir(exist_ok=False)
    start = utc()
    clock = time.monotonic()
    process = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=timeout)
    (folder / "stdout.txt").write_bytes(process.stdout)
    (folder / "stderr.txt").write_bytes(process.stderr)
    result = {
        "label": label, "command": command, "cwd": str(ROOT),
        "started_at": start, "ended_at": utc(),
        "elapsed_seconds": time.monotonic() - clock,
        "returncode": process.returncode, "expected_returncode": 0,
        "timeout_seconds": timeout,
    }
    (folder / "execution.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"label": label, "returncode": process.returncode}), flush=True)
    return result


def main():
    started = utc()
    distribution = metadata.distribution("enterprise-master-data-reconciliation")
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    package = Path(mdm.__file__).resolve().parent
    assert not package.is_relative_to(ROOT / "src")
    assert not direct.get("dir_info", {}).get("editable", False)
    assert direct.get("url", "").endswith(".whl")
    source_files = sorted(p for p in (ROOT / "src/mdm").rglob("*")
                          if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    package_files = []
    for path in source_files:
        relative = path.relative_to(ROOT / "src/mdm")
        installed = package / relative
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        wheel_hash = hashlib.sha256(installed.read_bytes()).hexdigest()
        package_files.append({"path": relative.as_posix(), "source_sha256": source_hash,
                              "installed_sha256": wheel_hash, "equal": source_hash == wheel_hash})
    assert package_files and all(item["equal"] for item in package_files)
    with psycopg.connect(os.environ["MDM_TEST_DATABASE_URL"]) as connection:
        server, database = connection.execute("SELECT version(), current_database()").fetchone()
    environment = {
        "python": platform.python_version(), "python_executable": sys.executable,
        "platform": platform.platform(), "postgres": server, "database": database,
        "package_location": str(package), "project_version": distribution.version,
        "direct_url": direct, "installed_wheel_resources": package_files,
        "packages": {name: metadata.version(name) for name in (
            "fastapi", "uvicorn", "pydantic", "pydantic-core", "psycopg", "pytest", "ruff")},
        "dependency_sync_performed": False, "distribution_build_performed": False,
        "dbt_demo_http_replayed": False,
    }
    write_json("environment.json", environment)
    commands = []
    commands.append(run("01-ruff", [str(ROOT / ".venv/bin/ruff"), "check", "src", "tests", "scripts", ".github/scripts"], 120))
    commands.append(run("02-full-postgres-suite", [sys.executable, "-m", "pytest", "-q", "--junitxml=" + str(OUT / "pytest.xml")], 900))
    tree = ET.parse(OUT / "pytest.xml").getroot()
    stdout = (OUT / "02-full-postgres-suite/stdout.txt").read_text()
    tests = re.findall(r"\b(\d+) passed\b", stdout)
    subtests = re.findall(r"\b(\d+) subtests passed\b", stdout)
    failures = len(list(tree.iter("failure")))
    errors = len(list(tree.iter("error")))
    skipped = len(list(tree.iter("skipped")))
    secret = os.environ.get("PGPASSWORD", "")
    leaks = []
    if secret:
        for file in OUT.rglob("*"):
            if file.is_file() and secret.encode() in file.read_bytes():
                leaks.append(file.relative_to(OUT).as_posix())
    report = {
        "passed": all(command["returncode"] == 0 for command in commands)
                  and not (failures or errors or skipped or leaks),
        "started_at": started, "ended_at": utc(), "commands": commands,
        "pytest_summary": {
            "passed_tests_from_stdout": int(tests[-1]) if tests else None,
            "passed_subtests_from_stdout": int(subtests[-1]) if subtests else None,
            "testcase_nodes": len(list(tree.iter("testcase"))),
            "suites": [suite.attrib for suite in tree.iter("testsuite")],
            "failures": failures, "errors": errors, "skipped": skipped,
        },
        "known_database_secret_scan": {"matched_files": leaks, "passed": not leaks},
        "scope": "Ruff and full PostgreSQL suite after copying the concurrent-main compatibility test; existing installed wheel, no sync/build or repeated dbt/demo/HTTP qualification.",
    }
    write_json("qualification.json", report)
    print(json.dumps({"passed": report["passed"], "pytest_summary": report["pytest_summary"]}), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
