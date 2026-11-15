# Enterprise Master Data Reconciliation

**Explain a match. Preserve its evidence. Correct it without losing identity.**

This synthetic industrial platform makes master-data decisions understandable and reversible across ERP systems. It consolidates organizations, establishments and products while keeping customer and supplier roles separate from legal identity. Each retained golden attribute has a source, a business-valid date and a survivorship rule.

The reference uses **Python, PostgreSQL, dbt and a FastAPI review console**. PostgreSQL is the transactional decision ledger. The separate Snowflake target publishes validated, versioned analytical snapshots; its constraint and concurrency semantics must be qualified on the actual provider.

## Delivery status — 15 November 2026

**The local reference is now qualified through its hosted database, container and actual browser paths.** The concurrent dependency/installed-wheel improvements were preserved through PR #10 and retested with the CircleCI changes. Full live Snowflake and production-target acceptance remain open.

| Gate | Latest observed result |
|---|---|
| Complete Python/PostgreSQL suite | 180 tests and 15 subtests; 195 JUnit case entries, zero errors/failures/skips |
| Distribution and dependencies | Locked Python 3.12.16 profile and installed-wheel qualification; lint, component and advisory controls executed |
| Database business workflow | Real PostgreSQL, source decisions, consumer correction, dbt build/docs/tests and restoration executed |
| Container and rendered lifecycle | Real image, PostgreSQL and API; browser merge/split/unmerge lifecycle executed with separate roles |
| Final browser/business checks | Browser passed; no recorded page/console errors; post-lifecycle business checks passed |
| Terraform provider schema | Static formatting, initialization without backend and provider-schema validation executed; no cloud apply |
| Live Snowflake | Not executed against an authorized account |
| Project licence and public visibility | Separate maintainer decisions; no licence selected by this work |

Qualified combined source: `b7485a20fa9a13aaa5a84179bf1a03f01bdbee7a`.

[Current acceptance](docs/acceptance.md) · [Database qualification](https://app.circleci.com/workflow/b514e6ba-1af2-4074-8a1c-b6751960d29c) · [Container/browser qualification](https://app.circleci.com/workflow/872b65af-ec73-4fd2-872c-9b3c38c31c40) · [Retained native evidence](evidence/2026-11-15/dependency-qualification/)

The original source integration (PR #2), dependency integration (PR #8) and additional native qualification (PR #9) remain preserved. CI success does not close the original live-provider acceptance issue or assert a stable production `v1.0.0` release.

## Start the synthetic local reference

Create external secret files using [operations](docs/operations.md#start-the-local-reference), then set `MDM_SECRET_DIR` to their directory.

```bash
docker compose build
docker compose up --detach --wait api
docker compose exec -T api mdm demo
docker compose exec -T api mdm check
```

Open `http://127.0.0.1:8000` with a configured operator token. Roles come from server configuration; requester, approver and executor are distinct identities. Tokens remain in browser memory.

The demo makes real transactions in the dedicated synthetic database: three-ERP ingestion, authoritative consolidation, a deliberately mistaken human merge, late correction, unmerge preserving later updates, and reporting-consumer reconciliation. It must not be run against a customer database. Repetition does not blindly replay decisions. For an unreviewed source dataset, use the manifest and `mdm run` in [the demo guide](docs/demo.md).

### Network boundary

PostgreSQL and migrations remain on the internal `data` network, without published database ports. Only the API also joins an ingress bridge. Its published host binding remains `127.0.0.1:8000`; it was not widened to all interfaces to obtain a pass.

**The API can initiate egress. This is not a whole-stack air-gap guarantee.** The additional bridge fixes the observed difference between configured and actually reachable Docker host ports.

## Data and decision contracts

Legal identity is not a business role: a company may be both customer and supplier, and a parent is not its subsidiary or establishment. Transitivity is not approval: every proposed group is checked for pairwise conflicts, including reconstructed business intervals. An incomplete record cannot bridge contradictory legal identities.

Attribute authority precedes recency. Source assertions and audit events are immutable; golden values preserve business-valid and knowledge intervals. Unmerge emits consumer corrections, but does not claim to reverse external invoices or orders.

The versioned corpus contains 34 identities across three ERPs: 18 development and 16 held-out records. Truth is separate from source contracts. Candidate generation unions explicit blocks and fails on oversized groups instead of silently truncating. Fuzzy names can add review suggestions, not automatic legal-identity merges. [Matching methods](docs/matching.md), [truth data](data/README.md) and [rules](contracts/rules.v1.json) define these boundaries.

## Develop and qualify

Use Python **3.12.16**, uv **0.13.6** and the reviewed lock:

```bash
uv sync --frozen --all-extras
uv run --no-sync pytest -q -m 'not integration'
uv run --no-sync ruff check src tests scripts .github/scripts
```

The complete suite requires a real disposable database ending in `_test`. Its fixture resets the schema and fails when the database is missing:

```bash
export MDM_TEST_DATABASE_URL=postgresql://mdm@127.0.0.1:5432/mdm_test
# Supply the password through PGPASSWORD or a protected PostgreSQL password file.
uv run --no-sync pytest -q
```

The full [quality workflow](.github/workflows/quality.yml) verifies the frozen lock and installed wheel, secret/history scan, dependencies, real PostgreSQL tests, demo, dbt, consistent backup/restoration, rejection of a second restore and bounded benchmarks. The [Terraform workflow](.github/workflows/terraform.yml) checks the schema without credentials or cloud apply.

The fast `.circleci/config.yml` remains a matching-unit Smarter Testing profile, not the complete database gate. `.circleci/reference.yml` is the manual native Linux VM deployment/browser qualification, with an isolated Compose project, actual three-role browser lifecycle, final business checks and scoped cleanup. No provider deployment is automatic.

```bash
uv run --no-sync dbt build --project-dir dbt --profiles-dir dbt --target postgres --target-path ../artifacts/dbt-build
uv run --no-sync dbt docs generate --project-dir dbt --profiles-dir dbt --target postgres --target-path ../artifacts/dbt-docs
uv run --no-sync mdm benchmark --size 300 --output artifacts/benchmark.json
```

The [verification guide](docs/verification.md) retains thresholds and commands. Measurements describe the tested fixture and hardware, not general scale or Snowflake cost.

## Repository map and remaining boundaries

`src/mdm/` contains contracts, matching, ledger, API, consumer and CLI; `src/mdm/sql/001.sql` is the checksummed migration. `contracts/` and `data/` hold versioned policy and synthetic truth. `dbt/` contains golden, lineage, quality and consumer views. `infra/snowflake/` is the separate provider path. Tests, operational scripts, documentation and evidence are kept distinct.

Graph mutations are serialized by one PostgreSQL advisory transaction lock. Parallel ingestion does not establish unlimited write throughput. Future-effective source assertions and source updates conflicting with accepted identity groups are rejected; a steward must explicitly resolve the latter first.

Snowflake qualification requires an authorized account/role, key-pair authentication, dedicated database/warehouse and approved budget. A warehouse resource monitor is not a cap on every account cost. See [provider semantics](docs/snowflake.md).

No repository licence has been selected. Third-party rights, including embedded dbt manifest macros, remain recorded in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). [Publication](docs/publication.md) separates licence, visibility, protections and runtime acceptance. Historical private-plan restrictions do not prove current protections. No paid plan or external resource was changed by this qualification.
