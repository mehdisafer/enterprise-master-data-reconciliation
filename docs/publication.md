# Publish the reference source

## Decision and current state

On 14 November 2026, the maintainer requested public source publication and chose to make repository-setting changes in GitHub's interface. [PR #2](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/2) integrated the original reference into `main` at [merge `e27f4c2f`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/e27f4c2f58d812a2213b1457378095dc72dafd8a). The [readback record](../evidence/2026-11-14/publication-preflight/integration-verification.json) verifies the default branch, complete matching tree and full README. Visibility was still private at 14:15:46 UTC; public access and About metadata remain for application and verification. The [metadata record](repository-metadata.json) separates observed visibility from requested public visibility.

The 15 November continuation initially recovered GitHub baseline `16f7325c5f8b16ce2c5259d2fba44f40e78bebe7` and the four dependency proposals. The initial native qualification used [commit `88c932de`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/88c932de80dd1d20f49b93798153f2986f3c5029). During that work, [PR #8](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/8) integrated the dependency rollup into `main` at [commit `03c927b3`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/03c927b3f19e387df770130d59d9c09bea3800d1), with eleven compatibility tests and a [refresh note](dependency-refresh-2026-11-15.md). Those additions were preserved in [reconciliation commit `bb369db1`](https://github.com/mehdisafer/enterprise-master-data-reconciliation/commit/bb369db1360ef17c5328dc6a68392355728e9920), whose complete remote tree was read back.

[PR #9](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/9) carries the additional qualification, controls and [retained evidence](../evidence/2026-11-15/dependency-qualification/). Its conversation is the source-delivery record for review, the expected head, final `main`/tree readback and workflow observations. The initial and supplementary local captures have separate source correspondence; neither is a GitHub Actions execution result.

Publishing this source leaves [issue #1](https://github.com/mehdisafer/enterprise-master-data-reconciliation/issues/1) open. Native PostgreSQL/HTTP results apply to the recorded synthetic scenarios. A separate CircleCI Linux runner reported success for full PostgreSQL/dependency/container and rendered-browser jobs on the tested setup branch; [CircleCI reconciliation](circleci.md) identifies their exact SHA, configuration correspondence and pending original artifact readback. Final-main job execution, Terraform provider schema, authorized live Snowflake and release/public-access decisions remain distinct. No release tag, deployment or cloud spending is part of this source delivery. The repository is still private; anonymous access has not been verified.

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
2. In the maintainer's GitHub interface, open [this repository's settings](https://github.com/mehdisafer/enterprise-master-data-reconciliation/settings). Go to **Settings → Danger Zone → Change visibility → Public**. Confirm the repository is `mehdisafer/enterprise-master-data-reconciliation`, acknowledge GitHub's displayed effects, and select **Make this repository public**. Follow GitHub's [visibility instructions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility) if the confirmation layout changes.
3. On the repository page, use the gear beside **About** to apply the exact description and topics below, then save the changes. GitHub documents the [About/topics controls](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics). Leave the website field unset: the reference console is local, and no hosted demonstration has been qualified.
4. Verify the resulting repository state and anonymous access before recording publication as complete. Repository-setting changes are performed by the maintainer; the API delivery work does not imply they have happened.

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
- Request the [repository page](https://github.com/mehdisafer/enterprise-master-data-reconciliation) and [README on `main`](https://raw.githubusercontent.com/mehdisafer/enterprise-master-data-reconciliation/main/README.md) without authentication. Record successful content retrieval and public visibility. No personal browser session is needed for these HTTP checks.
- Read back the description/topics and compare them with the JSON above. Check available protections separately; the ruleset and administration errors observed during private setup on 13 November do not establish their post-publication state.
- Inspect the latest runs of [Quality and PostgreSQL qualification](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/workflows/quality.yml) and [Terraform static qualification](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/workflows/terraform.yml) for the intended merged source revision. A merge push can already trigger these workflows. Confirm actual job steps, conclusions and artifacts; the visibility change alone is not a CI result.
- If a full run is still needed, use the appropriate workflow on `main` only after both workflow files are present there. Do not dispatch against the initial bootstrap branch state. For a prior failed run, verify its source revision and select a rerun only when it qualifies the intended code. Retain a still-unread admission annotation as an unresolved cause rather than attributing it to billing or policy.

## Licence status

No project licence has been selected. GitHub's [licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) states that choosing one is optional; public visibility does not create an open-source licence grant. GitHub users can view and fork a public repository under its platform terms. Original code and synthetic fixtures retain their current unlicensed status, while the [third-party notices](../THIRD_PARTY_NOTICES.md) preserve upstream rights. A later project-licence decision requires the maintainer's explicit choice.
