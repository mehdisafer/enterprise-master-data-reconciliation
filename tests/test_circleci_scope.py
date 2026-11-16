"""Guard the CircleCI mainline scope against multi-commit false skips."""

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

_SCOPE_MODULE = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts" / "circleci_scope.py"),
    run_name="test_import_scope",
)
select_scope = _SCOPE_MODULE["select_scope"]


def test_scope_never_skips_valid_source():
    sha = "a" * 40
    record = select_scope(expected_sha=sha, checkout_sha=sha)
    assert record["runtime_requested"] is True
    assert record["selection"] == "mandatory-mainline-qualification"
    assert record["changed_paths"] is None


@pytest.mark.parametrize("expected,actual", [("", "a" * 40), ("b" * 40, "a" * 40), ("x" * 40, "x" * 40)])
def test_invalid_or_mismatched_source_is_rejected(expected, actual):
    with pytest.raises(ValueError):
        select_scope(expected_sha=expected, checkout_sha=actual)


def test_multi_commit_push_with_docs_last_still_qualifies(tmp_path):
    def git(*args):
        return subprocess.run(["git", *args], cwd=tmp_path, text=True, check=True, capture_output=True).stdout.strip()

    git("init", "-q")
    git("config", "user.name", "CI scope test")
    git("config", "user.email", "ci-scope@example.invalid")
    (tmp_path / "app.py").write_text("VERSION = 1\n")
    git("add", ".")
    git("commit", "-qm", "qualified baseline")
    (tmp_path / "app.py").write_text("VERSION = 2\n")
    git("commit", "-qam", "runtime change")
    (tmp_path / "README.md").write_text("Documentation only at last commit\n")
    git("add", ".")
    git("commit", "-qm", "docs only")
    head = git("rev-parse", "HEAD")
    parent = git("rev-parse", "HEAD^")
    assert git("diff", "--name-only", parent, head) == "README.md"
    script = Path(__file__).resolve().parents[1] / "scripts" / "circleci_scope.py"
    env = {**os.environ, "CIRCLE_SHA1": head}
    subprocess.run([sys.executable, str(script)], cwd=tmp_path, env=env, check=True, capture_output=True, text=True)
    record = json.loads((tmp_path / "artifacts" / "scope.json").read_text())
    assert record["commit"] == head
    assert record["runtime_requested"] is True


def test_scope_fails_without_circleci_commit(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    script = Path(__file__).resolve().parents[1] / "scripts" / "circleci_scope.py"
    env = {**os.environ, "CIRCLE_SHA1": ""}
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert not (tmp_path / "artifacts" / "scope.json").exists()
