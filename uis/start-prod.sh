#!/bin/sh
set -eu

shutdown() {
  echo "Stopping Next.js production servers..."
  kill -TERM "$WEBSITE_PID" "$BACKOFFICE_PID" 2>/dev/null || true
  wait "$WEBSITE_PID" "$BACKOFFICE_PID" 2>/dev/null || true
  exit 0
}

trap shutdown INT TERM

cd /app/uis/website
npm run start -- -H 0.0.0.0 -p 3000 &
WEBSITE_PID=$!

cd /app/uis/backoffice
npm run start -- -H 0.0.0.0 -p 3001 &
BACKOFFICE_PID=$!

wait "$WEBSITE_PID" "$BACKOFFICE_PID"
