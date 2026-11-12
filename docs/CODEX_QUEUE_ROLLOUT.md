# Codex queue: controlled rollout (Draft, not active)

Order: #28 -> #29 -> #30 -> #31. Never automatically approve an issue or bypass `codex-development` required reviewer. Do not auto-merge or deploy.

`queue_policy.decide()` is a **pure policy component**, not a scheduler or an executor. A future trusted scheduler must:
1. Obtain current billing month, independently verified project spend, and outstanding reservations from a trusted source; do not trust Issue bodies, agent output, or repository variables as proof of actual spend.
2. Verify OpenAI project hard cap **USD 8/month**, API key project scoping, and existing environment review. The screenshot alone does not prove live cap enforcement at run time.
3. Serialize runs using a durable lock, recheck budget immediately before each invocation, reserve USD 2 conservatively, reconcile actual spend after completion, and stop on missing/stale billing evidence.
4. Require individually approved issue digest and human environment review. The current `issue_comment` workflow cannot safely self-trigger: a bot comment would fail the human approver check. Do not weaken it.
5. Only advance after the previous issue has a reviewed, green CI Draft PR and an explicit recorded acceptance; failed/blocked runs require triage, not paid automatic retries.
6. Enforce a small context window and targeted test output. TPM is separate from monthly USD budget; reserve headroom and use backoff on transient rate limits, never an unlimited retry loop.

**Current activation status: OFF**. This PR adds testable queue selection and budget checks only. Unattended end-to-end execution requires separate trusted billing integration, durable reservation/locking, explicit approval semantics and human review. Until those exist, fail closed rather than promise uninterrupted paid execution.
