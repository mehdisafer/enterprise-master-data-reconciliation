# Public source: publication state and outstanding acceptance

## Apache-2.0 project licence decision — 17 November 2026

The maintainer explicitly selected **Apache-2.0** for original project material. The full [LICENSE](../LICENSE) and [NOTICE](../NOTICE) are accompanied by the separate [third-party notices](../THIRD_PARTY_NOTICES.md); [pyproject.toml](../pyproject.toml) declares SPDX `Apache-2.0` and distributes those legal files with the Python package. This choice does not relicense upstream dbt macros or other third-party contributions embedded in retained evidence.

The latest **fully executed pre-licence** main reference is [`c18423efdc9e`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/c18423efdc9ea9db9430dcc0a64182452a1ef23e). [GitHub Actions #43991228308](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43991228308) successfully executed four jobs: **196 Python tests + 15 subtests**, dbt **48/48**, restored dbt **43/43**, and real Docker/browser lifecycle preserving 34 source identities. Both CircleCI main statuses were also successful. The licence/package change needs a new source-specific qualification after integration.

**Open publication conditions:** GitHub About description/topics remain unset, `main` unprotected, release/tag not published; CircleCI provider-specific original artefacts/settings remain uninspected. No live Snowflake load/readback/rollback, warehouse spend or production operation has been qualified. The prepared About values are in [repository-metadata.json](repository-metadata.json).

## Historical public-readback observation — 16 November 2026

GitHub's repository API now reports `mehdisafer/enterprise-master-data-reconciliation` as **public**, with default branch `main` at [`9b72725da693`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/9b72725da693b4587c27a12b1d65e6f639d69a86). The source successfully completed both default CircleCI jobs and the full [GitHub Actions Quality run #43920046617](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43920046617), including actual PostgreSQL, dbt, restore, container and rendered browser execution. The [source-linked evidence record](../evidence/2026-11-16/ci-main-qualification/) preserves observed job statuses and artifact identifiers.

Publication is **not** fully closed: the GitHub API returns **no repository project licence**, **no About description**, **no topics**, and `main` is **not protected**. The target description and topics are prepared in [repository-metadata.json](repository-metadata.json) but have not been applied. The initial isolated runtime could not resolve the anonymous HTTP URLs due to DNS/cache limitations. A **separate clean browser session with no saved profile, vault or sign-in** subsequently rendered both the public repository and the raw README on 16 November, with heading `Enterprise Master Data Reconciliation`, no login wall and no 404. Exact HTTP status codes and response-body digests were not independently captured.

The maintainer handles explicit licence choice, About metadata, branch protection and any release/tag decision in GitHub's interface. Source public visibility alone grants no open-source licence for original project code or synthetic fixtures. Live Snowflake and production-target qualification remain separate from public source delivery.

## Historical source integration and publication — 14–16 November 2026

On 14 November 2026, the maintainer requested public source publication and chose to make repository-setting changes in GitHub's interface. [PR #2](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/2) integrated the original reference into `main` at [merge `e27f4c2f`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/e27f4c2f58d812a2213b1457378095dc72dafd8a). The [readback record](../evidence/2026-11-14/publication-preflight/integration-verification.json) verifies the default branch, complete matching tree and full README. Visibility was still private at 14:15:46 UTC. **Current GitHub repository metadata confirms `public` on 16 November 2026**, while About description/topics remain unset. An unsigned-in browser subsequently displayed both the repository and raw README; it was not an authenticated GitHub API fetch. The [metadata record](repository-metadata.json) separates observed visibility from requested public visibility.

The 15 November continuation initially recovered GitHub baseline `16f7325c5f8b16ce2c5259d2fba44f40e78bebe7` and the four dependency proposals. The initial native qualification used [commit `88c932de`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/88c932de80dd1d20f49b93798153f2986f3c5029). During that work, [PR #8](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/8) integrated the dependency rollup into `main` at [commit `03c927b3`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/03c927b3f19e387df770130d59d9c09bea3800d1), with eleven compatibility tests and a [refresh note](dependency-refresh-2026-11-15.md). Those additions were preserved in [reconciliation commit `bb369db1`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/bb369db1360ef17c5328dc6a68392355728e9920), whose complete remote tree was read back.

[PR #9](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/9) carries the additional qualification, controls and [retained evidence](../evidence/2026-11-15/dependency-qualification/). Its conversation is the source-delivery record for review, the expected head, final `main`/tree readback and workflow observations. The initial and supplementary local captures have separate source correspondence; neither is a GitHub Actions execution result.

Public source visibility is now observed by GitHub API, but [issue #1](https://github.com/mehdisafer/enterprise-master-data-reconciliation/issues/1) remains open for live Snowflake and release/production acceptance. The 16 November hosted synthetic PostgreSQL, dbt, restore, Docker and rendered browser checks have passed on the source SHA linked above. The description/topics, project licence, `main` protections and release/tag are still pending. Anonymous repository/README readback has been observed separately from CI; none of the remaining gates is inferred from a green CI run.

The delivery agent handles the reviewed PR, integration verification and workflow follow-up through the authorized GitHub API. The maintainer handles visibility and About metadata in GitHub's interface. Personal-workstation access is outside this delivery's scope.

## Dependency qualification and source delivery — 15 November

PR #8 integrated the rollup from [FastAPI #4](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/4), [Pydantic #5](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/5), [Hatchling #6](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/6) and [Python #7](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/7); those individual proposals are closed. CI and both Docker stages select Python 3.12.16, matching the actual native qualification. PR #9 adds seven explicit hashed build constraints, an installed-package check, 44 HTTP regression cases and the rendered-browser lifecycle profile, while preserving the eleven tests from PR #8.

The latest [supplementary run](../evidence/2026-11-15/dependency-qualification/main-reconciliation/qualification.json) passed Ruff and **180 tests and 15 subtests**, including 55 real PostgreSQL cases, with zero failures, errors or skips. It used the existing installed wheel and [83 source inputs](../evidence/2026-11-15/dependency-qualification/main-reconciliation/source-correspondence.json) corresponding to `bb369db1`. The initial complete native run passed 169 tests and 15 subtests; five dbt models and 41 tests; exact 17-table restoration and 41 restored tests; and 34 live HTTP requests with 341 checks. Its [source correspondence](../evidence/2026-11-15/dependency-qualification/source-correspondence.json) binds 82 inputs to `88c932de`. The supplementary run did not repeat dbt, the business demonstration, restoration or live HTTP; their executable inputs are unchanged. Dated audits separately reported zero known vulnerabilities in 119 installed application, development and qualification packages and seven explicitly constrained build dependencies. The inventories overlap and are not additive. No successful Docker, rendered-browser, Terraform-schema or Snowflake execution is claimed.

The earlier continuation's 166-test narrative ended before a recoverable combined commit or PR was published. It is not used as evidence. The initial capture was reconstructed from verified GitHub content and qualified again; the later full-suite run also covers PR #8's preserved tests. The 454 historical artifact blobs remain unchanged in the final tree; `evidence/README.md`, the remaining entry in the 455-file baseline, is updated as the index. Its original version remains in Git history. New evidence is dated separately.

For PR #9, retain the final diff review, scoped source/evidence scan, expected-head check, final `main`/tree readback and actual workflow observations in the PR conversation. Read the latest recorded results there when assessing source delivery. PR #8's merged dependency rollup and the disposition of PRs #4–#7 remain separate historical facts. A branch commit or passing local report alone does not prove a remote merge or successful CI execution. The [Quality run at `bb369db1`](../evidence/2026-11-15/dependency-qualification/main-reconciliation/github-actions.json) failed in scope before runner assignment, with zero steps or artifacts and skipped dependent jobs. Its admission annotation text was unavailable; no billing, quota or policy cause is established.

## Recorded prepublication checks

The initial [remote-history scan](../evidence/2026-11-14/publication-preflight/remote-history-scan.json) covered 518 unique blobs across 10 commits reachable from the two enumerated branches, totaling 10,211,743 bytes. Its configured checks reported zero findings. Seventeen blobs unavailable in local Git were retrieved remotely and their Git object hashes verified. Tag enumeration was unavailable, so tag-only history is outside this scope. This pattern-based scan does not establish exhaustive secret detection.

The initial [Actions inventory](../evidence/2026-11-14/publication-preflight/actions-inventory.json), observed at 14:03 UTC on 14 November, recorded 12 runs, 33 jobs, zero recorded steps and zero artifacts. Admission annotations were not read; the cause of the failures remains unconfirmed. GitHub's [visibility guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility) describes public exposure of Actions history and logs. These captures are historical and precede the post-merge activity below.

## Historical post-merge checks and dependency triage — 14 November

The [expanded history capture](../evidence/2026-11-14/publication-preflight/post-merge-history/remote-history-scan.json), recorded at 14:22 UTC, covers the five then-listed branches and the retained head of closed PR #3. It enumerates 16 commits, 15 distinct complete trees and **540 unique blobs totaling 11,065,653 bytes**. Every blob's size and Git object hash matched; 517 were available locally and 23 were fetched from GitHub. All 16 commit messages were scanned. No pattern or limited input was reported within that scope. Tag-only history, unreachable objects and inaccessible account/log contents remain excluded. The [preservation manifest](../evidence/2026-11-14/publication-preflight/post-merge-history/preserved-artifacts.json) records the original reports and capture helper; old source contents are not duplicated in the evidence directory.

The [post-merge Actions record](../evidence/2026-11-14/publication-preflight/post-merge-actions.json) distinguishes two outcomes. The main-push Quality and Terraform runs still contain zero job steps and zero artifacts. Three initial Dependabot service runs succeeded with six recorded steps each, demonstrating that the update service ran. Those successes do not establish application qualification or resolve the unread qualification-job admission failure.

Dependabot proposed Python 3.15 in [PR #3](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/3), outside the project's `>=3.12,<3.13` runtime contract. That PR was closed without merging. The [Dependabot configuration](../.github/dependabot.yml) now ignores major and minor Docker updates for `python`, retaining eligibility for patch updates on 3.12. This follows GitHub's [documented ignore options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference#ignore); future service behavior under this rule had not yet been observed at that capture. The later Python 3.12.16 proposal is included in the 15 November candidate above. The FastAPI, Pydantic and Hatchling proposals in PRs [#4](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/4), [#5](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/5) and [#6](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/6) were outside the verified 14 November candidate. That triage did not change its runtime lock; the 15 November candidate has separate dependency changes and execution evidence.

## Source integration and maintainer visibility actions

1. **Recorded source delivery.** PR #2 integrated the original reference; its [readback record](../evidence/2026-11-14/publication-preflight/integration-verification.json) preserves the merge and tree identifiers. PR #8 integrated the dependency versions at `03c927b3`. PR #9 carries the qualification, controls and evidence, with review, the delivered head, final `main`/tree readback and workflow observations recorded in its conversation. Issue #1 remains open for full acceptance.
2. **Visibility already applied:** GitHub API returned `visibility=public` on 16 November. Do not toggle visibility again solely to reproduce this historical procedure. In [repository settings](https://github.com/mehdisafer/enterprise-master-data-reconciliation/settings), review the effective settings and consider branch protections separately; the authenticated API reports `main.protected=false`.
3. On the repository page, use the gear beside **About** to apply the exact description and topics below, then save the changes. GitHub documents the [About/topics controls](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics). Leave the website field unset: the reference console is local, and no hosted demonstration has been qualified.
4. Re-read the repository About description/topics after the maintainer edits them. Anonymous repository/README access was observed on 16 November in an unsigned-in browser; repeat that readback following any material publication change if source visibility needs requalification. GitHub still returns `description: null` and `topics: []`; no metadata edit is claimed. Main protections remain separate: the rulesets list is empty and classic protection readback is inaccessible to this integration.

## Repository description and topics

The source of truth is [repository-metadata.json](repository-metadata.json). Apply this description exactly:

> Explainable, reversible master-data reconciliation across industrial ERPs with Python, dbt, PostgreSQL and Snowflake.

Topics:

```text
master-data-management
data-engineering
entity-resolution
record-linkage
data-quality
data-lineage
dbt
postgresql
snowflake
fastapi
terraform
synthetic-data
```

## Verify publication and resume CI

- Verify that `main` is the default branch and presents the integrated candidate's README and complete source tree. Check the recorded merge commit rather than inferring integration from a PR action response.
- The [repository page](https://github.com/mehdisafer/enterprise-master-data-reconciliation) and [raw README on `main`](https://raw.githubusercontent.com/mehdisafer/enterprise-master-data-reconciliation/main/README.md) were both readable in a clean browser without authentication on 16 November. The heading matched `Enterprise Master Data Reconciliation`. This is an observed browser-access result, **not** a retained HTTP status-code/byte-hash capture; recheck if repository settings change.
- Read back the description/topics and compare them with the JSON above. Check available protections separately; the ruleset and administration errors observed during private setup on 13 November do not establish their post-publication state.
- The latest **executed** mainline [GitHub Actions Quality and PostgreSQL qualification](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43978646310) at `af4ed2b77616` passed all four jobs, including the full database and rendered browser path (189 tests + 15 subtests). Both CircleCI default jobs passed on that SHA as well. The new policy runs PostgreSQL/dbt on every main push, including docs-only. The [Terraform static run, attempt 2](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43593711641) passed format/init/validate/schema on byte-identical static Terraform files; no plan/apply or live Snowflake. A later CI run must be assessed by its own SHA and executed steps; green status alone does not prove a different source's tests.
- If a full run is still needed, use the appropriate workflow on `main` only after both workflow files are present there. Do not dispatch against the initial bootstrap branch state. For a prior failed run, verify its source revision and select a rerun only when it qualifies the intended code. Retain a still-unread admission annotation as an unresolved cause rather than attributing it to billing or policy.

## Licence status

The maintainer selected **Apache-2.0 on 17 November 2026**. [LICENSE](../LICENSE), [NOTICE](../NOTICE), [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) and the PEP 639 Python metadata provide the source and package licence declarations. Verify GitHub licence recognition after merging the change. This choice alone does not publish a release, protect `main`, qualify Snowflake or certify production.
