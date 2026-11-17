"""Execute the exact GitHub Actions scope selector against synthetic Git histories."""

import json
import os
import subprocess
import sys
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "quality.yml"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=True
    ).stdout.strip()


def _commit(root: Path, filename: str, content: str, message: str) -> str:
    path = root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(root, "add", filename)
    _git(root, "commit", "-qm", message)
    return _git(root, "rev-parse", "HEAD")


def _new_repo(root: Path) -> tuple[str, str]:
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Scope QA")
    _git(root, "config", "user.email", "scope@example.invalid")
    base = _commit(root, "src/app.py", "version = 1\n", "baseline")
    branch = _git(root, "branch", "--show-current")
    return base, branch


def _selector_code() -> str:
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = lines.index("          python3 - <<'PY'")
    end = lines.index("          PY", start + 1)
    return "\n".join(line[10:] for line in lines[start + 1 : end]) + "\n"


def _run_selector(root: Path, event_name: str, event: dict) -> tuple[dict, dict]:
    event_path = root / "github-event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    output_path = root / "scope-output.txt"
    env = {
        **os.environ,
        "GITHUB_EVENT_NAME": event_name,
        "GITHUB_EVENT_PATH": str(event_path),
        "GITHUB_SHA": _git(root, "rev-parse", "HEAD"),
        "GITHUB_OUTPUT": str(output_path),
        "GITHUB_STEP_SUMMARY": str(root / "scope-summary.md"),
    }
    cmd = subprocess.run(
        [sys.executable, "-c", _selector_code()],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert cmd.returncode == 0, cmd.stderr
    report = json.loads(cmd.stdout.strip().splitlines()[-1])
    outputs = dict(line.split("=", 1) for line in output_path.read_text().splitlines())
    return report, outputs


def _pr_event(base: str, head: str, *, before: str | None = None, after: str | None = None) -> dict:
    payload = {"action": "synchronize", "pull_request": {"base": {"sha": base}, "head": {"sha": head}}}
    if before is not None:
        payload["before"] = before
    if after is not None:
        payload["after"] = after
    return payload


def test_pr_runtime_change_then_docs_only_synchronize_must_run(tmp_path):
    base, branch = _new_repo(tmp_path)
    _git(tmp_path, "checkout", "-qb", "feature")
    earlier_code = _commit(tmp_path, "src/app.py", "version = 2\n", "runtime change")
    head = _commit(tmp_path, "README.md", "Some docs\n", "docs last")
    _git(tmp_path, "checkout", "-q", branch)
    _git(tmp_path, "merge", "--no-ff", "-qm", "synthetic PR merge", "feature")
    report, outputs = _run_selector(tmp_path, "pull_request", _pr_event(base, head, before=earlier_code, after=head))
    assert report["runtime"] is True
    assert report["selection"] == "full-pr-diff"
    assert outputs["runtime"] == "true"


def test_genuine_docs_only_pr_synchronize_may_skip(tmp_path):
    base, branch = _new_repo(tmp_path)
    _git(tmp_path, "checkout", "-qb", "feature")
    previous = _commit(tmp_path, "README.md", "First docs\n", "docs first")
    head = _commit(tmp_path, "README.md", "Latest docs\n", "docs second")
    _git(tmp_path, "checkout", "-q", branch)
    _git(tmp_path, "merge", "--no-ff", "-qm", "synthetic PR merge", "feature")
    report, outputs = _run_selector(tmp_path, "pull_request", _pr_event(base, head, before=previous, after=head))
    assert report["runtime"] is False
    assert outputs["runtime"] == "false"


def test_main_push_code_then_docs_in_one_event_must_run(tmp_path):
    base, _ = _new_repo(tmp_path)
    _commit(tmp_path, "src/app.py", "version = 2\n", "runtime")
    head = _commit(tmp_path, "README.md", "docs\n", "docs")
    report, outputs = _run_selector(tmp_path, "push", {"before": base, "after": head})
    assert report["runtime"] is True
    assert outputs["runtime"] == "true"


def test_docs_only_main_push_can_skip(tmp_path):
    base, _ = _new_repo(tmp_path)
    head = _commit(tmp_path, "README.md", "docs\n", "docs")
    report, outputs = _run_selector(tmp_path, "push", {"before": base, "after": head})
    assert report["runtime"] is False
    assert outputs["runtime"] == "false"


def test_missing_push_base_fails_closed(tmp_path):
    _, _ = _new_repo(tmp_path)
    head = _commit(tmp_path, "README.md", "docs\n", "docs")
    report, outputs = _run_selector(tmp_path, "push", {"before": "0" * 40, "after": head})
    assert report["runtime"] is True
    assert report["selection"] == "unavailable-reference-full-qualification"
    assert outputs["runtime"] == "true"


def test_inconsistent_pr_head_forces_runtime(tmp_path):
    base, branch = _new_repo(tmp_path)
    _git(tmp_path, "checkout", "-qb", "feature")
    head = _commit(tmp_path, "README.md", "docs\n", "docs")
    _git(tmp_path, "checkout", "-q", branch)
    _git(tmp_path, "merge", "--no-ff", "-qm", "synthetic PR merge", "feature")
    report, outputs = _run_selector(tmp_path, "pull_request", _pr_event(base, head, before=base, after="b" * 40))
    assert report["runtime"] is True
    assert report["selection"] == "inconsistent-pr-head-full-qualification"
    assert outputs["runtime"] == "true"


def test_manual_dispatch_always_runs(tmp_path):
    _new_repo(tmp_path)
    report, outputs = _run_selector(tmp_path, "workflow_dispatch", {})
    assert report["runtime"] is True
    assert report["selection"] == "manual-full-qualification"
    assert outputs["runtime"] == "true"
