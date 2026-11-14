uv run --no-sync python - <<'PY'
import json, subprocess
from pathlib import Path

directory = Path("artifacts")
directory.mkdir(exist_ok=True)
forbidden = directory / "forbidden-restore.json"
stdout = directory / "second-restore.stdout.txt"
stderr = directory / "second-restore.stderr.txt"
returncode = None
execution_error = None
timed_out = False
with stdout.open("wb") as output, stderr.open("wb") as errors:
    try:
        process = subprocess.run(
            ["bash", "scripts/restore.sh", "artifacts/reference.dump", "--expect-db", "mdm_restore",
             "--report", str(forbidden)],
            stdout=output, stderr=errors, timeout=60, check=False,
        )
        returncode = process.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        execution_error = "TimeoutExpired"
    except OSError as exc:
        execution_error = type(exc).__name__
response = None
parse_error = None
try:
    response = json.loads(stderr.read_bytes())
except (json.JSONDecodeError, UnicodeDecodeError) as exc:
    parse_error = type(exc).__name__
checks = {
    "exit_code_is_one": returncode == 1,
    "completed_within_timeout": not timed_out and execution_error is None,
    "restore_verified_is_false": isinstance(response, dict) and response.get("restore_verified") is False,
    "expected_error_type": isinstance(response, dict) and response.get("error_type") == "OperationError",
    "expected_reason": isinstance(response, dict) and response.get("reason") == "Restore target is not empty and isolated",
    "forbidden_report_absent": not forbidden.exists() and not forbidden.is_symlink(),
}
report = {
    "passed": all(checks.values()), "checks": checks, "returncode": returncode,
    "timeout_seconds": 60, "timed_out": timed_out, "execution_error": execution_error,
    "response": response, "parse_error": parse_error,
    "stdout_path": str(stdout), "stderr_path": str(stderr),
}
(directory / "second-restore-rejection.json").write_text(json.dumps(report, indent=2) + "\n")
if not report["passed"]:
    raise SystemExit("Second restore did not fail for the expected populated-target reason; inspect retained evidence")
PY
