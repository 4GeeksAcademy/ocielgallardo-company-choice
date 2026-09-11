-- HealthCore reporting schema for Monthly Clinic Supply Performance (Part 2).
-- Destination for the business KPI pipeline — never write back to telemetry_events.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS reporting;

CREATE TABLE IF NOT EXISTS reporting.monthly_clinic_supply_performance (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id text NOT NULL,
  country text NOT NULL,
  month_start date NOT NULL,
  total_supply_cost numeric NOT NULL DEFAULT 0,
  supply_consumption_count integer NOT NULL DEFAULT 0,
  critical_stockout_count integer NOT NULL DEFAULT 0,
  expiry_risk_count integer NOT NULL DEFAULT 0,
  currency text NOT NULL,
  computed_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (clinic_id, month_start)
);

CREATE TABLE IF NOT EXISTS reporting.pipeline_runs (
  run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  pipeline_name text NOT NULL DEFAULT 'monthly_clinic_supply_performance',
  month_start date,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  status text NOT NULL DEFAULT 'running',
  phase text,
  records_processed integer NOT NULL DEFAULT 0,
  records_extracted integer,
  window_start timestamptz,
  window_end timestamptz,
  error_message text,
  computed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_pipeline_runs_started_at
  ON reporting.pipeline_runs (started_at DESC);

CREATE INDEX IF NOT EXISTS ix_monthly_clinic_supply_performance_month
  ON reporting.monthly_clinic_supply_performance (month_start);
