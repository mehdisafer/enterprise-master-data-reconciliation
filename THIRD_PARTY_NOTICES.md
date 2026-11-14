# Third-party components and generated evidence

The licence for the original repository code and synthetic fixtures is still awaiting an explicit maintainer decision. This file does not select it or apply a third-party licence to the project.

The original [dbt parse manifest](evidence/2026-11-13/dbt-parse-manifest.json) and the [executed PostgreSQL build](evidence/2026-11-14/native-flow/dbt/build/manifest.json) and [restored-database manifests](evidence/2026-11-14/native-flow/dbt/restored-test/manifest.json) include macro definitions from installed dbt packages as part of dbt's generated output. Those definitions retain their upstream rights and copyright notices. Copies of the actual installed licence files are preserved separately:

| Package | Installed version | Preserved licence |
| --- | --- | --- |
| dbt-core | 1.12.7 | [dbt-core-LICENSE.txt](evidence/third-party-licenses/dbt-core-LICENSE.txt) |
| dbt-postgres | 1.11.0 | [dbt-postgres-LICENSE.txt](evidence/third-party-licenses/dbt-postgres-LICENSE.txt) |
| dbt-adapters | 1.24.5 | [dbt-adapters-LICENSE.txt](evidence/third-party-licenses/dbt-adapters-LICENSE.txt) |

The [source inventory](evidence/third-party-licenses/sources.json) records package versions, installed source paths and file digests. These copies include the Apache License 2.0 text and dbt Labs copyright notice supplied by the packages. The 14 November qualification used the same locked package versions. Macro source and compiled output derived from those packages have not been relabelled as project-authored code. Generated dbt application HTML, PostgreSQL/browser binaries and the database backup archive are not vendored with the evidence.

The [installed component inventory](evidence/2026-11-13/components.json) records 119 Python dependencies, their publisher declarations and available licence files. It keeps distribution-obligation review items visible, including the PostgreSQL driver packages; a successful metadata check is not a licensing certification. The locked requirements do not change those components' licences.

Terraform CLI 1.17.2 is a qualification tool under its upstream BUSL-1.1 terms; the Snowflake provider 2.22.1 declares MIT and the pinned setup action declares MPL-2.0. Their binaries are not vendored in this repository. Container/OS layers and any later distribution of built images require their own reviewed inventory. Upstream references are recorded in the Terraform workflow and operating documentation.
