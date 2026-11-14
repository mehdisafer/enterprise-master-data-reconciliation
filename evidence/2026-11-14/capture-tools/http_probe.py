"""Qualify real loopback HTTP against the already-populated dedicated database.

Run only as a child command of p02-postgres-runtime/run_with_postgres.py after
the parent agent releases the cluster. This script never starts PostgreSQL.
It writes no repository files and does not start a browser or Docker.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import math
import os
import platform
import secrets
import signal
import socket
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from uuid import UUID

from psycopg.conninfo import conninfo_to_dict

RUNTIME = Path(__file__).resolve().parent
REPOSITORY = RUNTIME.parent / "enterprise-master-data-reconciliation"
PG_RUNTIME = RUNTIME.parent / "p02-postgres-runtime"
HOST, PORT = "127.0.0.1", 8000
EXPECTED_SOURCES = 34
MAX_RESPONSE = 10_000_000


def utc_now():
    return datetime.now(UTC).isoformat()


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def source_hashes():
    paths = sorted(p for p in (REPOSITORY / "src").rglob("*")
                   if p.is_file() and p.suffix in {".py", ".js", ".css", ".html", ".sql"})
    paths += [REPOSITORY / "pyproject.toml", REPOSITORY / "uv.lock"]
    return {str(path.relative_to(REPOSITORY)): sha256(path.read_bytes()) for path in paths}


def main():
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = RUNTIME / "http-runs" / run_id
    output.mkdir(parents=True)
    private = output / "ephemeral-secrets"
    actor_file = private / "actors.json"
    tokens = {role: secrets.token_urlsafe(32) for role in ("requester", "approver", "executor", "reader")}
    invalid_token = secrets.token_urlsafe(32)
    sensitive = [*tokens.values(), invalid_token]
    actor_map = {token: {"name": "http." + role, "role": role} for role, token in tokens.items()}
    started = time.monotonic()
    deadline = started + 180
    before_hashes = source_hashes()
    report = {
        "run_id": run_id, "started_at": utc_now(), "passed": False,
        "transport": "real HTTP over loopback TCP", "host": HOST, "port": PORT,
        "application_executed": False, "browser_executed": False,
        "screenshots_created": False, "container_executed": False,
        "postgres_started_by_this_script": False,
        "readiness_endpoint": "/healthz",
        "readiness_contract": "database connection and schema migration version 1 present",
        "separate_ready_endpoint": False,
        "python": platform.python_version(),
        "packages": {name: version(name) for name in ("uvicorn", "fastapi", "psycopg")},
        "inputs_sha256": before_hashes,
        "requests": [], "checks": [], "failures": [],
    }
    process = None
    stdout = stderr = None
    returned_correlations = set()

    def redact(text):
        for token in sensitive:
            text = text.replace(token, "[REDACTED_EPHEMERAL_TOKEN]")
        return text

    def check(name, condition, observed=None):
        entry = {"name": name, "passed": bool(condition)}
        if observed is not None:
            entry["observed"] = observed
        report["checks"].append(entry)
        if not condition:
            raise AssertionError(name)

    def request(path, *, method="GET", role=None, invalid=False, body=None, headers=None):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("HTTP qualification exceeded its 180 second budget")
        request_headers = dict(headers or {})
        if role:
            request_headers["Authorization"] = "Bearer " + tokens[role]
        elif invalid:
            request_headers["Authorization"] = "Bearer " + invalid_token
        payload = None if body is None else json.dumps(body).encode()
        if payload is not None:
            request_headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection(HOST, PORT, timeout=min(10, remaining))
        request_started = time.monotonic()
        try:
            connection.request(method, path, body=payload, headers=request_headers)
            response = connection.getresponse()
            content = response.read(MAX_RESPONSE + 1)
            safe_headers = {name.lower(): value for name, value in response.getheaders()
                            if name.lower() in {"content-type", "content-length", "content-security-policy",
                                                "x-content-type-options", "referrer-policy", "cache-control",
                                                "x-correlation-id", "www-authenticate"}}
            item = {"method": method, "path": path,
                    "authentication": role or ("invalid bearer" if invalid else "absent"),
                    "status": response.status, "response_bytes": len(content),
                    "response_sha256": sha256(content), "headers": safe_headers,
                    "duration_ms": round((time.monotonic() - request_started) * 1000, 3)}
            report["requests"].append(item)
            check("bounded response " + method + " " + path, len(content) <= MAX_RESPONSE)
            check("ephemeral tokens absent from response " + path,
                  not any(token.encode() in content for token in sensitive))
            correlation = safe_headers.get("x-correlation-id")
            valid_uuid = False
            try:
                valid_uuid = str(UUID(correlation)) == correlation
            except (TypeError, ValueError, AttributeError):
                pass
            check("unique server correlation " + path,
                  valid_uuid and correlation not in returned_correlations)
            returned_correlations.add(correlation)
            check("security response headers " + path,
                  safe_headers.get("x-content-type-options") == "nosniff"
                  and safe_headers.get("referrer-policy") == "no-referrer"
                  and safe_headers.get("cache-control") == "no-store"
                  and "default-src 'self'" in safe_headers.get("content-security-policy", "")
                  and "frame-ancestors 'none'" in safe_headers.get("content-security-policy", ""))
            return response.status, content, safe_headers
        finally:
            connection.close()

    try:
        private.mkdir(mode=0o700)
        with os.fdopen(os.open(actor_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as handle:
            json.dump(actor_map, handle)
        report["secret_directory_mode"] = oct(private.stat().st_mode & 0o777)
        report["actor_file_mode"] = oct(actor_file.stat().st_mode & 0o777)
        config = json.loads((PG_RUNTIME / "connection.json").read_text())
        dsn = os.environ.get("MDM_DATABASE_URL", "")
        parts = conninfo_to_dict(dsn)
        check("dedicated local database target",
              parts.get("host") == HOST and parts.get("dbname") == "mdm"
              and parts.get("port") == str(config["port"]))
        report["database_target"] = {key: parts.get(key) for key in ("host", "port", "dbname", "user")}
        check("private ephemeral actor files", private.stat().st_mode & 0o777 == 0o700
              and actor_file.stat().st_mode & 0o777 == 0o600)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
            reservation.bind((HOST, PORT))
        environment = os.environ.copy()
        environment.pop("MDM_ACTORS_JSON", None)
        environment.pop("MDM_DATABASE_URL_FILE", None)
        environment.pop("DBT_ENV_SECRET_PG_PASSWORD", None)
        environment["MDM_ACTORS_JSON_FILE"] = str(actor_file)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        command = [sys.executable, "-m", "uvicorn", "mdm.api:app", "--host", HOST, "--port", str(PORT),
                   "--workers", "1", "--limit-concurrency", "32", "--no-access-log",
                   "--timeout-graceful-shutdown", "20"]
        report["server_command"] = command
        stdout = (output / "server-stdout.txt").open("w")
        stderr = (output / "server-stderr.txt").open("w")
        process = subprocess.Popen(command, cwd=REPOSITORY, env=environment, stdout=stdout, stderr=stderr)
        report["application_executed"] = True
        report["server_pid"] = process.pid
        readiness_deadline = time.monotonic() + 30
        attempts = 0
        while True:
            attempts += 1
            if process.poll() is not None:
                raise RuntimeError("Uvicorn exited before readiness; inspect retained server stderr")
            try:
                status, content, _ = request("/healthz")
                if status == 200:
                    check("live database readiness", json.loads(content) == {"status": "ok"})
                    break
            except (ConnectionRefusedError, ConnectionResetError):
                pass
            if time.monotonic() >= readiness_deadline:
                raise TimeoutError("Uvicorn did not become ready within 30 seconds")
            time.sleep(0.2)
        report["readiness_attempts"] = attempts

        for endpoint, source, content_type in (
            ("/", "index.html", "text/html"),
            ("/assets/app.js", "app.js", "text/javascript"),
            ("/assets/style.css", "style.css", "text/css"),
        ):
            status, content, headers = request(endpoint)
            check("served source asset " + endpoint,
                  status == 200 and content == (REPOSITORY / "src/mdm/static" / source).read_bytes()
                  and headers.get("content-type", "").startswith(content_type),
                  {"source_file": "src/mdm/static/" + source, "bytes": len(content), "sha256": sha256(content)})
        for path in ("/api/overview", "/api/me", "/api/openapi.json", "/metrics"):
            for invalid in (False, True):
                status, _, headers = request(path, invalid=invalid)
                check("authentication denied " + path + (" invalid" if invalid else " absent"),
                      status == 401 and headers.get("www-authenticate") == "Bearer")
        for role in tokens:
            status, content, _ = request("/api/me", role=role)
            check("server actor mapping " + role,
                  status == 200 and json.loads(content) == {"name": "http." + role, "role": role})

        client_correlation = "00000000-0000-4000-8000-000000000001"
        status, content, headers = request("/api/overview", role="requester",
                                           headers={"X-Correlation-ID": client_correlation})
        check("caller cannot select the server correlation", headers.get("x-correlation-id") != client_correlation)
        check("authenticated overview", status == 200)
        overview = json.loads(content)
        snapshot, quality = overview["snapshot"], overview["quality"]
        before_snapshot = canonical_hash(snapshot)
        status, _, _ = request("/api/reconcile", method="POST", body={})
        check("unauthenticated mutation denied", status == 401)
        status, _, _ = request("/api/reconcile", method="POST", role="requester", body={})
        check("requester cannot reconcile", status == 403)
        reference = {row["source_key"]: row["golden_id"] for row in snapshot["crosswalk"]}
        reporting_rows = [row for row in snapshot["consumer_crosswalk"] if row["consumer"] == "reporting"]
        consumed = {row["source_key"]: row["golden_id"] for row in reporting_rows}
        active = [row for row in snapshot["groups"] if row["status"] == "active"]
        check("demo preserves all 34 source identities",
              quality["sources"] == EXPECTED_SOURCES == len(snapshot["sources"]) == len(reference)
              == len(snapshot["crosswalk"]) and snapshot["contract_version"] == "snapshot.v1")
        check("34 reporting mappings equal the reference",
              len(reporting_rows) == EXPECTED_SOURCES and consumed == reference
              and quality["crosswalk_coverage"] == 1 and quality["unconsumed_events"] == 0)
        check("active golden count matches quality", len(active) == quality["active_groups"] and bool(active))
        executed_kinds = Counter(row["kind"] for row in snapshot["decisions"] if row["status"] == "executed")
        check("real merge and unmerge ledger is present", executed_kinds["merge"] > 0 and executed_kinds["unmerge"] > 0)
        report["business_state"] = {
            "source_count": quality["sources"], "reference_mappings": len(reference),
            "reporting_mappings": len(reporting_rows), "mapping_mismatches": sum(consumed.get(k) != v for k, v in reference.items()),
            "active_golden_records": len(active), "candidates": len(snapshot["candidates"]),
            "executed_decisions_by_kind": dict(executed_kinds), "quality": quality,
            "snapshot_before_sha256": before_snapshot,
            "golden_attributes_with_provenance": sum(bool(row.get("provenance")) for row in active),
        }
        golden = next(row for row in active if row.get("provenance"))
        status, content, _ = request("/api/golden/" + golden["golden_id"] + "/history", role="requester")
        history = json.loads(content)
        check("live golden temporal history", status == 200 and bool(history)
              and all(row["golden_id"] == golden["golden_id"] and row.get("known_from") and row.get("valid_from") for row in history))
        report["golden_history"] = {"golden_id": golden["golden_id"], "rows": len(history),
                                    "provenance_attributes": sorted(golden["provenance"])}
        candidate = next(row for row in snapshot["candidates"]
                         if reference[row["left_key"]] != reference[row["right_key"]]
                         and row["disposition"] != "dismissed")
        groups = [reference[candidate["left_key"]], reference[candidate["right_key"]]]
        status, content, _ = request("/api/preview-merge", method="POST", role="requester", body={"group_ids": groups})
        preview = json.loads(content)
        check("live evidence preview", status == 200 and set(preview["group_ids"]) == set(groups)
              and set(preview["expected_versions"]) == set(groups) and len(preview["source_keys"]) >= 2
              and isinstance(preview["provenance"], dict))
        report["evidence_preview"] = {"candidate_id": candidate["candidate_id"],
                                      "source_count": len(preview["source_keys"]),
                                      "hard_conflicts": preview["hard_conflicts"],
                                      "provenance_attribute_count": len(preview["provenance"])}

        status, content, _ = request("/api/openapi.json", role="reader")
        specification = json.loads(content)
        check("authenticated API specification", status == 200
              and {"/healthz", "/api/overview", "/api/preview-merge", "/metrics"}.issubset(specification["paths"]))
        report["openapi"] = {"title": specification["info"]["title"], "version": specification["info"]["version"],
                             "path_count": len(specification["paths"])}
        status, content, _ = request("/metrics", role="reader")
        metrics = {parts[0]: float(parts[1]) for line in content.decode().splitlines() if (parts := line.split())}
        check("live numeric metrics", status == 200 and all(math.isfinite(v) for v in metrics.values())
              and metrics["mdm_sources"] == EXPECTED_SOURCES
              and metrics["mdm_active_groups"] == len(active)
              and metrics["mdm_crosswalk_coverage"] == 1 and metrics["mdm_unconsumed_events"] == 0)
        report["metrics"] = metrics
        status, content, _ = request("/api/overview", role="reader")
        after_snapshot = canonical_hash(json.loads(content)["snapshot"])
        check("HTTP read and denied write checks preserved the snapshot", status == 200 and before_snapshot == after_snapshot)
        report["business_state"]["snapshot_after_sha256"] = after_snapshot
    except Exception as exc:  # noqa: BLE001 -- preserve any failed qualification and always clean up.
        report["failures"].append({"type": type(exc).__name__, "message": redact(str(exc))})
    finally:
        if process is not None:
            stopped_by = "already exited"
            shutdown_started = time.monotonic()
            if process.poll() is None:
                stopped_by = "SIGTERM"
                process.send_signal(signal.SIGTERM)
                try:
                    process.wait(timeout=25)
                except subprocess.TimeoutExpired:
                    stopped_by = "SIGKILL after 25 second shutdown timeout"
                    process.kill()
                    process.wait(timeout=5)
            report["server_shutdown"] = {"method": stopped_by, "exit_code": process.returncode,
                                          "duration_seconds": time.monotonic() - shutdown_started,
                                          "graceful": False}
        for handle in (stdout, stderr):
            if handle is not None:
                handle.close()
        redacted_files = []
        for path in output.glob("server-*.txt"):
            original = path.read_text(errors="replace")
            safe = redact(original)
            if safe != original:
                path.write_text(safe)
                redacted_files.append(path.name)
        report["server_logs_token_redactions"] = redacted_files
        if redacted_files:
            report["failures"].append({"type": "SecretLeak", "message": "An ephemeral token reached server logs; retained log redacted"})
        if process is not None:
            shutdown_log = (output / "server-stderr.txt").read_text(errors="replace")
            markers = ["Shutting down", "Waiting for application shutdown.",
                       "Application shutdown complete.", f"Finished server process [{process.pid}]"]
            marker_positions = [shutdown_log.find(marker) for marker in markers]
            lifecycle_complete = all(position >= 0 for position in marker_positions) and marker_positions == sorted(marker_positions)
            listener_closed = False
            try:
                with socket.create_connection((HOST, PORT), timeout=1):
                    listener_state = "connection still accepted"
            except ConnectionRefusedError:
                listener_closed = True
                listener_state = "connection refused after process exit"
            except OSError as exc:
                listener_state = type(exc).__name__
            # Uvicorn 0.52.1 restores handlers and re-raises captured SIGTERM
            # after its graceful shutdown. A -15 exit alone is insufficient:
            # require the completed lifespan log sequence and closed listener.
            graceful = (stopped_by == "SIGTERM" and process.returncode in {0, -signal.SIGTERM}
                        and lifecycle_complete and listener_closed
                        and "timeout graceful shutdown exceeded" not in shutdown_log)
            report["server_shutdown"].update({
                "graceful": graceful, "lifecycle_completion_logged": lifecycle_complete,
                "listener_closed": listener_closed, "listener_state": listener_state,
                "signal_policy": "Uvicorn re-raises captured SIGTERM after graceful shutdown",
            })
            if not graceful:
                report["failures"].append({"type": "ShutdownFailure", "message": "Uvicorn shutdown completion was not established"})
        actor_file.unlink(missing_ok=True)
        if private.exists():
            private.rmdir()
        report["ephemeral_secrets_removed"] = not private.exists()
        log_path = output / "server-stderr.txt"
        events = []
        if log_path.exists():
            for line in log_path.read_text(errors="replace").splitlines():
                try:
                    entry = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if isinstance(entry, dict) and entry.get("event") == "http.request":
                    events.append(entry)
        linked = {entry.get("correlation_id") for entry in events}
        report["http_observability"] = {"structured_http_events": len(events),
                                         "response_correlation_count": len(returned_correlations),
                                         "response_correlations_found_in_logs": len(returned_correlations & linked),
                                         "all_response_correlations_found": returned_correlations.issubset(linked)}
        if returned_correlations and not returned_correlations.issubset(linked):
            report["failures"].append({"type": "CorrelationFailure", "message": "A response correlation was missing from structured HTTP logs"})
        report["repository_runtime_inputs_unchanged"] = source_hashes() == before_hashes
        if not report["repository_runtime_inputs_unchanged"]:
            report["failures"].append({"type": "InputChanged", "message": "An application runtime input changed during qualification"})
        report["completed_at"] = utc_now()
        report["duration_seconds"] = time.monotonic() - started
        report["passed"] = not report["failures"] and bool(report["requests"])
        report["evidence_files"] = {path.name: {"bytes": path.stat().st_size, "sha256": sha256(path.read_bytes())}
                                     for path in output.glob("server-*.txt")}
        (output / "http-report.json").write_text(redact(json.dumps(report, indent=2)) + "\n")
        print(json.dumps({"http_report": str(output / "http-report.json"), "passed": report["passed"],
                          "requests": len(report["requests"]), "browser_executed": False,
                          "container_executed": False, "secrets_removed": report["ephemeral_secrets_removed"]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
