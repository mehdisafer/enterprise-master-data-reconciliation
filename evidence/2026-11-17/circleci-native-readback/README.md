# Native CircleCI evidence readback — 17 November 2026

This capture replaces earlier **status-only** assumptions with **direct, unauthenticated read-only reads of CircleCI's own API and original artifact URLs**. It is a semantic receipt inventory, not a byte-for-byte archive of the provider artifacts.

## Exact source correspondence

- Last fully executed source: [`57c78b657027`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/57c78b657027377bf656ef516f4e08aba313fb2a); CircleCI workflow [`56565fa9-a13b-4ec1-8f6c-fcdc30666b05`](https://app.circleci.com/workflow/56565fa9-a13b-4ec1-8f6c-fcdc30666b05), `build-and-test` job #81 and `postgres-integration` job **#82**.
- Latest documentation-only main at observation: [`96868b0540a5`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/96868b0540a55ed561a49cd295cdf6a25d4b2235); workflow [`1c0e671f-1417-4a5b-9f3c-fb6e8f78813b`](https://app.circleci.com/workflow/1c0e671f-1417-4a5b-9f3c-fb6e8f78813b), `build-and-test` #85 and `postgres-integration` **#86**.
- Both native PostgreSQL jobs report `success` and return **164 original CircleCI artifact entries** each. The public provider's `scope.json` identifies the expected source SHA and explicitly records `selection=mandatory-mainline-qualification` and `runtime_requested=true` in **both** jobs; `environment.json` confirms Python 3.12.16, PostgreSQL 17.12 and `snowflake_live_executed=false`.

## Provider-native test and dbt receipts

- CircleCI's original [test-result API for job #82](https://circleci.com/api/v2/project/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/82/tests) and [job #86](https://circleci.com/api/v2/project/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/86/tests) each report **212 `success` tests** and no other outcome category. The original [JUnit file #82](https://output.circle-artifacts.com/output/job/9b3406eb-53de-4fe4-b5b0-59b8b350597f/artifacts/0/postgres-junit/postgres.xml) and [JUnit #86](https://output.circle-artifacts.com/output/job/859ca94a-dd84-4655-a777-e47374121b57/artifacts/0/postgres-junit/postgres.xml) expose **212 case elements** with zero failure/error/skipped elements in the extracted text. Text extraction did **not** preserve the original XML `testsuite` root attributes.
- Native dbt `dbt-build/run_results.json` on both sources has **48 results**: 41 `pass` tests and seven `success` steps. The original build manifests describe **5 models, 41 tests, 2 operations, 16 sources**. Native docs run-results report 48 `success`, and the docs manifests report the same 48 nodes; the catalog contains five models and 16 sources. These are **CircleCI original output paths**, not GitHub Actions files.
- The native `business-check.json` for #82 reports **nine checks passed with zero violations**. Its original demonstration JSON includes **six true business assertions**, 34 source crosswalks, 34 consumed crosswalks, complete consumer coverage and no remaining events.

## Actual pipeline trigger and config/checkout values

- CircleCI `GET /pipeline/{id}/values` reports `pipeline.trigger.type=github_app`, webhook push event, branch `main`, `pipeline.config.file_path=.circleci/config.yml`, `pipeline.config.sha` equal to the checkout/revision SHA, and source repository `mehdisafer/enterprise-master-data-reconciliation`. Direct `GET /pipeline/{id}/config` also returns the effective CircleCI source/compiled configuration.
- This proves the **observed execution source and trigger** for these two pipelines, not the saved trigger preset/config/checkout settings in the project's administration UI.
- Direct unauthenticated CircleCI Project Administration reads (pipeline-definitions and trigger configuration) returned a login-required error. **Project Settings criterion remains open** until authorized owner-side readback.

## Evidence boundary and follow-up

- Original job artifact indexes and stable original URLs are recorded in [manifest.json](manifest.json). We retrieved original content over public HTTP, then parsed the extracted JSON/XML text. **Raw original byte streams and independent SHA-256 values were not retained or verified**; temporary signed storage URLs are deliberately excluded.
- Provider data satisfies the formerly open **native artifact-content inspection** criterion in issue #16. It does not authorize changing the separate Project Settings criterion, falsely claiming a settings UI read, or closing live Snowflake or V1 acceptance.
- No personal computer, authenticated CircleCI session, customer resource, live Snowflake environment or paid operation was accessed.

**Issue #16 target after integration: 5/6.** Issue #1 remains **8/10**. `main` protection, About metadata and GitHub release/tag remain unchanged.
