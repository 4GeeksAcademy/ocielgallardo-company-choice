-- Durable failure records for Celery tasks that exhausted their retries.
CREATE TABLE IF NOT EXISTS task_dead_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT NOT NULL,
    task_name TEXT NOT NULL,
    attempt INTEGER NOT NULL CHECK (attempt > 0),
    error_message TEXT NOT NULL,
    payload_reference TEXT,
    failed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_task_dead_letters_task_id
    ON task_dead_letters (task_id);
