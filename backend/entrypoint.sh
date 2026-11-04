#!/bin/sh
set -e

echo "Applying database migrations..."
alembic upgrade head

if [ "${SEED_DEMO_DATA:-true}" = "true" ]; then
  echo "Seeding demo data (skipped if already present)..."
  python seed.py
fi

exec "$@"
