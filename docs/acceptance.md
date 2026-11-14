# Acceptance and remaining work

Acceptance is evidence-based. “Implemented” means the code exists; “executed” identifies an actual command; “qualified” applies only to the corresponding environment and passing invariants. A source hash or implementation-agent review is not independent certification.

## Scope and current decision

Inventory on 13 November 2026: private empty repository, no branches, issues, PRs, code or licence. Scope was published in issue #1 before implementation. Only this repository and the provided isolated workspace were used. No personal PC, client data or client system was accessed. All demonstration records are synthetic.

**The native PostgreSQL reference and HTTP boundary are now qualified for the recorded synthetic scenarios. Full project acceptance remains open.** Docker, rendered-browser behavior, Terraform provider-schema validation, live Snowflake behavior and repository publication have separate unmet gates.

The application, test and dbt inputs qualified on 14 November match [commit `205e7507`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/205e7507b9cd7dc1b34a858f2c524ce0c832642c), tree `2075183147d1ff50ddfee7e86e99ad7d7bdb367e`. Local and remote trees were compared before the branch advanced. Original file hashes establish correspondence with the tests, native flow and HTTP runs; see [source correspondence](../evidence/2026-11-14/source-correspondence.json). Later CI and Snowflake evidence-capture changes have separate, explicitly scoped checks below.

## What changed during qualification

The original 112 tests passed against real PostgreSQL 17.12. Further review found a publication-completion gap and a historical-compatibility gap. The historical case was reproduced before correction. The resulting implementation:

- Drains publication in at most 100 batches per attempt, completes only at `caught_up=True`, and retains failed/resumable state on budget exhaustion or no progress.
- Repairs an older incomplete terminal result using its original run identity and checkpoints, within the existing three-attempt limit.
- Uses the same historical slice interpretation for preview, request validation, execution and golden reconstruction. An incompatible pair retains a dated conflict without aborting unrelated matches.
- Recomputes candidate disposition when a third member changes, and displays the group conflict in the console's evidence.

Thirteen new PostgreSQL regressions cover those boundaries. The final suite passed **125 tests plus 15 subtests, with zero skipped cases**, including **53 real PostgreSQL integration cases**. A Starlette TestClient deprecation warning remains recorded.

The CI evidence review then found that documentation generation overwrote dbt build results and that the negative restore check accepted unrelated failures. The workflow now uses separate build/docs paths and verifies the exact populated-target error, preserving raw outputs and per-condition results. A [targeted native run](../evidence/2026-11-14/ci-evidence-hardening/qualification.json) executed those revised commands: five models and 41 tests passed, build artifact hashes remained unchanged after docs, the expected rejection passed, and missing-archive/missing-configuration failures were correctly rejected as evidence. All 17 operational tables in each of the two databases remained unchanged. The equivalent Snowflake output-path correction is implemented and syntax-checked, not live-qualified.

## Acceptance matrix

| Requirement | Implementation / original evidence | Current acceptance |
| --- | --- | --- |
| Strict versioned composite source keys | Domain, JSON contracts and tests | Unit-qualified on the recorded lock |
| Original / standard / candidate / decision / identity / crosswalk separation | Migration and real ledger tests | PostgreSQL-qualified |
| Three ERPs and difficult negatives | Versioned synthetic inputs and separate truth | Unit-qualified; small synthetic corpus only |
| Candidate recall and deterministic/fuzzy comparison | Matching evaluator and bounded controls | Measured; no industrial accuracy generalization |
| Whole-group and historical constraints; authority | Shared temporal preflight, execution checks and regressions | PostgreSQL-qualified, including unrelated-match isolation |
| Stable IDs, late changes and bitemporal provenance | Lifecycle tests, demo and overlap trigger | PostgreSQL-qualified |
| Requester/approver/executor, merge/split/unmerge | Real API/database tests and audit ledger | Server workflow qualified; rendered console still pending |
| Crash/replay/concurrent decisions | Outbox, optimistic versions and source checkpoints | PostgreSQL-qualified |
| Complete publication and recovery | Bounded drain, durable receipts and legacy-terminal repair | Eight new publication cases passed on PostgreSQL |
| Consumer correction and retained mappings | Demo and reporting state | 34 of 34 mappings aligned; no outstanding delivery |
| dbt execution and lineage | Five models, 41 tests, manifest and populated catalog | Live PostgreSQL build passed |
| Database profile | 300-source workload, real query plan and history growth | Measured locally; limited synthetic distribution |
| Backup and restore | Native 17.12 clients, 17 table fingerprints and invariants | Restored content equal; 41 restored dbt tests passed; populated target correctly rejected |
| Native HTTP operation | 24 requests and 127 assertions | Authentication, assets, metrics, trace correlation and graceful shutdown checked |
| Container reference and rendered console | Compose and Playwright smoke procedure | Not qualified: Docker unavailable; browser startup blocked |
| Durable business correlation | HTTP/CLI, run, decision, audit, outbox and receipt tests | PostgreSQL/HTTP qualified; live warehouse query links not qualified |
| Snowflake snapshot and dbt semantics | Publisher, unit boundaries, real PostgreSQL export | Live Snowflake load/readback and parity not executed |
| Terraform and actual provider schema | Pinned CLI/provider, generated lock | Earlier format/install observed; schema validation blocked; no plan/apply |
| Dependency/licence/secret controls | Frozen lock, dated audit/inventory and scoped scans | Original local reports retained; remote CI execution remains blocked |
| Licence, metadata, protections and release | Prepared metadata and release notes | Explicit licence choice pending; repository remains private; no published release |

## Environment and CI limits

The earlier inference that Unix socket denial prevented every local server was too broad. A fresh probe established that loopback TCP works. PostgreSQL 17.12 ran with `unix_socket_directories=''` and Uvicorn bound to `127.0.0.1`. The packages came from the signed official PGDG repository; signature, package checksums, binary versions and real readiness queries are retained. No system installation, permission change or external resource was needed.

Chromium's official Playwright download returned an unavailable-site HTML response. The installed system Chromium was also attempted and aborted when its process singleton required a denied Unix socket. These are explicit failed attempts, not a rendered-interface result. Terraform's previously observed provider startup has the same Unix-socket boundary. Docker is absent.

The [version-specific provider transport review](terraform-provider-transport.md) establishes from official source code that the pinned Linux Snowflake executable still selects a Unix listener in managed debug mode. `TF_REATTACH_PROVIDERS` and the plugin port variables do not give this executable a TCP listener. This narrows the environment diagnosis without qualifying the provider schema. Static validation needs a compatible runner, not Snowflake credentials; live warehouse qualification has separate prerequisites.

At the qualified source revision, [quality run 43593711716](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43593711716) and [Terraform run 43593711641](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43593711641) again failed before runner execution. The failed jobs have `runner_id: 0`, no steps and one check annotation each; artifact collections are empty. The connected endpoint exposes the annotation count but not its text. Billing, quota and policy causes remain unconfirmed. These GitHub runs do not invalidate or replace the separately recorded native runs.

## Remaining gates, in order

1. Read the exact GitHub admission annotation through an authorized signed-in interface and restore runner execution, or use another explicitly authorized isolated runner. Run the delivered code's Docker, rendered-browser and Terraform schema profiles. A docs-only synchronization selects no heavy runtime work; use a full qualification trigger or the source-code run when appropriate. Do not change billing, visibility or policy merely to obtain a green check.
2. Run the dedicated Snowflake qualification with an authorized account, key-pair role, database/warehouse scope and explicit spending limit. Retain publication/readback/rollback results, dbt parity, query IDs and accessible credit metrics. PostgreSQL export success is not a Snowflake result.
3. Obtain the maintainer's explicit repository licence choice before publication. Any public-visibility change is a separate authorization and must be followed by an anonymous-access check.
4. Apply the prepared repository description/topics through a settings-capable interface. Recheck protection availability if account capabilities or visibility change; no paid plan has been enabled.
5. Extend the small holdout with independently labeled, rights-cleared industrial fixtures before making accuracy or scale claims beyond the measured synthetic profiles.

Issue #1 stays open and PR #2 stays in draft until the full agreed acceptance is met. Implementation-agent reviews are disclosed self-review, not independent approval.
