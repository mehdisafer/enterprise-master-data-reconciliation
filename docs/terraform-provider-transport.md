# Terraform provider transport investigation

## Decision and scope

The pinned Linux Snowflake provider cannot select a TCP listener through the official parameters examined. Its normal and `-debug` entry points both use a Unix socket. The existing `terraform validate` and provider-schema gates therefore remain blocked in this workspace, where that socket operation was denied.

This is a source-code investigation of the declared versions, completed on 14 November 2026. It is not a successful provider launch or schema validation. No provider was rebuilt, substituted or newly executed for this investigation, and no environment permission changed. No Snowflake account was contacted.

Use the existing [Terraform static workflow](../.github/workflows/terraform.yml) on a compatible runner to execute `init -backend=false`, `validate` and `providers schema -json`. Those static checks do not require Snowflake credentials or a warehouse. Live deployment and warehouse qualification have separate account, scope and spending prerequisites.

## Observed local boundary

The [original provider debug log](../evidence/2026-11-13/terraform-provider-debug.txt) records a real provider process failing at `listen unix` with `socket: operation not permitted`. PostgreSQL later ran successfully over loopback TCP with its optional Unix listener disabled, as recorded by its [real readiness query](../evidence/2026-11-14/native-flow/runtime/readiness-query.json) and [qualification runtime](../evidence/2026-11-14/native-flow/runtime/run.json). This proves that the PostgreSQL configuration is usable here; it does not give another executable a TCP transport option.

## Version-specific evidence

| Component | Inspected source | Finding |
| --- | --- | --- |
| P02 configuration | [Provider constraint](../infra/snowflake/main.tf), [lock](../infra/snowflake/.terraform.lock.hcl), [workflow](../.github/workflows/terraform.yml) | Snowflake provider `2.22.1`; Terraform CLI `1.17.2` |
| Snowflake `2.22.1` | [Entrypoint](https://github.com/snowflakedb/terraform-provider-snowflake/blob/ef814d9663972b0682d03ea65184660193f55f67/main.go), [dependencies](https://github.com/snowflakedb/terraform-provider-snowflake/blob/ef814d9663972b0682d03ea65184660193f55f67/go.mod) | `-debug` enables `WithManagedDebug()`; dependencies declare `terraform-plugin-go 0.31.0` and `go-plugin 1.8.0` |
| `terraform-plugin-go 0.31.0` | [Protocol-v6 server](https://github.com/hashicorp/terraform-plugin-go/blob/09a1181b051c53a3700401895ae281afbc91f0fc/tfprotov6/tf6server/server.go) | Both normal serving and managed debug call `plugin.Serve`; managed debug reports the listener's resulting address |
| `go-plugin 1.8.0` | [Server implementation](https://github.com/hashicorp/go-plugin/blob/155dcddc94873a285e14b7fa24b2f6ab6139668e/server.go) | `serverListener` chooses TCP on Windows and the Unix listener on other operating systems |
| Terraform `1.17.2` | [Reattach parser](https://github.com/hashicorp/terraform/blob/v1.17.2/internal/getproviders/reattach/reattach.go) | `TF_REATTACH_PROVIDERS` accepts TCP addresses, but describes an already running provider rather than configuring its listener |

The source commits above were resolved from the corresponding release tags and read directly. The conclusion is limited to those released implementations and this Linux environment.

## Why the proposed settings do not resolve this failure

`PLUGIN_MIN_PORT` and `PLUGIN_MAX_PORT` select ports after the TCP branch has already been chosen. They do not select that branch on Linux. `PLUGIN_UNIX_SOCKET_DIR` changes the socket's directory; the provider still calls `net.Listen("unix", ...)`.

`TF_REATTACH_PROVIDERS` tells Terraform where an existing provider is listening. Supplying a TCP address cannot start or reconfigure the official Snowflake executable. Managed debug also reaches the same listener selection before it can print a usable reattach configuration.

The [HashiCorp debugging guide](https://developer.hashicorp.com/terraform/plugin/debugging) likewise requires the provider to be started separately before its emitted reattach configuration is used. Its TCP example for attaching Delve concerns the debugger server, not a TCP mode for the provider process.

The unresolved check remains execution of the actual pinned provider on a compatible runner. The source investigation narrows the environment diagnosis; it does not establish that the Terraform resource configuration conforms to that provider's schema.
