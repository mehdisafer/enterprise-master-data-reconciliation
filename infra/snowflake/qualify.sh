#!/usr/bin/env bash
set -euo pipefail

# A live qualification consumes the explicitly configured dedicated warehouse.
# Run from the repository root after ingesting the synthetic demonstration.
if [[ "${1:-}" != "--execute-live" ]]; then
  printf '%s\n' 'Usage: bash infra/snowflake/qualify.sh --execute-live [evidence-directory]' >&2
  exit 2
fi
evidence_dir="${2:-evidence/snowflake-live}"
mkdir -p "$evidence_dir"
evidence_dir="$(cd "$evidence_dir" && pwd)"
git rev-parse HEAD > "$evidence_dir/commit.txt"
uv run --locked --extra snowflake python -m mdm.snowflake \
  --execute --exercise-rollback --output "$evidence_dir/publication.json"
uv run --locked --extra snowflake dbt build --project-dir dbt --profiles-dir dbt \
  --target snowflake --target-path "$evidence_dir/dbt/build" --log-path "$evidence_dir/logs"
uv run --locked --extra snowflake dbt docs generate --project-dir dbt --profiles-dir dbt \
  --target snowflake --target-path "$evidence_dir/dbt/docs" --log-path "$evidence_dir/logs"
printf '%s\n' 'Live publication, business readback, replay and dbt completed; inspect the retained results before accepting the environment.'
