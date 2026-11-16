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
   binds run, attempt and all 256 nonce bits. The GitHub job waits at most 120s for
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
