# ADR 001 — PostgreSQL control plane and Snowflake analytical target

Status: accepted for the reference implementation; live Snowflake qualification
has its own acceptance gate.

## Decision

Keep ingestion history, human decisions, group membership and outbox state in
PostgreSQL. Publish consistent snapshots into Snowflake and expose versioned
analytical views through dbt. Use one business contract and separate adapter SQL
where the engines have different JSON or timestamp syntax.

## Why

Identity decisions need enforced source uniqueness, foreign keys, version checks,
serialized graph edits and a transaction that covers both the decision and its
outbox event. PostgreSQL provides those mechanisms in the reference path.
Snowflake standard tables do not enforce the same unique/foreign-key semantics;
copying DDL would not establish equivalent protection. Snowflake publication uses
the loader and snapshot publication contract documented in [snowflake.md](../snowflake.md).

## Consequences

PostgreSQL remains the only operational decision writer. Snowflake is a real
integration target, not a local database renamed to look like a provider service.
Its dbt assertions verify business invariants over the published generation.
Snapshot publication must finish and its invariant checks must succeed before a
generation is accepted. Query durations, warehouse credits and privileges require
actual account execution.

The portable dbt contract can be exercised on both engines. PostgreSQL test
success does not establish Snowflake performance, authorization or billing. A
missing account is an explicit unfinished integration gate.

## Alternatives considered

A Snowflake-only operational ledger would need an explicit different concurrency
and constraint strategy. A second independent identity writer would introduce
reconciliation between competing golden records. Both are unnecessary for this
first reference deployment.

Sources: [Snowflake constraint behavior](https://docs.snowflake.com/en/sql-reference/constraints-overview),
[PostgreSQL concurrency](https://www.postgresql.org/docs/17/mvcc.html).
