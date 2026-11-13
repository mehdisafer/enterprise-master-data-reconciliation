# ADR 002 — One bounded, durable Python orchestrator

Status: accepted for the reference implementation.

## Decision

Use the application's `mdm run` state machine, persisted in `runs` and
`run_sources`. Hold a session advisory lock for orchestration and a separate
transaction advisory lock for each identity graph mutation. Keep operator runs
explicit, keyed and bounded to three attempts.

## Why

The current workflow has three phases and three inputs. It needs durable replay
semantics and clear partial-source behavior more than another always-on service.
A missing source is represented as `null`, produces a degraded result, and never
deletes the last known source records. Available inputs still commit.

## Recovery contract

| Failure boundary | Durable state | Recovery |
| --- | --- | --- |
| Before source commit | No new assertion | Retry the same manifest and run key. |
| After ingestion, before checkpoint | Assertion committed | Replay content-idempotent ingestion and finish the checkpoint. |
| During a graph mutation | Transaction rolls back | Retry after checking the recorded run error and current versions. |
| After decision commit, before consumer publication | Outbox event exists | Resume the run or invoke the bounded consumer drain. |
| Concurrent orchestration | One session owns the lease | The second invocation receives a conflict; it must not launch another writer. |
| Three failed attempts | Failed run remains inspectable | Diagnose the cause; a new reviewed run key is required. |
| Missing ERP later returns | Earlier run remains degraded | Submit a new manifest and run key; do not rewrite the old input hash. |

## Consequences

The reference has one write lane. Additional API workers may serve independent
reads, but do not increase identity-write capacity. The candidate algorithm can
only be partitioned by a strategy that preserves all relevant block intersections
and global group compatibility. Multiwriter scaling has not been qualified by
choosing this design.

The CLI is not an unattended scheduler. Scheduling, automatic retries beyond the
bounded recovery contract, and external notifications need an explicit operating
policy. Docker's `on-failure:3` process restart limit is separate from application
run attempts.

Source: [PostgreSQL advisory lock behavior](https://www.postgresql.org/docs/17/explicit-locking.html#ADVISORY-LOCKS).
