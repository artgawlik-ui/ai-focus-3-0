"""Authenticated cost preflight, shared by the executor and private controller.

CLI `check` performs only a GET to Costs API. It never starts a model or creates
a reservation. Missing credentials, ambiguous/stale costs and insufficient room
for the existing reservation amount fail closed, with fixed reason codes.
The private controller may call reserve_approved_task after its own authorization.
Costs API can lag; this preflight is not a per-task hard spending cap.
"""
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
import sys

try:
    from .openai_costs import CostsUnavailable, read_project_costs
    from .durable_reservations import CAP, RESERVE, reserve_transaction
except ImportError:
    from openai_costs import CostsUnavailable, read_project_costs
    from durable_reservations import CAP, RESERVE, reserve_transaction


class CostGateBlocked(RuntimeError):
    """Messages are fixed safe codes, never credentials or provider responses."""


@dataclass(frozen=True)
class CostObservation:
    spend_usd: Decimal
    covered_until: datetime
    billing_month: str


def check_live_costs(*, env=None, now=None, reader=None):
    env = os.environ if env is None else env
    now = datetime.now(timezone.utc) if now is None else now
    reader = read_project_costs if reader is None else reader
    key = env.get("OPENAI_COSTS_ADMIN_KEY", "")
    project = env.get("OPENAI_PROJECT_ID", "")
    if not key or not project:
        raise CostGateBlocked("COSTS_CREDENTIALS_REQUIRED")
    if now.tzinfo is None or now.utcoffset() is None:
        raise CostGateBlocked("UTC_CLOCK_REQUIRED")
    now = now.astimezone(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    try:
        spend, covered_until = reader(admin_key=key, project_id=project,
                                     month_start=int(month_start.timestamp()), now=now)
    except CostsUnavailable as exc:
        code = "COSTS_RATE_LIMITED" if str(exc) == "COSTS_RATE_LIMITED" else "COSTS_UNAVAILABLE"
        raise CostGateBlocked(code) from None
    except Exception:
        raise CostGateBlocked("COSTS_UNAVAILABLE") from None
    if (not isinstance(spend, Decimal) or not spend.is_finite() or spend < 0 or
        not isinstance(covered_until, datetime) or covered_until.tzinfo is None or
        covered_until.utcoffset() is None):
        raise CostGateBlocked("INVALID_COST_OBSERVATION")
    if not month_start <= covered_until <= now or (now-covered_until).total_seconds() > 86400:
        raise CostGateBlocked("STALE_COST_OBSERVATION")
    if spend + RESERVE > CAP:
        raise CostGateBlocked("MONTHLY_BUDGET")
    return CostObservation(spend, covered_until, now.strftime("%Y-%m"))


def reserve_approved_task(conn, *, authorize, issue, reservation_id, env=None, now=None, reader=None):
    """Use only after the controller supplies a real authorization callback.

    False/failed authorization or failed live costs means no reservation. Pending
    reservations are checked inside the existing serialized Postgres transaction.
    This function grants no GitHub/Environment permission and starts no executor.
    """
    try:
        approved = authorize()
    except Exception:
        raise CostGateBlocked("TASK_AUTHORIZATION_REQUIRED") from None
    if approved is not True:
        raise CostGateBlocked("TASK_AUTHORIZATION_REQUIRED")
    observation = check_live_costs(env=env, now=now, reader=reader)
    reserve_transaction(conn, month=observation.billing_month, issue=issue,
                        provider_spend=observation.spend_usd,
                        reservation_id=reservation_id, provider_verified=True)
    return observation


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check"])
    parser.parse_args(argv)
    try:
        observation = check_live_costs()
    except CostGateBlocked as exc:
        print("BLOCKED: " + str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("BLOCKED: COST_CONTROL_FAILURE", file=sys.stderr)
        return 1
    print(json.dumps({"status": "PASS", "billing_month": observation.billing_month,
                      "provider_spend_usd": str(observation.spend_usd),
                      "covered_until": observation.covered_until.isoformat(),
                      "monthly_cap_usd": str(CAP), "reservation_usd": str(RESERVE)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
