#!/bin/sh
set -eu
alembic upgrade head
if [ -n "${BOOTSTRAP_EMAIL:-}" ]; then python -m scripts.bootstrap; fi
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="${TRUSTED_PROXY_IPS:-127.0.0.1}"
