#!/bin/sh
set -eu
if python -c 'import sys; from backend.native_planning import schema_enabled; sys.exit(0 if schema_enabled() else 1)'; then
  if python -c 'import sys; from backend.google_transport import schema; sys.exit(0 if schema() else 1)'; then echo 'Separate schema profiles require an approved migration plan' >&2; exit 1; fi
  alembic -c native-alembic.ini upgrade head
elif python -c 'import sys; from backend.google_transport import schema; sys.exit(0 if schema() else 1)'; then
  alembic -c google-alembic.ini upgrade head
else
  alembic upgrade head
fi
if [ -n "${BOOTSTRAP_EMAIL:-}" ]; then python -m scripts.bootstrap; fi
exec python -m scripts.supervise
