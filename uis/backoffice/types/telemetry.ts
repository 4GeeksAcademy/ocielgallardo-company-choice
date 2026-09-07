/** Operational telemetry report payload from GET /telemetry/report. */

export interface TelemetryReportPeriod {
  from: string;
  to: string;
}

export interface EventsPerDayRow {
  date: string;
  count: number;
}

export interface ErrorRateByTypeRow {
  date: string;
  event_type: string;
  error_count: number;
  total_count: number;
  rate: number;
}

export interface AvgLatencyByPathRow {
  date: string;
  path: string;
  avg_duration_ms: number;
  sample_count: number;
}

export interface AuthFailureRateRow {
  date: string;
  failed: number;
  succeeded: number;
  total_attempts: number;
  rate: number;
}

export interface TelemetryReportMetrics {
  events_per_day: EventsPerDayRow[];
  error_rate_by_type: ErrorRateByTypeRow[];
  avg_latency_by_path: AvgLatencyByPathRow[];
  auth_failure_rate: AuthFailureRateRow[];
}

export interface TelemetryReport {
  period: TelemetryReportPeriod;
  metrics: TelemetryReportMetrics;
}
