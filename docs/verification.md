# Verification profiles and original evidence

## Reproducible profiles

| Profile | Command | Boundary |
| --- | --- | --- |
| Unit smoke | `uv run --no-sync pytest -q -m 'not integration'` | Domain, matching, API auth, Snowflake driver boundaries; no provider integration |
| Real integration | `uv run --no-sync pytest -q` with `MDM_TEST_DATABASE_URL` | Real PostgreSQL, destructive reset limited to supplied `*_test` DB |
| Business demonstration | `mdm demo --output artifacts/demo.json` | Existing dedicated synthetic DB; idempotent completed demo |
| dbt | `dbt build --project-dir dbt --profiles-dir dbt --target postgres` | Real PostgreSQL adapter models and tests |
| Bounded control | `mdm benchmark --size 300 --output artifacts/benchmark-control.json` | Candidate generation, actual blocked/exhaustive comparison, memory |
| Database load | `mdm benchmark --size 300 --database --output artifacts/benchmark-database.json` | Empty dedicated DB; ingestion, consolidation, SQL EXPLAIN ANALYZE/BUFFERS, history growth |
| Larger load | Manual workflow input, maximum 10,000 records | Explicit run, 180-second command bound; never every documentation change |
| Restore | `scripts/backup.sh` then `scripts/restore.sh` into empty DB | Native same-major PostgreSQL clients, exact fingerprints, invariants |
| Snowflake | `infra/snowflake/qualify.sh` | Authorized dedicated provider resources; no silent local fallback |

Predeclared safety/correctness thresholds: zero false automatic merges in the labeled control; complete control candidate recall; blocked/exhaustive automatic pair equivalence; Python traced heap below 256 MB for the bounded profile; no violated business invariants. The 180-second budget is a protective execution limit, not an enterprise latency SLO. Hardware and distributions must accompany every measured value.

No tests are skipped in the full CI qualification. A missing database is a failure. Snowflake unit doubles are explicitly named in the test module and never reported as a live integration.

## Evidence preservation

The workflow uploads JUnit, original dbt manifest/run results/catalog/compiled SQL/log, environment versions and image digests, demo snapshots, restore fingerprints, load output and audit reports. Artifacts are retained by GitHub for 14 days; selected JSON/SQL evidence is also committed in `evidence/` before final handoff. The evidence index records the exact source revision and workflow URL. Evidence-only commits do not change which code revision was executed.

Credentials are external and excluded. All domain values in demonstration artifacts are synthetic. A content digest shows file concordance only. It does not prove independent review, a licence grant or provider validation.

## Known operational constraints

The initial isolated editor environment prohibits socket creation. Therefore local PostgreSQL, HTTP socket/browser and Docker runtime execution cannot be asserted from that environment. In-process API tests and Python matching tests are possible; actual database/container evidence must be retrieved from CI. Provider credentials are absent, so Snowflake live tests remain a named release gate.

The single-writer graph lock is a likely throughput bottleneck; candidate blocks can also grow quadratically in dense groups and abort at their explicit limits. The database profile measures one bounded synthetic batch. It does not establish performance for arbitrary industrial distributions, extra workers or Snowflake warehouses.
