# Acceptance and remaining work

Updated 15 November 2026. “Implemented” means code exists; “executed” identifies an actual command; “qualified” applies only to the corresponding environment and passing invariants. A hash or an implementation review is not independent certification.

## Current decision

**The synthetic local PostgreSQL reference, installed package, Docker deployment and actual rendered lifecycle are qualified. Live Snowflake and target-specific production acceptance remain open.** No stable production V1 or provider success is inferred from these local results.

The maintainer's parallel dependency and native-qualification work was preserved. PR #10 merged current `main` into the CircleCI candidate before a fresh full test. No source, lockfile, compatibility test or retained upstream evidence was discarded. The combined qualified runtime revision is:

`b7485a20fa9a13aaa5a84179bf1a03f01bdbee7a`

The PC-Mehdi connection was used, with task-specific authorization, to control CircleCI and download proof into a dedicated temporary task directory. Application/database/browser execution occurred on CI workers. No client data, client infrastructure or personal database was used.

## Executed profiles

### Full package/database profile

Pipeline `f8810a1d-f659-493f-a513-e3c6a2bb9d06`; [workflow](https://app.circleci.com/workflow/b514e6ba-1af2-4074-8a1c-b6751960d29c).

The inspected workflow succeeded on the combined revision. It executed the locked Python 3.12.16 environment, installed-wheel controls, source/secret/dependency checks, real PostgreSQL tests, business demonstration, export validation, dbt build/docs, backup/restoration, refusal to restore over a populated database, restored dbt checks and bounded benchmarks.

The complete suite reports **180 tests and 15 subtests**. The retained JUnit contains **195 case entries, zero failures, zero errors and zero skipped entries**. Do not add those 195 entries to the 180 tests as independent tests.

### Native Docker/browser profile

Pipeline `cdd50eb5-fb9d-4a29-8612-37bc5d186c25`; [workflow](https://app.circleci.com/workflow/872b65af-ec73-4fd2-872c-9b3c38c31c40).

The manual `.circleci/reference.yml` ran on `ubuntu-2404:2026.10.1` with a dedicated Compose project and ephemeral identities. It built the actual image, started PostgreSQL/migrations/API, executed the demo from the installed container, reached the host loopback health endpoint and ran `scripts/browser_smoke.py --exercise-lifecycle`.

The browser receipt reports `passed`, with no recorded console or page errors. Its real form actions and distinct request/approve/execute identities exercised merge, split, unmerge and corrected consumer views. Observed lifecycle states were `executed`; the final business check also passed. This is not only a screenshot or an HTTP reachability check. Cleanup targeted only the stack marked as owned by this run.

### Terraform schema

Pipeline `0b0d2b4b-fc01-4f41-8fcf-c48d56003a8d` executed formatting, backend-disabled initialization, provider validation and schema extraction. Its scope is **static configuration/provider schema only**. No live account, plan or apply is claimed. Source changes made later to application/dependency code do not turn that static run into a provider deployment.

## Inspected artifact integrity

SHA-256 values below were calculated from downloaded original artifacts, not regenerated test results:

| Artifact | SHA-256 |
|---|---|
| Combined database `artifacts/pytest.xml` | `627c48e46b9fc3ae8488127d8b442287bef2ebae5468d5ecd6ad001a0443d602` |
| Combined database `artifacts/restore.json` | `6405f80122edbe8229966cc0fdd32a547a883f839ac56561af81dd974481cab93` |
| Combined database `artifacts/second-restore-rejection.json` | `a3a69b2f806c94701dbfc89c938a0f61a97965ab1f0e72d6fdbd694ae3fc077a` |
| Native reference `reference/browser-check.json` | `eae88c88efe68c3f1071bde7d0fe7cd7f3366d2f0f418d291b3cf3950cff9d34` |
| Native reference `reference/container-post-lifecycle-check.json` | `02df03919c8a29f7e416c2a16adf57eea377c7b519b406fb8030bfd695616544` |

The database artifacts also retain installed versions, source/environment, model manifests, consumer assertions, query plans and performance measurements. Original native evidence from the parallel dependency work remains at [dependency-qualification](../evidence/2026-11-15/dependency-qualification/), with its own environment and revision. CircleCI retention is finite; these fingerprints and acceptance decisions remain versioned.

## Corrections and network implications

Missing GitHub event metadata in a manually triggered CircleCI Actions run now requests full qualification, not a skip. The optional load profile is not invoked with an absent input. Explicit Python selection preserves the reviewed environment.

An API attached only to Docker's internal network had a configured port but was unreachable from the host in the observed runtime. The API now also joins an ingress bridge, while its published binding remains `127.0.0.1:8000`. PostgreSQL and migrations retain the internal `data` network with no published database port.

**The ingress-connected API can initiate egress. The deployment is not wholly air-gapped.** No `0.0.0.0` host binding or security bypass was introduced to obtain successful browser execution. Earlier failed container runs remain in history.

## Invariants and operational limits

Source hashes, schemas, OpenAPI, field provenance, legal-identity conflicts, immutable history, bitemporal values, separate human roles, optimistic versions, consumer corrections and repeat-safe operations remain required. A second restore into a non-empty target must be refused for the expected reason, not merely fail arbitrarily.

The ledger serializes graph mutations using a PostgreSQL advisory transaction lock. Tests and bounded measurements do not establish horizontal write scalability. The 34-identity synthetic truth corpus is not a real customer population. Corrections to reporting do not reverse external business actions.

Secrets must remain in protected external files, not repository artifacts. Tests requiring database reset use a dedicated `_test` database. See [operations](operations.md), [verification](verification.md), [demo](demo.md), [matching](matching.md) and the current README for executable instructions.

## Gates still open

| Gate | Closure evidence required |
|---|---|
| Live Snowflake | Authorized dedicated account/role, authentication, warehouse/database scope, budget, real load/dbt/idempotence/reconciliation/restore results and provider outputs |
| Production target | Selected environment, permissions, secret lifecycle, monitoring, measured recovery and operator acceptance |
| Project licence | Explicit maintainer choice; third-party notices are not a licence for original project code |
| Public visibility/protections | Maintainer setting changes followed by readback; historical private-plan restrictions are not current enforcement proof |

Issue #1 remains open for the original live-provider scope. Source integration, public visibility, static Terraform validity and production acceptance are separate decisions. No paid plan, external provider deployment or cloud spending was initiated in this qualification.
