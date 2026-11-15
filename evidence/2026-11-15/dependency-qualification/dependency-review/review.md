# Dependency consolidation review — 15 November 2026

This is intermediate analysis for the repository integrator. No remote mutation was made.

## Captured inputs

`pr-4.json` through `pr-7.json` retain exact PR metadata, base/head SHAs, original bodies and file patches. The companion `.patch` files contain normal unified diffs. Full `uv.lock` snapshots and the relevant `pyproject.toml`/Dockerfile snapshots are preserved. `source-manifest.json` records the six files' Git blob hashes, SHA-256 and sizes. Their bytes were checked against GitHub's supplied blob hashes.

The starting main SHA is `16f7325c5f8b16ce2c5259d2fba44f40e78bebe7`. PRs #4–#6 use the preceding merge as their base; no dependency or application changes lie between that merge and main. PR #7 uses current main.

## Combined result and method

Run `python dependency-prs/combine_candidates.py` from any directory. It reads only the captured inputs and writes `combined/pyproject.toml`, `combined/uv.lock` and `combined/Dockerfile`.

The script replaces exact package blocks from the inspected PRs, preserving their distribution URLs and hashes. It updates only the two root requirement strings and three dependency package blocks. All other package blocks remain byte-identical. There are 122 package entries both before and after; that total includes the project and optional dependencies and is not an installed-environment audit count.

| Component | Baseline | Candidate | Expected changed surface |
| --- | --- | --- | --- |
| FastAPI | 0.141.1 | 0.162.4 | Root pin and FastAPI lock block |
| Pydantic | 2.13.4 | 2.14.3 | Root pin and Pydantic/core lock blocks |
| pydantic-core | 2.46.4 | 2.50.4 | Exact version required by Pydantic 2.14.3 |
| Hatchling | 1.29.0 | 1.33.0 | Build-system pin; absent from app lock |
| Python image | 3.12.14-slim | 3.12.16-slim | Both Docker stages |

Eleven direct dependency requirements from the exact upstream FastAPI and Pydantic tags are satisfied by the combined lock. FastAPI's added AnyIO and OpenTelemetry API dependencies already have locked entries. The lock keeps AnyIO 4.16.0, OpenTelemetry API 1.45.2 and Starlette 1.10.0. All three upstream Python projects declare Python >=3.10 and MIT licensing in their tag-specific project metadata; none determines this repository's own licence.

`uv 0.13.6 lock --check --offline --python 3.12` succeeded on the combined directory using CPython 3.12.14 and resolved 122 entries. This checks the lock and metadata, not package installation or application behavior. Original output and the scope are recorded in `upstream-review.json`.

## Targeted primary-source findings

### Pydantic

The official advisories contain the current 2.13.4 pin in all four affected ranges below. The proposed 2.14.3 is beyond their fixed versions.

| Advisory | Affected range | Fixed version | Relevant precondition |
| --- | --- | --- | --- |
| [GHSA-qpmf-fgh3-ff25](https://github.com/pydantic/pydantic/security/advisories/GHSA-qpmf-fgh3-ff25) | >=2.13.0,<2.14.2 | 2.14.2 | JSON models accepting extra data with typed extra keys |
| [GHSA-3r8g-cqwr-jr29](https://github.com/pydantic/pydantic/security/advisories/GHSA-3r8g-cqwr-jr29) | >=2.0,<2.14.2 | 2.14.2 | TypedDict/dataclass with extra data and alias collision |
| [GHSA-gj4f-r7mf-jjxh](https://github.com/pydantic/pydantic/security/advisories/GHSA-gj4f-r7mf-jjxh) | >=2.10.0,<2.14.0 | 2.14.0 | Untrusted exponent notation validated as a Fraction |
| [GHSA-955g-x97g-8mcp](https://github.com/pydantic/pydantic/security/advisories/GHSA-955g-x97g-8mcp) | >=2.0.0,<2.14.0 | 2.14.0 | Untrusted multihost URLs with costly scheme/host combinations |

The current domain and HTTP input models use `extra="forbid"`. The source scan did not identify Fraction, multihost URL, typed-extra or aliased Pydantic TypedDict/dataclass models matching those preconditions. This is a scoped source assessment: no project exploitability was demonstrated. Updating the affected package remains justified without asserting an exploitable endpoint.

[Pydantic 2.14.3 release notes](https://github.com/pydantic/pydantic/releases/tag/v2.14.3) describe packaging and serialization/schema performance changes; the security fixes themselves were released in 2.14.0 and 2.14.2. Serialized ingestion payloads, their fingerprints, generated schemas and OpenAPI should be compared before integration because this project's contract persistence depends on them.

### FastAPI

[FastAPI 0.162.4](https://github.com/fastapi/fastapi/releases/tag/0.162.4) explicitly requires AnyIO >=4.1.0. The [official history](https://fastapi.tiangolo.com/release-notes/) shows native telemetry support added in 0.142.0 and automatic exporter setup changed to opt-in in 0.143.0. The project currently constructs `FastAPI` without telemetry options and uses its own correlation/logging module. Validate actual request authorization, body limits, JSON responses, correlation and shutdown under the new version; a dependency-only metadata check is insufficient. No exporter deployment is implied by this dependency update.

### Hatchling

The [official history](https://hatch.pypa.io/dev/history/hatchling/) confirms 1.33.0. Between the pins, core metadata defaults moved to 2.5, `tomlkit` became a backend dependency and file/shebang handling changed. The repository has no custom build hooks in its inspected pyproject. Build an sdist and then a wheel from that sdist, inspect packaged modules/assets/entrypoint, and test that wheel outside the source checkout. `uv.lock` does not include Hatchling; capture the build environment separately and avoid describing the app lock as a full build-backend lock.

### Python

[Python 3.12.16](https://www.python.org/downloads/release/python-31216/) is an official security release dated 25 October 2026, within the repository's declared >=3.12,<3.13 range. The [official Docker image listing](https://github.com/docker-library/official-images/blob/master/library/python), captured with blob `0db5e4b8faa59e26e1c7527371b6e9f88555c41b`, includes `3.12.16-slim` as the slim-trixie alias. This establishes tag publication, not successful image pull/build or a resolved image digest.

## Integration plan

1. Start from verified current main and preserve the separate CircleCI branch.
2. Copy the three combined candidate files after reviewing `combined-static-check.json`.
3. Align `.github/workflows/quality.yml` `PYTHON_VERSION` and `docs/operations.md` Python image reference to 3.12.16. Retain historical evidence versions as recorded.
4. Run the meaningful combined-environment tests: full existing PostgreSQL suite, actual dbt build, schema/serialization comparison, wheel packaging and live HTTP checks. Reuse existing harnesses and retain failures as well as corrected results.
5. Record actual command output, environment and source hashes. Do not reuse the uncommitted transcript's 166-test result as current evidence.
6. Publish one reviewed consolidation PR with explicit supersession of #4–#7 only once the combined result has evidence. Close superseded PRs after the integrated commit is verified. Do not treat local native execution as Docker, browser, Terraform or Snowflake qualification.
