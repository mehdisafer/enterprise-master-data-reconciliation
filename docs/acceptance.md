# Acceptance and remaining work

Acceptance is evidence-based. “Implemented” means the code exists; “executed” identifies an actual command; “qualified” requires the corresponding environment and passing invariants. No component hash or automated self-review is an independent certification.

## Scope baseline

Inventory on 2026-11-13: private empty repository, no branches, issues, PRs, code or licence. Scope was published in issue #1 before implementation. No other user repository was modified, and no personal/client system was accessed. Public upstream documentation and release sources were used to check dependencies. All demo records were authored for this repository.

## Execution blockers

The [first CI run](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43524025662) at `d60f423fab56add510ba16933f20497baccd3383` failed before execution: the scope job has no steps and `runner_id: 0`; the database, dependency and container jobs were skipped. There are no artifacts. The connector does not expose its failure annotation, and the isolated browser has no authenticated GitHub session. Billing, quota and policy explanations are unconfirmed hypotheses.

The local environment independently denies Unix socket creation. PostgreSQL startup and Terraform provider schema loading were blocked by that restriction. Terraform formatting and actual provider installation succeeded; `validate` did not. Snowflake account authorization, credentials, resource scope and spending limit have not been supplied.

The [evidence index](../evidence/README.md) records commands, source revisions and preserved outputs. An integration test present in the repository is not an executed result.

The final local capture at `f87abb572c03b5088c466e9c411a23b7c75a8da4` passed 72 tests and 15 subtests, with 40 real-PostgreSQL cases deselected. The [quality run](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43526045051) and [Terraform run](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43526045030) at that same revision both failed before runner execution and produced zero artifacts.

## Acceptance matrix

| Requirement | Implementation / evidence target | Current acceptance |
| --- | --- | --- |
| Strict versioned composite source keys | `domain.py`, `contracts/source.schema.json`, domain tests | Local unit-qualified |
| Original / standard / candidates / evidence / decisions / identities / crosswalk separation | Migration, service and architecture | PostgreSQL execution blocked |
| Three ERPs and difficult negatives | Versioned data/truth; heldout positive and negative pairs | Local unit-qualified; synthetic only |
| Blocking recall and deterministic/fuzzy comparison | Matching evaluator and benchmarks | Local measured; see evidence |
| Full-group constraints and attribute authority | Matching + merge/execution rechecks | Domain tests passed; transaction execution blocked |
| Stable IDs, late changes and bitemporal provenance | Golden and membership history; DB overlap trigger | PostgreSQL execution blocked |
| Review, separation of duties, merge/unmerge/split | Authenticated console/API and audit ledger | In-process auth tests passed; database and browser execution blocked |
| Crash/replay/concurrent decisions | Transactional outbox, version checks, source checkpoints | PostgreSQL execution blocked |
| Consumer correction and source mapping preservation | Reporting projection and explicit corrected events | PostgreSQL execution blocked |
| Real dbt execution and lineage | Five dbt models, schema tests and SQL invariants | PostgreSQL parse passed; build and data tests not executed |
| Measured candidate/join/heap/history costs | Bounded control + empty-database profile | Local candidate profile measured; database profile not executed |
| Reference deployment and operational recovery | Docker Compose, backup/restore and exact fingerprints | Container, browser and restore drill not executed |
| End-to-end business correlation | HTTP/CLI context, durable run/decision/outbox trace, consumer receipts and snapshot/query links | Implemented; local context tests distinct from blocked durable/provider qualification |
| Snowflake snapshot + dbt semantics | Validated publication, Terraform, qualification script | Implemented and unit-tested; live run blocked |
| Terraform configuration and actual provider schema | Dedicated resources, pinned provider and generated lock | Format/install observed; schema validation blocked, no plan/apply |
| CI dependency/licence/secret controls | Frozen lock, pip-audit, component inventory, history scanner | Local reports preserved; remote CI not executed; declarations are not legal approval |
| License/visibility/protections/release | Release candidate notes and repository controls | Licence choice pending; private visibility preserved; metadata prepared, not applied |

## Prioritized remaining gates

1. Resolve the GitHub runner-admission failure by reading its exact annotation through an authorized signed-in interface, or supply another explicitly authorized isolated runner. Do not change billing, visibility or policy merely to obtain a green check. Execute and review PostgreSQL/dbt/restore/container/browser and Terraform schema results at the delivered code revision; fix observed failures before claiming reference qualification.
2. Run the dedicated Snowflake qualification with an authorized account, key-pair role, warehouse/database and credit budget. Retain query IDs, timings, provider parity tests and observed credit metrics where available.
3. Obtain the maintainer's explicit repository licence choice. Public visibility requires a separate authorized change and an anonymous-access check after that change.
4. Apply the prepared description/topics through a repository-settings-capable interface. Recheck repository protection availability when account capabilities or visibility change; no paid plan is enabled by this project.
5. Extend the small synthetic holdout with independently labeled, rights-cleared industrial fixtures before any accuracy generalization.

## Release scope

The code may be reviewed as a reference release candidate while Snowflake remains unverified. Issue #1 must stay open until the full agreed acceptance is complete. A PR self-review is disclosed as such; no independent approval is invented.
