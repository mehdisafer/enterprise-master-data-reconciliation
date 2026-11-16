# Enterprise Master Data Reconciliation

**Explain a match. Preserve its evidence. Correct it without losing identity.**

I am building this platform to make master-data decisions understandable and reversible across industrial ERP systems. It consolidates organizations, establishments and products, while keeping customer and supplier roles separate from legal identity. Every retained golden attribute has a source, a business-valid date and a survivorship rule.

The reference implementation uses **Python, PostgreSQL, dbt and a FastAPI review console**. The Snowflake target publishes validated, versioned analytical snapshots; PostgreSQL remains the transactional decision ledger. This distinction is intentional: the two systems have different constraint and concurrency semantics.

## Delivery status

This is a **qualified synthetic PostgreSQL/HTTP/dbt/container reference release candidate**, not a production-ready data platform. On 16 November 2026, [GitHub Actions full qualification](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617) passed all four jobs at commit [`9b72725da693`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/9b72725da693b4587c27a12b1d65e6f639d69a86). Its real PostgreSQL suite passed **183 tests and 15 subtests** (one warning), dbt built **48/48** tasks, restored dbt passed **43/43**, the backup was verified, and Docker/Playwright exercised the actual three-role merge/unmerge/split lifecycle with 34 source identities and no recorded JavaScript errors. Both default CircleCI jobs, `build-and-test` and `postgres-integration`, independently report success on the same SHA. [Source-linked evidence](evidence/2026-11-16/ci-main-qualification/) distinguishes original job logs/artifacts from the retained API summary. The repository is **public but currently unlicensed**; description/topics and branch protection remain pending. **Live Snowflake and production-target acceptance are not established, and the full release is not yet accepted.**

The original reference was integrated through [PR #2](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/2); [PR #8](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/8) integrated the dependency versions into `main`. [PR #9](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/9) carries the additional qualification, controls and [retained evidence](evidence/2026-11-15/dependency-qualification/). Its conversation is the source-delivery record for the reviewed head, final `main`/tree readback and workflow observations. The [publication record](docs/publication.md) separates source integration, public visibility and runtime acceptance; [issue #1](https://github.com/mehdisafer/enterprise-master-data-reconciliation/issues/1) remains open for full acceptance.

| Area | Implementation | Latest execution evidence |
| --- | --- | --- |
| Synthetic ERP contracts, blocking, matching and survivorship | Implemented | Recorded synthetic controls passed; input serializations, ingestion hashes, five schemas and OpenAPI match the previous dependency baseline |
| Human review, merge, split, unmerge and temporal history | Implemented | Hosted CI: 183 tests + 15 subtests passed; actual three-role browser lifecycle and post-lifecycle business check passed |
| Transactional outbox and reporting consumer | Implemented | Lifecycle, crash/replay and correction tests passed; all 34 demo source mappings aligned |
| PostgreSQL dbt models and tests | Implemented | Five models, 41 data tests and two hooks: hosted build PASS=48/48, zero errors/skips |
| Backup and restoration | Implemented | 16 November hosted restore verified; second restore into a populated database correctly rejected; restored dbt PASS=43/43 including two hooks |
| Native HTTP server and assets | Implemented | 34 real requests and 341 checks passed; all 17 operational fingerprints unchanged |
| Build and installed distribution | Implemented | Wheel built through the source distribution, all 18 application resources preserved, CLI and non-editable installation exercised |
| Container deployment and rendered console | Implemented | 16 November GitHub Actions container job and real rendered lifecycle passed on the current tested application SHA, with retained artifacts |
| Terraform configuration | Implemented; provider lock retained | Local format/init passed, local provider startup blocked; an earlier CircleCI static job succeeded on setup, but its schema evidence was not independently read |
| Snowflake publication and dbt parity | Implemented | **Not live-qualified: dedicated authorized account, role, scope and budget required** |
| Public source and repository licence | Source public; project licence not chosen | No open-source licence grant, About metadata or release tag; `main` currently unprotected |

The qualified versions are FastAPI **0.162.4**, Pydantic **2.14.3**, Hatchling **1.33.0** and Python **3.12.16**. Forty-four HTTP regression cases cover validation, authorization, serialization and real decision lifecycles, alongside the eleven compatibility tests from PR #8. Seven build dependencies have explicit version and artifact-hash constraints alongside the application and development lock. The dated audits report zero known vulnerabilities across **119 installed application, development and qualification packages** and, separately, **seven explicitly constrained build dependencies**. The inventories overlap and are not a total of 126 unique packages or a continuous security guarantee.

The initial [26-command native capture](evidence/2026-11-15/dependency-qualification/native-flow/qualification.json) passed 169 tests and 15 subtests at [commit `88c932de`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/88c932de80dd1d20f49b93798153f2986f3c5029). After preserving PR #8, the [supplementary full suite](evidence/2026-11-15/dependency-qualification/main-reconciliation/qualification.json) passed 180 tests and 15 subtests at [commit `bb369db1`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/bb369db1360ef17c5328dc6a68392355728e9920), using the same installed wheel. The dbt, business demonstration, restore and live HTTP results belong to the initial capture; their executable inputs were unchanged, and those profiles were not repeated in the supplementary run.

The [acceptance matrix](docs/acceptance.md), [evidence index](evidence/README.md) and [release notes](docs/releases/0.1.0rc1.md) identify the environment and source inputs behind these results. Earlier 13–14 November captures remain historical records. The previous continuation's unpublished 166-test account could not be recovered as a committed candidate; it is not counted as evidence for this delivery.

The previously blocked [GitHub Actions runner](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43770574648) is historical evidence, not a current release blocker for the synthetic reference: the [16 November complete application run](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617) executed `scope`, `dependencies`, `postgres` and `container` successfully. Its JUnit/dbt/restore/browser artifacts are attached to the source SHA. This success does not imply that GitHub Actions admission will never fail in the future, or that live Snowflake has been exercised.

## Run the complete reference

Requirements: Docker Engine with Compose v2, approximately 2 CPU cores and 2–3 GB available RAM. The API binds only to `127.0.0.1:8000`; the database has no host port.

1. Create external secret files using the exact steps in [operations](docs/operations.md#start-the-local-reference).
2. Set `MDM_SECRET_DIR` to that directory.
3. Build, migrate and start:

```bash
docker compose build
docker compose up --detach --wait api
docker compose exec -T api mdm demo
docker compose exec -T api mdm check
```

Open [the local review console](http://127.0.0.1:8000). Use a configured operator token; its role comes from server configuration. Tokens stay in browser memory. Requester, approver and executor are distinct identities for human decisions.

The demonstration executes real transactions against the configured database. It ingests all three ERPs, automatically consolidates authoritative identities, records a deliberately mistaken human merge, ingests late corrections, unmerges while retaining later source updates, and reconciles the reporting consumer. Repeating the demo does not blindly replay those decisions. It should be used only in the dedicated synthetic reference database.

For an interactive review from an unreviewed dataset, use the source manifest and `mdm run` described in [the demo guide](docs/demo.md). The console provides source comparisons, score contributions, conflicts, golden lineage, temporal history and versioned approval actions.

## What the model protects

- **Legal identity is not a business role.** Parent, subsidiary and establishment cannot become one entity just because they share names or addresses. A company can be both customer and supplier.
- **Transitivity is not approval.** Every member of a proposed group is checked against every other member, both now and over reconstructed business intervals. An incomplete B record cannot bridge conflicting A and C legal identifiers. A historical conflict remains inspectable without aborting unrelated matches.
- **Authority comes before recency.** Each attribute uses its own source ranking. A recent lower-authority name cannot overwrite an authoritative legal name.
- **History is append-and-correct.** Source assertions and decision audit events are immutable. Golden values have separate business-valid and knowledge intervals.
- **Corrections propagate.** A committed unmerge emits new events. It does not claim to reverse invoices, orders or other decisions made by external consumers.

## Matching that can be inspected

The versioned corpus contains 34 source identities across three ERP systems: 18 development records and 16 held-out records. Truth labels are separate from source contracts. Candidate generation unions identifier, name, contact and location blocks; oversized blocks fail explicitly instead of truncating comparisons.

Deterministic evidence is the baseline. Conservative fuzzy name evidence can add **review suggestions**; it cannot automatically merge a legal identity. Metrics report candidate recall, automatic precision/recall, review burden and group impurity separately. See [matching methods and limitations](docs/matching.md), [truth data](data/README.md) and [rules](contracts/rules.v1.json).

## Develop and qualify

The default [CircleCI pipeline](.circleci/config.yml) now defines two levels of automated checking: `build-and-test` runs Ruff, the matching suite, all non-database tests and a scoped repository-history secret scan on branches; `postgres-integration` runs the complete PostgreSQL pytest suite, the three-ERP demo, business invariants, dbt build/catalog and a 300-source benchmark on **`main` only**. Both use Python 3.12.16 and the frozen uv dependency lock. JUnit, source/CI environment and selected dbt outputs are retained. Both default CircleCI jobs have **reported success on the 16 November application commit**; it does not replace the separate backup/restore, Docker/browser, Terraform or live Snowflake qualifications. Documentation/evidence-only commits on `main` write a scope receipt and bypass the expensive PostgreSQL/dbt steps; this is never counted as a passing integration test. An unknown change scope triggers the full suite. See [CI provenance and execution boundaries](docs/circleci.md).


Python **3.12.16**, uv **0.13.6** and the complete dependency/build constraints are the qualified development profile:

```bash
uv sync --frozen --all-extras
uv run --no-sync pytest -q -m 'not integration'
uv run --no-sync ruff check src tests scripts .github/scripts
```

For the full suite, provide a real disposable database whose name ends with `_test`. The fixture resets that schema and fails if the test database is missing:

```bash
export MDM_TEST_DATABASE_URL=postgresql://mdm@127.0.0.1:5432/mdm_test
# Supply its password through PGPASSWORD or a protected PostgreSQL password file.
uv run --no-sync pytest -q
```

The [CI workflow](.github/workflows/quality.yml) is configured to install the frozen lock, verify the installed wheel, scan Git history for common secret patterns, audit the installed application/development packages, execute real PostgreSQL tests, run the business demo and dbt, restore a consistent backup, measure a bounded database profile, and exercise the containerized deployment and three-role browser lifecycle. The browser profile finishes with a real business-invariant check; it completed successfully on a hosted GitHub Actions runner on 16 November (the isolated native workspace still cannot run Docker or Chromium). Runtime qualification is skipped for documentation-only changes; secret scanning still runs. A [separate Terraform workflow](.github/workflows/terraform.yml) validates configuration against the installed provider without cloud credentials or apply.

The isolated workspace allows loopback TCP but denies Unix sockets. PostgreSQL 17.12 therefore ran with `unix_socket_directories=''`, and Uvicorn used loopback TCP. No permission was relaxed. Those earlier native results established the database/HTTP path; the 16 November hosted GitHub Actions run additionally qualified Docker, the API and rendered browser at the current tested commit. Provider-schema and live Snowflake evidence remain separate gates.

```bash
uv run --no-sync dbt build --project-dir dbt --profiles-dir dbt --target postgres --target-path ../artifacts/dbt-build
uv run --no-sync dbt docs generate --project-dir dbt --profiles-dir dbt --target postgres --target-path ../artifacts/dbt-docs
uv run --no-sync mdm benchmark --size 300 --output artifacts/benchmark.json
```

Full profile commands, predeclared thresholds and evidence locations are in [verification](docs/verification.md). Load measurements describe the measured fixture and hardware, not general scale or Snowflake cost.

## Repository map

| Path | Purpose |
| --- | --- |
| `src/mdm/` | Strict contracts, matching, ledger, orchestrator, API, consumer and CLI |
| `src/mdm/sql/001.sql` | Checksummed PostgreSQL migration |
| `contracts/`, `data/` | Versioned policy, schemas, synthetic ERP inputs and truth |
| `dbt/` | Cross-platform golden, crosswalk, lineage, quality and consumer views |
| `infra/snowflake/` | Dedicated bounded warehouse/database configuration and live qualification |
| `tests/` | Domain, API, transactional, concurrency and failure scenarios |
| `scripts/`, `observability/` | Secret/dependency controls, backup/restore and operational queries |
| `docs/`, `evidence/` | Architecture, decisions, acceptance, runbooks and observed results |

## Boundaries and release prerequisites

The reference serializes graph mutations under one PostgreSQL advisory transaction lock. Parallel source ingestion preserves identity invariants but does not increase write throughput past that boundary. Matching runs are bounded; no horizontal-write scalability claim is made. Source assertions effective in the future are rejected until a scheduled activation policy is designed. Source updates that would introduce incompatible identities into an accepted group are rejected atomically; the steward must split the group first.

The Snowflake profile requires a dedicated account/role, key-pair authentication, database/warehouse scope and approved spending limit. Its resource monitor constrains warehouse credits, not every possible account cost. See [provider semantics and qualification](docs/snowflake.md).

No repository licence has been selected. Original code and synthetic data are not offered under an implied open-source grant; third-party dependencies retain their own licences. GitHub's [licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) does not require a licence choice to make a repository public. The [publication procedure](docs/publication.md) records the separate rights and visibility status.

During setup on 13 November 2026, GitHub reported a private-plan restriction for rulesets and denied the integration's branch-protection endpoint. These are historical observations, not proof of enforced protections or of their availability after publication. No paid plan or external resource change is part of source publication.

The [third-party notices](THIRD_PARTY_NOTICES.md) preserve the upstream rights of embedded dbt manifest macros. Repository description/topics are [prepared](docs/repository-metadata.json) for the maintainer to apply in GitHub's interface, followed by readback verification.
