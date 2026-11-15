# Dependency refresh — 15 November 2026

This change updates the packaging and Python runtime of my existing master-data reconciliation reference. It does not introduce a new reconciliation algorithm, alter business contracts or run a migration. The maintained Python range stays `>=3.12,<3.13`.

| Component | Prior pin | Selected pin | Source |
| --- | --- | --- | --- |
| Python Docker / CI | 3.12.14 | 3.12.16 | [Dependabot #7](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/7), [Python security release](https://www.python.org/downloads/release/python-31216/) |
| FastAPI | 0.141.1 | 0.162.4 | [Dependabot #4](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/4), [release notes](https://fastapi.tiangolo.com/release-notes/) |
| Pydantic | 2.13.4 | 2.14.3 | [Dependabot #5](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/5) |
| Pydantic Core | 2.46.4 | 2.50.4 | Transitive pin from #5 |
| Hatchling | 1.29.0 | 1.33.0 | [Dependabot #6](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/6), [changelog](https://hatch.pypa.io/dev/history/hatchling/) |

## Lockfile construction

The complete FastAPI package block comes from PR #4; the complete Pydantic and Pydantic Core blocks come from PR #5. Both direct dependency specifiers are updated in the locked root-project metadata. All other package blocks come unchanged from the qualified main lock. Hatchling remains a build-system requirement outside the application lock. No package checksums, URLs or compatibility claims were invented. The builder/runtime Docker tags, GitHub Actions Python selection and operating documentation now agree.

## Verification status

Previous committed original evidence is under [evidence](../evidence/README.md). The full 14 November Python/PostgreSQL, dbt, HTTP, restore and audit results apply to the **previous** executable source and dependency lock. A prior isolated continuation reported additional checks, but its unpublished original files are not present in this GitHub revision; these claims are not promoted to retained evidence for this change.

To qualify the new head:

1. Run `uv sync --locked --all-extras` with Python 3.12.16 and uv 0.13.6; build and test the sdist, wheel and editable install.
2. Run `uv run --no-sync pytest -q` against the dedicated real PostgreSQL test DB; execute the synthetic business demonstration, dbt build/catalog, HTTP checks, backup/restore and post-restore tests.
3. Execute the bounded load and retrieve the current dependency advisory, component and license inventory. Preserve raw output, inputs, source SHA, versions and any nonzero exit.
4. Run the container/rendered-browser and Terraform provider-schema profiles on an actually allocated runner. A successful Dependabot service job or empty Actions job does not pass them.
5. Qualify Snowflake publication, readback, rollback and dbt parity only with an explicitly authorized account/role/warehouse, cost cap and source-linked evidence.

No updated-runtime test is called successful merely from these edits. Full acceptance remains open in [issue #1](https://github.com/mehdisafer/enterprise-master-data-reconciliation/issues/1); the repository's public visibility and project licence are separate maintainer decisions.

## Rollback

Revert the dependency-refresh commit and deploy the previously qualified application build, subject to the usual source/schema/outbox compatibility checks. A dependency rollback does not reverse already-consumed business events; the existing correction and consumer-reconciliation processes remain authoritative.
