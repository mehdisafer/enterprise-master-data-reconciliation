# Apache-2.0 repository and installed-wheel evidence — 17 November 2026

The maintainer explicitly chose Apache License, Version 2.0 for the original source, tests, documentation and synthetic fixtures. [PR #25](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/25) merged the full root [LICENSE](../../../LICENSE), project [NOTICE](../../../NOTICE), third-party [notices](../../../THIRD_PARTY_NOTICES.md) and PEP 639 Python metadata into [`b36b260415d4`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/b36b260415d48a911916ab6b2ce24ca8900a6693). GitHub REST metadata subsequently detected SPDX `Apache-2.0`.

## Executed mainline CI

[GitHub Actions #44162018432](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/44162018432) completed **success**, and all four jobs `scope`, `dependencies`, `postgres` and `container` actually executed. Original PostgreSQL job logs confirm **199 pytest tests + 15 subtests** (one warning), dbt build **48/48**, restored-db dbt **43/43**, `restore_verified=true`, successful expected populated-target restore rejection, and successful installed-wheel verification. The latter reports `spdx_license_expression=true`, `license_files_declared=true`, `license_files_preserved=true`. The wheel was built from the sdist, installed non-editably, and all 18 source resources were preserved.

The original Docker/Playwright job reports `passed=true`, `actual_http_and_browser=true`, `lifecycle_executed=true`, `source_identities_preserved=34`, `javascript_errors=[]` and successful post-lifecycle checks.

CircleCI's default [build-and-test](https://app.circleci.com/workflow/fc4bdf21-d851-4090-a77f-5b4c223c58a2/job/249d5f2a-3f1b-4a65-9831-873f31617088) and `postgres-integration` both report **success** at the identical main source through GitHub commit-status readback. Their original `scope.json`, JUnit and dbt files and authenticated configuration/trigger/checkout settings were **not** independently downloaded or read; #16 remains **4/6**.

The [structured manifest](manifest.json) retains original job IDs, artifact IDs, expiration dates and source correspondence. It is a **derived evidence index**, not a copy of the original ZIP archives. The original GitHub Actions artifacts expire on 1 December 2026 UTC.

## Remaining boundaries

- GitHub public repository: **observed**, Apache-2.0: **detected**; About description/topics still null/empty, `main` unprotected, no release/tag published.
- PostgreSQL/dbt/container/browser synthetic reference: **executed successfully** at `b36b260`.
- Terraform provider: **static** historical fmt/init/validate/schema only, not plan/apply.
- Live Snowflake role/warehouse/dbt load/readback/rollback, credits/budget and actual production target: **not executed**.
- Full issue #1 remains **8/10** until live Snowflake and complete release/admin acceptance are demonstrated.

No personal workstation, client infrastructure or cloud target was accessed.
