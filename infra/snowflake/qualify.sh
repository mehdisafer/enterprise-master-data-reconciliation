#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

# This script is a deliberately opt-in, billable LIVE qualification.
# Never overwrite the original evidence of an earlier run.
usage() {
  printf '%s\n' 'Usage: bash infra/snowflake/qualify.sh --execute-live [new-evidence-directory]' >&2
  exit 2
}
if [[ $# -lt 1 || $# -gt 2 || "${1:-}" != "--execute-live" ]]; then
  usage
fi
if [[ $# -eq 2 && -z "$2" ]]; then
  usage
fi
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd -- "$repo_root"

# Preflight before creating an output directory or contacting either database.
for name in SNOWFLAKE_ACCOUNT SNOWFLAKE_USER SNOWFLAKE_DATABASE \
            SNOWFLAKE_SCHEMA SNOWFLAKE_WAREHOUSE SNOWFLAKE_ROLE \
            SNOWFLAKE_PRIVATE_KEY_PATH; do
  if [[ -z "${!name:-}" ]]; then
    printf 'Missing required authorized Snowflake configuration: %s\n' "$name" >&2
    exit 2
  fi
done
if [[ -z "${MDM_DATABASE_URL:-}" && -z "${MDM_DATABASE_URL_FILE:-}" ]]; then
  printf '%s\n' 'Dedicated PostgreSQL URL or URL file is required' >&2
  exit 2
fi
if [[ ! -f "$SNOWFLAKE_PRIVATE_KEY_PATH" || ! -r "$SNOWFLAKE_PRIVATE_KEY_PATH" ]]; then
  printf '%s\n' 'Snowflake private key must be a readable external file' >&2
  exit 2
fi
if [[ -n "${MDM_DATABASE_URL_FILE:-}" && ( ! -f "$MDM_DATABASE_URL_FILE" || ! -r "$MDM_DATABASE_URL_FILE" ) ]]; then
  printf '%s\n' 'PostgreSQL connection file must be readable' >&2
  exit 2
fi
for executable in git uv; do
  if ! command -v "$executable" >/dev/null 2>&1; then
    printf 'Required executable missing: %s\n' "$executable" >&2
    exit 2
  fi
done
# A commit hash does not identify modified tracked code. Refuse live execution
# until the tracked source/index match the SHA recorded in the evidence.
if ! git diff --quiet -- || ! git diff --cached --quiet --; then
  printf '%s\n' 'Tracked source is modified; commit/review it before live qualification' >&2
  exit 2
fi
source_sha="$(git rev-parse --verify HEAD)"
evidence_dir="${2:-evidence/snowflake-live}"
if [[ "$evidence_dir" == "." || "$evidence_dir" == "/" || "$evidence_dir" == "-" ]]; then
  printf '%s\n' 'A fresh dedicated evidence directory is required' >&2
  exit 2
fi
if [[ -e "$evidence_dir" || -L "$evidence_dir" ]]; then
  printf 'Refusing to overwrite a previous qualification: %s\n' "$evidence_dir" >&2
  exit 2
fi
parent="$(dirname -- "$evidence_dir")"
if [[ ! -d "$parent" || ! -w "$parent" ]]; then
  printf '%s\n' 'Evidence parent directory must already exist and be writable' >&2
  exit 2
fi

# Plain mkdir refuses an existing directory/file/symlink atomically.
mkdir -m 700 -- "$evidence_dir"
evidence_dir="$(cd -- "$evidence_dir" && pwd -P)"
stage="source-capture"
finish() {
  local rc=$?
  trap - EXIT
  local result="failed"
  if [[ "$rc" -eq 0 && "$stage" == "complete" ]]; then
    result="passed"
  fi
  # Stage names are fixed literals; never copy credentials or DB URLs into evidence.
  printf '{"status":"%s","last_stage":"%s","exit_code":%d}\n' \
    "$result" "$stage" "$rc" > "$evidence_dir/qualification-status.json" || true
  exit "$rc"
}
trap finish EXIT
printf '%s\n' "$source_sha" > "$evidence_dir/commit.txt"

stage="publisher"
uv run --locked --extra snowflake python -m mdm.snowflake \
  --execute --exercise-rollback --output "$evidence_dir/publication.json"
stage="dbt-build"
uv run --locked --extra snowflake dbt build --project-dir dbt --profiles-dir dbt \
  --target snowflake --target-path "$evidence_dir/dbt/build" --log-path "$evidence_dir/logs"
stage="dbt-docs"
uv run --locked --extra snowflake dbt docs generate --project-dir dbt --profiles-dir dbt \
  --target snowflake --target-path "$evidence_dir/dbt/docs" --log-path "$evidence_dir/logs"
stage="complete"
printf '%s\n' 'Live commands returned success; inspect the original grant, rollback, dbt, cost and cleanup evidence before accepting this environment.'
