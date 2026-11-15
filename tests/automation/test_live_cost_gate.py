"""Synthetic Costs API responses and mocked DB: no network, paid API or secrets."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO, StringIO
import json
from pathlib import Path
from unittest.mock import Mock, patch
from contextlib import redirect_stderr

import pytest

from scripts.codex_automation import live_cost_gate as gate
from scripts.codex_automation.openai_costs import read_project_costs, CostsUnavailable

NOW = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
ENV = {"OPENAI_COSTS_ADMIN_KEY": "synthetic-only", "OPENAI_PROJECT_ID": "proj_test"}


class Response(BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


def page(amount="0.03", **changes):
    result = {"data": [{"end_time": int((NOW-timedelta(hours=1)).timestamp()),
                "results": [{"project_id": "proj_test", "amount": {"currency": "usd", "value": amount}}]}],
              "has_more": False, "next_page": None}
    result.update(changes)
    return result


def read_pages(pages, requests=None):
    pages = iter(pages)
    def opener(request, timeout):
        if requests is not None:
            requests.append(request)
        item = next(pages)
        if isinstance(item, Exception):
            raise item
        return Response(json.dumps(item).encode())
    return read_project_costs(admin_key="synthetic-only", project_id="proj_test",
                             month_start=int(NOW.replace(day=1,hour=0).timestamp()), now=NOW, opener=opener)


def test_project_filtered_authenticated_get_and_pagination_sum():
    requests = []
    spend, _ = read_pages([page("0.03", has_more=True, next_page="next"), page("0.07")], requests)
    assert spend == Decimal("0.10")
    assert all(r.get_method() == "GET" for r in requests)
    assert all("project_ids=proj_test" in r.full_url for r in requests)
    assert "page=next" in requests[1].full_url
    assert all(r.get_header("Authorization") == "Bearer synthetic-only" for r in requests)


@pytest.mark.parametrize("response", [
    page(has_more=True, next_page=None), page(has_more=False, next_page="bad"),
    page(has_more="false"), {"data": None}, [],
    page(data=[{"end_time": True, "results": []}]),
    page(data=[{"end_time": int(NOW.timestamp())+1,"results": []}]),
    page(data=[{"end_time": int(NOW.timestamp()),"results": None}]),
    page(data=[{"end_time": int(NOW.timestamp()),"results": [{"project_id": None}]}]),
    page("NaN"), page("-1"), page("not-money"),
])
def test_ambiguous_or_malformed_provider_data_blocks(response):
    with pytest.raises(CostsUnavailable):
        read_pages([response])


def test_pagination_failure_after_first_page_does_not_return_partial_spend():
    with pytest.raises(CostsUnavailable, match="COSTS_API_UNAVAILABLE"):
        read_pages([page(has_more=True,next_page="next"), OSError("synthetic secret and response")])


def test_missing_credentials_does_not_read_provider():
    reader = Mock()
    with pytest.raises(gate.CostGateBlocked, match="COSTS_CREDENTIALS_REQUIRED"):
        gate.check_live_costs(env={}, now=NOW, reader=reader)
    reader.assert_not_called()


@pytest.mark.parametrize("spend,observed", [
    (Decimal("6.01"), NOW), (Decimal("NaN"), NOW), (Decimal("-1"), NOW),
    (Decimal("0.03"), NOW-timedelta(days=2)),
    (Decimal("0.03"), NOW+timedelta(seconds=1)),
    (Decimal("0.03"), NOW.replace(tzinfo=None)),
])
def test_budget_or_stale_observation_never_reserves(spend, observed):
    with patch.object(gate,"reserve_transaction") as reserve:
        with pytest.raises(gate.CostGateBlocked):
            gate.reserve_approved_task(Mock(), authorize=lambda: True, issue=28,
                reservation_id="synthetic",env=ENV,now=NOW,reader=lambda **kw:(spend,observed))
        reserve.assert_not_called()


def test_unapproved_task_does_not_read_provider_or_reserve():
    reader = Mock()
    with patch.object(gate,"reserve_transaction") as reserve:
        with pytest.raises(gate.CostGateBlocked,match="TASK_AUTHORIZATION_REQUIRED"):
            gate.reserve_approved_task(Mock(),authorize=lambda:False,issue=28,
                reservation_id="synthetic",env=ENV,now=NOW,reader=reader)
        reader.assert_not_called()
        reserve.assert_not_called()


def test_real_observation_is_passed_to_existing_serialized_reservation():
    conn=Mock()
    reader=Mock(return_value=(Decimal("0.03"),NOW-timedelta(hours=1)))
    with patch.object(gate,"reserve_transaction") as reserve:
        observation=gate.reserve_approved_task(conn,authorize=lambda:True,issue=28,
            reservation_id="synthetic",env=ENV,now=NOW,reader=reader)
        reserve.assert_called_once_with(conn,month="2026-11",issue=28,
            provider_spend=Decimal("0.03"),reservation_id="synthetic",provider_verified=True)
    assert observation.billing_month=="2026-11"
    assert reader.call_args.kwargs["month_start"]==int(NOW.replace(day=1,hour=0).timestamp())


def test_provider_error_is_sanitized_before_cli_output():
    output=StringIO()
    with patch.dict("os.environ",ENV,clear=True), patch.object(gate,"read_project_costs",side_effect=RuntimeError("SYNTHETIC_SECRET")), redirect_stderr(output):
        assert gate.main(["check"])==1
    assert output.getvalue()=="BLOCKED: COSTS_UNAVAILABLE\n"


def test_workflow_cost_check_precedes_paid_action_and_key_is_step_scoped():
    workflow=(Path(__file__).resolve().parents[2]/".github/workflows/codex-issues.yml").read_text()
    codex=workflow.split("  codex:\n",1)[1].split("  publish:\n",1)[0]
    assert codex.index("live_cost_gate.py check")<codex.index("uses: openai/codex-action@")
    assert "group: focus-codex-paid-executor" in codex
    before_action,action=codex.split("      - name: Real Codex executor",1)
    assert "OPENAI_COSTS_ADMIN_KEY: ${{ secrets.OPENAI_COSTS_ADMIN_KEY }}" in before_action
    assert "OPENAI_COSTS_ADMIN_KEY" not in action
    assert "environment: codex-development" in codex
    assert "contents: read" in codex and "contents: write" not in codex
