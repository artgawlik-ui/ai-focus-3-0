# Live cost control — activation runbook

## Scope and limits

`live_cost_gate.py check` performs authenticated, project-filtered GET requests to
OpenAI Costs API. It is inserted before the paid Codex action, within the existing
review-protected job, with the cost credential scoped to that step. Paid jobs are
serialized. Existing owner review and read-only agent permissions remain intact.

`reserve_approved_task()` connects the same authenticated observation to the
existing serialized PostgreSQL reservation, after a supplied controller authorization
callback. This is an interface for the private controller, not a public API and not
an authorization substitute. The GitHub runner cannot reach the private database:
this change does **not** claim to bridge GitHub admission to Render/PostgreSQL.

The read check is not a per-task hard cap and is not proof of available prepaid
credit. Costs API reporting may lag. The observed provider project hard limit,
the overall 50 PLN/month mandate, pending reservations and reconciliation must all
remain enforced separately. Do not mark the paid pilot READY from this PR alone.

## Credentials and configuration

- `OPENAI_COSTS_ADMIN_KEY`: a separate administrative key limited to Usage API read
  when supported by the account. Never reuse the model/executor project key.
- `OPENAI_PROJECT_ID`: the confirmed API project identifier, supplied as a variable.
- GitHub: the key is an environment secret in `codex-development`, not a repository
  variable, task artifact, prompt or model input. Keep the required owner reviewer.
- Render: supply the separate cost credential through the existing worker's secret
  environment only if validating this controller there. Never copy the executor key.
- Do not print keys or raw API errors. The CLI prints fixed blocking codes or a
  sanitized numeric observation. Redirects are rejected to avoid forwarding credentials.

Official endpoint and request schema:
https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/costs

## Verification sequence

1. Review the exact commit and CI; this is a dependent PR based on #43, not main.
2. The owner creates the new restricted credential and enters it directly into
   secret storage. No credential should pass through chat, GitHub comments or code.
3. Deploy the candidate only to the existing isolated worker after authorized review,
   retaining its diagnostic-and-idle start command and auto-deploy OFF.
4. In that worker's Shell run:
   `python scripts/codex_automation/live_cost_gate.py check`.
   Missing credential, denied API, stale/incomplete buckets, bad pagination, ambiguous
   attribution/currency or insufficient budget must return nonzero. Do not replace
   a failed API response with a manually typed spend or a dashboard screenshot.
5. Compare the successful authenticated month-to-date observation with the project
   dashboard for the same period; record only sanitized amounts and timestamps.
6. Connect and verify the durable reservation in actual executor admission and its
   post-execution reconciliation. Until then, the overall paid pilot remains BLOCKED.
7. Install the reviewed workflow on main only through the authorized release process.
   Merely creating this PR does not change the running GitHub workflow.

## Evidence from this change

Local tests use synthetic responses and mocked connections. No model call, real cost
read, new credential or production database operation is implied by their PASS.
Current account inspection found no administrative API key. Therefore the live read
remains BLOCKED pending secure credential entry and subsequent runtime verification.
