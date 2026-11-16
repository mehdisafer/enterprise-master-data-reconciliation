# CircleCI source and qualification reconciliation — 15 November 2026

The default `main` branch is the code source of truth. Each CI result applies to its checkout SHA; a setup-branch success must not be presented as execution on another commit.

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

## Mainline test gate: hosted job success, artifacts awaiting independent review

The low-cost branch job installs exactly Python 3.12.16, synchronizes the reviewed uv lock with development and PostgreSQL extras, and runs both the pre-existing `matching-unit` Smarter Testing suite and all non-database pytest regressions. `.circleci/test-suites.yml` now uses `uv run --no-sync` so its selected matching tests cannot silently resynchronize away dependencies needed by subsequent tests.

The `postgres-integration` job is filtered to `main`; it creates only the disposable `mdm_test` database on an ephemeral PostgreSQL service. It fails closed on missing database access, missing JUnit or any skipped/failing test, and then executes dbt and business invariants. It deliberately **does not** duplicate native backup/restore, installed-wheel packaging or rendered Chromium because these are covered in the separately scoped, previously executed full/reference workflows. This separation avoids triggering two expensive Docker/browser qualifications on every PR.

For `main` changes limited to `README.md`, `docs/` and `evidence/`, the PostgreSQL job records `artifacts/scope.json` with `runtime_requested: false` and exits its expensive steps without running tests. All other paths, missing parents or failed diffs select the complete suite (fail-open). The scope computation compares the checkout commit against its first Git parent, which is appropriate for ordinary mainline merges; a forced history rewrite requires an explicit source comparison before accepting a skipped result. **A successful skipped-scope job is not a PostgreSQL PASS.** Only a run whose scope record requests runtime qualification and whose JUnit/dbt artifacts actually exist can qualify the new main head.

Both job definitions underwent local YAML parsing, structural checks and Bash syntax checks, and the submitted configuration blob matched the statically checked file byte-for-byte. The scope selector was also executed against three isolated Git scenarios: documentation-only selected no heavy tests, source changes selected full qualification, and an unavailable parent selected full qualification. These are **static/local checks only**. GitHub now reports a successful CircleCI `postgres-integration` job on main `9b72725d`; its original `scope.json`, JUnit/dbt files and command log must still be inspected before interpreting this as full runtime qualification.

## CircleCI 2.1 config compilation failure — 16 November 2026

The CircleCI Pipelines overview showed [#39](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/39), [#40](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/40), [#41](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/41), and [#42](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/42) as **Not Run / No workflows**. The compiler reported `Unclosed '<<' tag` in the mainline `build-and-test` job. This is a configuration compilation error, not an executed pytest/PostgreSQL/dbt failure.

At original `main` SHA `bcc7571aad95c0f015e28babdb98ef787c12c94f`, the `.circleci/config.yml` source contained four inline Python heredoc commands using an unescaped opener: three `PY` and one `PYCODE`. In CircleCI config version 2.1, the opening marker must be written as `\<<` in YAML so it survives the template parser and functions as a shell heredoc.

The correction only escapes those **four delimiters** and adds a non-database regression test in `tests/test_circleci_config.py` that rejects raw non-template openers and checks marker balance. It does not change the Python bodies, matching logic, version pins, databases, or job orchestration. The historical green workflows on setup revision `b7485a2` remain separately attributed. A new CircleCI pipeline reaching **actual jobs** on the corrected SHA is required before calling the compiler issue resolved in execution; then inspect `scope.json`, pytest/JUnit and dbt results before claiming runtime acceptance.

CircleCI guidance: [compiler escape troubleshooting](https://circleci.zendesk.com/hc/en-us/articles/36469244864539-How-to-solve-the-escaping-character-error) and [2.1 configuration migration](https://discuss.circleci.com/t/breaking-changes-config-compilation-updates-september-21-2026/54719).

## Pipeline definitions and remaining work

The historical default `.circleci/config.yml` executed **matching-only** smoke testing; this is what the earlier successful `main` statuses actually prove. The new default configuration defines a fast `build-and-test` job (matching, complete non-database pytest, Ruff, secret-history scan) on every branch, followed by a **`postgres-integration` job on `main` only** (real PostgreSQL 17.12, full pytest with zero skipped tests, three-ERP demonstration, dbt build/catalog and a bounded benchmark). It records checkout SHA, Python version and PostgreSQL version and retains JUnit/DBT evidence. The `postgres-integration` job is **observed successful at main `9b72725d` (16 Nov)** ([CircleCI job](https://app.circleci.com/workflow/9fd56b39-9f8f-431e-bb11-177bcfe45f86/job/8098e38b-9f89-4910-9ab0-95cf0309f1a7)), alongside [build-and-test](https://app.circleci.com/workflow/9fd56b39-9f8f-431e-bb11-177bcfe45f86/job/1c1c7628-3f69-4fa0-aac0-4e8eca38444b). The exact original artifacts are not independently read in this reconciliation, so `runtime_requested: true` and complete dbt/JUnit acceptance are **not yet proven**.

The separate `.circleci/reference.yml` is a manual Docker/browser lifecycle profile. CircleCI's additional `v1-reference-qualification` pipeline exercised the original broader `.github/workflows/quality.yml` workflow on the setup revision. Neither historic pipeline status nor a new default smoke run alone can replace the mainline database job and the separately tested restore/browser/provider gates.

1. Review or export the original CircleCI `postgres`, `container` and `reference-containers` artifacts (pytest JUnit, dbt, backup/restore, screenshots, lifecycle and `mdm check`), including exact `CIRCLE_SHA1`.
2. Run the appropriate full and, if needed, separate container qualifications on the final `main` ref. Record actual job results; avoid unnecessary duplicate expensive runs if a reviewed source correspondence meets the intended acceptance threshold.
3. Keep GitHub Actions runner-admission failures separate from successful CircleCI execution. GitHub Actions has no confirmed billing/quota/policy root cause.
4. Live Snowflake publication/dbt parity, provider-schema evidence, anonymous public readback, About metadata, licence and release/tag decisions remain separate. GitHub already reports the source repository as public; this is not a pending visibility switch.

This document is a status reconciliation, not a generated test artifact or a provider certification. No CircleCI billing, external infrastructure or repository visibility is changed.
