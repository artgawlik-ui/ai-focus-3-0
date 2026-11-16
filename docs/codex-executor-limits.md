# Bounded Codex executor (PR #27)

This is a per-job request gateway, not the monthly Costs API ledger.
The model activation barrier remains unchanged and the checked-in policy is
DISABLED. No production API was called to test this change.

## Enforced request path

Existing pinned codex-action / drop-sudo -> its authentication proxy (dummy
credential) -> root-owned loopback quota gateway -> fixed OpenAI Responses API.
The actual API key is read from stdin only by the privileged quota gateway.
The action and agent never receive it. Preserve the pinned action's provider,
permission and sudo protections; do not replace this with an unguarded CLI.

Only POST /responses is exposed. Redirects, environment proxies, alternate
origins, compaction, persistent conversation IDs,
media and hosted billable tools are rejected. Only local function/custom tool
definitions, including a single namespace grouping of such local tools, are
accepted. A namespace cannot contain hosted or further nested namespaces. Compatibility failures stop the session; they must
not fall back to a direct API endpoint.

Before EVERY generation, the gateway asks /v1/responses/input_tokens to count
the same explicit history, instructions and tools. Unknown/missing token
counts or an unsupported count request stop execution without generating.
max_output_tokens is imposed on the outgoing generation request, independent
of CLI config or prompt instructions. It includes the provider's total output
allowance, including reasoning tokens. service_tier is fixed to default,
store=false and truncation=disabled. Pro reasoning mode is rejected.
Explicit provider reasoning history is passed unchanged to token counting;
there is no local guess at the size of encrypted reasoning content.

Under one lock the gateway checks request count, input limit, total reserved
tokens, rolling 60-second token allowance, deadline and conservative cost.
It fsyncs a reservation BEFORE a generation POST. Reservation =
counted input + maximum output. Cost ceiling uses Decimal arithmetic, rounds
UP to nanodollars, prices all input as uncached and reserves all possible
output. A separate reviewed maximum count-endpoint fee is also reserved
and fsynced BEFORE each counting request. Both allowances share the same budget.
Unused allowance is NEVER refunded in this gateway. Errors, HTTP429,
timeouts and missing results never retry or reset this allowance.

Reaching a quota permanently stops further generation for that job. A request
already accepted by the provider can finish or remain billable after a timeout;
the full reservation remains. A wall deadline prevents new requests and closes
the local listener; it is not a provider cancellation/billing guarantee.

## Policy and activation

executor-limits.json currently sets ceilings: 2USD/job, 3 generation requests,
24,000 input tokens/request, 2,048 output tokens/request, 60,000 total reserved
tokens, 30,000 reserved tokens/rolling minute and 300 seconds. These are upper
bounds, not measured spend or assertions about the selected model's rate limit.

enabled=false and model/tariff=null deliberately prevent launch until there is
a reviewed exact model and current STANDARD/default-tier tariff. Policy review
must record official pricing URL, repository review reference, verified_at and
expires_at (at most 24 hours apart), input/output USD per million, compatible
model context/output limits, and an allowance no higher than the controller's
live private receipt and available monthly budget. The tariff must explicitly include max_count_usd_per_request (a reviewed upper
bound per counting request, or zero only with evidence that it is free). Missing
count pricing blocks launch. Verify endpoint billing/permissions and compatibility
before activation; count costs are never silently assumed to be zero.

The policy is loaded into root memory before drop-sudo; later agent edits do
not change it. The root-owned exclusive /run/focus-codex-RUN-ATTEMPT directory
prevents accidental restart/reset. Never manually restart the gateway to get
another allowance or reuse a receipt. A new action attempt requires a new
controller admission, not merely another local ledger.

The per-job quota cannot account for unrelated project/API calls, provider
pricing changes, undocumented fees or provider counting/enforcement errors.
It does not replace the private monthly 8USD gate, the 50PLN agreement or
reconciliation against real Costs API data. This change does not settle #50.

## Offline evidence and next gates

tests/automation/test_executor_limits.py uses synthetic models/prices/counts,
an injected fake provider, temporary ledgers and loopback HTTP. It covers
boundary admission, denied paid POSTs, concurrent callers, no refund after
ambiguous failures, missing counts, tariff expiry, ledger failure before POST,
deadline checks, unsupported routes/tools/history and disabled policy.

GitHub Actions runs those tests without OPENAI_API_KEY. Green synthetic tests
prove the control path under that contract, not live billing. A separate native
CLI/action job exercises the same gateway against synthetic loopback SSE, including
privilege separation and a denied second request. It never constructs OpenAI
transport or loads an API credential.
Remaining activation gates: reconcile #50 from actual Costs -> independently
read private state -> successful NEW GitHub/Render NO-MODEL round trip ->
review tariff/model/receipt binding and native action compatibility -> controlled
activation in the agreed 09:00–18:00 Europe/Warsaw window. Keep owner review.

Official contract references (consulted 2026-11-16):
- https://developers.openai.com/api/docs/guides/token-counting
- https://developers.openai.com/api/reference/resources/responses/subresources/input_tokens/methods/count
- https://developers.openai.com/api/reference/resources/responses/methods/create
- https://github.com/openai/codex-action/blob/bdf19a4a223ec2549a3e2274a0cf61556bc07675/action.yml
