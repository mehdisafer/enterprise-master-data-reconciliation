# ADR 002 — One bounded, durable Python orchestrator

Status: accepted for the reference implementation.

## Decision

Use the application's `mdm run` state machine, persisted in `runs` and
`run_sources`. Hold a session advisory lock for orchestration and a separate
transaction advisory lock for each identity graph mutation. Keep operator runs
explicit, keyed and bounded to **three attempts in total**: the initial attempt
and at most two resumptions. Publication drains at most **100 consumer batches
per attempt** and can complete the run only when the consumer reports
`caught_up=True`.

## Why

The current workflow has three phases and three inputs. It needs durable replay
semantics and clear partial-source behavior more than another always-on service.
A missing source is represented as `null`, produces a degraded result, and never
deletes the last known source records. Available inputs still commit. The result
becomes `degraded` only after reconciliation and publication complete; a failed
publication remains a failed run even when a source is also unavailable.

## State and publication contract

The input hash binds the declared source manifest and matching mode to the run
key. A changed input needs a new key. Each source commits independently and then
receives a `run_sources` checkpoint. A resumption reuses committed checkpoints,
reruns reconciliation against current state, and continues publication without
discarding previously committed consumer receipts.

Publication calls the transactional consumer repeatedly. An individual call
requests at most 10,000 events by default and may expand its selection to finish
a complete identity correction, whose operation contract allows at most twenty
affected groups. The 100-batch orchestration limit bounds the number of calls;
it is not a wall-clock latency guarantee or an exact ceiling of one million
events after correction expansion.

`caught_up` requires both an empty outstanding outbox for the consumer and valid
projection state: source ownership, crosswalks and active group versions must
agree with the reference. An empty batch alone is insufficient. The orchestrator
stops immediately with `publication_no_progress` when a call processes zero
events but still reports `caught_up=False`. It stops with
`publication_batch_limit` when the hundredth batch returns without catching up.
Both controlled failures persist `status='failed'`, retain phase `publication`,
and record the error code and last consumer state in `runs.result`. They do not
roll back earlier committed batches or reset the attempt budget.

A prior `succeeded` or `degraded` result is replayed unchanged only if its recorded
consumer state says `caught_up=True`. Older implementations could persist a
terminal result after one incomplete batch. Such a result now resumes with the
same `run_id`, input hash, source checkpoints and origin correlation, consuming
one ordinary retry attempt. A run that has already used all three attempts is not
silently reopened. A valid completed replay consumes no new attempt and describes
the earlier completion; it does not assert that no new events have appeared since.

## Recovery contract

| Failure boundary | Durable state | Recovery |
| --- | --- | --- |
| Before source commit | No new assertion | Retry the same manifest and run key. |
| After ingestion, before checkpoint | Assertion committed | Replay content-idempotent ingestion and finish the checkpoint. |
| During a graph mutation | Transaction rolls back | Retry after checking the recorded run error and current versions. |
| After decision commit, before consumer publication | Outbox event exists | Resume the run's bounded drain; an individual consumer invocation remains one bounded batch. |
| Between consumer batches | Earlier inbox receipts and projections committed | Resume the same run and consume the outstanding events. |
| Publication batch limit | Failed run, last consumer state and committed progress remain | Retry the same manifest and key while an attempt remains. |
| No publication progress | Failed run with `publication_no_progress`; consistency gaps remain inspectable | Diagnose and repair the reported projection or delivery problem before retrying. |
| Old terminal result with incomplete publication | Existing run identity and checkpoints remain | Resume under the same key and ordinary attempt budget, then replace the incomplete result on success. |
| Concurrent orchestration | One session owns the lease | The second invocation receives a conflict; it must not launch another writer. |
| Three attempts used without a valid completed result | Run and checkpoints remain inspectable | Diagnose the cause; a new reviewed run key is required. |
| Missing ERP later returns | Earlier run remains degraded | Submit a new manifest and run key; do not rewrite the old input hash. |

## Metric scope

Successful publication results and controlled publication failures report these
fields under `consumer`:

| Field | Scope |
| --- | --- |
| `processed` | Sum of events acknowledged by the batches in this publication attempt. |
| `expanded_for_atomic_corrections` | Sum of additional events selected to finish corrections during this attempt. |
| `publication_batches` | Number of consumer calls that returned during this attempt, including a final empty but consistent batch if needed. |
| `requested_limit` | Limit of the last individual consumer call, not a cumulative event budget. |
| `remaining`, `caught_up`, coverage and inconsistency fields | Consumer/reference state observed by the last completed batch. |

Counters do not accumulate over earlier failed attempts. A process interruption
can leave committed receipts without a saved aggregate counter in `runs.result`;
the durable inbox and outbox establish which events were handled. On retry,
previously acknowledged events are not counted again.

Source acceptance counts have a different scope. A resumed run reuses the
`accepted` value stored in each source checkpoint. If ingestion committed but the
checkpoint did not, content-idempotent replay can write a checkpoint with zero
newly accepted rows even though the earlier attempt committed assertions. Raw
records provide the durable assertion history; checkpoint counts are not a
replacement for that history.

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

The implementation is [pipeline.py](../../src/mdm/pipeline.py). Real PostgreSQL
[publication regressions](../../tests/test_pipeline_regressions.py) cover
single-event batches, partial-source completion, failure after a committed batch,
budget exhaustion, no-progress recovery, incomplete terminal-result repair and
the three-attempt limit. Execution reports establish which revision was tested;
this recovery design makes no claim about dbt or Snowflake qualification.

Source: [PostgreSQL advisory lock behavior](https://www.postgresql.org/docs/17/explicit-locking.html#ADVISORY-LOCKS).
