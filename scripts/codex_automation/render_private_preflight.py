"""Explicit private diagnostic followed by the deliberately idle worker.

Controlled operator command (not the current Render start command):
python scripts/codex_automation/render_private_preflight.py --run-diagnostic-and-idle

Requires the already bootstrapped isolated budget database. Reuses the rollback-only
diagnostic from PR #37, then the private bootstrap/idle lifecycle from PR #36.
This command does not start Codex, contact OpenAI, or activate a job queue.
No arguments, unknown arguments, or failed diagnostics must stop before idle.
"""
import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-diagnostic-and-idle", action="store_true", required=True)
    parser.parse_args(argv)

    # Import only after explicit opt-in. Exceptions must propagate: never enter
    # the idle worker after an unsuccessful or interrupted diagnostic.
    from private_budget_gate_diagnostic import main as diagnose
    diagnose()

    from render_private_bootstrap import main as idle
    idle()


if __name__ == "__main__":
    main()
