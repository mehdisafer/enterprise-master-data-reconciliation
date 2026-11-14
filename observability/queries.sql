-- Run with a read-only monitoring role. These queries do not modify state.
-- Consumer names are explicit contractual consumers, including ones never started.

-- Per-source receipt freshness; this is observation time, not business validity.
SELECT source_system, count(*) AS source_records, max(ingested_at) AS last_observed_at
FROM public.source_records
GROUP BY source_system
ORDER BY source_system;

-- A never-started reporting consumer must still report all pending events.
WITH expected_consumers(consumer) AS (VALUES ('reporting'))
SELECT c.consumer,
       count(o.event_id) FILTER (WHERE i.event_id IS NULL) AS pending_events,
       coalesce(extract(epoch FROM current_timestamp - min(o.occurred_at)
           FILTER (WHERE i.event_id IS NULL)), 0) AS oldest_pending_seconds
FROM expected_consumers c
LEFT JOIN public.outbox o ON true
LEFT JOIN public.consumer_inbox i ON i.consumer = c.consumer AND i.event_id = o.event_id
GROUP BY c.consumer;

-- Human review age and requested/approved decisions waiting for their next actor.
SELECT status, kind, count(*) AS decisions,
       extract(epoch FROM current_timestamp - min(created_at)) AS oldest_seconds
FROM public.decisions
WHERE status IN ('pending', 'approved')
GROUP BY status, kind
ORDER BY status, kind;

-- Runs that need investigation. A running row is not evidence of a live lease.
SELECT run_id, status, phase, attempts, started_at, finished_at
FROM public.runs
WHERE status IN ('failed', 'degraded')
   OR (status = 'running' AND started_at < current_timestamp - interval '10 minutes')
ORDER BY started_at;

-- Storage and history growth. Relation sizes include indexes and TOAST.
SELECT c.relname AS object_name, pg_total_relation_size(c.oid) AS total_bytes,
       s.n_live_tup AS approximate_live_rows, s.n_dead_tup AS approximate_dead_rows
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY total_bytes DESC;

-- Invariant failures must be zero; missing provenance is not a mere availability alert.
SELECT count(*) AS attributes_without_provenance
FROM public.golden_history h
CROSS JOIN LATERAL jsonb_each(h.attributes) AS a
WHERE NOT (h.provenance ? a.key)
   OR (a.value NOT IN ('null'::jsonb, '[]'::jsonb)
       AND NOT coalesce(h.provenance -> a.key ? 'source_key', false));

-- Expected-consumer source references must equal the current reference after drain.
SELECT count(*) AS reporting_crosswalk_mismatches
FROM public.memberships m
FULL JOIN (SELECT source_key, golden_id FROM public.consumer_crosswalk WHERE consumer = 'reporting') c
  ON c.source_key = m.source_key
WHERE m.golden_id IS DISTINCT FROM c.golden_id;

-- Latest durable business correlations. Values are opaque IDs, not record bodies.
-- The same trace is preserved inside the versioned Snowflake snapshot document.
SELECT o.event_id, o.aggregate_id, o.aggregate_version,
       o.payload->'trace'->>'correlation_id' AS producer_correlation_id,
       o.payload->'trace'->>'origin_correlation_id' AS origin_correlation_id,
       o.payload->'trace'->>'run_id' AS run_id,
       o.payload->>'correction_for' AS decision_id,
       i.consumer, i.processed_at
FROM public.outbox o
LEFT JOIN public.consumer_inbox i ON i.event_id = o.event_id
ORDER BY o.occurred_at DESC, o.event_id, i.consumer
LIMIT 100;

-- Each transition records its own HTTP/CLI correlation while retaining the origin.
SELECT decision_id, event_id, transition, occurred_at,
       payload->'trace'->>'correlation_id' AS transition_correlation_id,
       payload->'trace'->>'origin_correlation_id' AS origin_correlation_id
FROM public.decision_events
ORDER BY occurred_at DESC, event_id
LIMIT 100;
