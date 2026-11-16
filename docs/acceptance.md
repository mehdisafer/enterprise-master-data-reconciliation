# Acceptance and remaining work

## Current qualification — 17 November 2026 CET

**The corrected mainline CI policy is now qualified on [`af4ed2b77616`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/af4ed2b776162f8dce497b20d4f4fad063adeeab).** Both default CircleCI jobs and all four executed GitHub Actions quality jobs succeeded after [PR #22](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/22) removed the first-parent docs-only false skip. Original GitHub Actions postgres logs report **189 passed tests + 15 subtests** (one warning), dbt build **48/48**, restored dbt **43/43**, verified backup/restore and a successful real Docker/Playwright three-role lifecycle with 34 identities and zero JavaScript errors. The [source-specific evidence index](../evidence/2026-11-17/ci-mainline-hardening/) is a derivative manifest with original run/job/artifact references.

The previously blocked **Terraform provider schema** is now actually qualified in a compatible runner: [static workflow attempt 2](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43593711641) passed `fmt`, `init -backend=false`, `validate` and `providers schema` on an older commit with byte-identical workflow/HCL/lock inputs to the current source. No Terraform `plan`/`apply`, live Snowflake account or Snowflake dbt execution was performed.

**Acceptance boundary:** This validates the synthetic reference and static Terraform provider, not a deployed industrial production workload, the live Snowflake integration, licence or release. The optional original CircleCI artifact and Project Setup readbacks remain under #16.

## Historical acceptance snapshot — 16 November 2026

**The synthetic reference is now qualified through the hosted PostgreSQL, dbt, Docker and rendered-browser paths on [`9b72725da693`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/9b72725da693b4587c27a12b1d65e6f639d69a86).** Both default CircleCI jobs reported success at that SHA; all four jobs of [GitHub Actions full qualification #43920046617](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617) executed and succeeded. Original GitHub Actions logs confirm **183 pytest tests and 15 subtests**, dbt build **48/48**, restored dbt **43/43** (zero errors/skips), `restore_verified=true` and a real rendered merge/unmerge/split lifecycle with 34 source identities preserved. Source-linked artifact collections for security, dependencies, PostgreSQL and container were uploaded. The [dated evidence index](../evidence/2026-11-16/ci-main-qualification/) identifies the API/log basis and limitations.

**Not accepted by this result:** live Snowflake publication/readback/rollback and dbt parity, any production target and representative industrial data, repository licence grant, branch protections and full release/tag approval. GitHub reports public visibility (16 November) but no licence, About description/topics or `main` protection; anonymous repository and raw-README browser access was subsequently verified without sign-in (no HTTP codes or byte digests captured). Earlier 13–15 November status limitations below are retained as dated history, not claimed as the current source status.

Acceptance is evidence-based. “Implemented” means the code exists; “executed” identifies an actual command; “qualified” applies only to the corresponding environment and passing invariants. A source hash or implementation-agent review is not independent certification.

## Scope and current decision

Inventory on 13 November 2026: private empty repository, no branches, issues, PRs, code or licence. Scope was published in issue #1 before implementation. Only this repository and the provided isolated workspace were used. No personal PC, client data or client system was accessed. All demonstration records are synthetic.

**The 15 November native PostgreSQL/HTTP reference passed its dated synthetic qualification; 16 November hosted GitHub Actions now additionally qualified real Docker/browser and PostgreSQL/dbt on the corrected mainline SHA.** See [current snapshot](#current-acceptance-snapshot--16-november-2026). Full production/warehouse/release acceptance remains open.

The maintainer has requested public source publication. The original reference was integrated into `main` through PR #2, with the [merge, complete tree and README verified](../evidence/2026-11-14/publication-preflight/integration-verification.json). [PR #8](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/8) subsequently integrated the dependency versions. [PR #9](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/9) carries the qualification, controls and evidence; its conversation records the reviewed head, final `main`/tree readback and workflow observations. Source delivery does not close full qualification or issue #1. Visibility **was private** during the 14 November source integration, but **GitHub reports the repository public on 16 November 2026**. Anonymous repository and raw-README access was later observed in a clean unsigned-in browser; About metadata and licence remain unselected. About metadata is still blank, and the project licence remains unselected. The [publication procedure](publication.md) separates those checks from runtime acceptance and the still-unselected project licence.

## Current dependency qualification — 15 November

The initial [fresh native capture](../evidence/2026-11-15/dependency-qualification/native-flow/qualification.json) uses Python 3.12.16, PostgreSQL 17.12, FastAPI 0.162.4, Pydantic 2.14.3 and Hatchling 1.33.0. The [source-correspondence record](../evidence/2026-11-15/dependency-qualification/source-correspondence.json) binds its executable inputs to [commit `88c932de`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/88c932de80dd1d20f49b93798153f2986f3c5029). The capture records commands, source-file hashes, UTC intervals and original outputs. This is an isolated native run, not a GitHub Actions, container or warehouse result.

- The latest [complete suite](../evidence/2026-11-15/dependency-qualification/main-reconciliation/qualification.json) passed **180 tests and 15 subtests**, including 55 real PostgreSQL cases, with zero failures, errors or skips. It preserves the eleven compatibility tests added by PR #8 and uses the existing non-editable installed wheel. Its [source correspondence](../evidence/2026-11-15/dependency-qualification/main-reconciliation/source-correspondence.json) binds 83 inputs to [commit `bb369db1`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/bb369db1360ef17c5328dc6a68392355728e9920).
- The initial complete native capture passed **169 tests and 15 subtests**, including the same 55 real PostgreSQL cases. The editable smoke separately passed 114 tests and 15 subtests, with the 55 integration cases intentionally deselected for that profile.
- Forty-four new HTTP cases cover nested source validation, protected routes, serialization, error handling and two real decision lifecycles. The live Uvicorn exercise passed **34 requests and 341 checks**; all 17 operational table fingerprints stayed unchanged.
- Five dbt models and 41 tests passed. A new backup restored all 17 operational table fingerprints exactly, passed the invariants and 41 restored dbt tests, and rejected a populated target for the intended reason.
- The wheel preserves all 18 application resources and the CLI. The application lock and seven explicitly hashed build dependencies were exercised. Dated audits reported zero known vulnerabilities in 119 installed application, development and qualification packages and, separately, seven explicitly constrained build dependencies. The inventories overlap; their counts are not additive.
- [Contract comparison](../evidence/2026-11-15/dependency-qualification/contract-comparison.json) preserved the 35 reference assertions' serialization and ingestion hashes, five schemas and OpenAPI across the dependency change. Those 35 assertions are the compatibility input set; the business demo still retains 34 source identities.

The supplementary run executed Ruff and the full pytest suite only. The business demonstration, dbt, restore and live HTTP outputs remain the initial capture; their executable inputs are unchanged.

The previous continuation's account of 166 passing tests was not recovered as a published candidate. It is not reused as proof. The current qualification was executed again against the reconstructed GitHub baseline and reviewed update proposals. [Source-delivery status](publication.md) is separate from these local results.

The browser workflow now invokes the optional lifecycle profile and checks `mdm check` afterward. That profile implements merge, approval, execution, unmerge, split and consumer correction under three distinct operators. The native local workspace still cannot run Chromium; the separately executed CircleCI `reference-containers` job reported success at `b7485a2`. Original screenshots, response checks and post-lifecycle artifacts have not been read back independently here.

## Supplementary original CircleCI artifact register

A parallel workstream documented additional [original CircleCI artifact inspection and SHA-256 values](circleci.md#parallel-original-artifact-inspection-recorded-in-pr-12) in [PR #12](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/12). It reports 195 JUnit entries (180 tests + 15 subtests, zero failures/errors/skips), successful browser merge/unmerge/split and successful post-lifecycle business checks for the tested combined source `b7485a2`. This conversation has verified the GitHub success contexts and executable-file correspondence; it has **not independently downloaded or rehashed** the artifact files. These different verification scopes must remain visible when deciding acceptance.

## Historical source correspondence — 14 November

The application, test and dbt inputs qualified on 14 November match [commit `205e7507`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/205e7507b9cd7dc1b34a858f2c524ce0c832642c), tree `2075183147d1ff50ddfee7e86e99ad7d7bdb367e`. The [source correspondence](../evidence/2026-11-14/source-correspondence.json) remains unchanged. Its dependency and test versions describe that earlier capture, not the updated candidate.

## Historical correctness and evidence fixes — 14 November

The original 112 tests passed against real PostgreSQL 17.12. Further review found a publication-completion gap and a historical-compatibility gap. The historical case was reproduced before correction. The resulting implementation:

- Drains publication in at most 100 batches per attempt, completes only at `caught_up=True`, and retains failed/resumable state on budget exhaustion or no progress.
- Repairs an older incomplete terminal result using its original run identity and checkpoints, within the existing three-attempt limit.
- Uses the same historical slice interpretation for preview, request validation, execution and golden reconstruction. An incompatible pair retains a dated conflict without aborting unrelated matches.
- Recomputes candidate disposition when a third member changes, and displays the group conflict in the console's evidence.

Thirteen new PostgreSQL regressions cover those boundaries. That capture's final suite passed **125 tests plus 15 subtests, with zero skipped cases**, including **53 real PostgreSQL integration cases**. A Starlette TestClient deprecation warning remains recorded.

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
| Native HTTP operation | 34 requests and 341 checks; 17 table fingerprints unchanged | Authentication, assets, metrics, trace correlation and graceful shutdown checked |
| Container reference and rendered console | Compose, actual rendered three-role lifecycle and business checks | 16 November GitHub Actions container job executed successfully on tested `main`: `passed=true`, `lifecycle_executed=true`, 34 identities, no JavaScript errors |
| Durable business correlation | HTTP/CLI, run, decision, audit, outbox and receipt tests | PostgreSQL/HTTP qualified; live warehouse query links not qualified |
| Snowflake snapshot and dbt semantics | Publisher, unit boundaries, real PostgreSQL export | Live Snowflake load/readback and parity not executed |
| Terraform and actual provider schema | Pinned CLI/provider lock; `fmt`, `init -backend=false`, `validate`, `providers schema` | **Hosted static provider-schema qualification passed** on historical commit with byte-identical workflow/HCL/lock; no plan/apply/live account |
| Dependency/licence/secret controls | Locked deps, dated audits, source-history scan and notices | 16 November `scope` and `dependencies` jobs executed and passed; no project licence chosen |
| Installed package | Source distribution, wheel, resource hashes and entrypoint | All 18 resources preserved; full suite passed against the installed wheel |
| Source publication, licence and release | Public source, metadata manifest and release-candidate notes | Visibility public by GitHub API and anonymous browser readback; About metadata blank, no project licence/tag, `main` unprotected |

## Environment and CI limits

The earlier inference that Unix socket denial prevented every local server was too broad. A fresh probe established that loopback TCP works. PostgreSQL 17.12 ran with `unix_socket_directories=''` and Uvicorn bound to `127.0.0.1`. The 14 November capture used signed PGDG packages. The current 15 November capture uses Debian Security packages for trixie, version `17.12-0+deb13u1`; its [runtime manifest](../evidence/2026-11-15/dependency-qualification/environment/runtime_manifest.json) and [signature verification](../evidence/2026-11-15/dependency-qualification/environment/signature_verification.json) retain package provenance and verification. No system installation, permission change or external resource was needed.

Fresh [15 November environment attempts](../evidence/2026-11-15/dependency-qualification/environment/) confirmed the remaining boundary: Docker is absent, Chromium fails before rendering at Unix socket creation, and Terraform formatting/initialization pass while provider validation/schema startup fail with the socket permission error. These results reaffirm the earlier limitation on this environment; they are not successful browser or provider-schema runs. The older Playwright download failure remains a historical failed attempt.

The [version-specific provider transport review](terraform-provider-transport.md) establishes from official source code that the pinned Linux Snowflake executable still selects a Unix listener in managed debug mode. `TF_REATTACH_PROVIDERS` and the plugin port variables do not give this executable a TCP listener. This narrows the environment diagnosis without qualifying the provider schema. Static validation needs a compatible runner, not Snowflake credentials; live warehouse qualification has separate prerequisites.

At the historically qualified 14 November source revision, [quality run 43593711716](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43593711716) and [Terraform run 43593711641](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43593711641) failed before runner execution. The failed jobs have `runner_id: 0`, no steps and one check annotation each; artifact collections are empty. The connected endpoint exposes the annotation count but not its text. The [post-merge record](../evidence/2026-11-14/publication-preflight/post-merge-actions.json) confirms the same absence of steps for the main-push qualification runs, while recording three successful Dependabot service jobs with 18 steps in total. Update-service execution did not qualify the application or the then-proposed dependencies. The 15 November local qualification above supplies separate evidence for the consolidated dependency candidate. Billing, quota and policy causes for the qualification failures remain unconfirmed. The [15 November Quality record at `bb369db1`](../evidence/2026-11-15/dependency-qualification/main-reconciliation/github-actions.json) likewise records scope failure before runner assignment, no executed steps or artifacts, and skipped dependent jobs. Its one admission annotation remains unread. These GitHub observations do not invalidate or replace the separately recorded native runs.

## Extended default CircleCI gate — qualified on the mainline SHA

After [PR #17](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/17) escaped four literal Python heredoc delimiters, both default CircleCI jobs (`build-and-test` and `postgres-integration`) reported **success** on `9b72725da693`. The earlier pipelines #39–#42 were **Not Run** due to a CircleCI 2.1 config compilation error; they were not failed application tests. The repo now includes `tests/test_circleci_config.py` guarding against unescaped non-template openers.

The same SHA's [GitHub Actions full run](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617) independently executed scope, dependency auditing, actual PostgreSQL pytest, five dbt models and 41 data tests, consistent backup/restoration and real Docker/browser lifecycle. The original logs and artifact inventory were inspected; the original CircleCI `scope.json` and other CircleCI artifact bytes were not separately downloaded, so their values must not be invented or conflated with GitHub Actions evidence. The repo remains a **synthetic reference**, not an authorized live Snowflake or production target.

## 17 November mainline CI skip-safety hardening — remote CI qualified

An isolated Git reproduction found a **real CI-selection false negative**: the old CircleCI `postgres-integration` scope logic compared only the head commit to its first parent, potentially skipping all PostgreSQL/dbt tests when a multi-commit push ended in documentation. This is a *selection-policy defect*, not evidence of incorrect application data. The new policy eliminates documentation-only runtime skipping on `main`, verifies the exact checkout SHA, and records a `runtime_requested=true` scope receipt. It retains the cheaper `build-and-test` profile on branches and the separate full GitHub Actions qualification. The tradeoff is additional CircleCI minutes on every main push.

Six standalone tests of the new scope helper passed using both pytest entrypoints; **the corrected mainline source subsequently passed both default CircleCI jobs and all four GitHub Actions quality jobs** at [`af4ed2b77616`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/af4ed2b776162f8dce497b20d4f4fad063adeeab). The six checks remain local test evidence, while remote integration and browser execution are separately verified through original GitHub Actions logs. No provider-specific CircleCI artifact bytes were downloaded. The synthetic Snowflake adapter, licence and production target remain separate.

## Source publication and remaining qualification

The maintainer previously requested public source publication. On 16 November 2026, GitHub's repository API reports visibility **public**, with **no selected project licence**, no About description/topics and no protection on `main`. Those are independently tracked release/publication obligations, not a failure of the new synthetic CI qualification. The isolated environment could not resolve anonymous HTTP URLs; an independent browser session without sign-in subsequently read both the repository and raw README on 16 November. This does not certify an HTTP status code or response digest. The [publication procedure](publication.md) and [metadata record](repository-metadata.json) contain the prepared values.

1. Treat historical GitHub Actions runner-admission failures as source-dated incidents. The 16 November full Actions run succeeded on an assigned runner; continue to retain source SHA, JUnit/dbt/restore/browser evidence for each future runtime-changing commit. A documentation-only scope result is not another full application PASS. Use [the current evidence index](../evidence/2026-11-16/ci-main-qualification/) for the qualified source.
2. Run the dedicated Snowflake qualification with an authorized account, key-pair role, database/warehouse scope and explicit spending limit. Retain publication/readback/rollback results, dbt parity, query IDs and accessible credit metrics. PostgreSQL export success is not a Snowflake result.
3. Inspect actual branch protections on the now-public repository: GitHub rulesets enumeration returns `[]`, while classic protection read is forbidden to this integration. Maintain explicit unlicensed status until the maintainer chooses a project licence; third-party notices remain applicable.
4. Extend the small holdout with independently labeled, rights-cleared industrial fixtures before making accuracy or scale claims beyond the measured synthetic profiles.

PR #2 integrated the original reference, PR #8 integrated the dependency versions, and PR #9 carries the supplementary qualification and controls. Issue #1 remains open for full acceptance. No release tag is part of that action. Implementation-agent reviews are disclosed self-review, not independent approval.
