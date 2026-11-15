#!/usr/bin/env python3
"""Verify a non-editable installation, including SQL and browser assets.

Run after building an sdist, rebuilding its wheel, and installing that wheel
with --no-deps. This catches packaging omissions that an editable test run hides.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata, resources
import json
from pathlib import Path
import subprocess
import sys

import mdm


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / "src" / "mdm"
    installed = Path(mdm.__file__).resolve().parent
    bundled = resources.files("mdm")
    expected = sorted(path for path in source.rglob("*")
                      if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
    files = []
    for path in expected:
        relative = path.relative_to(source).as_posix()
        target = bundled.joinpath(relative)
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        installed_hash = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
        files.append({"path": relative, "source_sha256": source_hash,
                      "installed_sha256": installed_hash, "equal": source_hash == installed_hash})
    dist = metadata.distribution("enterprise-master-data-reconciliation")
    direct_url = json.loads(dist.read_text("direct_url.json") or "{}")
    entrypoints = [entry.value for entry in dist.entry_points if entry.group == "console_scripts" and entry.name == "mdm"]
    cli = subprocess.run([sys.executable, "-m", "mdm.cli", "--help"], capture_output=True, text=True, timeout=10)
    checks = {
        "installed_outside_source": not installed.is_relative_to(source),
        "not_editable": not direct_url.get("dir_info", {}).get("editable", False),
        "installed_from_wheel": direct_url.get("url", "").endswith(".whl"),
        "all_source_resources_preserved": bool(files) and all(item["equal"] for item in files),
        "entrypoint": entrypoints == ["mdm.cli:main"],
        "cli_usable": cli.returncode == 0 and "benchmark" in cli.stdout and "migrate" in cli.stdout,
    }
    report = {"passed": all(checks.values()), "checks": checks, "version": dist.version,
              "installed_package_path": str(installed), "files": files,
              "core_metadata_version": dist.metadata.get("Metadata-Version"),
              "wheel_metadata": dist.read_text("WHEEL"),
              "cli_returncode": cli.returncode, "cli_stdout": cli.stdout, "cli_stderr": cli.stderr}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "resources": len(files), "checks": checks}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
