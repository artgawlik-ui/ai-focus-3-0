# Worker readiness audit — Focus 3.0
Date: 2026-11-15, Europe/Warsaw. Refs #39, #40.
Performed directly in this session; no separate paid Codex executor was launched.

## Inputs
- main: ce295cd99f1c5b5afcbd5c708c904f56268c54dd.
- PR #36: 38503e9c5aac610589288b6fd8324ec297f552d4.
- PR #37: a35089e86b878763a35f332d62fab957a9d8befa.
- Both target feat/codex-private-db-integration at ef4dfba08f6024a93cea36d7e044d64cf602fc03; neither is merged.
- Production Render latest deploy remains live at d15265b26524d594bdbcb4bc6b63fcbc398a1424. This is not deployment of the candidate CRM.
- Existing worker: one instance, auto-deploy off, private-db-integration branch, bootstrap start command.
- Existing hourly coordinator and daily 08:30 Europe/Warsaw planner enabled; no duplicate automation created.

## Findings
| Check | Status | Evidence / limits |
|---|---|---|
| Restart cause | CONFIRMED | Render events at 22:03:03Z, 21:58:20Z and 21:52:59Z show server_failed earlyExit=true. Repeated schema PASS logs at roughly five-minute intervals. |
| Idle lifecycle change | READY in code | #36 flushes PASS and READY_IDLE, then sleeps. No paid executor or queue processing. Runtime >10 min without restart is unverified. |
| Independent CI | PASS for inspected heads | #36 Verify Focus 3 run 43324805204 and policy run 43324805379; #37 Verify run 43328905030 and policy run 43328905052 succeeded. This does not prove execution of diagnostic in Render. |
| Local offline tests on #36 head | PASS | 32 unittest policy tests, plus 10 plain function tests across test_render_private_bootstrap.py, test_costs_durable_gate.py, test_queue_policy.py. No network/DB/API within these tests. Initial pytest invocation could not run because pytest was absent; not counted as PASS. |
| Private destination validation | BLOCKED | Exact host and database checks exist, but query parameters are not rejected. A synthetic URI with connection overrides passes validate_private_url. Needs fail-closed regression before runtime activation; no external connection attempted. |
| Diagnostic integration | BLOCKED | #37 adds private_budget_gate_diagnostic.py only. Existing start command does not invoke it; #36 does not add an invocation. Sibling PRs must not be treated as an integrated release. |
| Diagnostic scope | READY for limited review | Session-local temporary shadow table, wrapper suppresses inner commit, explicit rollback. No provider-cost API request. Not a cross-connection concurrency test, not proof of provider budget enforcement. |
| Active paid executor / actual costs | UNKNOWN / BLOCKED | Existing Render worker is only a bootstrap process. No independent current billing or enforced total-cost evidence obtained. 50 PLN/month existing mandate retained. |

The trusted host in source is an exact Render private hostname, not a generic requirement that it end in ".internal"; preserve the verified actual host. No credentials or customer data belong in this document.

## Three missing conditions, in dependency order
1. Reject connection overrides and ambiguous private DSNs; add offline tests proving rejection before any DB call. Preserve secret-free failure codes.
2. After separately authorized controlled deployment, observe one initialization PASS + READY_IDLE with >10 minutes no restart. Provide a deliberate one-shot diagnostic entry point; run only against the isolated test DB. Do not treat a branch deployment as running #37.
3. Validate cross-connection reservations, one executor, fresh authenticated provider costs, project-scoped credentials, and budget enforcement before any paid pilot. UNKNOWN means BLOCKED.

## Security and data-protection gate
This is an automation-readiness audit, not a complete penetration test or GDPR certification. Repository visibility is currently public. Visibility alone is not proof of a leak; a secret/history and customer-data exposure review remains required. Publish only sanitized code/test evidence.

Before production GO, verify server-side role/object authorization, secure sessions, CSRF, login throttling, dependency risks, secret rotation, encrypted backup and restore, retention/deletion and access audit. Separately establish controller/processor responsibilities, lawful purposes/bases, information duties, processor agreements, transfers, and incident procedures. These are UNVERIFIED, not complete merely because tests pass.
Reference: GDPR articles 5, 6, 13–14, 25, 28, 30, 32–35, 44 onward, https://eur-lex.europa.eu/legal-content/PL/TXT/?uri=CELEX:32016R0679 .

## Acceptance / next step
Next small work: private DSN hardening on a branch based on #36, offline synthetic regression tests, Draft PR. No production migration, merge/deploy, environment/secret change, real customer messaging, new Render service, or paid API call performed here.
