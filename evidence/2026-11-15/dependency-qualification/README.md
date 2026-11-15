# Dependency qualification — 15 November 2026

The combined update passed the native Python/PostgreSQL qualification described below. The latest full suite passed **180 tests and 15 subtests**, including 55 real PostgreSQL cases, after preserving the eleven compatibility tests integrated through [PR #8](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/8). The initial 26-command capture matches [commit `88c932de`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/88c932de80dd1d20f49b93798153f2986f3c5029); the supplementary test capture matches [commit `bb369db1`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/bb369db1360ef17c5328dc6a68392355728e9920). This is a reference-source delivery; container deployment, rendered browser behavior, Terraform provider-schema validation and live Snowflake qualification remain open.

## Recovered work and scope

The supplied continuation transcript ended before its consolidation reached GitHub. The initial live inventory found `main` at `16f7325c`, with dependency PRs #4–#7 still open. The transcript's 166-test result was not reused. The exact PR changes were retrieved, compared with the existing lock and independently executed in a fresh isolated workspace. No personal workstation, client system or client data was used.

During qualification, PR #8 integrated the same dependency rollup at [commit `03c927b3`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/03c927b3f19e387df770130d59d9c09bea3800d1), with eleven compatibility tests and a [refresh note](../../../docs/dependency-refresh-2026-11-15.md). The reconciliation commit preserves that work and the new controls. [PR #9](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/9) carries the qualification, controls and evidence; its conversation records the review, delivered head, final `main`/tree readback and workflow observations. PRs #4–#7 are closed following the rollup.

| Component | Previous pin | Qualified candidate |
| --- | --- | --- |
| Python | 3.12.14 | 3.12.16 |
| FastAPI | 0.141.1 | 0.162.4 |
| Pydantic / core | 2.13.4 / 2.46.4 | 2.14.3 / 2.50.4 |
| Hatchling | 1.29.0 | 1.33.0 |
| PostgreSQL | 17.12 | 17.12 |

The [dependency review](dependency-review/review.md) retains the targeted upstream sources, original PR heads and exact composition method. That intermediate review precedes the additional backend constraints. The final `pyproject.toml` and `uv.lock` also retain seven explicitly constrained build dependencies, including Hatchling and the backend's editable-build requirement, with distribution hashes. The 122 application lock entries match the combined PR candidate. uv 0.13.6 enforces these hashes; its build-dependency-hashes capability is marked experimental upstream and its warning remains in the original logs. The installed-package audit covers 119 application, development and qualification packages on Linux. Four packages also appear among the seven build dependencies (`packaging`, `pathspec`, `pluggy` and `tomlkit`); the two audit counts must not be added as unique packages.

## Results actually obtained

| Check | Observed result | Original evidence |
| --- | --- | --- |
| Latest full suite, existing installed wheel | 180 tests and 15 subtests; zero failures, errors or skips; 55 real PostgreSQL tests | [Qualification](main-reconciliation/qualification.json), [JUnit](main-reconciliation/pytest.xml) |
| Initial complete installed-wheel suite | 169 tests and 15 subtests; zero failures, errors or skips; 55 real PostgreSQL tests | [JUnit](native-flow/pytest.xml), [output](native-flow/commands/08-full-postgres-suite/stdout.txt) |
| Editable installation | 114 non-integration tests and 15 subtests passed; 55 integration cases deliberately deselected for this packaging comparison | [JUnit](native-flow/editable-unit.xml), [output](native-flow/commands/04-editable-unit/stdout.txt) |
| Wheel rebuilt from sdist | Hatchling 1.33.0, metadata 2.5; 18 package resources byte-identical; installed CLI works outside `src/` | [Distribution check](native-flow/distribution.json), [build log](native-flow/commands/05-build-sdist-and-wheel/stderr.txt) |
| Dependency-sensitive contracts | 35 serialized records and ingestion hashes, five schemas and OpenAPI unchanged | [Comparison](contract-comparison.json) |
| Business demonstration | Six assertions true, nine invariants without violations, 34 source identities and 34 aligned consumer mappings | [Demonstration](native-flow/demo.json), [business checks](native-flow/business-check.json) |
| dbt build and catalog | Five models and 41 tests succeeded; populated catalog with five models and 16 sources | [Build results](native-flow/dbt/build/run_results.json), [catalog](native-flow/dbt/docs/catalog.json) |
| Restore | All 17 table fingerprints identical; business checks passed; populated target rejected for the exact intended reason | [Restore](native-flow/restore.json), [negative check](native-flow/second-restore-rejection.json) |
| dbt after restore | 41 tests succeeded | [Restored results](native-flow/dbt/restored/run_results.json) |
| Real HTTP server | 34 requests, 341 checks, exact response/log correlation; all 17 table fingerprints unchanged; graceful shutdown | [HTTP qualification](native-flow/http/qualification.json), [server log](native-flow/http/server.stderr.log) |
| Dependency advisories | Zero known findings in the dated result for 119 installed application, development and qualification packages; separately, seven explicitly constrained build dependencies | [Application audit](native-flow/dependency-audit.json), [build audit](native-flow/build-dependency-audit.json) |
| Bounded database workload | 300 records, 309 candidates versus 44,850 exhaustive pairs; declared control thresholds met | [Measured profile](native-flow/benchmark-database.json) |

The initial [26-command capture](native-flow/qualification.json) records arguments, UTC intervals, elapsed time and exit codes. The negative restore correctly returns 1 and is accepted only after checking the exact error and absence of a success report. Its JUnit suite count is 184 because that count includes the 15 subtests; pytest reports 169 tests plus 15 subtests. The supplementary run at 21:43:50–21:44:08 UTC passed Ruff and 180 tests plus 15 subtests (JUnit suite count 195), using the existing non-editable installed wheel. It did not repeat the build, editable smoke, demo, dbt, restoration, live HTTP, audits or benchmark. Their executable inputs are unchanged, and those results remain attributed to the initial capture. The Starlette/httpx deprecation warning is retained.

The 44 added HTTP regressions comprise 42 transport/contract checks and two lifecycle cases using ASGI TestClient with real PostgreSQL. The separately captured Uvicorn run uses an actual TCP listener and does not claim rendered-browser execution. It exercises the normal 10,000,000-byte request limit, four roles, authentication, rejected mutations, strict nested input, JSON contracts and correlation. Reads and refused writes leave the 17 operational tables unchanged. Uvicorn's signal exit `-15` is accepted only with completed lifespan shutdown and a closed listener. Temporary operator credentials were removed.

The database profile measured 0.846 seconds for ingestion and 1.377 seconds for consolidation. It is one small synthetic workload, not an industrial throughput guarantee. Matching heap and the pre-database RSS sample do not measure PostgreSQL's peak memory. No Snowflake time, credits or cost was observed.

## Environment limits rechecked

Python 3.12.16 and native PostgreSQL 17.12 ran in the provided Linux workspace. PostgreSQL used loopback TCP, private SCRAM credentials and no Unix socket. The current PostgreSQL packages are Debian Security trixie version `17.12-0+deb13u1`; the historical 14 November capture used PGDG packages. The [runtime manifest](environment/runtime_manifest.json) and [signature verification](environment/signature_verification.json) record the current package checksums and signed repository evidence. [Final wrapper output](native-wrapper-final-output.json) records the successful qualification exit and clean PostgreSQL stop.

Docker and Podman are absent. Chromium failed before rendering at Unix socket creation; its [original error](environment/browser-launch-error.log) is retained. The enhanced browser profile is implemented in `scripts/browser_smoke.py --exercise-lifecycle`, including distinct requester, approver and executor actions, merge/unmerge/split, consumer publication and screenshots. CI now also checks business invariants after those UI mutations. These commands still require a capable runner.

Terraform 1.17.2 formatting and credential-free provider installation succeeded against Snowflake provider 2.22.1 with an unchanged lock. Both validation and schema extraction failed when the provider attempted its denied Unix socket. [Command results](environment/terraform-qualification/results.json) and [provider diagnostics](environment/terraform-qualification/provider-debug.log) are retained. No plan, apply, cloud credential use or live warehouse connection occurred.

The initial [GitHub inventory](github-state-audit-20261115.json) records private visibility and the separate CircleCI setup branch. At that initial inventory, the observed CircleCI success covered matching-only tests and did not qualify PostgreSQL, containers or the warehouse. The [concurrent branch capture](main-reconciliation/concurrent-github-state.json) records later changes on that separate branch, including a VM profile; those changes were not integrated into the main source being qualified here. The branch was preserved.

The [Quality run at `bb369db1`](main-reconciliation/github-actions.json) failed in scope with `runner_id: 0`, zero executed steps and zero artifacts; its dependent jobs were skipped. One admission annotation exists, but its text was unavailable, so the cause remains unconfirmed. The PR #9 conversation records later final-head workflow observations separately.

## Preservation and source correspondence

The initial [source correspondence](source-correspondence.json) checks 82 executable/configuration inputs against `88c932de`. The supplementary [source correspondence](main-reconciliation/source-correspondence.json) checks 83 inputs against `bb369db1`: the same 82 inputs plus PR #8's compatibility test file. Application source and the 122 application package blocks are unchanged between those captures. The initial code commit preserves all 455 pre-existing evidence blobs. The final documentation update revises their index while retaining all 454 historical artifact blobs unchanged. [The initial preservation manifest](preserved-artifacts.json) identifies 406 byte-preserved originals with source locations, sizes and SHA-256 values. The separate [supplementary manifest](main-reconciliation/preserved-artifacts.json) records fifteen byte-preserved originals: twelve capture files and three GitHub capture files. The comparison establishes content identity, not independent certification.

Original capture helpers remain under `capture/` as records of the executed isolated layout. They expect the workspace-relative `repo` and runtime setup used for this capture; normal reproduction uses the commands in [verification](../../../docs/verification.md) and the repository CI definitions. Credentials, database archives, vendor binaries, built distributions, dbt application HTML and parse/graph caches are excluded. The [known-secret check](known-secret-scan.json) covers the generated database password; the HTTP harness separately checks its ephemeral credentials before retaining logs. Broader pattern scans have their own recorded scope.

Upstream dbt macros and their compiled derivatives retain the notices in [THIRD_PARTY_NOTICES.md](../../../THIRD_PARTY_NOTICES.md). The repository's own licence remains awaiting an explicit maintainer decision. Public visibility and full V1 acceptance are separate from this native qualification.
