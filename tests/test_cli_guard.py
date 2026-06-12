"""Phase 4: `preflight guard` enforces budget + policy over a recorded run."""

from __future__ import annotations

from examples.sample_agent import run_sample_agent
from typer.testing import CliRunner

from preflight.cli import app
from preflight.store import Store

runner = CliRunner()


def _seed(tmp_path):
    db = tmp_path / "preflight.db"
    store = Store(db)
    run_sample_agent(store)
    store.close()
    return db


def test_guard_blocks_over_policy(tmp_path):
    """The sample agent makes a high-value payment; a $10k block rule must catch it."""
    db = _seed(tmp_path)
    policy = tmp_path / "preflight.yaml"
    policy.write_text(
        "budget_usd: 100.0\n"
        "rules:\n"
        "  - name: block-big\n"
        "    kind: payment\n"
        "    max_amount: 1\n"  # any payment >= $1 is blocked
        "    effect: block\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["guard", "--policy", str(policy), "--db", str(db)])
    assert result.exit_code == 2  # something was blocked
    assert "blocked by the guard" in result.stdout


def test_guard_all_allowed_within_limits(tmp_path):
    db = _seed(tmp_path)
    policy = tmp_path / "preflight.yaml"
    policy.write_text("budget_usd: 1000.0\ndefault_effect: allow\nrules: []\n", encoding="utf-8")
    result = runner.invoke(app, ["guard", "--policy", str(policy), "--db", str(db)])
    assert result.exit_code == 0
    assert "KILL SWITCH" not in result.stdout
