# ADR 003 — Compensating corrections instead of erasing decisions

Status: accepted for the reference implementation.

## Decision

Keep original assertions and audit events immutable. Treat a split or unmerge as
a new versioned decision against expected current versions. Preserve subsequent
source updates when separating a mistaken group. Publish corrective golden and
crosswalk state through the outbox; retain retired IDs and their history.

## Why

Restoring an old database row would lose later observations and could break
source references. It would also imply, incorrectly, that downstream business
actions had disappeared. The reference instead records both the mistaken
interpretation and the later correction.

The golden ID is an identity reference, not a hash of attributes. Its attributes
can change without inventing a new identity. Membership decisions determine how
IDs are retained, retired or restored. Golden history distinguishes business
validity from when the platform learned the fact.

## Consumer contract

Consumers deduplicate by event ID, order updates by aggregate version, retain
source-to-golden mappings, apply retirements and reconcile after a correction.
The supplied reporting consumer demonstrates this behavior transactionally.

A correction does not undo an issued invoice, approved supplier payment,
inventory movement or external cache by itself. Each external consumer owns its
compensation and reference-remapping process. A database restore can rewind local
delivery receipts while an external consumer remains ahead; reconnecting requires
an explicit version and crosswalk reconciliation.

## Consequences

History grows. Retention cannot remove a source assertion, retired identity or
event still referenced by a consumer without an archival contract. The reference
does not run an automatic destructive cleanup. Backup restores the ledger and
local delivery state together, then verifies their fingerprints and business
invariants. It does not claim to restore external applications.
