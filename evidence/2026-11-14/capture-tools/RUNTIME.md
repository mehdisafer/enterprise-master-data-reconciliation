# Dedicated local PostgreSQL qualification runtime

This directory contains a synthetic PostgreSQL cluster, extracted upstream
packages, verification evidence and a scoped process launcher. It does not modify
the project repository, system packages, privileges or operating-system controls.

## Run a qualification

```bash
python /workspace/scratch/fc83c385ce79/p02-postgres-runtime/run_with_postgres.py \
  --timeout-seconds 1200 -- bash /absolute/path/to/qualification.sh
```

The command can run several sequential checks against the same server. The
launcher supplies client binaries, library paths, passwordless DSNs, the private
libpq passfile and the dbt password environment variable. It first starts the
server and executes a real version/settings query, then runs the supplied command
and stops this cluster in `finally`. It records run-specific evidence in `logs/`.
With no command, it performs the readiness query and stops.

The cluster data remains on disk across invocations. The detached server did not
survive the executor call that originally launched it, so clients must run inside
this launcher. `connection.env` is a private optional shell environment file; it
does not start the server. Neither it nor reports contain a password literal.
`admin-password` and `pgpass` are private credential files: do not publish them.

Databases are `mdm`, `mdm_test`, `mdm_restore` and `mdm_load`. All are owned by the
dedicated local bootstrap role `mdm`; this role is a cluster superuser for the
isolated qualification only. Host authentication is SCRAM-SHA-256, limited by
`pg_hba.conf` to that role and IPv4 loopback. Unix sockets are disabled.

## Exact software and provenance

- PostgreSQL server and clients: `17.12-1.pgdg13+1`, amd64, Debian 13 PGDG packages.
- Shared libpq: `18.7-1.pgdg13+2`, the current PGDG library satisfying the client
  package's `libpq5 >= 17.12` dependency.
- PostgreSQL's [17.12 release notes](https://www.postgresql.org/docs/release/17.12/)
  give the release date as 2026-11-12.
- PostgreSQL's [official Debian download page](https://www.postgresql.org/download/linux/debian/)
  documents the PGDG repository and public signing key.
- Repository: `https://apt.postgresql.org/pub/repos/apt`, suite `trixie-pgdg`.
- Verified signing fingerprint: `B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8`.

The downloaded InRelease signature was verified with that fingerprint. The
Packages.gz index SHA-256 was checked against the signed release metadata, and
each selected .deb's size and SHA-256 were checked against that index before
rootless extraction with `dpkg-deb --extract`. Package maintainer scripts were not
run. No source compilation or pgserver wheel was used.

Proof files include `logs/pgdg-signature.log`,
`logs/repository-verification.json`, `logs/verified-packages.json`,
`logs/binary-versions.json` and the original metadata/packages under `downloads/`.
The original public-key import attempted to contact gpg-agent and returned an
error under the Unix-socket restriction; the subsequent signature verification
uses public-key verification with `--no-autostart` and succeeded. The original
import log is preserved rather than rewritten.

## Observed readiness and bounds

The first complete launcher run was `logs/20261114T120548446004Z/`:

- SQL reported PostgreSQL 17.12 and server version number `170012`.
- The actual connection was to `127.0.0.1:59701`, database/user `mdm`.
- `SELECT current_database(), current_user, 6*7` returned `mdm|mdm|42`.
- The SQL readiness evidence reports empty `unix_socket_directories`.
- Client command and clean server stop each returned zero.

Observed settings: 20 connections, 64 MB shared buffers, 4 MB work memory,
32 MB maintenance work memory, 128 MB temporary-file limit, 256 MB maximum WAL
size, at most two parallel workers with one per query, JIT disabled, two-minute
statement/idle-transaction timeouts and ten-second lock timeout. These are
PostgreSQL resource settings, not a hard operating-system memory quota.
Data checksums, fsync, full-page writes and synchronous commit are enabled.

The official [connection settings documentation](https://www.postgresql.org/docs/17/runtime-config-connection.html)
describes `listen_addresses` and empty `unix_socket_directories` as standard
server configuration. No denied socket family or permission was enabled.

This validates the local engine and launcher. It does not establish that project
integration tests, dbt models, backup/restore or load qualification have passed;
those need the project owner's subsequent commands and retained outputs.
