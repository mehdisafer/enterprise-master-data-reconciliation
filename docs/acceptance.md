# Acceptance and remaining work

Acceptance is evidence-based. “Implemented” means the code exists; “executed” identifies an actual command; “qualified” requires the corresponding environment and passing invariants. No component hash or automated self-review is an independent certification.

## Scope baseline

Inventory on 2026-11-13: private empty repository, no branches, issues, PRs, code or licence. Scope was published in issue #1 before implementation. No other repository or personal/client system was accessed for implementation. All demo records were authored for this repository.

## Acceptance matrix

| Requirement | Implementation / evidence target | Current acceptance |
| --- | --- | --- |
| Strict versioned composite source keys | `domain.py`, `contracts/source.schema.json`, domain tests | Local unit-qualified |
| Original / standard / candidates / evidence / decisions / identities / crosswalk separation | Migration, service and architecture | Integration pending CI |
| Three ERPs and difficult negatives | Versioned data/truth; heldout positive and negative pairs | Local unit-qualified; synthetic only |
| Blocking recall and deterministic/fuzzy comparison | Matching evaluator and benchmarks | Local measured; see evidence |
| Full-group constraints and attribute authority | Matching + merge/execution rechecks | Domain tests passed; transaction tests pending CI |
| Stable IDs, late changes and bitemporal provenance | Golden and membership history; DB overlap trigger | Integration pending CI |
| Review, separation of duties, merge/unmerge/split | Authenticated console/API and audit ledger | Integration pending CI |
| Crash/replay/concurrent decisions | Transactional outbox, version checks, source checkpoints | Integration pending CI |
| Consumer correction and source mapping preservation | Reporting projection and explicit corrected events | Integration pending CI |
| Real dbt execution and lineage | Five dbt models, schema tests and SQL invariants | PostgreSQL parse passed; build pending CI |
| Measured candidate/join/heap/history costs | Bounded control + empty-database profile | Local candidate profile measured; DB pending CI |
| Reference deployment and operational recovery | Docker Compose, backup/restore and exact fingerprints | Pending CI |
| Snowflake snapshot + dbt semantics | Validated publication, Terraform, qualification script | Implemented and unit-tested; live run blocked |
| CI dependency/licence/secret controls | Frozen lock, pip-audit, component inventory, history scanner | CI pending; declarations are not legal approval |
| License/visibility/protections/release | Release candidate notes and repository controls | Licence choice pending; private visibility preserved |

## Prioritized remaining gates

1. Execute and review the PostgreSQL/dbt/restore/container CI results at the delivered code revision; fix observed failures before claiming reference qualification.
2. Run the dedicated Snowflake qualification with an authorized account, key-pair role, warehouse/database and credit budget. Retain query IDs, timings, provider parity tests and observed credit metrics where available.
3. Obtain the maintainer's explicit repository licence choice. Public visibility requires a separate authorized change and an anonymous-access check after that change.
4. Recheck repository protection availability when the account capabilities or visibility change; no paid plan is enabled by this project.
5. Extend the small synthetic holdout with independently labeled, rights-cleared industrial fixtures before any accuracy generalization.

## Release scope

The code may be reviewed as a reference release candidate while Snowflake remains unverified. Issue #1 must stay open until the full agreed acceptance is complete. A PR self-review is disclosed as such; no independent approval is invented.
