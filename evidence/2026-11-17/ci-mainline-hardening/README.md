# Mainline CI selector hardening and Terraform static qualification — 17 November 2026 (CET)

This directory documents **observed, source-specific results** rather than copying CI-generated archives into Git. The dated structured [manifest](manifest.json) contains the tested commit, original run/job/artifact identifiers, counts, scope limitations and source-correspondence hashes.

## Why mainline CI changed

[PR #22](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/22) removes a false-green condition. The former CircleCI PostgreSQL job compared only the final commit against its first parent: a single push with a runtime change followed by a docs-only commit could therefore skip integration tests while reporting success. An isolated three-commit Git history reproduced the failure. CircleCI GitHub App does not provide a dependable previous-push SHA through the assumed `pipeline.git.base_revision` field.

On `main`, the replacement helper `scripts/circleci_scope.py` now refuses a missing/mismatched source SHA, records `artifacts/scope.json` with `selection=mandatory-mainline-qualification` and `runtime_requested=true`, and **always requires** the real PostgreSQL/dbt job. All six former docs-only early returns were removed. This deliberately costs extra CircleCI minutes for every main push, even docs-only. The branch-only smoke job remains cheaper. Six isolated selector regressions passed using both `pytest` and `python -m pytest`. These local checks are independent of remote outcomes.

## Original 16 November UTC run — corrected mainline source

- Exact checked-out commit: [`af4ed2b776162f8dce497b20d4f4fad063adeeab`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/af4ed2b776162f8dce497b20d4f4fad063adeeab) (mainline merge of PR #22).
- [CircleCI `build-and-test`](https://app.circleci.com/workflow/6bf085dd-9633-4c01-8ad8-5062d54f2bfc/job/21c07969-24df-4dc4-8098-371c27364ac3): **success** by the GitHub commit-status API.
- [CircleCI `postgres-integration`](https://app.circleci.com/workflow/6bf085dd-9633-4c01-8ad8-5062d54f2bfc/job/ffbca4c9-ba92-47f9-83a7-b71249d757be): **success** by the same API. The raw CircleCI `scope.json` and JUnit/dbt archive bytes have **not** been downloaded independently. The source config contains no skipped-runtime branch and this job was actually scheduled on main; nevertheless, do not invent its artifact contents.
- [GitHub Actions Quality run #43978646310](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43978646310): **completed, success**. All four jobs `scope`, `dependencies`, `postgres`, `container` executed and succeeded on assigned runners. Original logs and step summaries were inspected.

| Source-bound control | Original observed result |
| --- | --- |
| Real Python and PostgreSQL suite | **189 passed**, plus **15 subtests**, one warning; no failed or skipped tests accepted |
| dbt build | 5 models, 41 data tests, 2 hooks: **PASS=48/48, ERROR=0, SKIP=0** |
| PostgreSQL backup/restore | `restore_verified=true`, expected populated-target negative-restore step succeeded |
| dbt restored | **PASS=43/43, ERROR=0, SKIP=0** |
| Real Docker/Playwright | `passed=true`, `actual_http_and_browser=true`, `lifecycle_executed=true`, 34 identities retained, zero JavaScript errors, post-lifecycle business check succeeded |
| Component audit and scoped secret scan | Both workflow jobs succeeded, with retained original artifacts |

Four original Actions artifact collections were created with the source SHA; names, GitHub artifact IDs, sizes and expiry **30 November 2026 UTC** are in the manifest. The archive contents have not been copied into Git or rehashed here, so the manifest is an *index to originals*, not independent reproduction of their raw bytes.

## Terraform static qualification — actual provider loaded, no cloud account

A separate historical [Terraform static workflow, attempt 2](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43593711641) was rerun **without changing any cloud resources**. Its recorded checkout SHA is `205e7507b9cd7dc1b34a858f2c524ce0c832642c`. The actual job loaded the provider and returned:

```json
{"fmt":"success","init":"success","validate":"success","schema":"success"}
```

The pinned Terraform workflow, provider HCL, variables and `.terraform.lock.hcl` Git blobs **match the current main source byte for byte**; their hashes are retained in the manifest. `infra/snowflake/qualify.sh` differs between the two commits but **was not executed by this static workflow**. The original Terraform job's logs and artifact metadata were inspected; this is a provider-schema/static-configuration success, **not** a Terraform `plan`, `apply`, key-pair login, Snowflake publication or billing result.

## Unqualified boundaries

This is a **synthetic reference qualification**. No live Snowflake publisher/dbt execution, target role/grants or warehouse-cost evidence exists. No real client or production target has been tested or modified.

The repository is public and previously had an anonymous read-only browser check, but original project code is still without a selected licence; GitHub About description/topics are not applied and `main` is not protected. No release tag was selected. These are independent maintainer release decisions, tracked in [acceptance](../../../docs/acceptance.md), [publication](../../../docs/publication.md) and [issue #1](https://github.com/mehdisafer/enterprise-master-data-reconciliation/issues/1).

For historical results of 13–16 November, see the [evidence index](../../README.md). Do not overwrite those records or retroactively convert their earlier local failures into successful runs.
