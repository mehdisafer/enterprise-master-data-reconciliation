# Mainline CI qualification — 16 November 2026

This is an **evidence index and reproducible observation record**, not a substitute for the original CI logs or downloaded artifacts. The structured [manifest](manifest.json) was assembled from the GitHub Actions run/jobs/artifacts APIs, selected original stdout lines, and GitHub's reported CircleCI status contexts.

## Exact source under test

- Repository: `mehdisafer/enterprise-master-data-reconciliation`
- Application and CI source SHA: [`9b72725da693b4587c27a12b1d65e6f639d69a86`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/9b72725da693b4587c27a12b1d65e6f639d69a86)
- CircleCI source: the same SHA; both `build-and-test` and `postgres-integration` reported `success`.
- GitHub Actions: [Quality and PostgreSQL qualification, run #43920046617](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617) — **completed / success**. All four jobs ran on assigned runners and have zero failed steps.

| Executed control | Observed result | Original run |
| --- | --- | --- |
| Source scope and history-pattern secret scan | Job succeeded, source-linked scan artifact retained | [scope](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617/job/133484571624) |
| Locked packages, component/licence inventory, vulnerability audit | Job succeeded, dated audit artifact retained | [dependencies](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617/job/133484750058) |
| Real PostgreSQL, full pytest, dbt, backup/restore and synthetic load | **183 passed + 15 subtests**, 1 warning. dbt build **PASS=48**, restored dbt **PASS=43**, no errors or skips | [postgres](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617/job/133484749971) |
| Docker Compose, installed API, real browser and distinct human roles | **Job success**; browser JSON `passed=true`, `lifecycle_executed=true`, no JavaScript errors, 34 source identities preserved and consumer alignment checked after each decision | [container](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617/job/133485726286) |

The PostgreSQL job's original logs record `restore_verified: true` and its dedicated *reject second restore into populated target* step succeeded. The rendered browser exercised merge, unmerge, split, requester/approver/executor and source/consumer corrections from actual controls; the post-lifecycle `mdm check` command completed successfully.

CircleCI also reported success for the source-matched [matching and branch job](https://app.circleci.com/workflow/9fd56b39-9f8f-431e-bb11-177bcfe45f86/job/1c1c7628-3f69-4fa0-aac0-4e8eca38444b) and [PostgreSQL/dbt job](https://app.circleci.com/workflow/9fd56b39-9f8f-431e-bb11-177bcfe45f86/job/8098e38b-9f89-4910-9ab0-95cf0309f1a7). Their success contexts are independently observed in GitHub; **CircleCI raw JUnit, scope receipt and artifact bytes were not downloaded in this continuation**. The GitHub Actions job provides separate, independently read PostgreSQL/CI evidence on the same SHA.

## Artifact retention

Four original GitHub Actions artifact collections were uploaded: `secret-scan`, `dependencies`, `postgres-evidence` and `container-evidence`, all suffixed with the tested SHA. IDs, sizes and the API-reported expiry metadata appear in the [manifest](manifest.json). The workflow requests 14-day retention; these collections may expire and must not be presented later as permanently archived raw evidence. The manifest records their existence and links while available; it does not preserve the full archives.

## Acceptance boundary

This qualifies the **synthetic PostgreSQL/HTTP/dbt/container/browser reference** at the recorded SHA. It does **not** qualify a live Snowflake account, Snowflake load/readback/rollback or dbt parity, a real client dataset, scale beyond the declared synthetic test, or a production operating environment.

At the time of this capture, GitHub reported repository visibility **public**, with no selected repository licence, description/topics not yet applied and `main` unprotected. Public visibility does not confer a licence grant. Anonymous HTTP access was not independently established from the isolated runtime. These are [publication gates](../../../docs/publication.md) and are separate from CI success.

Later documentation-only commits can cite these source-specific results if all executable/configuration Git blobs remain identical; that identity must be rechecked. A green docs-only CI selection is not another runtime qualification.
