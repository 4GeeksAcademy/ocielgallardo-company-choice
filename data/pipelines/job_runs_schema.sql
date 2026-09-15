-- HealthCore nightly orchestration state (Hito 22, Ticket #DEV-53).
-- Tracks the nightly_export script lifecycle: CSV backup export + pipeline trigger.
-- This table is NOT the Hito 6 ETL audit: reporting.pipeline_runs (see
-- reporting_schema.sql) keeps recording extract/transform/load internals while
-- the pipeline subprocess runs. job_runs records the orchestration layer only
-- (lock via `processing`, idempotency via (job_name, target_date)).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS job_runs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_name      TEXT NOT NULL,
  target_date   DATE NOT NULL,
  status        TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  started_at    TIMESTAMPTZ,
  finished_at   TIMESTAMPTZ,
  error_message TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Idempotency lookups: completed-for-date and live-lock checks per job.
CREATE INDEX IF NOT EXISTS ix_job_runs_job_date
  ON job_runs (job_name, target_date);
