#!/usr/bin/env python3
"""Scan publishable files and optional reachable Git history without echoing secrets.

This small, dependency-free control detects common credential formats, populated
database URLs, and accidentally tracked secret files. It is deliberately not a
claim that all secrets can be detected. Findings contain locations and rule IDs
only. Oversized/binary inputs are reported as unscanned, never called clean.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import subprocess
import sys


RULES = {
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github-token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{36,255}\b"),
    "github-fine-grained-token": re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{60,255}\b"),
    "aws-access-key": re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "google-api-key": re.compile(rb"\bAIza[0-9A-Za-z_-]{35}\b"),
    "slack-token": re.compile(rb"\bxox[baprs]-[0-9A-Za-z-]{20,200}\b"),
    "database-password-in-url": re.compile(
        rb"(?:postgres(?:ql)?|mysql|snowflake|mongodb(?:\+srv)?)://[^:/\s'\"]+:(?P<credential>[^@\s'\"]+)@"
    ),
    "literal-secret-assignment": re.compile(
        rb"(?i)(?:password|api[_-]?key|client[_-]?secret|access[_-]?token)\s*[=:]\s*['\"]"
        rb"(?P<credential>[A-Za-z0-9_./+=-]{24,200})['\"]"
    ),
}
MAX_BYTES = 4 * 1024 * 1024
SAFE_PLACEHOLDERS = {b"ci-ephemeral-only", b"example-password", b"replace-me", b"placeholder"}
IGNORED_DIRECTORIES = {".git", ".venv", ".secrets", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}


@dataclass(frozen=True)
class Finding:
    location: str
    line: int
    rule: str


def secret_path(path: str) -> bool:
    parts = Path(path).parts
    name = Path(path).name.lower()
    if ".secrets" in parts or name in {"id_rsa", "id_ed25519", ".pgpass", ".netrc"}:
        return True
    if name == ".env" or (name.startswith(".env.") and not name.endswith((".example", ".template"))):
        return True
    return name.endswith((".p12", ".pfx", ".key"))


def scan(location: str, data: bytes) -> list[Finding]:
    results = []
    for rule, pattern in RULES.items():
        for match in pattern.finditer(data):
            credential = match.groupdict().get("credential", b"")
            if credential:
                if credential.lower() in SAFE_PLACEHOLDERS or any(x in credential for x in (b"${", b"{", b"<")):
                    continue
            results.append(Finding(location, data.count(b"\n", 0, match.start()) + 1, rule))
    return results


def git(root: Path, *args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args], input=data, capture_output=True, check=True
    ).stdout


def working_files(root: Path) -> tuple[list[Path], bool]:
    try:
        paths = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0")
        return sorted({root / path.decode("utf-8", "surrogateescape") for path in paths if path}), True
    except subprocess.CalledProcessError:
        return sorted(
            path for path in root.rglob("*")
            if path.is_file() and not (set(path.relative_to(root).parts) & IGNORED_DIRECTORIES)
        ), False


def history_blobs(root: Path):
    objects = git(root, "rev-list", "--objects", "--all").splitlines()
    if len(objects) > 50000:
        raise ValueError("History object limit exceeded; run a scoped, reviewed full-history scanner")
    names = {}
    for record in objects:
        sha, _, name = record.partition(b" ")
        names[sha] = name.decode("utf-8", "replace") or "(unnamed)"
    if not names:
        return
    checked = git(
        root, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
        data=b"\n".join(names) + b"\n",
    )
    for row in checked.splitlines():
        sha, kind, size = row.split(b" ")
        if kind != b"blob":
            continue
        path = names[sha]
        location = f"git:{sha.decode()[:12]}:{path}"
        if int(size) > MAX_BYTES:
            yield location, path, None
        else:
            yield location, path, git(root, "cat-file", "blob", sha.decode())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    findings: list[Finding] = []
    unscanned = []
    files, is_git = working_files(root)
    scanned_files = 0
    history_count = 0
    for path in files:
        label = str(path.relative_to(root))
        if secret_path(label):
            findings.append(Finding(label, 0, "secret-file-path"))
        if path.is_symlink():
            unscanned.append({"location": label, "reason": "symlink"})
            continue
        if not path.exists():
            continue  # A staged deletion remains in the index until commit.
        if path.stat().st_size > MAX_BYTES:
            unscanned.append({"location": label, "reason": "oversized"})
            continue
        data = path.read_bytes()
        findings.extend(scan(label, data))
        scanned_files += 1
        if b"\0" in data:
            unscanned.append({"location": label, "reason": "binary: common-byte-patterns-only"})
    if args.history:
        if not is_git:
            unscanned.append({"location": "git-history", "reason": "repository-unavailable"})
        else:
            for label, path, data in history_blobs(root):
                if secret_path(path):
                    findings.append(Finding(label, 0, "secret-file-path"))
                if data is None:
                    unscanned.append({"location": label, "reason": "oversized"})
                    continue
                history_count += 1
                findings.extend(scan(label, data))
                if b"\0" in data:
                    unscanned.append({"location": label, "reason": "binary: common-byte-patterns-only"})
    report = {
        "schema_version": 1,
        "scan_scope": "working-tree-and-reachable-git-history" if args.history else "working-tree",
        "files_scanned": scanned_files,
        "historical_blobs_scanned": history_count,
        "findings": [asdict(item) for item in sorted(set(findings), key=lambda f: (f.location, f.line, f.rule))],
        "unscanned_or_limited": unscanned,
        "credential_values_printed": False,
        "complete_secret_detection_claimed": False,
    }
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    print(payload, end="")
    return 1 if findings or unscanned else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(json.dumps({"scan_completed": False, "error_type": type(exc).__name__}), file=sys.stderr)
        raise SystemExit(2) from None
