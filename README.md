# Enterprise Master Data Reconciliation

**Explain a match. Preserve its evidence. Correct it without losing identity.**

I am building this platform to make master-data decisions understandable and reversible across industrial ERP systems. It consolidates organizations, establishments and products, while keeping customer and supplier roles separate from legal identity. Every retained golden attribute has a source, a business-valid date and a survivorship rule.

The reference implementation uses **Python, PostgreSQL, dbt and a FastAPI review console**. The Snowflake target publishes validated, versioned analytical snapshots; PostgreSQL remains the transactional decision ledger. This distinction is intentional: the two systems have different constraint and concurrency semantics.

## Delivery status

This is a **reference release candidate with a verified native PostgreSQL implementation**, developed in [PR #2](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/2) under [issue #1](https://github.com/mehdisafer/enterprise-master-data-reconciliation/issues/1). On 14 November 2026, the real database suite, business demonstration, dbt build, restore drill and live HTTP checks succeeded in the isolated workspace. Container deployment, rendered-browser checks, Terraform schema validation and live Snowflake qualification remain open. The full release is not accepted.

The maintainer has requested public source publication. PR #2 has integrated the complete reference into `main`; its [merge and full-tree readback](evidence/2026-11-14/publication-preflight/integration-verification.json) are recorded. Source delivery leaves issue #1 and the remaining qualification work open. Repository visibility, About metadata and anonymous-access checks are tracked separately in the [publication record](docs/publication.md).

| Area | Implementation | Execution evidence |
| --- | --- | --- |
| Synthetic ERP contracts, blocking, matching and survivorship | Implemented | Local unit tests and measured synthetic control |
| Human review, merge, split, unmerge and temporal history | Implemented | Real PostgreSQL lifecycle, concurrency and failure tests passed |
| Transactional outbox and reporting consumer | Implemented | Crash/replay, bounded publication and complete correction tests passed |
| PostgreSQL dbt models and tests | Implemented | Five models and 41 data tests passed; populated catalog generated |
| Backup and restoration | Implemented | Exact comparison of 17 tables; invariants and 41 dbt tests passed after restore; populated target correctly rejected |
| Native HTTP server and assets | Implemented | 24 real requests, 127 assertions; authentication, provenance, metrics, correlation and graceful shutdown checked |
| Container deployment and rendered console | Implemented | **Not qualified**: Docker unavailable; Chromium startup blocked by Unix socket denial |
| Terraform configuration | Implemented; provider lock generated | Formatting passed; provider schema validation still blocked by Unix socket denial |
| Snowflake publication and dbt parity | Implemented | **Not live-qualified: dedicated authorized account and budget required** |
| Source integration | Complete reference merged into `main` through PR #2 | Merge/tree/README verified; visibility and anonymous-access status tracked separately |
| Repository licence | No licence selected | No open-source licence grant or release tag |

The [acceptance matrix](docs/acceptance.md), [evidence index](evidence/README.md) and [release notes](docs/releases/0.1.0rc1.md) distinguish observed results from implementation. A passing local unit suite does not qualify a database, provider or deployment.

The qualified application, test and dbt inputs match [commit `205e7507`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/205e7507b9cd7dc1b34a858f2c524ce0c832642c): **125 tests and 15 subtests passed, with no skipped cases**, including 53 real PostgreSQL integration cases. Thirteen regressions cover incomplete publication, historical incompatibility and stale candidate status. The 13 November locked audit reported zero known vulnerabilities across 119 dependencies at that capture time; it is not a continuous security guarantee.

A subsequent [targeted native check](evidence/2026-11-14/ci-evidence-hardening/qualification.json) qualifies the revised CI evidence controls: dbt build results survive documentation generation, and the populated-target restore control rejects unrelated failures. Its 41 dbt tests passed again; both databases' 17 operational table fingerprints remained unchanged. These are local results from selected workflow commands, not an executed GitHub job. The Snowflake helper now separates the same output paths, with live execution still pending.

The merged reference's [quality workflow](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43603763090) and [Terraform workflow](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43603763082) again stopped before runner execution. The [post-merge inventory](evidence/2026-11-14/publication-preflight/post-merge-actions.json) separately records successful Dependabot service steps; these do not qualify the application or its proposed dependency updates. The native results remain separate original evidence. The precise qualification-job admission annotation remains inaccessible through the connected interface.

**Dependency refresh (15 November 2026):** Python 3.12.16, FastAPI 0.162.4, Pydantic 2.14.3 and Hatchling 1.33.0 are consolidated in [a separate change record](docs/dependency-refresh-2026-11-15.md). The 14 November full-suite and audit reports concern the earlier source and lock; they do not automatically qualify this refresh. Runtime and CI evidence for the updated commit must be captured separately.

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

Python 3.12 and the complete dependency lock are required:

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

The [CI workflow](.github/workflows/quality.yml) is configured to install the frozen lock, scan Git history for common secret patterns, audit dependencies, execute real PostgreSQL tests, run the business demo and dbt, restore a consistent backup, measure a bounded database profile, and start the containerized deployment. Runtime qualification is skipped for documentation-only changes; secret scanning still runs. A [separate Terraform workflow](.github/workflows/terraform.yml) validates configuration against the installed provider without cloud credentials or apply.

The isolated workspace allows loopback TCP but denies Unix sockets. PostgreSQL 17.12 therefore ran with `unix_socket_directories=''`, and Uvicorn used loopback TCP. No permission was relaxed. Those native results establish the database/HTTP path; a capable runner is still required for the container, rendered-browser and provider-schema gates.

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
