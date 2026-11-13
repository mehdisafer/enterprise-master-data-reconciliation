# Operating and recovering the reference deployment

This runbook covers the single-host Linux container reference, the PostgreSQL
integration workflow and the explicitly authorized Snowflake path. Commands act
on the named dedicated environment. The business API is bound to loopback; the
repository's visibility does not expose a running service.

## Versions and qualification scope

| Component | Selected version or contract | Evidence boundary |
| --- | --- | --- |
| Python image | `python:3.12.14-slim` | Version tag exists in the official image registry; the container job records its actual built image. |
| PostgreSQL image | `postgres:17.12` | Selected after the 12 November 2026 security update; CI records `version()` and the pulled digest. |
| uv | `0.13.6` | The Docker build and CI install from the same lock. |
| Python dependencies | `uv.lock` | Direct constraints are in `pyproject.toml`; the lock captures transitive versions and hashes. |
| dbt | PostgreSQL and Snowflake adapters in the lock | SQL compilation is distinct from executing models and data tests. |
| Source and rules | `contracts/` | Input data is synthetic; repository licensing awaits maintainer approval. |

Image version tags can be moved by their publishers. Release evidence records
resolved image digests; the source does not pretend a tag is immutable. External
GitHub Actions are pinned to full commit SHAs verified against their release refs.

The local authoring sandbox refused socket creation, including Unix sockets, so
starting PostgreSQL there was not a database integration. The CI workflow runs
real PostgreSQL, dbt, restoration and container checks when a runner is available. The initial workflow failed before runner assignment and produced no test or deployment artifacts. Its raw results determine
their acceptance status. An unexecuted or failed CI job is not a passed check.
Snowflake requires a separate dedicated authorized account configuration; see
[its qualification procedure](snowflake.md).

## Start the local reference

Prerequisites: Linux containers, Docker Compose v2 with health dependencies,
Python 3.12 for secret generation, and enough host capacity for two bounded
containers. The configured steady-state limit is 2 GiB memory and 2 CPU cores
across PostgreSQL and API, plus temporary build/migration overhead. A volume's disk
capacity must be bounded by the host storage policy; Compose memory limits do not
limit disk growth.

Create fresh secret files once. This example refuses to reuse a secret directory:

```bash
export MDM_SECRET_DIR="$PWD/.secrets/local"
python3 - <<'PY'
import json, os, secrets
from pathlib import Path

directory = Path(os.environ["MDM_SECRET_DIR"])
directory.mkdir(mode=0o700, parents=True, exist_ok=False)
password = secrets.token_urlsafe(32)
actors = {
    secrets.token_urlsafe(32): {"name": f"local.{role}", "role": role}
    for role in ("requester", "approver", "executor", "reader")
}
contents = {
    "postgres_password": password,
    "database_url": f"postgresql://mdm:{password}@postgres:5432/mdm",
    "actors.json": json.dumps(actors, indent=2),
}
for name, content in contents.items():
    with (directory / name).open("x") as file:
        file.write(content)
    (directory / name).chmod(0o444)
PY
docker compose config --quiet
docker compose build
docker compose up --detach --wait --wait-timeout 120 api
docker compose exec -T api mdm demo
docker compose exec -T api mdm check
```

The secret directory is private on the host. Its bind-mounted files are readable
by container UID `10001`; local Compose bind mounts do not implement a hosted
secret manager. Keep the directory out of Git and backups intended for publication.
For an actual operating environment, inject files from its secret manager and
retain the required file ownership/read permissions.

Open `http://127.0.0.1:8000`. Read an appropriate token from the local `actors.json`
with a local text editor and enter it in the console. Use distinct named actors
for requesting, approving and executing a decision. Do not paste tokens into an
issue, a URL, a screenshot or a terminal command recorded as evidence.

`mdm demo` executes the synthetic three-ERP scenario, a human-approved mistaken
merge, late source changes, unmerge and reference-consumer correction. Repeating
the completed demo returns its recorded state. For a fresh demo, use a new
dedicated database or separate Compose project and volume; do not truncate a
database with useful decisions.

### Shutdown and restart

```bash
docker compose stop --timeout 30
docker compose up --detach --wait --wait-timeout 120 api
```

`stop` retains the database volume. `down` also retains a named volume unless
`--volumes` is supplied. The CI cleanup uses `--volumes` only for a uniquely named
ephemeral CI project. Do not copy that cleanup command into an operating runbook.

The API receives SIGTERM and has 20 seconds for graceful shutdown inside a
30-second container stop budget. PostgreSQL has a 30-second stop budget. A hard
kill still needs database crash recovery and outbox reconciliation on restart.

## Run profiles and limits

| Profile | Command or workflow | Bound and purpose |
| --- | --- | --- |
| Pure contract smoke | `uv run --no-sync pytest -m 'not integration' -q` | No database claim; validates contracts and algorithms. |
| Full integration | `uv run --no-sync pytest -q` | Requires an explicit `MDM_TEST_DATABASE_URL` ending in `_test`; tests reset that schema. Missing DB access fails instead of skipping. |
| Business demonstration | `mdm demo --output artifacts/demo.json` | Named synthetic fixtures and assertions over actual PostgreSQL state. |
| Small load control | `mdm benchmark --size 300 --output artifacts/benchmark-control.json` | Measured candidate work and exhaustive small control. |
| Database load | `mdm benchmark --size 300 --database --output artifacts/benchmark-database.json` | Requires an empty dedicated DB; measures ingestion, consolidation, query plans and historical growth. |
| Manual larger load | Workflow dispatch `load_records=100..10000` | Explicit operator input, command timeout 180 seconds, no cloud warehouse. |
| Snowflake qualification | Procedure in `snowflake.md` | Dedicated approved account, bounded warehouse and statement/run limits. |

The orchestrator permits three attempts per run. A graph operation has a
30-second statement timeout and a 5-second lock timeout. Candidate limits raise
errors explicitly. The API reference uses one worker. CI is limited to 5 minutes
for scope checks, 10 for dependency auditing, 20 for PostgreSQL qualification and
20 for the container job. Runs on the same ref are serialized. A documentation-only
update does not cancel an already running qualification. Pull-request synchronize
events select work from the previous head to the new head; opened, reopened and
ready-for-review events consider the full PR. Manual dispatch always selects the
full runtime profile. Missing comparison commits select runtime conservatively.
Scheduling or skipping a job is not a new qualification result; final acceptance
requires an actual full result for the delivered executable code.

These bounds prevent runaway work; they are not throughput guarantees. The
benchmark output records input size, candidate/exhaustive counts, elapsed time,
memory measures and, when selected, database work. A 300-record fixture cannot
establish enterprise-scale capacity. The serialized graph lock, dense candidate
blocks, full-snapshot export and temporal history are concrete scaling limits.

## Resume a failed or degraded run

Inspect the persisted `runs` row, source checkpoints and `mdm check` before retry.
The input manifest must include all three ERP names; `null` explicitly represents
an unavailable source. Do not substitute an empty source and infer deletions.

```bash
timeout --signal=TERM --kill-after=10s 300s \
  mdm run --input path/to/erp-manifest.json --run-key operator-run-2026-11-13-01
mdm consume --consumer reporting --limit 10000
mdm check
```

A retry of a failed run uses the same input file and run key. Changing either the
input contents or matching mode under an existing key is rejected. A completed
degraded run remains evidence of the outage. When that ERP returns, submit the new
manifest under a new key. If a process crashed after a decision commit, the
consumer drain replays the durable outbox without replaying the decision.

The example uses GNU `timeout` to bound the CLI invocation to five minutes with
a ten-second forced-stop allowance. The Python orchestrator itself does not
enforce a global wall-clock deadline; statement, lock, input and retry bounds have
different scopes. A process timeout can leave committed source checkpoints or
outbox events, so inspect and resume the same run rather than changing its key.
API latency, runtime CPU/RAM, additional workers and representative source skew
still require measurements in the target environment.

## Monitoring and correlation

`/healthz` is a bounded database readiness check. The authenticated `/metrics`
endpoint exposes numeric quality values including `mdm_sources`,
`mdm_active_groups`, `mdm_pending_decisions`, `mdm_unconsumed_events` and
`mdm_crosswalk_coverage`. `mdm quality`, the dbt quality view and
[queries.sql](../observability/queries.sql) provide the corresponding operational
inspection paths.

The example Prometheus configuration and alert rules are optional external
monitoring configuration. No monitoring service is automatically deployed.
`mdm_unconsumed_events` counts events received by no consumer; use the explicit
consumer-lag SQL for a particular consumer, including one that has never started.

Each completed API request receives a server-generated `X-Correlation-ID` and
logs an allowlisted JSON event with method, route template, status and duration.
The synchronous service calls inherit that context. CLI invocations use the same
scoping mechanism. Request headers, tokens, actor names, reasons, source keys,
record bodies, SQL and exception messages are excluded from those diagnostics.

The `correlation.v1` metadata is persisted separately from business attributes in
decision requests, immutable transition payloads and outbox events. Each human
transition keeps its current request ID and the original request's correlation
ID. Pipeline work also carries its durable run ID across retries. Consumer inbox
receipts join to the original event, the projection retains its producer trace,
and post-commit receipt logs identify the consumer invocation. Context scopes
reset after success, failure or cancellation. A failed log sink must not turn a
committed business transaction into an application failure.

Use the correlation queries in [queries.sql](../observability/queries.sql) to
connect an HTTP ID to a decision, its outbox events and consumer receipts.
Snowflake's full JSON export preserves these fields. A publication report links
its snapshot ID to the recorded Snowflake query IDs, providing an
event-to-snapshot-to-publication join. It does not map every event directly to one
SQL statement, and no distributed-tracing collector is deployed. In-process
tests can verify request isolation and safe logging; durable and warehouse
propagation still require the real PostgreSQL/Snowflake qualification.

### Initial service objectives

These are operating targets and alert design inputs, not measured service levels:

| Signal | Target or alert | Action |
| --- | --- | --- |
| Readiness/metrics reachability | Investigate after 2 minutes unavailable | Check health, reader token, network and logs before restarting. |
| Source mapping | 100% coverage after a committed ingestion | Stop publication on a gap; inspect invariant failure and transaction state. |
| Reference consumer freshness | Drain committed changes within 5 minutes while the consumer runs | Inspect per-consumer lag, errors and versions; retry the bounded drain. |
| Review work | Inspect a continuously nonempty queue after 24 hours | Review oldest decisions and conflicts; do not approve to improve the metric. |
| Backup recovery point | 24-hour target with a configured daily off-host backup | The repository does not enable a backup scheduler automatically. |
| Restore time | 30-minute target for the agreed reference dataset | Record actual drill duration; scale qualification needs representative volume. |

## Incident actions

| Symptom | Evidence to inspect | Safe next action |
| --- | --- | --- |
| ERP unavailable | `run_sources`, degraded run and ingestion freshness | Retain known records; process available ERPs, then use a new manifest/key when recovered. |
| Pair should be rejected | Source revisions, criterion contributions and hard conflicts | Reject the pending request; preserve evidence and source identities. |
| HTTP 409 / stale decision | Current group/decision versions and immutable audit | Refresh the console and reconsider the changed state; never blindly replace the expected version. |
| Wrong merge already executed | Merge request, before/after membership and later source changes | Create an unmerge or explicit split, obtain distinct approval/execution, publish corrections and verify consumer crosswalks. |
| Crash after decision | Decision status, aggregate version and outbox event | Consume the existing event; do not create another merge request to compensate for missing publication. |
| Reporting disagrees | Per-consumer inbox, versions and `consumer_crosswalk` | Drain, compare maps, then investigate consumer logic; a local rollback cannot undo external business effects. |
| Reconciliation exceeds a bound | Block family/count, candidate count, memory and run error | Inspect skew and revise a versioned blocking strategy with recall measurement before increasing limits. |
| Migration checksum changed | `schema_migrations`, source commit and deployment image | Restore the intended code version or add a new migration; never edit the stored checksum to bypass the check. |
| Snowflake outcome uncertain | Publication manifest, active snapshot ID and recorded query IDs | Reconcile the existing snapshot before retrying; do not publish another generation merely because a response was lost. |

## Backup and restoration

Use PostgreSQL client binaries from the same supported major version as the
server, with current security fixes. Only restore a dump produced by this trusted
environment and reviewed code version: a PostgreSQL archive contains executable
database definitions.

The backup script holds a read-only repeatable-read transaction, exports its
snapshot for `pg_dump`, and calculates deterministic row counts and SHA-256
fingerprints for all 17 operational tables in that same snapshot. The dump uses
custom format. The destination must be new. A sidecar manifest records the archive
hash, database/client versions, size and duration. No database password is passed
as a command-line argument.

```bash
uv run --no-sync bash scripts/backup.sh backups/mdm-2026-11-13.dump --expect-db mdm
```

Set `MDM_DATABASE_URL` or `MDM_DATABASE_URL_FILE` to the verified source. The
script's `--expect-db` must match the connected database. Keep backups outside
published evidence, encrypt them with the operating environment's storage
controls, and maintain retention/off-host copies separately.

For a restore drill, create a new empty dedicated database with the intended
owner. Set **`MDM_RESTORE_DATABASE_URL`** or **`MDM_RESTORE_DATABASE_URL_FILE`** to
that target. This is deliberately separate from the source setting. Fence the
target from application clients and retain the old database for comparison.

```bash
uv run --no-sync bash scripts/restore.sh backups/mdm-2026-11-13.dump \
  --expect-db mdm_restore --report artifacts/restore.json
```

Restoration rejects a populated target, another session, a wrong expected name,
a competing restore lock or a mismatched archive hash. It runs `pg_restore` with
one transaction, no owner/ACL recreation and exit-on-error. It compares every
operational table fingerprint with the backup snapshot, runs `mdm check` and
writes the result only after these succeed. A hash proves content agreement;
it does not certify the data or validate an external consumer.

CI is configured to exercise these same scripts against PostgreSQL 17.12 and check that a second
restore into the populated target is rejected. Its narrow client wrappers execute
the real `pg_dump`/`pg_restore` binaries inside the service container, streaming the
archive without passing credentials in arguments. CI then runs dbt tests on the
restored database. No restore report has been produced by the initial blocked run.
When executed, original reports belong in the workflow artifact; no restore
success should be asserted without reading that result.

After recovery, external consumers may still be ahead of the restored delivery
ledger. Compare their last aggregate versions and source mappings, publish any
necessary corrective interpretation, and resume them deliberately. Restoring
the reference database does not restore external decisions.

## Migration, rollback and release

Take a consistent backup before a stateful migration. Review the exact migration
and required application version, quiesce decision writers, and run `mdm migrate`
once. The current reference migration is additive and checksum-checked. Run the
business invariants and dbt before restoring normal publication.

An application rollback is safe only if the previous image supports the current
schema and event contracts. Otherwise restore a backup to a new database and
reconcile consumers before changing the connection target. There is no generic
destructive downgrade that pretends to undo downstream events.

Before release, retain the exact source commit, installed component inventory,
input/truth-set version, test report, dbt manifest/run results/catalog, real demo,
restore report and resolved image information. Review published logs and Git
history for credentials and client material. The lightweight scanner reports its
limited coverage and never prints matched credentials. `pip-audit` checks known
published advisories; missing network access is a failed audit, not a clean one.
The license inventory records publisher declarations and license files, flags
missing/proprietary evidence and keeps distribution obligations visible. It is
not a licensing certification and does not choose this repository's license.

The repository remains private. During initial setup, reading the rulesets endpoint
returned a plan restriction for private repositories, and the integration could
not read the branch-protection administration endpoint. Do not represent protections as
enforced. Maintainer license approval, available branch rules, required checks,
public visibility and anonymous access are separate release decisions. No paid
plan change or public publication is performed by this workflow.

## Primary implementation references

- [Official PostgreSQL Docker image, supported tags and volume layout](https://hub.docker.com/_/postgres)
- [PostgreSQL 17.12 security release](https://www.postgresql.org/about/news/postgresql-187-1712-1616-1520-1425-and-19-rc-2-released-3442/)
- [PostgreSQL `pg_dump`](https://www.postgresql.org/docs/17/app-pgdump.html) and [`pg_restore`](https://www.postgresql.org/docs/17/app-pgrestore.html)
- [Docker Compose health dependency ordering](https://docs.docker.com/compose/how-tos/startup-order/) and [file secrets](https://docs.docker.com/compose/how-tos/use-secrets/)
- [Docker Compose resource and service options](https://docs.docker.com/reference/compose-file/services/)
- [uv in Docker](https://docs.astral.sh/uv/guides/integration/docker/) and [locked/frozen behavior](https://docs.astral.sh/uv/concepts/projects/sync/)
- [GitHub Actions PostgreSQL services](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers) and [secure action pinning](https://docs.github.com/en/actions/reference/security/secure-use)
- [Dependabot supported ecosystems](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories)
- [pip-audit usage and limitations](https://github.com/pypa/pip-audit)
- [PostgreSQL license](https://www.postgresql.org/about/licence/) and [uv license](https://docs.astral.sh/uv/reference/policies/license/)
