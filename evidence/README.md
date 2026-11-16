# Observed evidence — 0.1.0rc1

**The synthetic PostgreSQL/dbt, container and rendered-browser reference passed hosted CI on 16 November 2026; full live Snowflake, production and release acceptance remain open.** The 13–15 November native evidence below is preserved at its original source versions. A database-only result did not qualify Docker at that time; a separate later GitHub Actions container job has now executed successfully.

## Latest verified hosted qualification — 17 November 2026 CET

[PR #22](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/22) eliminated the CircleCI first-parent docs-only false skip by requiring complete mainline PostgreSQL/dbt on **every main push**. The merged source [`af4ed2b77616`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/af4ed2b776162f8dce497b20d4f4fad063adeeab) passed both CircleCI mainline jobs and all four jobs of [GitHub Actions Quality #43978646310](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43978646310). Original logs confirm **189 Python tests + 15 subtests**, one warning, dbt **PASS=48/48**, restored dbt **PASS=43/43**, `restore_verified=true`, and a passing real browser lifecycle with 34 source identities and zero JavaScript errors. Four original GitHub Actions artifact collections were retained with finite 14-day retention. Original CircleCI artifact bytes remain uninspected.

The separate [Terraform static workflow #43593711641, attempt 2](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43593711641) concluded success for `fmt`, backend-free `init`, `validate`, and actual `providers schema` on a historical SHA with byte-identical static Terraform workflow/HCL/lock. That source correspondence does **not** imply Terraform `apply` or live Snowflake. See the [17 November original-run evidence record](2026-11-17/ci-mainline-hardening/) and [structured manifest](2026-11-17/ci-mainline-hardening/manifest.json). The older 13–16 November captures below are preserved at their original sources.

## Historical hosted CI capture — 16 November 2026

The fully executed [GitHub Actions Quality run #43920046617](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617) at commit [`9b72725da693`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/9b72725da693b4587c27a12b1d65e6f639d69a86) completed **successfully**, with all four jobs on assigned runners: `scope`, `dependencies`, `postgres`, and `container`. Both default CircleCI jobs (`build-and-test`, `postgres-integration`) also reported `success` for the exact source SHA. These distinct platforms' evidence is not conflated.

| Check | Executed result | Retained reference |
| --- | --- | --- |
| Full Python test suite | **183 passed + 15 subtests passed**, one warning | [Original postgres job](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617/job/133484749971) |
| dbt build | Five models, 41 data tests, two hooks; **PASS=48, ERROR=0, SKIP=0** | Same job; `postgres-evidence` artifact |
| Consistent backup/restore | `restore_verified=true`; expected repeated-restore refusal step succeeded | Same job; `restore.json` and refusal report |
| Restored dbt tests | 41 data tests, two hooks; **PASS=43, ERROR=0, SKIP=0** | Same job; dbt restored result |
| Docker + browser | Real API/demo/health; `passed=true`, `lifecycle_executed=true`, 34 preserved source identities, no JavaScript errors, post-lifecycle business check passed | [Original container job](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617/job/133485726286) |
| Locked dependencies and security | Scope/history scan and dependency inventory/audit jobs passed | `secret-scan` and `dependencies` artifacts |

Original GitHub Actions `postgres-evidence`, `container-evidence`, `secret-scan` and `dependencies` artifact collections were uploaded with the tested SHA and limited retention. See the [16 November evidence report](2026-11-16/ci-main-qualification/) and its [structured observation manifest](2026-11-16/ci-main-qualification/manifest.json) for the original run/job IDs, artifact identifiers, sizes and proof boundaries. The manifest is a derived record, not a copy of the raw archives.

This qualifies the recorded **synthetic** source only. Live Snowflake publication/readback/dbt parity, real production deployment/permissions/monitoring and an explicit open-source licence remain outside the result. The repository's visibility is now public by GitHub API, but no project licence, description/topics or branch protection is present; an anonymous repository/raw-README browser readback was subsequently observed on 16 November without a login wall. Exact HTTP response codes and content digests were not independently captured.

## Historical capture — 15 November dependency qualification

The initial native capture used [commit `88c932de80dd1d20f49b93798153f2986f3c5029`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/88c932de80dd1d20f49b93798153f2986f3c5029), tree `00fe3801be1c48b5c8ddb729f4d8c02b2ad7dc54`; its [source-correspondence record](2026-11-15/dependency-qualification/source-correspondence.json) checks 82 inputs. After preserving the dependency rollup and eleven tests integrated through [PR #8](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/8), the supplementary suite used [commit `bb369db1`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/bb369db1360ef17c5328dc6a68392355728e9920), tree `052360b31b0b831d80ddbaa34d93870577c68637`; its [source correspondence](2026-11-15/dependency-qualification/main-reconciliation/source-correspondence.json) checks 83 inputs. [PR #9](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/9) carries the controls and evidence, and its conversation records review, the delivered head, final `main`/tree readback and workflows. [Publication](../docs/publication.md) remains separate from full runtime acceptance.

The [new qualification directory](2026-11-15/dependency-qualification/) contains original native outputs and the capture procedure. The [environment](2026-11-15/dependency-qualification/native-flow/environment.json) records Python 3.12.16, PostgreSQL 17.12, FastAPI 0.162.4 and Pydantic 2.14.3; Hatchling 1.33.0 built the package. This was an isolated Linux workspace, not GitHub Actions or a container. The earlier continuation's unpublished 166-test narrative is not treated as a recovered original; the candidate was qualified again.

| Check | Observed result | Original evidence |
| --- | --- | --- |
| Latest complete suite, existing installed wheel | **180 tests and 15 subtests passed; 55 real PostgreSQL cases; zero failures, errors or skips** | [Qualification](2026-11-15/dependency-qualification/main-reconciliation/qualification.json), [JUnit](2026-11-15/dependency-qualification/main-reconciliation/pytest.xml) |
| Initial complete installed-wheel suite | 169 tests and 15 subtests passed; 55 real PostgreSQL cases; zero skipped cases | [JUnit](2026-11-15/dependency-qualification/native-flow/pytest.xml) |
| Editable smoke | 114 tests and 15 subtests passed; 55 integration cases deselected for the smoke profile | [JUnit](2026-11-15/dependency-qualification/native-flow/editable-unit.xml) |
| Build/installed package | Source distribution and wheel built; all 18 application resources and CLI retained | [Distribution](2026-11-15/dependency-qualification/native-flow/distribution.json) |
| Contract comparison | 35 reference assertions' serialization and ingestion hashes, five schemas and OpenAPI unchanged | [Comparison](2026-11-15/dependency-qualification/contract-comparison.json) |
| Business demonstration | 34 source identities, 28 active goldens, six scenario assertions and nine invariants passed | [Demo](2026-11-15/dependency-qualification/native-flow/demo.json), [invariants](2026-11-15/dependency-qualification/native-flow/business-check.json) |
| dbt build/catalog | Five models and 41 data tests passed; populated catalog | [Build results](2026-11-15/dependency-qualification/native-flow/dbt/build/run_results.json), [catalog](2026-11-15/dependency-qualification/native-flow/dbt/docs/catalog.json) |
| Restore and negative control | All 17 table fingerprints matched; populated target refused for the intended reason | [Restore](2026-11-15/dependency-qualification/native-flow/restore.json), [refusal](2026-11-15/dependency-qualification/native-flow/second-restore-rejection.json) |
| Restored data | 41 dbt tests passed | [Restored results](2026-11-15/dependency-qualification/native-flow/dbt/restored/run_results.json) |
| Native HTTP | **34 requests and 341 checks passed**; 17 fingerprints unchanged, 34 correlated HTTP log events and graceful shutdown | [HTTP report](2026-11-15/dependency-qualification/native-flow/http/qualification.json) |
| Installed-package audit | 119 installed application, development and qualification packages; zero known vulnerabilities reported at capture | [Audit](2026-11-15/dependency-qualification/native-flow/dependency-audit.json) |
| Build dependency audit | Seven explicitly constrained build dependencies; zero known vulnerabilities reported at capture | [Build audit](2026-11-15/dependency-qualification/native-flow/build-dependency-audit.json) |
| Component declarations | Current installed component/licence metadata retained | [Inventory](2026-11-15/dependency-qualification/native-flow/components.json) |
| Bounded database profile | 300 sources, 309 candidates; 0.846 s ingestion, 1.377 s consolidation; zero invariant violations | [Benchmark](2026-11-15/dependency-qualification/native-flow/benchmark-database.json) |

The initial [26-command record](2026-11-15/dependency-qualification/native-flow/qualification.json) preserves arguments, time bounds and exit codes. The supplementary 21:43:50–21:44:08 UTC capture reran Ruff and the complete suite using the existing wheel. The build, editable smoke, demo, dbt, restore, HTTP, audit and benchmark outputs above belong to the initial capture; those profiles were not repeated, and their executable inputs are unchanged. The 35 contract-comparison assertions comprise the 34-source baseline plus one late assertion, not 35 distinct source identities. The 341 HTTP checks include repeated checks of headers, authentication and correlation and are not additional pytest cases. Native HTTP reads/refused writes preserved all business tables; the two new PostgreSQL HTTP lifecycle tests separately exercised real mutations.

Seven build dependencies have explicit artifact hashes in `pyproject.toml`; uv 0.13.6 successfully exercised the experimental `require-build-hashes` option. These constraints complement the application/development package entries in `uv.lock`. The 119-package audit includes development and qualification tools; four packages also occur in the seven-build-dependency inventory, so the audit counts are not additive. [Primary dependency references](2026-11-15/dependency-qualification/dependency-review/) and dated audits describe this candidate, not future security status or a licence certification.

The [fresh environment attempts](2026-11-15/dependency-qualification/environment/) retain failed and successful outcomes separately: Terraform formatting and initialization passed, while validate/schema and Chromium startup encountered Unix socket denial. Docker was absent. The new browser lifecycle profile and post-browser invariant command remain implemented but unexecuted; Snowflake still lacks an authorized live environment.

The [Quality workflow capture at `bb369db1`](2026-11-15/dependency-qualification/main-reconciliation/github-actions.json) records scope failure before runner assignment, zero steps and artifacts, and skipped dependent jobs. The unread admission annotation remains an unresolved cause; this is separate from the passing native suite.

The recovered tree contained 454 historical artifact blobs plus this index. The artifacts remain unchanged; this index is updated, with its earlier version retained in Git history. The sections below describe the dated 13–14 November captures and their earlier source/dependency baseline. Their original counts, failures and file hashes have not been replaced with the newer results.

## Historical source and provenance — 14 November

The application, test and dbt inputs qualified by the full suite match [remote commit `205e7507b9cd7dc1b34a858f2c524ce0c832642c`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/205e7507b9cd7dc1b34a858f2c524ce0c832642c), with complete source tree `2075183147d1ff50ddfee7e86e99ad7d7bdb367e`. The corresponding local commit is `e39a0b508ac9188558840d3ecb9e4602d002f4e0`. Publication used the GitHub Git-data API with an expected-head check; the complete local and remote trees matched before the branch advanced.

The [source correspondence](2026-11-14/source-correspondence.json) independently compares 88 test/runtime input hashes, 54 native-flow input hashes and 20 HTTP input hashes with that committed source. The first evidence delivery also corrects only the explanatory annotations of one optional alert: its name, expression, duration and severity are unchanged. The [structural comparison](2026-11-14/alert-annotation-review.json) is retained; that monitoring configuration was not deployed. Application, test, dbt project, dependency and Docker deployment contents were identical to the qualified source at that historical delivery. Subsequent changes to the CI workflow and Snowflake qualification helper are recorded separately below. The local repository was restored from the previous remote tree before continuation; its local commit ancestry differs from the preserved remote history.

All runtime work in this 14 November capture used the provided isolated workspace, Linux x86_64 and Python 3.12.14. Nine CPUs were visible to the process; this is not a dedicated hardware allocation or a throughput entitlement. The actual database was PostgreSQL 17.12 from verified official PGDG packages. [Repository signature verification](2026-11-14/postgres-provenance/repository-verification.json), [package hashes](2026-11-14/postgres-provenance/verified-packages.json), [binary versions](2026-11-14/postgres-provenance/binary-versions.json) and the [real readiness query](2026-11-14/native-flow/runtime/readiness-query.json) are retained. Packages were extracted locally without running a system installer.

The earlier claim that every local socket-based process was unavailable was too broad. Unix sockets are denied; loopback TCP works. PostgreSQL ran with `unix_socket_directories=''` and normal private SCRAM credentials. No permission or security policy was relaxed.

## Results actually obtained on 14 November

| Check | Observed result | Original evidence |
| --- | --- | --- |
| Initial real PostgreSQL suite | 112 tests and 15 subtests passed before the added regressions | [Initial JUnit](2026-11-14/baseline-postgres/pytest.xml), [output](2026-11-14/baseline-postgres/stdout.txt) |
| Historical defect reproduction | Three new cases failed, one passed against the earlier implementation | [Before-fix JUnit](2026-11-14/temporal-before-fix/pytest.xml), [original failure output](2026-11-14/temporal-before-fix/stdout.txt) |
| Final complete suite | **125 tests and 15 subtests passed, zero skipped; 53 PostgreSQL integration cases** | [Final JUnit](2026-11-14/pytest/pytest.xml), [stdout](2026-11-14/pytest/stdout.txt), [command/input record](2026-11-14/pytest/execution.json) |
| Ruff / JavaScript syntax | Exit code zero for both commands | [Ruff](2026-11-14/final-static/execution.json), [JavaScript](2026-11-14/final-javascript/execution.json) |
| New business demonstration | Six assertions true; nine invariants without violations | [Full original demo](2026-11-14/native-flow/demo.json), [business check](2026-11-14/native-flow/business-check.json) |
| PostgreSQL analytical export | Sixteen operational tables exported and validated | [Export report](2026-11-14/native-flow/warehouse-export.json) |
| dbt build | Five models and two hooks succeeded; **41 data tests passed** | [Original run results](2026-11-14/native-flow/dbt/build/run_results.json), [executed manifest](2026-11-14/native-flow/dbt/build/manifest.json) |
| dbt catalog | Five models and sixteen source relations introspected; no catalog errors | [Catalog](2026-11-14/native-flow/dbt/docs/catalog.json) |
| Backup / restore | Native 17.12 clients; 17 operational table fingerprints equal; nine invariants passed | [Backup manifest](2026-11-14/native-flow/reference.dump.manifest.json), [restore](2026-11-14/native-flow/restore.json) |
| Populated-target negative case | Code 1 with the exact intended rejection; no forbidden success report | [Negative restore](2026-11-14/native-flow/second-restore-rejection.json) |
| dbt on restored database | **41 tests and two hooks passed** | [Restored run results](2026-11-14/native-flow/dbt/restored-test/run_results.json), [restored manifest](2026-11-14/native-flow/dbt/restored-test/manifest.json) |
| Database profile | 300 inputs; measured ingestion, consolidation, query plan and historical growth; declared checks passed | [Full database benchmark](2026-11-14/native-flow/benchmark-database.json) |
| Real HTTP | **24 requests and 127 assertions passed**; auth, assets, provenance, metrics and correlation checked | [HTTP report](2026-11-14/http/http-report.json), [server log](2026-11-14/http/server-stderr.txt) |
| Process cleanup | PostgreSQL stopped with code zero; HTTP lifecycle completed and port closed | [Native-flow runtime](2026-11-14/native-flow/runtime/run.json), [HTTP runtime](2026-11-14/http/runtime/run.json) |

The complete pytest suite has one recorded Starlette TestClient deprecation warning. Unit transport/provider doubles remain explicitly distinct from the 53 real PostgreSQL cases. The 127 HTTP assertions include repeated checks over headers, responses and traces; they are not 127 additional pytest test cases.

The new regressions cover eight publication cases and five temporal/group cases. The code prevents completion before actual consumer convergence, preserves bounded retries, preflights historical compatibility without aborting unrelated pairs, and removes stale group-conflict status after a third member changes. The comparison score and source revision evidence remain separate from current group disposition.

## Business and recovery observations

The fresh demonstration finished with **34 retained sources, 28 active golden records, eight executed decisions and 34 aligned reporting mappings**. The deliberately mistaken Orion merge was corrected, its original IDs were restored, and later source updates were retained. Final outstanding delivery was zero. The six demonstration assertions include repeat ingestion, duplicate-event polling, late-assertion preservation, original-ID restoration, consumer alignment and business invariants.

The sixteen-table analytical export has snapshot ID `65f67c169a9bbddc085dd8a7f97df002e12309fd98b6800b4aa8b9e61e411341`. It includes 36 raw assertions, 48 golden-history rows, 18 decision events and 52 outbox events. It is a real PostgreSQL export; no Snowflake load followed it.

The backup archive contained 132,994 bytes. The restore compared all seventeen operational tables, including the migration ledger, against the consistent exported snapshot. The restore's internal elapsed field was 0.802 seconds for this small fixture. The next restore attempt was rejected specifically because the target was not empty and isolated. All 41 dbt tests then passed over the restored database. This does not restore external consumer business decisions or qualify a larger recovery-time objective. The archive itself is excluded from the repository.

## Measured bounded database profile

| Measurement | Observation |
| --- | ---: |
| Source records | 300 |
| Candidate pairs / exhaustive pairs | 309 / 44,850 |
| Ingestion | 1.294 seconds |
| Consolidation | 1.774 seconds |
| Observed ingestion rate | 231.9 source records/second |
| Measured SQL join execution | 0.519 milliseconds |
| Raw assertions after 30 updates | 300 → 330 |
| Golden-history rows after updates | 500 → 530 |
| Outbox events after updates | 700 → 730 |
| Post-load invariants | Nine checks, zero violations |

The 150-record exhaustive control had complete candidate recall, zero false automatic pairs and equal automatic pair sets between blocked and exhaustive comparison. The 300-record distribution has complete identifiers and is easier than the held-out ambiguity set. These observations do not establish production-scale throughput, arbitrary skew, additional-worker performance or Snowflake cost.

The benchmark's traced heap covers blocking/comparison, and its maximum RSS is sampled before the database branch. Neither is a peak for the complete database flow or PostgreSQL server. The query plan measures one small join, not application or warehouse latency.

## HTTP and browser boundaries

The successful native HTTP run checked actual Uvicorn responses backed by the populated PostgreSQL database. All 34 reporting pointers aligned with the reference. Reads and refused writes left the business snapshot unchanged. Each of the 24 distinct response correlation IDs was found in an actual structured server event. Temporary actor files were deleted and no actor token was found in retained responses/logs.

The [first HTTP harness report](2026-11-14/http-initial-harness/http-report.json) remains `passed: false`: its HTTP assertions passed, but the harness incorrectly demanded process exit zero after Uvicorn's graceful SIGTERM sequence. The wrapper was corrected to verify lifecycle completion and a closed port along with the expected signal exit. The second run succeeded without changing application code. The original failed report was not rewritten.

No rendered screenshot was produced. The [official Playwright download](2026-11-14/browser-blockers/install-report.json) received an unavailable-site HTML response instead of a browser archive. A separate [system Chromium launch](2026-11-14/browser-blockers/system-launch-report.json) failed when its singleton needed a denied Unix socket. Standard launch was attempted without additional permission-workaround flags. Docker was unavailable. Native HTTP success does not qualify either browser rendering or container deployment.

## GitHub: Quality and Terraform at the qualified source

| Workflow at source `205e7507` | Run | Observed outcome |
| --- | --- | --- |
| Quality and PostgreSQL qualification | [43593711716](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43593711716) | Scope failed with `runner_id: 0`, no steps; dependency, database and container jobs skipped |
| Terraform static qualification | [43593711641](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43593711641) | Static job failed with `runner_id: 0`, no steps |

Both artifact collections are empty. Original responses are retained under [github](2026-11-14/github/ci-quality-run.json), including [jobs](2026-11-14/github/ci-quality-jobs.json), [artifacts](2026-11-14/github/ci-quality-artifacts.json) and [check outputs](2026-11-14/github/ci-checks.json). Each failed check reports one annotation, but the connected interface cannot read its text. The exact cause remains unknown; billing, quota and policy explanations are unconfirmed.

The earlier source runs [43526045051](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43526045051) and [43526045030](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43526045030), and the initial run [43524025662](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43524025662), are retained unchanged in the 13 November folder. No billing, visibility or external-resource setting was changed to bypass the admission failure.

## Subsequent CI evidence-control qualification

The [13:45 UTC targeted run](2026-11-14/ci-evidence-hardening/qualification.json) executes the revised workflow's actual dbt commands and negative-restore block on native PostgreSQL 17.12. This is separate from the full suite and from GitHub execution. The runtime substitutes native clients and a private passfile for the CI service-container wrappers; the original PostgreSQL fixtures and archived backup are reused without resetting or successfully restoring either database.

| Control | Observed result | Original evidence |
| --- | --- | --- |
| Separate build/docs output | 41 dbt tests passed; five models and two hooks succeeded; build manifest/results hashes unchanged after docs; distinct invocation IDs | [Build](2026-11-14/ci-evidence-hardening/dbt/build/run_results.json), [docs](2026-11-14/ci-evidence-hardening/dbt/docs/run_results.json) |
| Catalog | Five models and 16 sources, no errors | [Catalog](2026-11-14/ci-evidence-hardening/dbt/docs/catalog.json) |
| Populated-target refusal | Control exit 0 only after exact reason, restore exit 1 and all six recorded conditions | [Expected rejection](2026-11-14/ci-evidence-hardening/restore-controls/populated-target/second-restore-rejection.json) |
| Missing archive | Actual restore exit 1, but control exit 1 and `passed: false`; wrong failure rejected | [Negative control](2026-11-14/ci-evidence-hardening/restore-controls/missing-archive/second-restore-rejection.json) |
| Missing target configuration | Actual restore exit 1, but control exit 1 and `passed: false`; wrong failure rejected | [Negative control](2026-11-14/ci-evidence-hardening/restore-controls/missing-restore-configuration/second-restore-rejection.json) |
| State and cleanup | 17 table fingerprints unchanged in each database; 24 source files unchanged during capture; server stop exit 0 | [Before](2026-11-14/ci-evidence-hardening/database-before.json), [after](2026-11-14/ci-evidence-hardening/database-after.json), [runtime](2026-11-14/ci-evidence-hardening/runtime/run.json) |

The [copy manifest](2026-11-14/ci-evidence-hardening/preserved-artifacts.json) records 52 byte-preserved originals, including command bodies, UTC timings, outputs, results and the capture helper. Original negative-control reports remain `passed: false`; the encompassing qualification expects their rejection. The [known-secret check](2026-11-14/ci-evidence-hardening/known-secret-scan.json) found no occurrence of the runtime's private password in those originals. Upstream dbt notices also apply to these generated manifests.

The same output collision existed in the Snowflake qualification helper, whose build/docs paths are now separated. Its live execution remains pending. A separate [official-source transport review](../docs/terraform-provider-transport.md) establishes that the pinned Linux provider's managed-debug path still chooses a Unix socket; this is analysis, not provider-schema execution.

The [static verification record](2026-11-14/ci-evidence-hardening/static-verification.json) retains shell/Python syntax checks, relative-link checks, byte-preservation verification and the scoped comparison with the previously qualified application inputs. It also records that the Snowflake helper was not executed live.

The subsequent [publication pattern scan](2026-11-14/ci-evidence-hardening/publication-secret-scan.json) checked 543 publishable files and 452 reachable local-history blobs, with no detected pattern or unscanned input. This scan includes the explicitly staged build artifacts and logs that Git ignore rules would otherwise omit. It precedes copying its own report and does not claim complete secret detection or coverage of every remote ancestor.

## Public-source publication preflight

On 14 November the maintainer requested a public repository and retained responsibility for GitHub interface actions. The [remote branch-history inventory](2026-11-14/publication-preflight/remote-inventory.json) enumerates both observed branch heads, all ten reachable commits and their ten complete recursive trees at that capture. The [scoped history scan](2026-11-14/publication-preflight/remote-history-scan.json) checked **518 distinct blobs, 10,211,743 bytes and ten commit messages**, with no detected pattern or limited input within that scope. All blob sizes and Git object hashes were verified: 501 matching objects were available locally and 17 older versions were fetched through the connected GitHub blob endpoint. Commit identity addresses use the GitHub noreply domain.

This closes the earlier gap between the reconstructed local history and the reachable histories of the two named remote branches at `fc67bf68` / `8fc92d96`. It does not claim coverage of tags, whose enumeration endpoint was unavailable, unreachable objects, other repositories or account configuration. The generated publication documentation and its own evidence are later inputs, checked separately before publication. Pattern scanning is not complete secret detection; the synthetic fixtures and notices were also reviewed for presentation scope.

The separate [Actions inventory](2026-11-14/publication-preflight/actions-inventory.json) reconciled all **12 runs and 33 jobs** returned at 14:03 UTC. Every job has an explicitly empty step list, and all twelve artifact collections are empty. Twelve failed jobs report `runner_id: 0`; the remaining 21 are skipped. No annotation text or inaccessible log was read, and the inventory does not infer the admission cause. The [preservation record](2026-11-14/publication-preflight/preserved-artifacts.json) identifies the original reports and capture helper.

Publication of the documented source candidate and full runtime acceptance are separate outcomes. The current publication procedure, maintainer interface actions and anonymous-access checks are in [publication](../docs/publication.md). No additional runtime gate is credited by these read-only inventories.

The later [documentation verification](2026-11-14/publication-preflight/static-verification.json) checked 172 relative links, the exact About metadata and preservation hashes, with no executable-input change from `fc67bf68`. Its [working-tree scan](2026-11-14/publication-preflight/publication-working-tree-scan.json) includes the newly prepared publication files: 552 files and 501 reachable local-history blobs, with no detected pattern or limited input. That local scope complements the separately enumerated remote history above and precedes copying its own report.

## Post-merge readback and dependency automation

The [integration record](2026-11-14/publication-preflight/integration-verification.json) verifies that PR #2 merged at `e27f4c2f58d812a2213b1457378095dc72dafd8a` and that `main` contained the full reviewed tree `4e3591997281aeb6666c933d39d731e00b53186c`. The full README was fetched from `main`. Visibility was private and About metadata was empty at the recorded 14:15:46 UTC check; the maintainer owns those interface changes. This record proves source integration, not anonymous public access or full runtime acceptance.

The [expanded remote-history scan](2026-11-14/publication-preflight/post-merge-history/remote-history-scan.json) includes the five branches listed after integration and the closed Python-update PR's head: **16 commits, 15 complete trees, 540 unique blobs, 11,065,653 bytes and 16 commit messages**. All blob sizes and Git object hashes matched. Of these blobs, 517 matched local Git objects and 23 were retrieved remotely. No configured pattern or limited input was reported within this scope. This includes the new dependency proposal branches without integrating their contents into `main`. Tags, unreachable objects and inaccessible account/log contents remain outside the scan. Four originals are recorded in the [preservation manifest](2026-11-14/publication-preflight/post-merge-history/preserved-artifacts.json).

The [post-merge Actions inventory](2026-11-14/publication-preflight/post-merge-actions.json) preserves the main-push Quality and Terraform job summaries: zero steps and zero artifacts. Separately, three Dependabot service runs succeeded with six steps each. The historical 14:03 inventory above remains unchanged; the 18 later service steps must not be mistaken for application qualification. The Python 3.15 proposal was closed without merging because it conflicts with the Python 3.12 contract. At that capture the new Docker-update ignore rule had not yet been observed in a subsequent service run, and PRs #4–#6 were unqualified and unmerged with the reference lock unchanged. The 15 November candidate above includes those updates and the later Python 3.12.16 proposal, supported by new execution evidence.

The final consolidation's [static checks](2026-11-14/publication-preflight/post-merge-static-verification.json) cover the runtime contract, metadata, relative links and original evidence hashes. The corresponding [working-tree scan](2026-11-14/publication-preflight/post-merge-working-tree-scan.json) covers the new publication files separately from the recorded remote history and precedes copying its own report. No full runtime suite was rerun for these documentation and automation-policy changes.

## Historical 13 November capture

The earlier retained source was [`f87abb572c03b5088c466e9c411a23b7c75a8da4`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/f87abb572c03b5088c466e9c411a23b7c75a8da4), tree `966ec4b81c4e2fe38a8b4d22d73d5b353c56b840`. Its [environment](2026-11-13/environment.json) and [command record](2026-11-13/local-execution.json) remain historical evidence.

| Historical check | Observed at capture | Original artifact |
| --- | --- | --- |
| Unit suite | 72 tests and 15 subtests passed; 40 integration cases deselected | [JUnit](2026-11-13/unit-tests.xml) |
| PostgreSQL integration collection | Forty cases collected, not executed then | [Collection](2026-11-13/integration-collection-stdout.txt) |
| dbt parse | Five models, sixteen sources and 41 test nodes parsed; not executed then | [Parse manifest](2026-11-13/dbt-parse-manifest.json) |
| Unsafe-schema negative case | Rejected with the intended simple-identifier error | [Output](2026-11-13/dbt-reject-unsafe-schema-stdout.txt) |
| Locked dependency audit | 119 dependencies, zero known vulnerabilities reported at capture time | [Audit JSON](2026-11-13/dependency-audit.json) |
| Component declarations | 119 dependencies inventoried; three distribution-obligation review items retained | [Inventory](2026-11-13/components.json) |
| Terraform | Format passed and provider installed; schema loading failed at Unix socket creation | [Validation output](2026-11-13/terraform-validate-blocked.json), [debug log](2026-11-13/terraform-provider-debug.txt) |
| Secret-pattern control | Scoped working-tree and local reachable-history report | [Original scan](2026-11-13/secret-scan.json) |

The [matching evaluation](2026-11-13/matching-evaluation.json) still records the unchanged matching rules on the separate sixteen-record holdout: seven positive pairs retrieved among eleven candidates, three true automatic pairs and zero false automatic pairs. Deterministic auto-plus-review retrieved six of seven positives with one false review; hybrid review retrieved all seven with the same one false review. These small synthetic denominators remain explicit.

## Preservation, controls and remaining evidence

The [preserved-artifact manifest](2026-11-14/preserved-artifacts.json) lists original file paths, sizes and digests for byte-preserved copies. [Native command records](2026-11-14/native-flow/qualification.json) retain UTC intervals, arguments and exit codes for all seventeen phases. Build/restored SQL and dbt logs remain alongside their manifests. Capture helpers preserve the actual execution procedure; they are records of this isolated setup, not an installed system service.

The [known-database-secret scan](2026-11-14/native-flow/known-secret-scan.json) checked 338 original qualification files against the generated database password without retaining its value or digest. Its scope is that known value, not universal secret detection. The [final repository pattern scan](2026-11-14/security/scan.json) checked 483 files and 146 reachable local-history blobs, with no detected pattern and no unscanned input. The [earlier prepublication scan](2026-11-14/secret-scan.json) is also preserved. These scans precede copying their own reports into the evidence folder; their limited coverage is explicit. Local reachable history is the restored baseline plus continuation commits; it is not presented as a new scan of every remote ancestor.

Upstream macros and compiled derivatives retain the rights in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) and [preserved licence files](third-party-licenses/sources.json). Credentials, database archives, vendor binaries and generated dbt application HTML are excluded. Evidence hashes prove correspondence, not independent certification, licence approval or production readiness.

The latest 17 November CET hosted CI has now executed the full PostgreSQL/dbt/container/browser reference at `af4ed2b77616`, and a compatible runner has completed **static Terraform provider-schema validation** on byte-identical static inputs. Remaining qualification is **live Snowflake** publication/readback/rollback, dbt parity and cost evidence, production-target controls, public licence/protection/release decisions, and direct original CircleCI artifact/settings inspection in #16. The [acceptance matrix](../docs/acceptance.md) retains these boundaries. Synthetic and provider-static success cannot establish a live warehouse or production acceptance.
