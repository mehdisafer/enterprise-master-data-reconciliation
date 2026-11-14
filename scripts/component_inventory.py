#!/usr/bin/env python3
"""Inventory the installed environment and retain license evidence for review.

Metadata is a publisher declaration, not legal assurance. --check fails for
missing license evidence or an explicit proprietary classification. Copyleft and
unparsed declarations remain visible review items; they are not relabelled MIT.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import sys


LOCAL_PACKAGE = "enterprise-master-data-reconciliation"


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def inventory() -> dict:
    components = []
    for dist in metadata.distributions():
        name = dist.metadata.get("Name", "UNKNOWN")
        if normalize_name(name) == LOCAL_PACKAGE:
            continue
        declared = (dist.metadata.get("License-Expression") or dist.metadata.get("License") or "").strip()
        classifiers = [item for item in dist.metadata.get_all("Classifier", []) if item.startswith("License ::")]
        license_files = [str(file) for file in (dist.files or []) if re.search(r"(?:license|copying|notice)", str(file), re.I)]
        normalized = declared.lower()
        if "proprietary" in normalized or any("Proprietary" in item for item in classifiers):
            state = "explicit-proprietary-review-required"
        elif not declared and not classifiers and not license_files:
            state = "missing-license-evidence"
        elif "lgpl" in normalized or "lesser general public" in normalized or "mozilla" in normalized:
            state = "distribution-obligations-review"
        elif "gpl" in normalized or "general public license" in normalized:
            state = "copyleft-scope-review"
        else:
            state = "publisher-metadata-recorded"
        components.append({
            "name": name,
            "version": dist.version,
            "purl": f"pkg:pypi/{normalize_name(name)}@{dist.version}",
            "license_expression": dist.metadata.get("License-Expression"),
            "license_declaration_excerpt": declared[:1200] if declared else None,
            "license_declaration_sha256": hashlib.sha256(declared.encode()).hexdigest() if declared else None,
            "license_classifiers": classifiers,
            "license_files": sorted(license_files),
            "project_urls": dist.metadata.get_all("Project-URL", []),
            "review_status": state,
        })
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "commit": os.environ.get("GITHUB_SHA"),
        "components": sorted(components, key=lambda item: normalize_name(item["name"])),
        "scope": "installed-python-environment; OS and container-image layers are separate",
        "repo_license": "pending-maintainer-approval",
        "certification": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = inventory()
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    else:
        print(payload, end="")
    blocked = [item["name"] for item in report["components"] if item["review_status"] in {
        "missing-license-evidence", "explicit-proprietary-review-required"
    }]
    if args.check and blocked:
        print(json.dumps({"license_metadata_check": "needs-review", "components": blocked}), file=sys.stderr)
        return 1
    if args.output:
        print(json.dumps({"components": len(report["components"]), "inventory": str(args.output), "certification": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
