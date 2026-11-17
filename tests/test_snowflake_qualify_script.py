"""Offline safety tests for the explicitly opt-in live Snowflake wrapper.

A controlled fake uv is placed first on PATH. These tests never connect to
PostgreSQL or Snowflake and never use actual credentials.
"""
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "infra/snowflake/qualify.sh"
REQUIRED = (
    "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_ROLE",
    "SNOWFLAKE_PRIVATE_KEY_PATH",
)


@pytest.fixture
def sandbox(tmp_path):
    binary = tmp_path / "bin"
    binary.mkdir()
    fake_uv = binary / "uv"
    fake_uv.write_text(
        """#!/usr/bin/env python3
import os
from pathlib import Path
import sys

args = sys.argv[1:]
with Path(os.environ["MDM_FAKE_UV_LOG"]).open("a", encoding="utf-8") as handle:
    handle.write(" ".join(args) + "\\n")
if os.environ.get("MDM_FAKE_FAIL_STAGE") == "dbt-build" and "dbt" in args and "build" in args:
    sys.exit(31)
if "mdm.snowflake" in args:
    if os.environ.get("MDM_FAKE_SKIP_OUTPUT") != "publisher":
        dest = Path(args[args.index("--output") + 1])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text('{"publication":{"snapshot_id":"synthetic"}}\\n')
elif "dbt" in args:
    target = Path(args[args.index("--target-path") + 1])
    target.mkdir(parents=True, exist_ok=True)
    (target / "manifest.json").write_text("{}\\n")
    if "build" in args:
        (target / "run_results.json").write_text("{}\\n")
    else:
        (target / "catalog.json").write_text("{}\\n")
""",
        encoding="utf-8",
    )
    fake_uv.chmod(0o700)
    log = tmp_path / "uv-calls.txt"
    key = tmp_path / "external-synthetic-key"
    key.write_text("placeholder: not an actual key", encoding="utf-8")
    env = dict(os.environ)
    for name in REQUIRED:
        env.pop(name, None)
    env.pop("MDM_DATABASE_URL", None)
    env.pop("MDM_DATABASE_URL_FILE", None)
    env["PATH"] = str(binary) + os.pathsep + env.get("PATH", "")
    env.update({
        "SNOWFLAKE_ACCOUNT": "synthetic-account",
        "SNOWFLAKE_USER": "synthetic-loader",
        "SNOWFLAKE_DATABASE": "SYNTHETIC_DB",
        "SNOWFLAKE_SCHEMA": "SYNTHETIC_RAW",
        "SNOWFLAKE_WAREHOUSE": "SYNTHETIC_XS",
        "SNOWFLAKE_ROLE": "SYNTHETIC_LOADER",
        "SNOWFLAKE_PRIVATE_KEY_PATH": str(key),
        "MDM_DATABASE_URL": "postgresql://synthetic.invalid/never_connected",
        "MDM_FAKE_UV_LOG": str(log),
    })
    return env, log


def invoke(*args, env):
    return subprocess.run(
        ["bash", str(SCRIPT), *map(str, args)], cwd=ROOT,
        env=env, text=True, capture_output=True, check=False, timeout=15,
    )


def test_requires_explicit_opt_in_without_creating_evidence(tmp_path, sandbox):
    env, log = sandbox
    dest = tmp_path / "new"
    for args in [(), ("--wrong", dest), ("--execute-live", dest, "extra"),
                 ("--execute-live", "")]:
        result = invoke(*args, env=env)
        assert result.returncode == 2 and "Usage:" in result.stderr
        assert not dest.exists() and not log.exists()



@pytest.mark.parametrize("mutation", ["unstaged", "staged"])
def test_dirty_tracked_source_is_rejected_before_any_remote_command(
    tmp_path, sandbox, mutation
):
    env, log = sandbox
    checkout = tmp_path / "synthetic-checkout"
    copied = checkout / "infra/snowflake/qualify.sh"
    copied.parent.mkdir(parents=True)
    shutil.copyfile(SCRIPT, copied)
    source = checkout / "tracked.txt"
    source.write_text("committed", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(checkout)],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(checkout), "add", "."], check=True)
    subprocess.run([
        "git", "-C", str(checkout),
        "-c", "user.email=synthetic@example.invalid",
        "-c", "user.name=Synthetic",
        "commit", "-qm", "synthetic source",
    ], check=True)
    source.write_text("uncommitted mutation", encoding="utf-8")
    if mutation == "staged":
        subprocess.run(["git", "-C", str(checkout), "add", "tracked.txt"], check=True)
    dest = tmp_path / "must-not-exist"
    run = subprocess.run(
        ["bash", str(copied), "--execute-live", str(dest)],
        cwd=checkout, env=env, text=True, capture_output=True,
        check=False, timeout=15,
    )
    assert run.returncode == 2
    assert "Tracked source is modified" in run.stderr
    assert not dest.exists() and not log.exists()


def test_refuses_existing_directory_and_preserves_original_bytes(tmp_path, sandbox):
    env, log = sandbox
    dest = tmp_path / "prior-run"
    dest.mkdir()
    (dest / "publication.json").write_bytes(b"old-publication\n")
    (dest / "qualification-status.json").write_bytes(b"old-status\n")
    outcome = invoke("--execute-live", dest, env=env)
    assert outcome.returncode == 2 and "Refusing to overwrite" in outcome.stderr
    assert (dest / "publication.json").read_bytes() == b"old-publication\n"
    assert (dest / "qualification-status.json").read_bytes() == b"old-status\n"
    assert not log.exists()


def test_refuses_dangling_symlink_target(tmp_path, sandbox):
    env, log = sandbox
    dest = tmp_path / "unsafe"
    dest.symlink_to(tmp_path / "not-created", target_is_directory=True)
    assert invoke("--execute-live", dest, env=env).returncode == 2
    assert dest.is_symlink() and not log.exists()


@pytest.mark.parametrize("missing", ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_PRIVATE_KEY_PATH",
                                      "MDM_DATABASE_URL"])
def test_invalid_authorization_never_executes_uv(tmp_path, sandbox, missing):
    env, log = sandbox
    env.pop(missing)
    dest = tmp_path / "must-not-exist"
    result = invoke("--execute-live", dest, env=env)
    assert result.returncode == 2
    assert not dest.exists() and not log.exists()


def test_nonexistent_external_key_fails_preflight(tmp_path, sandbox):
    env, log = sandbox
    env["SNOWFLAKE_PRIVATE_KEY_PATH"] = str(tmp_path / "no-key")
    dest = tmp_path / "must-not-exist"
    result = invoke("--execute-live", dest, env=env)
    assert result.returncode == 2
    assert "readable external file" in result.stderr
    assert not dest.exists() and not log.exists()


def test_success_only_with_fresh_private_directory_and_distinct_dbt_paths(tmp_path, sandbox):
    env, log = sandbox
    dest = tmp_path / "new evidence with spaces"
    result = invoke("--execute-live", dest, env=env)
    assert result.returncode == 0, result.stderr
    assert stat.S_IMODE(dest.stat().st_mode) == 0o700
    assert json.loads((dest / "qualification-status.json").read_text()) == {
        "status": "passed", "last_stage": "complete", "exit_code": 0,
    }
    expected_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert (dest / "commit.txt").read_text().strip() == expected_sha
    calls = log.read_text().splitlines()
    assert len(calls) == 3
    assert "python -m mdm.snowflake --execute --exercise-rollback" in calls[0]
    assert str(dest / "publication.json") in calls[0]
    assert "dbt build" in calls[1] and str(dest / "dbt/build") in calls[1]
    assert "dbt docs generate" in calls[2] and str(dest / "dbt/docs") in calls[2]


def test_zero_exit_without_required_receipt_is_not_a_pass(tmp_path, sandbox):
    env, log = sandbox
    env["MDM_FAKE_SKIP_OUTPUT"] = "publisher"
    dest = tmp_path / "missing-publication"
    result = invoke("--execute-live", dest, env=env)
    assert result.returncode == 1
    assert "Missing expected publisher evidence" in result.stderr
    assert json.loads((dest / "qualification-status.json").read_text()) == {
        "status": "failed", "last_stage": "publisher", "exit_code": 1,
    }
    assert len(log.read_text().splitlines()) == 1
    assert not (dest / "publication.json").exists()


def test_partial_failure_preserves_status_and_prohibits_reuse(tmp_path, sandbox):
    env, log = sandbox
    env["MDM_FAKE_FAIL_STAGE"] = "dbt-build"
    dest = tmp_path / "incomplete"
    result = invoke("--execute-live", dest, env=env)
    assert result.returncode == 31
    assert json.loads((dest / "qualification-status.json").read_text()) == {
        "status": "failed", "last_stage": "dbt-build", "exit_code": 31,
    }
    calls = log.read_text().splitlines()
    assert len(calls) == 2 and "dbt docs" not in "\n".join(calls)
    assert (dest / "commit.txt").is_file()
    assert invoke("--execute-live", dest, env=env).returncode == 2
    assert log.read_text().splitlines() == calls
