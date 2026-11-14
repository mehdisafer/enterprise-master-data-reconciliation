# Publish the reference source

## Decision and current state

On 14 November 2026, the maintainer requested public source publication and chose to make the repository-setting changes in GitHub's interface. The delivery sequence is to integrate the documented reference candidate into `main` through [PR #2](https://github.com/mehdisafer/enterprise-master-data-reconciliation/pull/2), then verify the requested public visibility and metadata. Merge completion and public access are not yet established by this preparation. The [metadata record](repository-metadata.json) distinguishes observed private visibility from requested public visibility.

Publishing this source leaves [issue #1](https://github.com/mehdisafer/enterprise-master-data-reconciliation/issues/1) open. The native PostgreSQL/HTTP results remain scoped to their recorded synthetic scenarios. Docker, rendered-browser, Terraform provider-schema and live Snowflake qualification remain open in the [acceptance matrix](acceptance.md). No release tag, deployment or cloud spending is part of this delivery.

The delivery agent handles the PR transition, merge verification and workflow follow-up through the authorized GitHub API. The maintainer handles visibility and About metadata in GitHub's interface. Personal-workstation access is outside this delivery's scope.

## Recorded prepublication checks

The [remote-history scan](../evidence/2026-11-14/publication-preflight/remote-history-scan.json) covered 518 unique blobs across 10 commits reachable from the two enumerated branches, totaling 10,211,743 bytes. Its configured checks reported zero findings. Seventeen blobs unavailable in local Git were retrieved remotely and their Git object hashes verified. Tag enumeration was unavailable, so tag-only history is outside this scope. This pattern-based scan does not establish exhaustive secret detection.

The [Actions inventory](../evidence/2026-11-14/publication-preflight/actions-inventory.json), observed at 14:03 UTC on 14 November, recorded 12 runs, 33 jobs, zero recorded steps and zero artifacts. Admission annotations were not read; the cause of the failures remains unconfirmed. GitHub documents that Actions history and logs become visible when a repository becomes public. These captures describe the recorded state before publication, rather than successful CI execution.

## Integrate the candidate and apply visibility

1. Finish and verify the documented PR head. Mark PR #2 ready and integrate that exact candidate into `main` through the GitHub API, retaining the unresolved qualification status. Record the resulting commit and verify that `main` contains the complete reference, including `src/`, `tests/`, `dbt/`, the Compose files, documentation, evidence and both workflow files. Keep issue #1 open.
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
