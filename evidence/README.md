# Observed evidence — 0.1.0rc1

**The reference and provider integrations are not accepted.** The records below preserve actual local results and actual GitHub execution blockers. They do not substitute unit tests for a database, container, browser or Snowflake run.

## Executed source

The final local capture used source commit [`f87abb572c03b5088c466e9c411a23b7c75a8da4`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/f87abb572c03b5088c466e9c411a23b7c75a8da4), whose Git tree is `966ec4b81c4e2fe38a8b4d22d73d5b353c56b840`. The local and remote commit histories have different commit IDs because publication used the GitHub Git-data API; their complete source trees were compared and matched. The [environment record](2026-11-13/environment.json) retains that correspondence, package versions, platform facts and SHA-256 values for executable inputs. Subsequent documentation/evidence additions do not qualify a different implementation.

Commands, UTC start times, process wall times, exit codes, output paths and explicit environment overrides are retained in [local-execution.json](2026-11-13/local-execution.json). The capture ran in the provided isolated authoring environment, not on a GitHub runner. Content hashes establish correspondence only; they are not independent certification.

## Results actually obtained

| Check | Observed result | Original evidence |
| --- | --- | --- |
| Python unit, matching, HTTP/context and provider-boundary tests | **72 passed; 15 subtests passed; 40 integration cases deselected** | [pytest output](2026-11-13/unit-tests-stdout.txt), [JUnit](2026-11-13/unit-tests.xml) |
| PostgreSQL integration collection | 40 cases collected, **not executed** | [collection output](2026-11-13/integration-collection-stdout.txt) |
| Ruff / JavaScript syntax | Exit code 0 | [Ruff](2026-11-13/ruff-stdout.txt), command records for both |
| dbt PostgreSQL parse | Exit code 0; five models, 16 sources and 41 data-test nodes parsed | [parse output](2026-11-13/dbt-parse-stdout.txt), [original manifest](2026-11-13/dbt-parse-manifest.json), [parse log](2026-11-13/dbt-parse-log.txt) |
| Unsafe dbt schema negative case | Exit code 2 with the intended simple-identifier compilation error | [negative-case output](2026-11-13/dbt-reject-unsafe-schema-stdout.txt) |
| Locked dependency audit | 119 dependencies checked; zero known vulnerabilities reported at capture time | [pip-audit JSON](2026-11-13/dependency-audit.json), [locked requirements](2026-11-13/audit-requirements.txt) |
| Component licence declarations | 119 dependencies inventoried; metadata check completed; three distribution-obligation review items remain visible | [component inventory](2026-11-13/components.json), [third-party notices](../THIRD_PARTY_NOTICES.md) |
| Bounded Python matching profile | 300 synthetic records; 309 candidates versus 44,850 exhaustive pairs | [benchmark JSON](2026-11-13/benchmark-control.json) |
| Terraform formatting/version | Format exit code 0; Terraform 1.17.2 and Snowflake provider 2.22.1 recorded | [version JSON output](2026-11-13/terraform-version-stdout.txt), command records |
| Terraform provider schema | **Blocked** before schema loading: provider could not create a Unix socket | [original validation JSON](2026-11-13/terraform-validate-blocked.json), [original debug log](2026-11-13/terraform-provider-debug.txt) |
| Unix socket capability | `PermissionError`, errno 1, operation not permitted | [capability observation](2026-11-13/socket-capability-stdout.txt) |
| Secret-pattern scan | Working tree and local reachable history reviewed; results and coverage are explicit | [scan report](2026-11-13/secret-scan.json) |

The unit run has one Starlette warning about deprecation of `httpx` with its TestClient. The tests passed with the locked versions; future adapter migration is not implied by that result. HTTP context tests use an explicitly named service double to exercise in-process transport and isolation. Snowflake boundary tests also use explicit doubles. Neither is reported as a live integration.

The dbt manifest is an **actual parse artifact**. Its 41 test nodes were not executed, and no `run_results.json`, populated catalog, deployed-model lineage or warehouse result is invented. Embedded upstream macros retain their rights; installed licence files accompany the manifest under [third-party licences](third-party-licenses/sources.json).

## Matching observations and their limits

The [split evaluation](2026-11-13/matching-evaluation.json) preserves deterministic and hybrid results on the separate development and held-out identities. On the 16-record holdout:

- Candidate generation retrieves all seven labeled positive pairs among 11 candidates, compared with 120 exhaustive pairs.
- Automatic matching produces three true pairs and zero false pairs: precision 3/3 and recall 3/7.
- Deterministic auto-plus-review retrieves six of seven true pairs with one false review.
- The hybrid policy retrieves seven of seven true pairs with the same one false review: suggestion precision 7/8, with five review pairs.

The 300-record load corpus is a separate, easier distribution with complete identifiers. Its measured candidate reduction is 99.31%. Blocking took approximately 0.019 seconds and candidate comparison 0.055 seconds in this run. Peak traced Python heap was 571,470 bytes; process maximum RSS was 57,020 KiB. The 150-record exhaustive control produced the same automatic pair set as blocking, with full labeled candidate recall and zero false automatic pairs.

These are bounded single-process measurements. They do not establish database join cost, consolidation latency, history growth, extra-worker throughput, provider performance or provider billing. Those require the unexecuted profiles.

## GitHub runs: no runner execution

The final executable revision triggered these workflows:

| Workflow | Run | Observation |
| --- | --- | --- |
| Quality and PostgreSQL qualification | [43526045051](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43526045051) | Scope job failed with `runner_id: 0`, empty runner name and no steps; PostgreSQL/dependency/container jobs skipped |
| Terraform static qualification | [43526045030](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43526045030) | Static job failed with `runner_id: 0`, empty runner name and no steps |

Both runs were created at `2026-11-13T23:17:52Z` and updated as failed by `23:17:55Z`. Both artifact collections are empty. Original API responses are retained as `ci-43526045051-{run,jobs,artifacts}.json` and `ci-43526045030-{run,jobs,artifacts}.json` in this directory's date folder. The earlier run [43524025662](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43524025662), at `d60f423fab56add510ba16933f20497baccd3383`, is preserved separately under `ci-initial-*` and had the same pre-runner outcome.

The connector does not expose the failure annotation through its allowed endpoints. The isolated browser presented the private GitHub URL without an authenticated session. **The exact cause is unknown**; quota, billing and repository-policy explanations remain hypotheses. No billing, policy, visibility or external resources were changed to work around it.

## Missing evidence and continuation

No successful PostgreSQL transaction scenario, dbt build/data test, restoration, database load, container startup, rendered console capture, Terraform provider-schema validation or Snowflake qualification exists in this delivery. Those gaps remain explicit in [acceptance](../docs/acceptance.md).

Read the exact failed-job annotation through an authorized signed-in GitHub interface and provide a runner-capable environment. Run the full [verification profiles](../docs/verification.md) against the intended revision and retain their original artifacts. Snowflake additionally needs a dedicated authorized account/role, key-pair credential, resource scope and budget. A skipped job, clean parse, source-tree hash or published PR is not a replacement for those results.
