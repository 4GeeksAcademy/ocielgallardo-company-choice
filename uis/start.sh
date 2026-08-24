#!/bin/sh
set -eu

shutdown() {
  echo "Stopping Next.js apps..."
  kill -TERM "$BACKOFFICE_PID" "$WEBSITE_PID" 2>/dev/null || true
  wait "$BACKOFFICE_PID" "$WEBSITE_PID" 2>/dev/null || true
  exit 0
}

trap shutdown INT TERM

cd /app/uis/backoffice
HOSTNAME=0.0.0.0 PORT=3000 npm run start &
BACKOFFICE_PID=$!

cd /app/uis/website
HOSTNAME=0.0.0.0 PORT=3001 npm run start &
WEBSITE_PID=$!

wait "$BACKOFFICE_PID" "$WEBSITE_PID"
