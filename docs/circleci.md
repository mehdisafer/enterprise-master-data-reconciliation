# CircleCI pipeline source reconciliation (15 November 2026)

The production reference source is the repository's default `main` branch. The configured CircleCI `build-and-test` pipeline requires `.circleci/config.yml` at the **checkout commit**. The path existed in the historical `circleci-project-setup` branch, but not on `main` at commit `977512f5831556485bb04d6e2e208cbdf72816c2`.

## Observed mismatch

- CircleCI pipeline [#10](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/10) on older `main` did not start: `error fetching config - config file .circleci/config.yml could not be located`.
- Pipeline [#11](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/11) succeeded on `circleci-project-setup` at `9cae866`. This runs a **matching-only** test suite, not all unit, PostgreSQL, dbt or browser tests.
- Manual container pipeline [#12](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/12) was observed running on that setup branch, with no qualified terminal result at this observation.
- The original CircleCI legacy qualification [#7](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/Chxu19ueaSaHpEwDgFD9t2/7) was failed. It is not a passing full suite.

## Source alignment

The three CircleCI files are copied verbatim from the latest observed setup-branch Git objects, without merging that branch's older application tree:

| Path | Purpose | Boundary |
| --- | --- | --- |
| `.circleci/config.yml` | Default `build-and-test`, uv install, Ruff and `matching-unit` | Matching-only CI, not full application acceptance |
| `.circleci/test-suites.yml` | Names the matching test and JUnit output | Tests run only when CircleCI executes its suite |
| `.circleci/reference.yml` | Separate manual Linux Docker/HTTP/rendered-console workflow | Only a completed job with actual evidence qualifies the container/profile |

The source checkout must be confirmed against `CIRCLE_SHA1`. A green setup-branch pipeline is not evidence for the merged `main` commit. GitHub Actions and live Snowflake have independent acceptance gates. The CircleCI project settings may contain multiple pipeline definitions; their config paths and triggers must be reviewed in the authorized CircleCI interface before deleting or disabling any pipeline.

## Next qualification

1. Observe a successful **new-commit** CircleCI build on the code branch and merged `main`, with actual steps and the matching-suite JUnit file.
2. Extend mainline CircleCI beyond matching-only smoke to genuine PostgreSQL/full pytest/dbt, preserving the existing evidence-based acceptance criteria.
3. Verify the manually triggered `reference.yml` Docker/browser run, with its own source SHA, finished status, logs, and retained report. Do not repeat expensive manual runs solely for documentation edits.
4. Keep full acceptance open for live Snowflake, Terraform provider schema, backup/restore and authenticated public publication unless those independent gates are actually tested.

This change does **not** change repository visibility, licensing, CircleCI project billing, cloud resources or client infrastructure.
