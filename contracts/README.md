# Versioned contracts

`source.schema.json` is the strict pre-normalization source assertion. Composite keys include ERP, entity domain and local identifier; roles never change the identity domain. `rules.v1.json` documents reviewed code, not executable metadata.

The merge, split, unmerge and decision-transition JSON Schemas are generated from strict API input models. Caller-supplied actors are rejected. Group and decision versions are optimistic concurrency preconditions, and an idempotency key names exactly one canonical request.

`golden-event.v1.schema.json` defines the outbox payload. The outbox envelope supplies its globally unique `event_id`, aggregate ID/version, event type and occurrence time. Active payloads contain current attributes plus all business-valid slices known at that revision. Retired identities carry empty source keys and slices. Each nonempty attribute has a source key, rule and reason; missing attributes use explicit null-source provenance. Roles additionally retain all contributing sources.

Delivery is at least once. Consumers must deduplicate `event_id`, apply only newer aggregate versions and reconcile complete correction groups before claiming coherent crosswalks. A `correction_for` references the identity decision; it is not an instruction to reverse an invoice or order. The API exposes current goldens, source crosswalks and history through the authenticated overview/history endpoints; dbt provides the analytical table contract.

The unreleased v1 event schema also permits a separate `trace` metadata object. It links server-assigned correlation IDs with durable run, decision and event IDs; it never contributes to matching or attribute survivorship. Older events without this optional field remain readable. Consumers using an older closed-schema validator must update that validator before receiving new traced events. Technical correlation is not an authority to replay a decision or change its expected version.

Any incompatible field removal, type change, identifier meaning change or decision-policy change requires a new major contract version and an explicit migration. Additive optional fields still require consumer review because current source/operation schemas intentionally reject unknown fields. No user-controlled object name, column, operation, rule expression or SQL text is executed. Snowflake object identifiers are separately restricted to the reviewed simple-identifier grammar.
