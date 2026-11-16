"""Record mandatory mainline qualification without guessing a push change range.

CircleCI GitHub App does not provide a trustworthy previous-qualified commit
in this job. A first-parent diff misses earlier changes in multi-commit pushes.
Always run the real PostgreSQL/dbt job on main; this script records selection,
not a test result. The CircleCI workflow's branch filter keeps it off PRs.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


def select_scope(*, expected_sha: str, checkout_sha: str) -> dict[str, object]:
    """Fail closed for source mismatches; never make a docs-only runtime skip."""
    if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        raise ValueError("Expected a full CircleCI checkout SHA")
    if checkout_sha != expected_sha:
        raise ValueError("CircleCI checkout differs from the source commit")
    return {
        "commit": checkout_sha,
        "selection": "mandatory-mainline-qualification",
        "runtime_requested": True,
        "changed_paths": None,
        "reason": "A first-parent diff cannot safely classify multi-commit GitHub App pushes",
    }


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    report = select_scope(expected_sha=os.environ.get("CIRCLE_SHA1", ""), checkout_sha=head)
    directory = Path("artifacts")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "scope.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
