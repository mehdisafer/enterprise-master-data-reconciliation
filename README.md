# Enterprise Master Data Reconciliation

**Explain a match. Preserve its evidence. Correct it without losing identity.**

I am building this platform to make master-data decisions understandable and reversible across industrial ERP systems. It consolidates organizations, establishments and products, while keeping customer and supplier roles separate from legal identity. Every retained golden attribute has a source, a business-valid date and a survivorship rule.

The reference implementation uses **Python, PostgreSQL, dbt and a FastAPI review console**. The Snowflake target publishes validated, versioned analytical snapshots; PostgreSQL remains the transactional decision ledger. This distinction is intentional: the two systems have different constraint and concurrency semantics.

## Delivery status

This is a **private release candidate**, developed under [issue #1](https://github.com/mehdisafer/enterprise-master-data-reconciliation/issues/1). Full project acceptance remains open until the authorized Snowflake qualification and release prerequisites are satisfied.

| Area | Implementation | Execution evidence |
| --- | --- | --- |
| Synthetic ERP contracts, blocking, matching and survivorship | Implemented | Local unit tests and measured synthetic control |
| Human review, merge, split, unmerge and temporal history | Implemented | Real PostgreSQL qualification is required in CI |
| Transactional outbox and reporting consumer | Implemented | Crash, replay and correction scenarios are exercised by integration tests |
| PostgreSQL dbt models and tests | Implemented | Parse executed; live build tracked in CI artifacts |
| Container deployment and restore drill | Implemented | Execution tracked in CI artifacts |
| Snowflake publication, dbt parity and Terraform | Implemented | **Not live-qualified: dedicated authorized account and budget required** |
| Repository licence and public visibility | Pending maintainer decision | No licence grant or visibility change made |

The [acceptance matrix](docs/acceptance.md) is the detailed status record. A passing local unit suite does not qualify a database, provider or deployment.

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
- **Transitivity is not approval.** Every member of a proposed group is checked against every other member. An incomplete B record cannot bridge conflicting A and C legal identifiers.
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

The [CI workflow](.github/workflows/quality.yml) installs the frozen lock, scans Git history for common secret patterns, audits dependencies, executes real PostgreSQL tests, runs the business demo and dbt, restores a consistent backup, measures a bounded database profile, and starts the containerized deployment. Runtime qualification is skipped for documentation-only changes; secret scanning still runs. The initial development sandbox forbids local sockets, so its database integration evidence must come from the isolated CI runner.

```bash
uv run --no-sync dbt build --project-dir dbt --profiles-dir dbt --target postgres
uv run --no-sync dbt docs generate --project-dir dbt --profiles-dir dbt --target postgres
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

No repository licence has been selected. Original code and synthetic data are not offered under an implied open-source grant; third-party dependencies retain their own licences. GitHub reported unavailable rulesets for the current private plan and denied the integration's branch-protection endpoint. These constraints are recorded, with no billing, visibility or external resource changes.
