# CircleCI source and qualification reconciliation — 15 November 2026

The default `main` branch is the code source of truth. Each CI result applies to its checkout SHA; a setup-branch success must not be presented as execution on another commit.

## Direct CircleCI native artifact inspection — 17 November 2026

The [provider-native evidence register](../evidence/2026-11-17/circleci-native-readback/) now records independent read-only CircleCI API and original artifact URL inspection for executable `57c78b657027` (jobs #81/#82) and the documentation-only main `96868b0540a5` (jobs #85/#86). Original `scope.json` on each SHA reports `runtime_requested=true` and the correct checkout commit. The CircleCI test-result API reports **212/212 successes** for each PostgreSQL job, with matching extracted JUnit case counts; native dbt build results have **41 pass + 7 success (48 total)**, and the manifests describe **5 models, 41 tests, 2 operations and 16 sources**. The real business report records nine checks without violations and complete 34/34 consumer coverage on the executable source.

**Acceptance boundary:** Original artifact content was retrieved and semantically parsed, not independently preserved as raw byte streams or SHA-256 hashes. Actual CircleCI pipeline metadata confirms a GitHub App push, `.circleci/config.yml` and matching config/checkout SHA. The saved Project Settings (trigger preset, config source and checkout source administration fields) still require authenticated owner-side readback. **Issue #16: 5/6 after integration; only Project Settings remains open.** This does not change issue #1 (8/10), live Snowflake, release or production acceptance.

## Historical mainline selector qualification — 17 November 2026 (CET)

[PR #22](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/22) merged at [`af4ed2b776162f8dce497b20d4f4fad063adeeab`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/af4ed2b776162f8dce497b20d4f4fad063adeeab) and eliminated a real false-green risk: the old CircleCI selector compared only `HEAD^` with `HEAD`, missing runtime commits earlier in a multi-commit push ending with docs. The new `scripts/circleci_scope.py` always requests PostgreSQL/dbt on `main`, verifies the checkout SHA against `CIRCLE_SHA1`, records `runtime_requested=true`, and **has no docs-only skip**. Six isolated selector regressions passed (both `pytest` and `python -m pytest`); this is a separate local result.

Both default CircleCI [`build-and-test`](https://app.circleci.com/workflow/6bf085dd-9633-4c01-8ad8-5062d54f2bfc/job/21c07969-24df-4dc4-8098-371c27364ac3) and [`postgres-integration`](https://app.circleci.com/workflow/6bf085dd-9633-4c01-8ad8-5062d54f2bfc/job/ffbca4c9-ba92-47f9-83a7-b71249d757be) report **success at `af4ed2b77616`**. [GitHub Actions Quality run #43978646310](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43978646310) independently executed and passed scope, dependency audit, real PostgreSQL/dbt/restore and Docker/browser jobs on exactly that SHA: **189 pytest + 15 subtests** (one warning), dbt **48/48**, restored dbt **43/43**, `restore_verified=true`, rendered three-role lifecycle `passed=true`, 34 source identities and zero JavaScript errors. The [dated manifest](../evidence/2026-11-17/ci-mainline-hardening/manifest.json) records the original job/artifact IDs and evidence boundaries.

**Provider-specific caveat:** The original CircleCI `scope.json`, JUnit and dbt artifact bytes are *not* independently downloaded. Thus do not infer their precise fields from the green badge; the source configuration and successful reported job, plus separate original GitHub Actions logs, establish the mainline runtime behavior. The extra CircleCI minutes on each `main` push are an intentional safety cost. Terraform static qualification and live Snowflake have independent evidence requirements.

## Historical mainline qualification — 16 November 2026

At [commit `9b72725da693`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/9b72725da693b4587c27a12b1d65e6f639d69a86), both default CircleCI jobs successfully completed: [`build-and-test`](https://app.circleci.com/workflow/9fd56b39-9f8f-431e-bb11-177bcfe45f86/job/1c1c7628-3f69-4fa0-aac0-4e8eca38444b) and [`postgres-integration`](https://app.circleci.com/workflow/9fd56b39-9f8f-431e-bb11-177bcfe45f86/job/8098e38b-9f89-4910-9ab0-95cf0309f1a7). The commit-status results come from GitHub's source-linked CI contexts. The original CircleCI scope receipt and artifact bytes were **not** independently downloaded.

The independently executed [GitHub Actions Quality run #43920046617](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617) completed with success on **that same commit**, for `scope`, `dependencies`, `postgres` and `container`. Original GitHub Actions logs confirm **183 pytest tests and 15 subtests passed**, dbt build **PASS=48/48**, dbt on restored database **PASS=43/43**, `restore_verified=true`, successful expected rejection of a repeated restore, and a rendered browser lifecycle reporting `passed=true`, `lifecycle_executed=true` with 34 source identities preserved and no JavaScript errors. Four named artifact collections were uploaded. The dated [evidence manifest](../evidence/2026-11-16/ci-main-qualification/manifest.json) is a derived index linked to the original run, not a replacement for raw logs and artifacts.

Previous GitHub Actions jobs that failed **before runner assignment** are historical and no longer describe this particular qualified source. The synthetic reference is now qualified at the same mainline SHA in hosted CI. Live Snowflake execution, production-target acceptance, branch protection, licensing and public release designation remain independent; anonymous repository and README access was separately observed on 16 November in a clean browser.

## Pipeline observations

| Pipeline | Checkout | Observed conclusion | Qualification boundary |
| --- | --- | --- | --- |
| [#10](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/10) | Previous `main` `03c927b3` | Not Run; `.circleci/config.yml` absent | Historical configuration failure |
| [#11](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/11) | Setup `9cae866` | Success | Matching-only smoke |
| [#20](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/20) | Setup `b7485a2` | Success | Full `scope`, `dependencies`, `postgres` and `container` jobs |
| [#21](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/21) | Setup `b7485a2` | Success | Separate `reference-containers` rendered browser/Compose profile |
| [#22](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/22) | PR branch `620c5f1` | Success | Matching-only smoke |
| [#23](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/23) | `main` `a1ea115` | Success | Matching-only smoke |
| [#25](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/25) | Setup `cd359b4` | Success | Matching-only smoke |

The linked GitHub combined status for [commit `b7485a2`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/b7485a20fa9a13aaa5a84179bf1a03f01bdbee7a) confirms the individual CircleCI successes: [scope](https://app.circleci.com/workflow/b59ccc8c-7b24-4d78-a7eb-d2c7523b188f/job/e06d3e1f-7dc6-403a-ac1e-4f4bc2106a0f), [dependencies](https://app.circleci.com/workflow/b59ccc8c-7b24-4d78-a7eb-d2c7523b188f/job/447295b3-35e6-4b4f-9025-76c5c02b4604), [postgres](https://app.circleci.com/workflow/b59ccc8c-7b24-4d78-a7eb-d2c7523b188f/job/dd9810a6-a61d-4ac5-93ea-6a8122f156ff), [container](https://app.circleci.com/workflow/b59ccc8c-7b24-4d78-a7eb-d2c7523b188f/job/a9328ca0-cc8c-4caf-8175-cf6ba33dbff3), and [reference-containers](https://app.circleci.com/workflow/9e653f43-eefe-4329-b54b-0371dc817a06/job/788cd34a-5c18-48c8-8944-a1d89ec46659).

**Proof boundary:** These are successful job statuses, not independently downloaded original CircleCI logs. JUnit counts, restored-table fingerprints, dbt manifests, Playwright screenshots and post-lifecycle business assertions require original artifact readback. The native 180-test result has [separate committed evidence](../evidence/2026-11-15/dependency-qualification/main-reconciliation/qualification.json) and must not be copied as a CircleCI count.

## Exact executable source reconciliation

At the initial comparison, `main` `a1ea115` and the successful setup revision `b7485a2` differed in only `.github/workflows/quality.yml`, `compose.yaml` and this main-only document. All source modules, tests, migrations, rule contracts, dependencies, synthetic data and dbt files were Git-blob-identical.

The final CI integration imports **exactly** the already-tested blobs `.github/workflows/quality.yml` (`07fb682b8e8ab0023064417975bdcafb1dde5d07`) and `compose.yaml` (`32118804f900d9bca9bea1d80c61e647edb35d05`) without altering application behavior. Quality now handles absent event metadata by selecting full qualification, pins Python 3.12.16 and recognizes `.circleci/` changes. Compose gives only the API a second loopback-bound ingress bridge while PostgreSQL and migrations stay on the internal network. This permits validated configuration correspondence, but does not mean CircleCI ran against the new merge SHA.

## Parallel original-artifact inspection recorded in PR #12

[PR #12](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/12) contains a separate qualification report from an authorized execution session. Its author states that the original CircleCI artifacts were downloaded, inspected and hashed at the tested combined revision `b7485a2`. This current reconciliation independently verified the **GitHub status contexts and executable Git blob equality**, but **did not recompute these external file hashes**. The table preserves the reported SHA-256 values rather than claiming they were regenerated here.

| Original artifact recorded by the parallel qualification | Reported SHA-256 |
| --- | --- |
| Database `artifacts/pytest.xml` | `627c48e46b9fc3ae8488127d8b442287bef2ebae5468d5ecd6ad001a0443d602` |
| Database `artifacts/restore.json` | `6405f80122edbe8229966cc0fdd32a547a883f839ac56561af81dd974481cab93` |
| Database `artifacts/second-restore-rejection.json` | `a3a69b2f806c94701dbfc89c938a0f61a97965ab1f0e72d6fdbd694ae3fc077a` |
| Browser `reference/browser-check.json` | `eae88c88efe68c3f1071bde7d0fe7cd7f3366d2f0f418d291b3cf3950cff9d34` |
| Post-lifecycle `reference/container-post-lifecycle-check.json` | `02df03919c8a29f7e416c2a16adf57eea377c7b519b406fb8030bfd695616544` |

The parallel report says the database JUnit had 195 case entries with zero failures, errors or skips, corresponding to **180 tests and 15 subtests**, and that the rendered browser lifecycle and post-lifecycle business check passed. Its workflow references are [database/package qualification](https://app.circleci.com/workflow/b514e6ba-1af2-4074-8a1c-b6751960d29c) and [rendered container qualification](https://app.circleci.com/workflow/872b65af-ec73-4fd2-872c-9b3c38c31c40). These are **reported observations from PR #12**, not new tests executed by this reconciliation.

A file hash establishes content identity only once original bytes are available. The CircleCI artifact retention window is finite; if those artifacts expire, the register is a historical third-party capture, not independently reproducible raw evidence. Live Snowflake, production permissions/cost and the repository's public release decision remain separate.

## Mainline test-gate implementation and verified execution

The low-cost branch job installs exactly Python 3.12.16, synchronizes the reviewed uv lock with development and PostgreSQL extras, and runs both the pre-existing `matching-unit` Smarter Testing suite and all non-database pytest regressions. `.circleci/test-suites.yml` now uses `uv run --no-sync` so its selected matching tests cannot silently resynchronize away dependencies needed by subsequent tests.

The `postgres-integration` job is filtered to `main`; it creates only the disposable `mdm_test` database on an ephemeral PostgreSQL service. It fails closed on missing database access, missing JUnit or any skipped/failing test, then executes dbt and business invariants. **That job reports success at `9b72725da693`.** Native backup/restore, installed-wheel packaging and rendered Chromium are instead covered by the separately executed full/reference GitHub Actions workflow on the same commit, rather than duplicated on every PR.

**17 November 2026 hardening — remotely qualified:** An isolated multi-commit Git history reproduced that the previous `HEAD^` diff missed a runtime change followed by docs-only content. CircleCI's [pipeline-value table](https://circleci.com/docs/guides/orchestrate/pipeline-variables/) does not make `pipeline.git.base_revision` available for GitHub App, so [PR #22](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/22) deliberately replaced the selector with **mandatory mainline PostgreSQL/dbt on every push**, including docs-only. The helper checks full source SHA and records `runtime_requested=true`. Both mainline CircleCI jobs and the complete same-source GitHub Actions suite now report success at `af4ed2b77616`. Do not claim independent inspection of original CircleCI artifact bytes.

The original (15–16 November) selector's local tests omitted a multi-commit push ending with docs; it has now been replaced. The new scope helper's six local regression tests passed under both pytest entrypoints. Its GitHub Actions full workflow and both CircleCI mainline jobs have since succeeded on the merged SHA, distinct from previous historical successful runs. The original CircleCI job artifact bytes remain uninspected and are tracked in issue #16.

## CircleCI 2.1 config compilation failure — 16 November 2026

The CircleCI Pipelines overview showed [#39](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/39), [#40](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/40), [#41](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/41), and [#42](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/42) as **Not Run / No workflows**. The compiler reported `Unclosed '<<' tag` in the mainline `build-and-test` job. This is a configuration compilation error, not an executed pytest/PostgreSQL/dbt failure.

At original `main` SHA `bcc7571aad95c0f015e28babdb98ef787c12c94f`, the `.circleci/config.yml` source contained four inline Python heredoc commands using an unescaped opener: three `PY` and one `PYCODE`. In CircleCI config version 2.1, the opening marker must be written as `\<<` in YAML so it survives the template parser and functions as a shell heredoc.

The correction only escapes those **four delimiters** and adds a non-database regression test in `tests/test_circleci_config.py` that rejects raw non-template openers and checks marker balance. It does not change the Python bodies, matching logic, version pins, databases, or job orchestration. The historical green workflows on setup revision `b7485a2` remain separately attributed. The corrected PR [#17](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/17) passed CircleCI branch smoke and merged. Both default CircleCI mainline jobs and all four GitHub Actions quality jobs subsequently succeeded on the merged SHA, resolving the compiler failure in observed execution. The original CircleCI `scope.json` bytes remain uninspected, while original GitHub Actions pytest/dbt/restore/browser logs were inspected.

CircleCI guidance: [compiler escape troubleshooting](https://circleci.zendesk.com/hc/en-us/articles/36469244864539-How-to-solve-the-escaping-character-error) and [2.1 configuration migration](https://discuss.circleci.com/t/breaking-changes-config-compilation-updates-september-21-2026/54719).

## Pipeline definitions and remaining work

The historical default `.circleci/config.yml` executed **matching-only** smoke testing; this is what the earlier successful `main` statuses actually prove. The new default configuration defines a fast `build-and-test` job (matching, complete non-database pytest, Ruff, secret-history scan) on every branch, followed by a **`postgres-integration` job on `main` only** (real PostgreSQL 17.12, full pytest with zero skipped tests, three-ERP demonstration, dbt build/catalog and a bounded benchmark). It records checkout SHA, Python version and PostgreSQL version and retains JUnit/DBT evidence. The `postgres-integration` job is now reported successful on the 16 November tested main commit. The source-linked GitHub Actions run supplies separately inspected original database/dbt/restore logs.

The separate `.circleci/reference.yml` is a manual Docker/browser lifecycle profile. CircleCI's additional `v1-reference-qualification` pipeline exercised the original broader `.github/workflows/quality.yml` workflow on the setup revision. Neither historic pipeline status nor a new default smoke run alone can replace the mainline database job and the separately tested restore/browser/provider gates.

1. Optional evidence parity: download and inspect original CircleCI JUnit and `scope.json` from the successful 16 November job. The same-commit GitHub Actions original logs and artifacts have already been inspected, but should not be mislabeled as CircleCI artifact files.
2. The new mandatory gate has now executed successfully on `af4ed2b77616`: verify original GitHub Actions and CircleCI statuses by commit, then inspect available job artifacts when seeking provider-specific proof. Do not mistake an earlier docs-only skipped job for a full qualification; future CircleCI main pushes no longer have that skip path.
3. Keep earlier GitHub Actions runner-admission failures as historical incidents. The 16 November GitHub Actions run received runners and completed successfully; no billing/quota/policy root cause was retroactively established for the earlier failures.
4. Live Snowflake publication/dbt parity, production operations and provider-specific acceptance remain open. GitHub currently reports public visibility but no project licence, no About description/topics, and no enforced protection on `main`; anonymous browser readback has been observed; release/tag decisions remain separate.

This document is a status reconciliation, not a generated test artifact or a provider certification. No CircleCI billing, external infrastructure or repository visibility is changed.
