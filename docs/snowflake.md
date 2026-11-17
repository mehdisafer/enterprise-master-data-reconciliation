# PostgreSQL and Snowflake integration

## Status and scope

PostgreSQL is the reference system of record for identity decisions. Snowflake is
the integration warehouse for the same original records, candidates, decision
history, golden slices, crosswalks and consumer state. The Python publisher and
dbt project are implemented. **No Snowflake environment has been connected or
qualified for this delivery.** Offline connector tests are unit tests. PostgreSQL
tests, SQL compilation and a deployment template do not establish Snowflake
permissions, execution results, performance or cost.

The missing prerequisites are an explicitly authorized dedicated Snowflake
account/environment, a service principal with an external key, a bounded
warehouse, the dedicated database and schemas, and approved grants. No account,
warehouse, billing setting or public service is created by the local demo.

## Static provider qualification — 17 November 2026 CET

The pinned Snowflake **Terraform provider and static configuration** have now been successfully validated by [GitHub Actions static run #43593711641, attempt 2](https://github.com/mehdisafer/enterprise-master-data-reconciliation/actions/runs/43593711641), with `fmt`, `init -backend=false`, `validate` and `providers schema` all successful. That historical job's static Terraform workflow/HCL/lock files match current main by exact Git SHA. [Original-job evidence and identity boundaries](../evidence/2026-11-17/ci-mainline-hardening/) are retained. The local Unix-socket provider failure was an environment restriction, not a universal provider failure. This check involved **no plan, apply, credentials, Snowflake environment, credits or billing**, and it does **not** qualify the Snowflake publisher/dbt target. Live qualification still requires explicit authorization of the dedicated account, role, scope, costs and cleanup.

## Version and upstream checks

The selected Python 3.12 environment uses the dependency lock at the repository
root. The following versions were checked against maintainer-published metadata
on 2026-11-13; installation resolution is a separate compatibility check.

| Component | Selected version | Upstream licence / evidence |
| --- | --- | --- |
| dbt Core | 1.12.7 | Apache-2.0; [PyPI release](https://pypi.org/project/dbt-core/1.12.7/) |
| dbt PostgreSQL adapter | 1.11.0 | Apache-2.0; [PyPI release](https://pypi.org/project/dbt-postgres/1.11.0/) |
| dbt Snowflake adapter | 1.12.5 | Apache-2.0; [PyPI release](https://pypi.org/project/dbt-snowflake/1.12.5/) |
| Snowflake Python Connector | 4.8.1 | Apache-2.0; [PyPI release](https://pypi.org/project/snowflake-connector-python/4.8.1/) |
| Snowflake Terraform provider | 2.22.1 | MIT; [pinned provider](https://registry.terraform.io/providers/snowflakedb/snowflake/2.22.1), [licence](https://github.com/snowflakedb/terraform-provider-snowflake/blob/v2.22.1/LICENSE) |

dbt Core 1.x is chosen to keep the Python adapter path explicit and reproducible;
this is not a claim that it is the only current dbt distribution. The official
[Python compatibility table](https://docs.getdbt.com/faqs/Core/install-python-compatibility)
includes Python 3.12 for the selected Core line. Adapters use independent version
numbers; equality of those numbers is not a compatibility criterion. This table
does not grant a licence to this repository. The project licence remains unselected;
the [source-publication decision](publication.md) is separate from that choice and
does not authorize or qualify a live Snowflake deployment.

The initial connector pin, 4.7.4, constrained `filelock` below version 4 and left
known dependency advisories unresolved. It was replaced before publication by
4.8.1 with an explicit `filelock>=4.2.1,<5` dependency floor. The
[official connector release notes](https://docs.snowflake.com/en/en/release-notes/clients-drivers/python-connector-2026)
confirm support for filelock 4.x and Python 3.11 or later. The published adapter
metadata accepts connector versions `>=4.2.0,<6.0.0`; connector 4.8.1 declares
`filelock>=3.12,<5`. A normal Python 3.12 dependency resolution with the selected
dbt versions succeeded and selected filelock 4.2.10. No library constraint was
overridden. The complete application lock and its actual dependency audit remain
the release evidence, rather than this compatibility explanation.

## Semantic boundary

| Invariant or operation | PostgreSQL authority | Snowflake integration |
| --- | --- | --- |
| Source identity | Composite key and enforced uniqueness | Published snapshot; explicit duplicate checks |
| Decisions and concurrent merges | Transactions, version checks and graph lock | Read-only decision history, never a second decision writer |
| Relationships | Enforced foreign keys | Validated source snapshot plus dbt relationship tests |
| Golden time ranges | Business and knowledge intervals with overlap guard | Same timestamp values and overlap SQL tests |
| JSON | `jsonb` | `VARIANT`; readback compares decoded JSON values |
| Timestamps | `timestamptz` | `TIMESTAMP_TZ`, session timezone UTC |
| Primary/foreign keys | Enforced by the database | Standard-table key metadata is not relied on |
| Publication | Outbox written atomically with the identity change | Whole consistent snapshot becomes visible in one DML transaction |
| Consumer rollback | Compensation events and explicit consumer reconciliation | New snapshot carries changed identities and retained history |

Snowflake standard tables do not enforce primary-key, unique and foreign-key
constraints. The application therefore does not copy PostgreSQL DDL and treat it
as equivalent enforcement. See the official
[constraint overview](https://docs.snowflake.com/en/sql-reference/constraints-overview).
The current documentation also describes enforced `NOT NULL` and `CHECK`
constraints; neither replaces the key and relationship checks needed here.

## Publication protocol

`python -m mdm.snowflake` obtains a PostgreSQL session advisory lock dedicated to
the Snowflake publisher. A competing publisher fails before cloud mutation. The
publisher uses a fresh read-only `REPEATABLE READ` transaction to read an explicit
list of columns from the sixteen reviewed tables. The outbox is retained in that
same snapshot so change events and the golden state cannot originate from
different source transactions.

The export keeps PostgreSQL operational tables untouched. A normalized SHA-256
content identifier excludes the capture time: repeating an unchanged export
reconciles the existing publication. A digest identifies content; it is not an
independent certification. There is no per-event acknowledgement in the source
outbox and no distributed transaction spanning both databases. The durable
Snowflake manifest is the retry checkpoint.

In the already-authorized Snowflake schema, bootstrap creates three internal
tables and fixed source views. DDL is deliberately outside publication because
Snowflake DDL can commit an active transaction; see
[transaction semantics](https://docs.snowflake.com/en/sql-reference/transactions).
The internal storage is append-only by convention and restricted writer grants:

1. `_MDM_SNAPSHOT_DATA` holds versioned rows by snapshot, source table and source
   row key, with JSON documents and row hashes.
2. `_MDM_SNAPSHOT_MANIFEST` records a complete committed snapshot and its counts.
3. `_MDM_ACTIVE_SNAPSHOT` contains one checked singleton pointer. Source views
   join all rows through that pointer.

Loading all rows, checking counts, duplicate keys and full document content, inserting the manifest,
and advancing the pointer occur in one explicit DML transaction. Failure before
commit rolls back both rows and visibility. An uncertain commit is reconciled by
content identifier before retry. An already-published historical content id
cannot rewind a newer active generation. A successful publication reads back
every row through the source views and compares values with the PostgreSQL
snapshot. The business test suite then runs using the Snowflake dbt target.

Consumers must read a generation coherently: a single query sees a consistent
snapshot, while a client issuing several unrelated queries should capture the
manifest id and query the versioned data or retry if the active id changed.
The reference publisher is serialized; adding independent publishers without
the PostgreSQL lock is unsupported. Restrict the Snowflake writer principal so
manual duplicate pointer rows cannot bypass this convention.

This is a bounded snapshot adapter, not a claim of high-volume CDC. It sends
bound rows, keeps previous snapshots and caps exports at 100,000 total rows by
default. SQL statements time out after 120 seconds, warehouse queueing after 30,
and the publisher stops starting queries after a 600-second wall-clock budget.
An already-running query can complete up to its statement timeout later. Larger
datasets need a separately measured staged bulk loader and retention policy.
No automatic old-snapshot deletion runs in this implementation.

## Configuration and SQL safety

Database, schema, role and warehouse names must be simple identifiers, at most
63 characters. Names with quotes, dots, semicolons or expressions are rejected.
Table names and column expressions come from reviewed code. Row values use
connector bindings and `PARSE_JSON`, including hostile punctuation in source
names. The [connector examples](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-example)
document binding and transactions; no source metadata is treated as executable
SQL.

Required environment variables are `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`,
`SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA`, `SNOWFLAKE_WAREHOUSE`,
`SNOWFLAKE_ROLE`, and `SNOWFLAKE_PRIVATE_KEY_PATH`. Optional encrypted-key
passphrases use `DBT_ENV_SECRET_SNOWFLAKE_KEY_PASSPHRASE`. Credentials belong in a
secret manager or mounted file, outside the repository and evidence. The source
connection uses `MDM_DATABASE_URL` or `MDM_DATABASE_URL_FILE` and the same dedicated
database validation as the application.

The dbt Snowflake output uses the same account, principal, role and warehouse.
`MDM_SOURCE_SCHEMA` defaults to `MDM_RAW`; `MDM_ANALYTICS_SCHEMA` defaults to
`ANALYTICS` on Snowflake. For PostgreSQL they default to `public` and `analytics`.
PostgreSQL dbt credentials use `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE`, and
`DBT_ENV_SECRET_PG_PASSWORD`. The `DBT_ENV_SECRET_` prefix enables dbt secret
redaction. See the official [PostgreSQL profile](https://docs.getdbt.com/docs/local/connect-data-platform/postgres-setup)
and [Snowflake profile](https://docs.getdbt.com/docs/local/connect-data-platform/snowflake-setup).

Connector 4.8 changes its OCSP default. The Python publisher explicitly passes
`ocsp_fail_open=False`, enabling certificate-revocation checking and failing if
that check cannot complete. Its network must therefore permit the required
revocation endpoints. A unit test inspects the real factory arguments; no live
TLS connection has been qualified.

The installed dbt Snowflake 1.12.5 adapter was also inspected. It supports
`query_tag` but does not forward `ocsp_fail_open` or arbitrary `session_parameters`
from a profile. Those ineffective fields are not configured here. Fixed startup
and model hooks set the Snowflake session timeouts and UTC; the dedicated
warehouse's limits cover other dbt worker sessions, including tests. The adapter's
certificate-revocation policy is not guaranteed to match the publisher's explicit
OCSP policy. This is a documented live-qualification item; no dependency internals
are patched and no TLS bypass is enabled.

## Dedicated environment and roles

`infra/snowflake` pins the provider and declares only supported database, schema,
warehouse and resource-monitor resources. It keeps the warehouse single-cluster
X-Small, initially suspended, with auto-suspend at 60 seconds, no query
acceleration, concurrency two, and statement/queue limits. The monitor has a
non-renewing quota, graceful suspension at 90% and immediate suspension at 100%.
The default quota is one credit; the accepted profile range is one to ten.
`environment_authorized` defaults to false and a resource precondition blocks
creation. This is a concrete deployment boundary, not a request to approve an
unknown account.

The provider's pinned [warehouse schema](https://github.com/snowflakedb/terraform-provider-snowflake/blob/v2.22.1/docs/resources/warehouse.md)
and [monitor schema](https://github.com/snowflakedb/terraform-provider-snowflake/blob/v2.22.1/docs/resources/resource_monitor.md)
were inspected. The provider documents an administrator requirement for monitor
assignment. That elevated deployment identity must not be the runtime loader.
This module does not create a user, grant `ACCOUNTADMIN`, alter network policies,
change subscription settings, or attach an account-wide monitor.

After inspecting the plan, an authorized administrator must grant the chosen
runtime identities only the required access:

| Principal | Scope |
| --- | --- |
| Loader | USAGE on dedicated database, raw schema and warehouse; CREATE TABLE/VIEW and DML in the raw schema; one controlled publisher identity |
| Transformer | USAGE and SELECT on raw views; CREATE VIEW in analytics; USAGE on dedicated warehouse |
| Reader | USAGE and SELECT on approved analytics views |

Use the configured restricted role for each command; do not reuse the deployment
administrator for dbt or the application. Exact grants and service-user binding
are environment-specific pending work, not secretly applied resources. Database
and schema `prevent_destroy` guards require a reviewed decommission operation.
Terraform state must use an access-controlled backend before a shared deployment.
`terraform init`, provider-schema validation, plan, apply and restore remain
separate evidence requirements; an unexecuted HCL file is not a deployed system.
Provider installation and formatting were observed in the earlier **local** environment;
schema loading failed there at Unix socket creation. The [pinned-provider
transport investigation](terraform-provider-transport.md) explains that local
limit. On 16 November UTC, a separate compatible GitHub Actions runner
successfully executed format, backend-free init, validation and actual pinned
provider-schema inspection (the static Terraform files match current main).
**Live** Snowflake plan/apply and publisher/dbt operations still require an
explicitly authorized account, role, budget, evidence and cleanup plan.

Resource monitors help control warehouse usage but are not an exact currency
cap and do not cover every serverless feature. No such feature is enabled here.
The [resource-monitor documentation](https://docs.snowflake.com/en/user-guide/resource-monitors)
describes these operational limits. Never report the configured credit quota as
an observed charge.

## Live qualification

Run the complete synthetic demo first. Once the environment and grants are
authorized, supply the external configuration and execute from the repository
root:

```bash
bash infra/snowflake/qualify.sh --execute-live evidence/snowflake-live-YYYYMMDD-HHMMSS
```

**Proof preservation and authorization preflight:** the script requires an
explicit `--execute-live` flag, a complete `SNOWFLAKE_*` environment, a
readable external key file, a dedicated PostgreSQL connection URL/file and
installed `git`/`uv`. It checks these before creating an output directory
or connecting to the cloud. The selected output directory must be **new**:
an existing path, including a dangling symlink, is rejected, not replaced.
Tracked source and the Git index must also be clean before execution; an
uncommitted change would make a recorded commit SHA misleading. Untracked
synthetic inputs still require separate identity/provenance. The parent must
exist and be writable. Every attempt, including a failed
one, needs a unique path. A private 0700 evidence directory contains the
source SHA and a minimal `qualification-status.json` indicating the last
stage and actual exit code. If dbt fails after Snowflake publication, the
partial evidence remains and the status is **failed**, not PASS. Do not rerun
over those files; reconcile the committed Snowflake manifest before a new
attempt, because publication and dbt are not one cross-service transaction.

[Offline wrapper regressions](../tests/test_snowflake_qualify_script.py)
use a fake `uv` executable to verify missing authorization, output refusal,
clean tracked-source identity, failure preservation and separate dbt paths. **They do not connect to
Snowflake or qualify an actual provider.**

The script records the commit, publishes a real snapshot, exercises rollback
before the first publication, reads all source views back, repeats the same
publication to test idempotency, executes `dbt build --target snowflake`, and
generates dbt documentation. It preserves the connector report, query ids,
build `manifest.json` and `run_results.json` under `dbt/build/`, and documentation
results and `catalog.json` under `dbt/docs/`, with compiled SQL and logs. This
separation prevents documentation compilation from replacing executed test results.
The dbt build/docs output separation and the additional evidence-preservation
wrapper are tested without provider access; live Snowflake execution remains
open. Inspect
the report: on a previously-published identical snapshot, rollback is not
re-exercised and `rollback_exercised` remains false. Use a genuine changed input
for a new rollback exercise; do not relabel an idempotent no-op as a failure test.

The report includes query timings, scan bytes, rows and accessible cloud-services
credits from [session query history](https://docs.snowflake.com/en/sql-reference/functions/query_history).
It explicitly leaves the billing amount null. Warehouse compute credits and
currency billing need metering privileges, delayed usage data and the account's
actual commercial terms. Query credits are not a Snowflake invoice.

Acceptance requires successful business readback, zero failing dbt tests,
rollback and idempotent-retry evidence, a documented role/grant inspection and
measured runtime/cost metadata. Snowflake load scaling, concurrent-reader tests,
provider apply and a Snowflake restore exercise remain unverified until their
real evidence is added. The PostgreSQL restore exercise is not a Snowflake
restore test.
