# Dependency refresh — 15 November 2026

This change updates the packaging and Python runtime of my existing master-data reconciliation reference. It does not introduce a new reconciliation algorithm, alter business contracts or run a migration. The maintained Python range stays `>=3.12,<3.13`. [PR #8](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/8) integrated this dependency rollup at [commit `03c927b3`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/03c927b3f19e387df770130d59d9c09bea3800d1). [PR #9](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/9) preserves it and its eleven compatibility tests while adding qualification, controls and retained evidence. The PR #9 conversation records review, the delivered head, final `main`/tree readback and workflow observations.

| Component | Prior pin | Selected pin | Source |
| --- | --- | --- | --- |
| Python Docker / CI | 3.12.14 | 3.12.16 | [Dependabot #7](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/7), [Python security release](https://www.python.org/downloads/release/python-31216/) |
| FastAPI | 0.141.1 | 0.162.4 | [Dependabot #4](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/4), [release notes](https://fastapi.tiangolo.com/release-notes/) |
| Pydantic | 2.13.4 | 2.14.3 | [Dependabot #5](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/5) |
| Pydantic Core | 2.46.4 | 2.50.4 | Transitive pin from #5 |
| Hatchling | 1.29.0 | 1.33.0 | [Dependabot #6](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/6), [changelog](https://hatch.pypa.io/dev/history/hatchling/) |

## Lockfile construction

The complete FastAPI package block comes from PR #4; the complete Pydantic and Pydantic Core blocks come from PR #5. Both direct dependency specifiers are updated in the locked root-project metadata. All other application package blocks come unchanged from the preceding main lock. PR #9 preserves all 122 package entries from the rollup and adds seven explicit build constraints with distribution hashes under `[tool.uv]`: `editables==0.6`, `hatchling==1.33.0`, `packaging==26.3`, `pathspec==1.0.4`, `pluggy==1.7.0`, `tomlkit==0.15.2` and `trove-classifiers==2026.9.21.13`. These constrain isolated backend resolution, which the application package entries alone do not cover.

Hatchling remains the selected build-system backend. uv 0.13.6 successfully exercised the experimental `require-build-hashes` control for the editable install, source distribution and wheel. The builder/runtime Docker tags, GitHub Actions Python selection and operating documentation agree. Actual container execution remains a separate qualification gate.

## Verification status

The original 13–14 November results remain dated under [evidence](../evidence/README.md). They describe the previous executable inputs and dependency versions. The unpublished continuation's 166-test narrative was not recovered as original evidence and is not counted here. The new results come from fresh isolated execution with Python 3.12.16 and PostgreSQL 17.12, using Debian Security trixie packages `17.12-0+deb13u1` for this capture; the 14 November capture used PGDG packages.

| Capture | Observed result | Source and evidence |
| --- | --- | --- |
| Initial complete native qualification | 169 tests and 15 subtests, including 55 real PostgreSQL cases; zero failures/errors/skips; non-editable installed wheel | [Commit `88c932de`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/88c932de80dd1d20f49b93798153f2986f3c5029), [26-command record](../evidence/2026-11-15/dependency-qualification/native-flow/qualification.json) |
| Supplementary suite after preserving PR #8 | Ruff passed; **180 tests and 15 subtests**, including the same 55 real PostgreSQL cases; zero failures/errors/skips; existing installed wheel | [Commit `bb369db1`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/bb369db1360ef17c5328dc6a68392355728e9920), [qualification](../evidence/2026-11-15/dependency-qualification/main-reconciliation/qualification.json), [83-input source correspondence](../evidence/2026-11-15/dependency-qualification/main-reconciliation/source-correspondence.json) |
| Package and contracts | All 18 application resources and the CLI preserved; 35 input serializations and ingestion hashes, five schemas and OpenAPI unchanged | [Distribution](../evidence/2026-11-15/dependency-qualification/native-flow/distribution.json), [comparison](../evidence/2026-11-15/dependency-qualification/contract-comparison.json) |
| PostgreSQL, dbt and recovery | Five models and 41 tests passed; 17 restored table fingerprints matched; 41 restored tests passed | [Native evidence guide](../evidence/2026-11-15/dependency-qualification/README.md) |
| Live native HTTP | 34 requests and 341 checks passed; all 17 operational table fingerprints unchanged | [HTTP qualification](../evidence/2026-11-15/dependency-qualification/native-flow/http/qualification.json) |
| Dated dependency advisories | Zero known vulnerabilities in 119 installed application, development and qualification packages; separately, seven explicitly constrained build dependencies | [Installed-package audit](../evidence/2026-11-15/dependency-qualification/native-flow/dependency-audit.json), [build audit](../evidence/2026-11-15/dependency-qualification/native-flow/build-dependency-audit.json) |

The supplementary capture reran Ruff and the full pytest suite only. The build, editable smoke, business demonstration, dbt, restore, live HTTP, audits and bounded workload remain attributed to the initial capture; their executable inputs are unchanged. The two audit inventories overlap and are not a total of 126 unique packages. Their results describe the dated advisory lookup, not continuous security assurance.

The 44 additional HTTP regressions include 42 transport/contract checks and two lifecycle cases using ASGI TestClient with real PostgreSQL. The separate Uvicorn exercise uses actual TCP HTTP. Neither establishes rendered-browser behavior. The optional browser lifecycle and post-browser invariant check are implemented but not successfully executed in this environment.

Remaining qualification is explicit:

1. Run the container/rendered-browser and Terraform provider-schema profiles on an actually allocated runner. Docker is absent here; Chromium and the Terraform provider fail at denied Unix socket creation. Terraform formatting and initialization passed. The [recorded Actions run at `bb369db1`](../evidence/2026-11-15/dependency-qualification/main-reconciliation/github-actions.json) failed in scope before runner assignment, with zero executed steps and artifacts; its dependent jobs were skipped. A service job or empty Actions job does not qualify the application.
2. Qualify Snowflake publication, readback, rollback and dbt parity only with an explicitly authorized account/role/warehouse, cost cap and source-linked evidence.
3. Record source-delivery checks and final workflow observations in PR #9; verify public visibility and About metadata separately through the [publication procedure](publication.md).

Full acceptance remains open in [issue #1](https://github.com/mehdisafer/enterprise-master-data-reconciliation/issues/1); repository visibility and the project licence remain separate maintainer decisions. No release tag or live warehouse acceptance follows from these native results.

## Rollback

Prepare a reviewed rollback that keeps `pyproject.toml`, `uv.lock`, the seven build constraints and their hashes, and the Docker/CI Python selections consistent with the intended previous versions. Reverting PR #8 alone would leave the later Hatchling 1.33.0 build constraint paired with the older 1.29.0 backend requirement. Requalify the coherent rollback, including the installed distribution and real PostgreSQL suite, before deployment; check source/schema/outbox compatibility against the target environment. A dependency rollback does not reverse already-consumed business events; the existing correction and consumer-reconciliation processes remain authoritative.
