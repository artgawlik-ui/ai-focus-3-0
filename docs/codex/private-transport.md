# Outbound private budget transport — candidate, disabled

This dependent change builds on #45. It does not activate the paid executor, merge
workflows, change Render settings, create a credential or expose PostgreSQL.

## Protocol

1. The existing protected `codex` job runs only after its required environment
   approval. Trusted admission outputs supply issue, digest and base. `request`
   creates a fresh nonce and one `request.json` Actions artifact. It contains no
   credentials, prompts or customer records. Downloaded agent snapshots cannot
   supply approval metadata.
2. The existing private worker initiates outbound HTTPS requests to GitHub. It
   reads only the named request artifact for a running first-attempt workflow.
   ZIP content is bounded and parsed as data; nothing is extracted or executed.
   Authenticated artifact redirects never forward GitHub authorization to asset
   storage. Unexpected domains or further redirects fail closed.
3. Before reservation, it verifies the fixed repository/workflow, exact reviewed
   main SHA pinned in its own environment, actor and rerun actor permissions,
   live issue content, original approval comment, issue branch claim and required
   owner environment review configuration. A request older than 15 minutes from
   run start is rejected; delayed environment approval may require a new explicit
   task instead of automatic retry. First-attempt only is intentional.
4. The private PostgreSQL lifecycle commits the reservation and immutable task
   identity before the controller posts a success commit status. Receipt context
   binds run, attempt and all 256 nonce bits. The GitHub job uses a 120s deadline
   (plus a possible in-flight HTTP timeout of 20s) for
   that exact status, target URL, description and pinned controller user. It never
   accepts a combined CI success, another run's context or github-actions[bot].
5. A failed/lost receipt leaves the reservation intact; repeat delivery cannot
   create another hold or issue another success receipt. Timeout is BLOCKED,
   never a fallback executor. This conservative design needs operator diagnosis
   for ambiguous delivery; it does not silently retry a paid task.
6. The controller observes the terminal GitHub run to record finish after a crash
   or cancellation. A local agent report is not finish evidence. It records the
   observation time conservatively. Costs reporting must cover that time before
   reconciliation; full allowances remain charged after settlement as in #45.
7. `--serve` polls on the existing worker, stopping on SIGTERM/SIGINT. It keeps
   committed holds through process death, backs off on failures and closes each
   database connection. It never invokes a model or exposes an HTTP listener.

## Default and activation barriers

All commands require `FOCUS_PRIVATE_TRANSPORT_ENABLED=true`; absence is OFF.
The candidate workflow contains request/upload/wait steps but **retains** the
unconditional `PRIVATE_ADMISSION_TRANSPORT_REQUIRED` barrier before the paid action.
This is deliberate until the reviewed installed version and authenticated
transport have passed a real, non-model round trip. Do not remove the barrier on
the strength of synthetic CI. Current main and live worker are not this candidate.

No durable schema is provisioned by the transport. The approved isolated budget
schema and #45 lifecycle schema must already exist before an actual controller
start. Existing Render auto-deploy OFF, plan, instance count and production CRM
must not be changed implicitly. Keep one controller and serialize paid jobs.

## Exact missing access for a future activation

The worker needs a **separate**, repository-selected GitHub credential, stored only
as `FOCUS_BUDGET_GITHUB_TOKEN` in the existing worker's secret environment. It is
not the OpenAI costs key, executor key, GitHub Actions ephemeral token or a connector
token to export. The current prototype pins receipt identity to `artgawlik-ui` and
checks authenticated `/user` before reserving. A dedicated GitHub App would need a
separate reviewed identity policy; it is not silently accepted.

Proposed fine-grained PAT, selected repository `artgawlik-ui/ai-focus-3-0` only:

| Repository permission | Level | Purpose |
| --- | --- | --- |
| Actions | Read | Runs, artifacts and environment protection metadata |
| Issues | Read | Approval comment and current task |
| Contents | Read | Atomic issue branch claim |
| Commit statuses | Read and write | Publish private reservation receipt |
| Metadata | Read | Collaborator permission checks; automatically included |

No contents-write, workflow-write, secrets, administration or deploy permissions
are requested. This nevertheless grants new persistent access and requires the
owner's proper authorization and secure entry; do not generate, reveal or copy a
token through chat, Issues, source, screenshots or an agent prompt. A short expiry
and documented revocation are appropriate. No token has been created by this PR.

The worker also requires `FOCUS_BUDGET_TRUSTED_SHA` set to the exact installed,
reviewed main workflow SHA (never an arbitrary candidate branch), the existing
private DB and Costs API settings, and explicit enablement. The model job receives
only statuses-read, never the worker credential. Existing required review remains.

## Verification before activation

- Local stdlib tests cover malformed ZIP/JSON, traversal, oversized payloads,
  redirects without auth forwarding, permission/content/claim changes, wrong
  workflow/SHA/run/attempt, stale requests, forged/cross-run receipts, timeouts,
  DB rejection, lost acknowledgements, cancellation and shutdown.
- Full CI has an additional PostgreSQL test using temporary tables and fake HTTP:
  request -> private durable transaction -> status -> wait -> cancelled finish ->
  retained hold -> later synthetic reconciliation. It asserts the DB transaction
  is actually committed before receipt, rather than just testing a mock callback.
- The CI PostgreSQL test is limited to GitHub Actions and a localhost
  `focus3_test` DSN; local stdlib-only policy runs skip it. It never contacts real
  GitHub/OpenAI or a production DB.
- Still required: reviewer acceptance, proper credential provisioning, installed
  schema/workflow and an actual authenticated round trip while paid action remains
  blocked. No inference of credit, hard per-task spend cap or completed activation.

## Official API references checked for this implementation

- https://docs.github.com/en/rest/actions/artifacts#download-an-artifact
- https://docs.github.com/en/rest/commits/statuses#create-a-commit-status
- https://docs.github.com/en/rest/collaborators/collaborators#get-repository-permissions-for-a-user
- https://docs.github.com/en/rest/deployments/environments#get-an-environment


### Costs API HTTP 429 after the first installed smoke test

Run 43903822511 (issue #48) failed at receipt wait, before the model barrier.
Read-only diagnostics found no reservation or execution rows and HTTP 429 on
the controller's Costs API request. The runner's earlier Costs API GET had
succeeded; this does not prove the provider's exact rate-limit policy.

The runner now requires the private receipt without making a duplicate Costs API
request. The controller still authenticates the task and reads live project costs
before every admission transaction and receipt. HTTP 429 is reported only as
COSTS_RATE_LIMITED, with the existing 60-second controller backoff; no provider
body, credentials, cached spend, or manually entered spend grants admission.
The unconditional paid-model barrier and owner Environment review remain.
Do not rerun/replay issue #48. Any subsequent smoke needs a new approved issue
after the fix is reviewed, installed and its trusted commit pin updated.


### Reject admission after the runner stops waiting

Issue #50 / run 43909025185 timed out at 16:39:20 UTC on 2026-11-16.
After transient Costs API HTTP 429 responses the controller committed its hold
and receipt at 16:39:40 UTC. Whole-workflow `in_progress` was insufficient:
the Codex job's receipt-wait step had already failed. The model action was skipped.
The private lifecycle recorded failure/awaiting_costs and retained a 2 USD hold;
this is an accounting reservation, not a model charge. Do not delete/release it
because the workflow failed, and do not rerun/replay issue #50.

Admission now checks authenticated GitHub job metadata for exactly one `codex`
job with the matching run, first attempt and SHA. The receipt-wait step must be
in progress, unfinished and inside 90 seconds of GitHub's start timestamp,
leaving 30 seconds of the runner's 120-second wait. The check occurs before
Costs I/O, again under the PostgreSQL lock after Costs I/O, and before posting
a receipt. Production recomputes wall time after the GitHub read. Closed or
ambiguous steps never authorize admission. If the step closes after commit,
withhold the receipt and retain the hold for the existing finish/reconcile path.
This narrows the distributed race; it cannot atomically join GitHub and PostgreSQL.
The runner still enforces its own timeout and exact nonce receipt.

No timeout increase, synthetic spend fallback, hold release, model activation,
review bypass, automatic replay or new service is introduced. HTTP 429 itself
remains a provider-side availability constraint. A subsequent live smoke still
requires separate release authorization, reconciliation of the existing hold and
a new approved issue. CI uses synthetic HTTP and isolated PostgreSQL; it does
not establish successful live transport.


### Waiting for genuine cost coverage

An unresolved hold blocks admission until provider coverage includes the trusted
finish timestamp. No timeout, low historical spend or skipped model step releases
it. Pending coverage is now logged as WAIT: COSTS_NOT_YET_COVERING_EXECUTION and
checked again after 900 seconds instead of 60. This reduces unnecessary reads
without caching an observation as authorization or changing reconciliation rules.

HTTP 429 remains fail-closed. Its Retry-After header can supply seconds or an
HTTP date (RFC 9110 section 10.2.3). Only a normalized integer delay crosses the
cost adapter/gate boundary. Invalid values use 900 seconds; valid values are
bounded to 900–86400 seconds. Raw headers, URLs, bodies and credentials are never
logged. These are local scheduling bounds, not a provider freshness guarantee.
The existing 120-second runner wait and 90-second admission window do not grow;
a rate-limited task may fail and must not be replayed automatically.

Cooldown uses the existing interruptible stop event, so SIGTERM remains prompt.
It is process-local: a restart may perform one fresh GET sooner; durable holds
remain authoritative across restart. There is no new cron, service, schema,
permission, model call or hold release. Default ready polling stays unchanged.
