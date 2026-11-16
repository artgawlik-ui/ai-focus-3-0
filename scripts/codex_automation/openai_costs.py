"""Read-only OpenAI organization costs client. Never logs credentials or raw responses."""
import json
from email.utils import parsedate_to_datetime
from math import ceil
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener

ENDPOINT = "https://api.openai.com/v1/organization/costs"


class CostsUnavailable(RuntimeError):
    def __init__(self, code, *, retry_after_seconds=None):
        super().__init__(code)
        self.retry_after_seconds = retry_after_seconds


def retry_delay(value, now):
    """Bounded Retry-After seconds/date; raw provider fields never leave here."""
    fallback, maximum = 900, 86400
    if (not isinstance(value, str) or len(value) > 128 or
        any(ord(c) < 32 or ord(c) == 127 for c in value)):
        return fallback
    value = value.strip()
    try:
        if re.fullmatch(r'[0-9]{1,9}', value):
            seconds = int(value)
        else:
            until = parsedate_to_datetime(value)
            if until.utcoffset() is None:
                return fallback
            seconds = ceil((until-now).total_seconds())
        return max(fallback, min(seconds, maximum))
    except (ValueError, TypeError, OverflowError):
        return fallback


class RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # An administrative credential must never follow a provider redirect.
        return None


def read_project_costs(*, admin_key: str, project_id: str, month_start: int,
                       now: datetime, opener=None) -> tuple[Decimal, datetime]:
    """Return (USD cost, latest completed bucket end). Fail closed on ambiguity.

    API may lag behind incurred charges. Do NOT treat this alone as a hard cap.
    """
    if (not isinstance(admin_key, str) or not admin_key or
        not isinstance(project_id, str) or not re.fullmatch(r"proj_[A-Za-z0-9_-]+", project_id)):
        raise CostsUnavailable("CREDENTIALS_OR_PROJECT_MISSING")
    if now.tzinfo is None or now.utcoffset() is None:
        raise CostsUnavailable("TIMEZONE_REQUIRED")
    if type(month_start) is not int or not 0 <= month_start < int(now.timestamp()):
        raise CostsUnavailable("INVALID_TIME_RANGE")
    opener = build_opener(RejectRedirect()).open if opener is None else opener
    total = Decimal("0")
    cursor = None
    latest_end = 0
    seen = set()
    while True:
        params = {"start_time": month_start, "end_time": int(now.timestamp()),
                  "bucket_width": "1d", "group_by": ["project_id"],
                  "project_ids": [project_id], "limit": 31}
        if cursor:
            params["page"] = cursor
        url = ENDPOINT + "?" + urlencode(params, doseq=True)
        request = Request(url, headers={"Authorization": "Bearer " + admin_key,
                                       "Accept": "application/json"}, method="GET")
        try:
            with opener(request, timeout=15) as response:
                data = json.load(response, parse_float=Decimal)
        except HTTPError as exc:
            code = "COSTS_RATE_LIMITED" if exc.code == 429 else "COSTS_API_UNAVAILABLE"
            delay = retry_delay(exc.headers.get('Retry-After') if exc.headers else None, now) if exc.code == 429 else None
            raise CostsUnavailable(code, retry_after_seconds=delay) from None
        except Exception:
            raise CostsUnavailable("COSTS_API_UNAVAILABLE") from None
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise CostsUnavailable("INVALID_COSTS_RESPONSE")
        for bucket in data["data"]:
            if not isinstance(bucket, dict):
                raise CostsUnavailable("INVALID_COSTS_RESPONSE")
            end = bucket.get("end_time")
            if type(end) is not int or end > int(now.timestamp()) or end <= month_start:
                raise CostsUnavailable("INCOMPLETE_BUCKET")
            latest_end = max(latest_end, end)
            if not isinstance(bucket.get("results"), list):
                raise CostsUnavailable("INVALID_COSTS_RESPONSE")
            for result in bucket["results"]:
                if not isinstance(result, dict):
                    raise CostsUnavailable("INVALID_COSTS_RESPONSE")
                if result.get("project_id") != project_id:
                    # Filtering + grouping must identify this project unambiguously.
                    raise CostsUnavailable("UNEXPECTED_PROJECT")
                amount = result.get("amount", {})
                if not isinstance(amount, dict) or amount.get("currency") != "usd":
                    raise CostsUnavailable("INVALID_CURRENCY")
                try:
                    value = Decimal(str(amount.get("value")))
                except InvalidOperation:
                    raise CostsUnavailable("INVALID_AMOUNT") from None
                if not value.is_finite() or value < 0:
                    raise CostsUnavailable("INVALID_AMOUNT")
                total += value
        more, cursor = data.get("has_more"), data.get("next_page")
        if type(more) is not bool or (more and (not isinstance(cursor, str) or not cursor)):
            raise CostsUnavailable("INVALID_PAGINATION")
        if not more:
            if cursor is not None:
                raise CostsUnavailable("INVALID_PAGINATION")
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
