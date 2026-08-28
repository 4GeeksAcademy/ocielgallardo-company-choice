#!/bin/sh
set -eu

# Website on 3000, backoffice on 3001 (Ticket #infra-40).
# Prefer hot-reload for local Docker development.

shutdown() {
  echo "Stopping Next.js apps..."
  kill -TERM "$WEBSITE_PID" "$BACKOFFICE_PID" 2>/dev/null || true
  wait "$WEBSITE_PID" "$BACKOFFICE_PID" 2>/dev/null || true
  exit 0
}

trap shutdown INT TERM

cd /app/uis/website
HOSTNAME=0.0.0.0 PORT=3000 npm run dev &
WEBSITE_PID=$!

cd /app/uis/backoffice
HOSTNAME=0.0.0.0 PORT=3001 npm run dev &
BACKOFFICE_PID=$!

wait "$WEBSITE_PID" "$BACKOFFICE_PID"
