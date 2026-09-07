-- HealthCore telemetry_events — append-only storage for ingested batches.
-- Events are immutable facts: no UPDATE or DELETE application paths.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS telemetry_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id    TEXT NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL,
    event_type  TEXT NOT NULL,
    service     TEXT NOT NULL DEFAULT 'backoffice',
    user_id     TEXT NOT NULL,
    session_id  TEXT,
    tags        JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Analytical indexes
CREATE INDEX IF NOT EXISTS ix_telemetry_events_timestamp
    ON telemetry_events (timestamp);

CREATE INDEX IF NOT EXISTS ix_telemetry_events_event_type
    ON telemetry_events (event_type);

CREATE INDEX IF NOT EXISTS ix_telemetry_events_tags
    ON telemetry_events USING GIN (tags);

-- Enforce immutability for typical application roles (adjust role names as needed).
-- Superuser / table owner may still bypass; application code must never UPDATE/DELETE.
REVOKE UPDATE, DELETE ON telemetry_events FROM PUBLIC;
