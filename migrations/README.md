# Migration contract

The executable initial migration is packaged at `src/mdm/sql/001.sql`. `mdm migrate` records its SHA-256 checksum in `schema_migrations` and takes the graph advisory transaction lock. Reapplying the same migration is a no-op. An edited applied migration is rejected; subsequent schema changes must add a new numbered migration and an explicit upgrade path before deployment.

There is deliberately no destructive automatic down migration. Stop writers, preserve the original database and restore a verified backup into a new empty database for rollback. Read `docs/operations.md` for the tested restore procedure. Current release migration history contains only version 1.
