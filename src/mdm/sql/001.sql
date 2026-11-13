CREATE TABLE source_records (
  source_key text PRIMARY KEY,
  source_system text NOT NULL CHECK (source_system IN ('ERP_ALPHA','ERP_BETA','ERP_GAMMA')),
  entity_type text NOT NULL CHECK (entity_type IN ('organization','establishment','product')),
  source_id text NOT NULL,
  current_payload jsonb NOT NULL,
  revision bigint NOT NULL CHECK (revision > 0),
  ingested_at timestamptz NOT NULL,
  UNIQUE (source_system,entity_type,source_id),
  CHECK (source_key = source_system || ':' || entity_type || ':' || source_id)
);
CREATE TABLE raw_records (
  raw_id uuid PRIMARY KEY,
  source_key text NOT NULL REFERENCES source_records(source_key),
  payload jsonb NOT NULL,
  payload_hash text NOT NULL CHECK (length(payload_hash)=64),
  effective_from timestamptz NOT NULL,
  observed_at timestamptz NOT NULL,
  UNIQUE (source_key,payload_hash)
);
CREATE INDEX raw_timeline ON raw_records(source_key,effective_from,observed_at);
CREATE FUNCTION immutable_record() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable ledger: append a correction'; END $$;
CREATE TRIGGER raw_immutable BEFORE UPDATE OR DELETE ON raw_records FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TABLE standard_records (
  source_key text PRIMARY KEY REFERENCES source_records(source_key),
  revision bigint NOT NULL,
  normalization_version text NOT NULL,
  attributes jsonb NOT NULL
);
CREATE TABLE identity_groups (
  golden_id uuid PRIMARY KEY,
  entity_type text NOT NULL CHECK (entity_type IN ('organization','establishment','product')),
  status text NOT NULL CHECK (status IN ('active','retired')),
  version bigint NOT NULL CHECK (version >= 0),
  created_at timestamptz NOT NULL
);
CREATE TABLE memberships (
  source_key text PRIMARY KEY REFERENCES source_records(source_key),
  golden_id uuid NOT NULL REFERENCES identity_groups(golden_id)
);
CREATE INDEX memberships_golden ON memberships(golden_id);
CREATE TABLE membership_history (
  history_id uuid PRIMARY KEY,
  source_key text NOT NULL REFERENCES source_records(source_key),
  golden_id uuid NOT NULL REFERENCES identity_groups(golden_id),
  known_from timestamptz NOT NULL,
  known_to timestamptz,
  CHECK (known_to IS NULL OR known_to > known_from)
);
CREATE UNIQUE INDEX one_current_membership ON membership_history(source_key) WHERE known_to IS NULL;
CREATE TABLE golden_history (
  history_id uuid PRIMARY KEY,
  golden_id uuid NOT NULL REFERENCES identity_groups(golden_id),
  group_version bigint NOT NULL CHECK (group_version > 0),
  attributes jsonb NOT NULL,
  provenance jsonb NOT NULL,
  conflicts jsonb NOT NULL,
  valid_from timestamptz NOT NULL,
  valid_to timestamptz,
  known_from timestamptz NOT NULL,
  known_to timestamptz,
  CHECK (valid_to IS NULL OR valid_to > valid_from),
  CHECK (known_to IS NULL OR known_to > known_from),
  CHECK (jsonb_typeof(attributes)='object' AND jsonb_typeof(provenance)='object'),
  UNIQUE (golden_id, group_version, valid_from)
);
CREATE INDEX golden_time ON golden_history(golden_id,known_to,valid_from,valid_to);
CREATE FUNCTION forbid_temporal_overlap() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  PERFORM pg_advisory_xact_lock(24022002);
  IF EXISTS(SELECT 1 FROM golden_history h WHERE h.golden_id=NEW.golden_id AND h.history_id<>NEW.history_id
    AND tstzrange(h.valid_from,h.valid_to,'[)') && tstzrange(NEW.valid_from,NEW.valid_to,'[)')
    AND tstzrange(h.known_from,h.known_to,'[)') && tstzrange(NEW.known_from,NEW.known_to,'[)'))
  THEN RAISE EXCEPTION 'overlapping business and knowledge intervals'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER golden_nonoverlap BEFORE INSERT OR UPDATE ON golden_history FOR EACH ROW EXECUTE FUNCTION forbid_temporal_overlap();
CREATE TABLE candidates (
  candidate_id uuid PRIMARY KEY,
  left_key text NOT NULL REFERENCES source_records(source_key),
  right_key text NOT NULL REFERENCES source_records(source_key),
  left_revision bigint NOT NULL,
  right_revision bigint NOT NULL,
  rule_version text NOT NULL,
  mode text NOT NULL CHECK(mode IN ('deterministic','hybrid')),
  evidence jsonb NOT NULL,
  disposition text NOT NULL CHECK(disposition IN ('auto','reject','review','merged','group_conflict','dismissed')),
  created_at timestamptz NOT NULL,
  UNIQUE(left_key,right_key,left_revision,right_revision,rule_version,mode),
  CHECK(left_key < right_key)
);
CREATE TABLE decisions (
  decision_id uuid PRIMARY KEY,
  idempotency_key text UNIQUE NOT NULL,
  kind text NOT NULL CHECK(kind IN ('merge','split','unmerge','automatic_merge')),
  status text NOT NULL CHECK(status IN ('pending','approved','rejected','executed')),
  version bigint NOT NULL,
  requested_by text NOT NULL,
  approved_by text,
  executed_by text,
  request jsonb NOT NULL,
  result jsonb,
  created_at timestamptz NOT NULL,
  CHECK(kind='automatic_merge' OR approved_by IS NULL OR requested_by<>approved_by),
  CHECK(kind='automatic_merge' OR executed_by IS NULL OR (executed_by<>requested_by AND executed_by<>approved_by))
);
CREATE TABLE decision_events (
  event_id uuid PRIMARY KEY,
  decision_id uuid NOT NULL REFERENCES decisions(decision_id),
  actor text NOT NULL,
  transition text NOT NULL,
  payload jsonb NOT NULL,
  occurred_at timestamptz NOT NULL
);
CREATE TRIGGER decisions_audit_immutable BEFORE UPDATE OR DELETE ON decision_events FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TABLE outbox (
  event_id uuid PRIMARY KEY,
  aggregate_id uuid NOT NULL REFERENCES identity_groups(golden_id),
  aggregate_version bigint NOT NULL,
  event_type text NOT NULL CHECK(event_type IN ('golden.changed','golden.retired')),
  payload jsonb NOT NULL,
  occurred_at timestamptz NOT NULL,
  UNIQUE(aggregate_id,aggregate_version)
);
CREATE TRIGGER outbox_immutable BEFORE UPDATE OR DELETE ON outbox FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TABLE consumer_inbox (
  consumer text NOT NULL,
  event_id uuid NOT NULL REFERENCES outbox(event_id),
  processed_at timestamptz NOT NULL,
  PRIMARY KEY(consumer,event_id)
);
CREATE TABLE consumer_records (
  consumer text NOT NULL,
  golden_id uuid NOT NULL,
  group_version bigint NOT NULL,
  payload jsonb NOT NULL,
  active boolean NOT NULL,
  PRIMARY KEY(consumer,golden_id)
);
CREATE TABLE consumer_crosswalk (
  consumer text NOT NULL,
  source_key text NOT NULL,
  golden_id uuid NOT NULL,
  PRIMARY KEY(consumer,source_key)
);
CREATE TABLE runs (
  run_id uuid PRIMARY KEY,
  idempotency_key text NOT NULL UNIQUE,
  input_hash text NOT NULL,
  status text NOT NULL CHECK(status IN ('running','succeeded','degraded','failed')),
  phase text NOT NULL,
  attempts integer NOT NULL DEFAULT 1 CHECK(attempts <= 3),
  result jsonb NOT NULL DEFAULT '{}',
  started_at timestamptz NOT NULL,
  finished_at timestamptz
);
CREATE TABLE run_sources (
  run_id uuid NOT NULL REFERENCES runs(run_id),
  source_system text NOT NULL,
  status text NOT NULL CHECK(status IN ('succeeded','unavailable')),
  accepted integer NOT NULL,
  PRIMARY KEY(run_id,source_system)
);
