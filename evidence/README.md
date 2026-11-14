# Observed evidence — 0.1.0rc1

**The native PostgreSQL reference and HTTP path passed the recorded qualification. Full release acceptance remains open.** Original successes, failures and environment limits are preserved separately. Database results do not establish Docker, rendered-browser, Terraform or Snowflake qualification.

## Qualified source and provenance

The application, test and dbt inputs qualified by the full suite match [remote commit `205e7507b9cd7dc1b34a858f2c524ce0c832642c`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/205e7507b9cd7dc1b34a858f2c524ce0c832642c), with complete source tree `2075183147d1ff50ddfee7e86e99ad7d7bdb367e`. The corresponding local commit is `e39a0b508ac9188558840d3ecb9e4602d002f4e0`. Publication used the GitHub Git-data API with an expected-head check; the complete local and remote trees matched before the branch advanced.

The [source correspondence](2026-11-14/source-correspondence.json) independently compares 88 test/runtime input hashes, 54 native-flow input hashes and 20 HTTP input hashes with that committed source. The first evidence delivery also corrects only the explanatory annotations of one optional alert: its name, expression, duration and severity are unchanged. The [structural comparison](2026-11-14/alert-annotation-review.json) is retained; that monitoring configuration was not deployed. Application, test, dbt project, dependency and Docker deployment contents remain identical to the qualified source. Subsequent changes to the CI workflow and Snowflake qualification helper are recorded separately below. The local repository was restored from the previous remote tree before continuation; its local commit ancestry differs from the preserved remote history.

All runtime work used the provided isolated workspace, Linux x86_64 and Python 3.12.14. Nine CPUs were visible to the process; this is not a dedicated hardware allocation or a throughput entitlement. The actual database was PostgreSQL 17.12 from verified official PGDG packages. [Repository signature verification](2026-11-14/postgres-provenance/repository-verification.json), [package hashes](2026-11-14/postgres-provenance/verified-packages.json), [binary versions](2026-11-14/postgres-provenance/binary-versions.json) and the [real readiness query](2026-11-14/native-flow/runtime/readiness-query.json) are retained. Packages were extracted locally without running a system installer.

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

## GitHub: source-code workflows still received no runner

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

Remaining evidence is the actual container/browser run, Terraform provider-schema validation, GitHub runner execution and authorized live Snowflake publication/dbt parity/cost observations. The exact acceptance and publication prerequisites are in [the acceptance matrix](../docs/acceptance.md). A successful native reference does not close those gates.
