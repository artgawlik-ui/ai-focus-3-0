# Controlled installation of the private budget controller

Status: reviewed candidate preparation; no merge, installation or paid activation.
This runbook complements `private-transport.md`, not an automatic deployment order.

## Verified starting point

The existing isolated Render worker remains on #44 (`0862b912`), one instance,
auto-deploy OFF and diagnostic-and-idle. It has the private budget DB and the
restricted Costs API read key. Runtime presence checks confirmed the separate
GitHub controller key and pinned main SHA are absent, and transport is OFF.
The production CRM is a separate service and is outside this installation.

The dependent PR chain is not installed on main:

| PR | Source branch | Target branch |
| --- | --- | --- |
| #43 | feat/private-worker-preflight-20261115 | security/private-worker-dsn-20261115 |
| #44 | feat/live-cost-executor-gate-20261116 | feat/private-worker-preflight-20261115 |
| #45 | feat/private-execution-lifecycle-20261116 | feat/live-cost-executor-gate-20261116 |
| #46 | feat/github-private-budget-transport-20261116 | feat/private-execution-lifecycle-20261116 |

Do not assume merging #46 alone updates main. Before installation, prepare one
reviewable automation-only integration branch against the then-current main,
containing the reviewed workflow, automation scripts, tests and runbooks. Exclude
CRM/backend/frontend application changes, production migrations and Render YAML.
Resolve any upstream automation differences explicitly, without force-push.
Run policy and full CI on that final integration SHA. Obtain the required release
authorization before installing that reviewed version on main.

## One owner-only credential step

Prepare a fine-grained GitHub PAT for `ai-focus-3-0` only, with the exact permissions
listed in `private-transport.md` and short expiry. The owner completes credential
creation and pastes it directly into the existing worker's protected environment
as `FOCUS_BUDGET_GITHUB_TOKEN`. No value enters chat, source, a GitHub comment,
agent prompt or screenshot. Do not export the connected app's token.
This requires the owner's account because it creates new persistent access.
Do not change an existing token's permissions or use all-repository/classic scope.
Keep transport disabled while saving this credential. Do not modify existing
database, Costs API or executor keys. Verify only the presence of the new key.

## Installation sequence after acceptance and credential entry

1. Recheck there is no active controller, paid run or in-progress deploy. Record
   exact current service/branch/start command/deploy SHA for rollback. Do not
   create another service, instance, database, scheduler or paid plan.
2. Ensure only the dedicated private budget DB is selected. Within a transaction,
   initialize the existing reservation schema and the additive #45 lifecycle
   schema. No production CRM migration or data operation is authorized here.
   If a table exists with an incompatible schema, STOP; do not ALTER blindly.
3. Install the accepted automation-only workflow on main through the authorized
   release process, retaining required owner review and the final unconditional
   `PRIVATE_ADMISSION_TRANSPORT_REQUIRED` stop before the model.
4. Pin `FOCUS_BUDGET_TRUSTED_SHA` to that exact installed main commit. It must match
   workflow-run head SHA and approved task base. Never pin only a source branch
   name or an unrelated candidate SHA. Any main change requires a new review/pin.
5. Deploy the same reviewed controller code only to the existing isolated worker,
   retaining auto-deploy OFF, current plan and one instance. Validate missing-key,
   wrong-identity and wrong-SHA cases before opt-in. Credentials remain in Render.
6. Start `github_budget_transport.py --serve` with explicit transport opt-in in
   the worker and the corresponding GitHub variable; do not enable a second
   consumer. Confirm outbound GitHub authentication as the pinned controller
   identity, DB transaction behavior and graceful stop, without running a model.
7. Use one explicitly approved, synthetic transport-smoke issue through the
   existing digest command and protected environment. Observe the real artifact,
   private durable reservation, matching receipt and runner's final forced stop.
   Verify the model step is skipped and no executor/API charge was incurred.
   This creates a conservative 2 USD bookkeeping hold, not an API charge. Keep
   its lifecycle/audit; do not delete it or recycle budget solely from a failure
   status. Assess its disposition separately after independent no-model evidence.
8. Confirm finish comes from the terminal GitHub run, cancellation retains the
   hold, and delayed Costs reporting blocks the next task. Synthetic CI is not
   evidence that this real round trip has completed.

## Paid pilot remains a separate gate

No step above removes the final model barrier. Before a paid pilot, verify current
project spend, provider project cap and credit, the overall 50 PLN mandate with
FX/tax margin, effective task limits, immutable approval, required review and
the installed controller/workflow identities. A 2 USD reservation is not a hard
per-task cap. UNKNOWN remains BLOCKED. Do not increase limits automatically.

## Stop and rollback

- Missing auth, wrong identity/SHA/repo/run, stale reporting, incompatible schema,
  network or DB errors, ambiguous delivery or duplicate execution: stop admission.
- Disable the transport flag and return the existing worker to its recorded idle
  start command/code through a controlled deploy. Do not suspend/restart the CRM.
- Keep committed reservations and lifecycle audit. Do not erase records, reset
  months, drop tables, undo schema with a destructive migration or retry a paid run.
- Restoring idle code is not evidence that an in-flight workflow stopped. Inspect
  that workflow independently and record the outcome before resuming.
