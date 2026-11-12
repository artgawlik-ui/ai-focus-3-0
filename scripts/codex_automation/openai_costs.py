"""Read-only OpenAI organization costs client. Never logs credentials or raw responses."""
import json
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ENDPOINT = "https://api.openai.com/v1/organization/costs"


class CostsUnavailable(RuntimeError):
    pass


def read_project_costs(*, admin_key: str, project_id: str, month_start: int,
                       now: datetime, opener=urlopen) -> tuple[Decimal, datetime]:
    """Return (USD cost, latest completed bucket end). Fail closed on ambiguity.

    API may lag behind incurred charges. Do NOT treat this alone as a hard cap.
    """
    if not admin_key or not project_id.startswith("proj_"):
        raise CostsUnavailable("CREDENTIALS_OR_PROJECT_MISSING")
    if now.tzinfo is None or now.utcoffset() is None:
        raise CostsUnavailable("TIMEZONE_REQUIRED")
    total = Decimal("0")
    cursor = None
    latest_end = 0
    seen = set()
    while True:
        params = {"start_time": month_start, "end_time": int(now.timestamp()),
                  "bucket_width": "1d", "group_by": ["project_id"], "limit": 31}
        if cursor:
            params["page"] = cursor
        url = ENDPOINT + "?" + urlencode(params, doseq=True)
        request = Request(url, headers={"Authorization": "Bearer " + admin_key,
                                       "Accept": "application/json"}, method="GET")
        try:
            with opener(request, timeout=15) as response:
                data = json.load(response)
        except Exception:
            raise CostsUnavailable("COSTS_API_UNAVAILABLE") from None
        if not isinstance(data.get("data"), list):
            raise CostsUnavailable("INVALID_COSTS_RESPONSE")
        for bucket in data["data"]:
            end = bucket.get("end_time")
            if not isinstance(end, int) or end > int(now.timestamp()):
                raise CostsUnavailable("INCOMPLETE_BUCKET")
            latest_end = max(latest_end, end)
            for result in bucket.get("results", []):
                if result.get("project_id") != project_id:
                    continue
                amount = result.get("amount", {})
                if amount.get("currency") != "usd":
                    raise CostsUnavailable("INVALID_CURRENCY")
                value = Decimal(str(amount.get("value")))
                if not value.is_finite() or value < 0:
                    raise CostsUnavailable("INVALID_AMOUNT")
                total += value
        cursor = data.get("next_page")
        if not cursor:
            break
        if cursor in seen or len(seen) > 50:
            raise CostsUnavailable("PAGINATION_FAILURE")
        seen.add(cursor)
    if not latest_end:
        raise CostsUnavailable("NO_COMPLETED_BUCKET")
    observed = datetime.fromtimestamp(latest_end, timezone.utc)
    if (now - observed).total_seconds() > 86400:
        raise CostsUnavailable("STALE_COSTS")
    return total, observed
