#!/bin/sh
set -eu
if python -c 'import sys; from backend.google_transport import schema; sys.exit(0 if schema() else 1)'; then
  alembic -c google-alembic.ini upgrade head
else
  alembic upgrade head
fi
if [ -n "${BOOTSTRAP_EMAIL:-}" ]; then python -m scripts.bootstrap; fi
exec python -m scripts.supervise
