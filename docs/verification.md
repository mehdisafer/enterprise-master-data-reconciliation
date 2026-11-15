# Verification profiles and original evidence

## Reproducible profiles

| Profile | Command | Boundary |
| --- | --- | --- |
| Installed package | `uv build --no-sources`, wheel install, then `python scripts/verify_distribution.py` | Seven hashed build pins; all 18 installed application resources and CLI checked |
| Unit smoke | `uv run --no-sync pytest -q -m 'not integration'` | Domain, matching, in-process auth and Snowflake driver boundaries; no provider integration |
| Real integration | `uv run --no-sync pytest -q` with `MDM_TEST_DATABASE_URL` | Real PostgreSQL; reset restricted to an explicitly supplied `*_test` database |
| Business demonstration | `mdm demo --output artifacts/demo.json` | Dedicated synthetic database; completed demonstration is idempotent |
| dbt | `dbt build --project-dir dbt --profiles-dir dbt --target postgres --target-path ../artifacts/dbt-build` | Real PostgreSQL models and data tests; retained build results |
| Catalog | `dbt docs generate --project-dir dbt --profiles-dir dbt --target postgres --target-path ../artifacts/dbt-docs` | Executed catalog and lineage; separate results cannot overwrite the build |
| Bounded control | `mdm benchmark --size 300 --output artifacts/benchmark-control.json` | Candidate/exhaustive work and Python memory |
| Database load | `mdm benchmark --size 300 --database --output artifacts/benchmark-database.json` | Empty dedicated database; ingestion, consolidation, EXPLAIN ANALYZE/BUFFERS and history growth |
| Larger load | Manual workflow input, maximum 10,000 records | Explicit run with a 180-second command bound; not every documentation change |
| Restore | `scripts/backup.sh` then `scripts/restore.sh` into an empty database | Native same-major clients, exact fingerprints and invariants |
| Restored data | `dbt test --project-dir dbt --profiles-dir dbt --target postgres --target-path ../artifacts/dbt-restored` with restored `PGDATABASE` | Tests over restored views and operational tables |
| Container/browser | Container job in `quality.yml`, including `scripts/browser_smoke.py --exercise-lifecycle`, followed by `mdm check` | Real image, rendered three-role merge/unmerge/split, consumer alignment and screenshots |
| Terraform | Static workflow: init without backend, format, validate and provider schema | Actual pinned provider; no cloud apply |
| Snowflake | `infra/snowflake/qualify.sh --execute-live` | Authorized dedicated provider resources; no local substitute |

Predeclared correctness and safety thresholds are zero false automatic merges in the labeled control, complete control candidate recall, equivalent automatic pairs between blocked and exhaustive comparison, traced Python heap below 256 MB for that control, and no violated business invariants. The 180-second limit is a protective execution bound, not an enterprise latency objective. Every measured value needs its input distribution and execution context.

The full suite fails if its database is missing. No skipped test is accepted as integration evidence. Snowflake unit doubles are explicitly identified and never reported as a live provider run.

## Observed 15 November dependency qualification

The initial complete native capture used [commit `88c932de`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/88c932de80dd1d20f49b93798153f2986f3c5029), with [source correspondence](../evidence/2026-11-15/dependency-qualification/source-correspondence.json). The supplementary full test suite used [commit `bb369db1`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/bb369db1360ef17c5328dc6a68392355728e9920), preserving all eleven tests from the dependency rollup integrated through [PR #8](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/8); its [correspondence record](../evidence/2026-11-15/dependency-qualification/main-reconciliation/source-correspondence.json) checks 83 inputs. Both runs used Python 3.12.16 and PostgreSQL 17.12 with the same installed wheel, FastAPI 0.162.4, Pydantic 2.14.3 and Hatchling 1.33.0 build. [PR #9](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/9) carries these controls and evidence; its conversation records review, the delivered head, final `main`/tree readback and workflow observations separately from native execution.

| Profile | Observed result | Original evidence |
| --- | --- | --- |
| Latest full suite, existing installed wheel | 180 tests and 15 subtests passed; 55 real PostgreSQL cases; zero failures, errors or skips | [Qualification](../evidence/2026-11-15/dependency-qualification/main-reconciliation/qualification.json), [JUnit](../evidence/2026-11-15/dependency-qualification/main-reconciliation/pytest.xml) |
| Initial full suite, installed wheel | 169 tests and 15 subtests passed; 55 real PostgreSQL cases; zero skips | [JUnit](../evidence/2026-11-15/dependency-qualification/native-flow/pytest.xml) |
| Editable smoke | 114 tests and 15 subtests passed; 55 database cases deselected for this profile | [JUnit](../evidence/2026-11-15/dependency-qualification/native-flow/editable-unit.xml) |
| Build and distribution | Source distribution and wheel built; 18 installed application resources and CLI preserved | [Distribution report](../evidence/2026-11-15/dependency-qualification/native-flow/distribution.json) |
| Contract compatibility | 35 input assertions, ingestion hashes, five schemas and OpenAPI unchanged | [Comparison](../evidence/2026-11-15/dependency-qualification/contract-comparison.json) |
| dbt build and catalog | Five models and 41 data tests passed; populated catalog generated | [Build](../evidence/2026-11-15/dependency-qualification/native-flow/dbt/build/run_results.json), [catalog](../evidence/2026-11-15/dependency-qualification/native-flow/dbt/docs/catalog.json) |
| Backup and restore | Exact match for all 17 table fingerprints; business invariants passed; populated target correctly refused | [Restore](../evidence/2026-11-15/dependency-qualification/native-flow/restore.json), [negative case](../evidence/2026-11-15/dependency-qualification/native-flow/second-restore-rejection.json) |
| Restored dbt | 41 data tests passed | [Run results](../evidence/2026-11-15/dependency-qualification/native-flow/dbt/restored/run_results.json) |
| Native HTTP | 34 actual requests and 341 checks passed; 17 table fingerprints unchanged; graceful shutdown observed | [HTTP qualification](../evidence/2026-11-15/dependency-qualification/native-flow/http/qualification.json) |
| Installed-package and build audits | Zero known vulnerabilities at capture in 119 installed application, development and qualification packages; separately, seven explicitly constrained build dependencies | [Installed-package audit](../evidence/2026-11-15/dependency-qualification/native-flow/dependency-audit.json), [build audit](../evidence/2026-11-15/dependency-qualification/native-flow/build-dependency-audit.json) |
| Database profile | 300 inputs, 309 candidates; 0.846 s ingestion, 1.377 s consolidation; nine invariants passed | [Measured profile](../evidence/2026-11-15/dependency-qualification/native-flow/benchmark-database.json) |

The initial [26-command capture](../evidence/2026-11-15/dependency-qualification/native-flow/qualification.json) retains actual command arguments, intervals and exits. The supplementary run at 21:43:50–21:44:08 UTC passed Ruff and the 180-test suite using the existing installed wheel. It did not repeat the build, editable smoke, demonstration, dbt, restore, audits, benchmark or live HTTP; the corresponding executable inputs stayed unchanged. The two audit inventories overlap and must not be added as unique package counts. Both complete test runs use the non-editable installed wheel; the initial editable run is a separate smoke profile. The 341 native HTTP checks include repeated header, authorization and correlation assertions, not 341 extra pytest cases. The two new database HTTP scenarios do exercise mutations; the separate live HTTP harness intentionally checks reads/refused writes and verifies unchanged business fingerprints.

The 150-record exhaustive control again preserved candidate recall and automatic-pair equivalence. The 300-record benchmark measured a 0.420 ms SQL join and the recorded history growth. Its easy synthetic distribution and partial memory measurements do not establish industrial throughput, overall server-memory peaks or a service-level objective.

### Reproduce package qualification

Use uv 0.13.6. The project uses its experimental `require-build-hashes` setting with seven explicit `build-constraint-dependencies`; the application/development package entries in `uv.lock` do not by themselves constrain isolated build resolution. A tooling upgrade must recheck those supported settings rather than silently dropping the build constraints.

```bash
uv sync --frozen --all-extras
uv build --no-sources --out-dir artifacts/dist
uv pip install --python .venv/bin/python --no-deps --reinstall \
  artifacts/dist/enterprise_master_data_reconciliation-0.1.0rc1-py3-none-any.whl
uv run --no-sync python scripts/verify_distribution.py --output artifacts/distribution.json
uv run --no-sync pytest -q --junitxml=artifacts/pytest.xml
```

The full test command requires the disposable PostgreSQL configuration described above. `--no-sync` preserves the installed-wheel mode; an ordinary project sync can reinstall the package in editable mode. A source hash proves correspondence, not an independent review. The earlier continuation's uncommitted 166-test account is not used as qualification evidence.

## Historical 14 November qualification

The application, test and dbt inputs for this historical section match [source revision 205e7507](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/205e7507b9cd7dc1b34a858f2c524ce0c832642c). The [source correspondence](../evidence/2026-11-14/source-correspondence.json) compares file hashes from three actual captures with that complete source tree. Subsequent changes to qualification scripts are recorded separately below.

| Profile | Observed result | Evidence |
| --- | --- | --- |
| Full suite | 125 tests and 15 subtests passed, zero skipped; 53 PostgreSQL cases | [JUnit and command output](../evidence/2026-11-14/pytest/pytest.xml) |
| Business scenario | Six assertions true, nine invariants without violations, 34 retained sources | [Original demo](../evidence/2026-11-14/native-flow/demo.json) |
| dbt build and docs | Five models, 41 tests and two hooks succeeded; catalog includes five models and 16 sources | [Run results](../evidence/2026-11-14/native-flow/dbt/build/run_results.json), [catalog](../evidence/2026-11-14/native-flow/dbt/docs/catalog.json) |
| Restore | All 17 operational fingerprints equal; business checks passed; second restore rejected for the intended reason | [Restore](../evidence/2026-11-14/native-flow/restore.json), [negative case](../evidence/2026-11-14/native-flow/second-restore-rejection.json) |
| Restored dbt | 41 tests and two hooks succeeded | [Restored results](../evidence/2026-11-14/native-flow/dbt/restored-test/run_results.json) |
| Database profile | 300 inputs; 1.294 s ingestion, 1.774 s consolidation; nine invariants passed | [Full measured profile](../evidence/2026-11-14/native-flow/benchmark-database.json) |
| HTTP runtime | 24 real requests, 127 assertions; no business-state change from reads/refused writes | [HTTP report](../evidence/2026-11-14/http/http-report.json) |

The native non-test flow completed 17 phases in 34.795 seconds. This includes CLI startup and evidence capture; individual timing fields have narrower scopes. PostgreSQL and Uvicorn both shut down cleanly after the captures. The first HTTP harness incorrectly required exit zero after graceful SIGTERM; its failed report is retained beside the corrected harness rerun. No application change was needed for that harness correction.

The database benchmark measured one small synthetic workload. Its traced Python heap covers blocking/comparison, and its process maximum RSS was sampled before the database branch. Neither value measures the complete database application's memory peak or PostgreSQL server memory. The real query plan's 0.519 ms execution time is one measured join, not an API latency or warehouse SLA. Thirty later assertions increased raw/history/outbox rows by 30 each; the original counts and plan are retained.

## Evidence preservation and reproducibility

The committed [evidence index](../evidence/README.md) retains original command arguments, UTC intervals, exit codes, stdout/stderr, JUnit, manifests, catalog, compiled/executed SQL, dbt logs, demonstration, restore fingerprints, profiles and remote API observations. A [copy manifest](../evidence/2026-11-14/preserved-artifacts.json) maps retained originals to their source path and SHA-256. Capture helpers document the exact isolated setup; normal verification commands remain in this page and the CI workflow.

Native `dbt` ran on a byte-identical copy of the tracked project so generated targets/logs stayed outside the source checkout. Database backup archives, credentials, PostgreSQL/browser binaries and generated dbt application HTML are excluded from published evidence. Embedded upstream macros and their compiled derivatives retain the notices in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

The CI workflow is configured to retain artifacts for 14 days after successful uploads. It keeps build, documentation and restored-test results in separate directories, including their manifests and applicable compiled/executed SQL. The observed GitHub runs produced no artifacts because they never received a runner. Locally preserved results must not be relabelled as CI output. The dated 13 November parse/audit/unit capture remains unchanged as historical evidence; the 14 November live database results supersede its database-execution gap.

## Targeted verification of CI evidence controls

The [13:45 UTC capture](../evidence/2026-11-14/ci-evidence-hardening/qualification.json) executes the revised workflow's dbt commands and populated-target check on the same isolated PostgreSQL 17.12 runtime. Its capture helper extracts the commands from the workflow, records their hashes and uses fresh output directories. Native clients and a private passfile replace the CI container wrappers; neither Docker nor GitHub Actions is executed by this capture.

- Build produced 41 passing data tests, five successful models and two successful hooks. Both build artifact hashes stayed identical after documentation generation. The two phases have distinct invocation IDs, and the documentation catalog contains five models and 16 sources.
- The populated-target control accepted only exit 1 with `restore_verified: false`, `error_type: OperationError` and the exact expected reason, with no forbidden report.
- Two real alternate failures, a missing archive and missing restore configuration, each returned exit 1 from the restore tool. The revised control rejected both with its own exit 1 and a retained `passed: false` report. These are deliberate negative controls, not failed qualification attempts.
- Fingerprints for all 17 operational tables in both the source and restored databases matched before/after. The existing populated database was not reset, and no successful restore was repeated. PostgreSQL stopped with exit zero.

The [original command outputs](../evidence/2026-11-14/ci-evidence-hardening/commands/02-dbt-build/execution.json), [copy manifest](../evidence/2026-11-14/ci-evidence-hardening/preserved-artifacts.json), dbt results, restore-control responses and runtime logs are retained. The Snowflake helper uses the same separation between build/docs output paths; only its shell syntax and source changes are checked here. No live Snowflake result follows from this native run.

## Remaining environment boundaries

Loopback TCP is allowed in the provided workspace; Unix socket creation is denied. PostgreSQL 17.12 used `unix_socket_directories=''`, with standard TCP and private SCRAM credentials. The 14 November capture extracted signed PGDG packages. The 15 November capture instead extracted signed Debian Security trixie packages, PostgreSQL `17.12-0+deb13u1`, without a system installation; the [runtime manifest](../evidence/2026-11-15/dependency-qualification/environment/runtime_manifest.json) and [signature record](../evidence/2026-11-15/dependency-qualification/environment/signature_verification.json) retain that provenance. Uvicorn served actual HTTP on loopback. The earlier blanket socket restriction diagnosis was therefore too broad and is superseded by these observed runs.

Fresh [15 November environment captures](../evidence/2026-11-15/dependency-qualification/environment/) again found Docker absent and Chromium unable to start because Unix socket creation is denied. Terraform formatting and initialization passed, but actual provider-schema startup and validation failed at that boundary. No rendered console, screenshot, browser interaction or container startup is claimed. The older Playwright download failure remains part of the historical evidence. The [official-source transport investigation](terraform-provider-transport.md) confirms that normal/debug startup of the pinned Linux provider does not expose a TCP selection; it is source analysis, not schema execution. Snowflake account authorization, credentials, target scope and spending limit remain absent.

The historical [quality run](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43593711716) and [Terraform run](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43593711641) at the qualified code revision have zero executed steps and zero artifacts. Their precise admission failure requires an authorized interface exposing the annotation text. There is no evidence establishing a billing, quota or policy cause.

The graph lock serializes writes, dense candidate blocks can grow quadratically and fail at explicit limits, and full snapshots/history grow with changes. The recorded profile does not establish arbitrary industrial performance, additional-worker throughput, long-term storage growth or provider cost.
