#!/bin/sh
set -eu
alembic upgrade head
if [ -n "${BOOTSTRAP_EMAIL:-}" ]; then python -m scripts.bootstrap; fi
exec python -m scripts.supervise
