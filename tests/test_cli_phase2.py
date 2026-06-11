"""Phase 2: CLI save -> replay -> diff end-to-end with danger flagging."""

from __future__ import annotations

import re

from examples.sample_agent import run_sample_agent
from typer.testing import CliRunner

from preflight.cli import app
from preflight.store import Store

runner = CliRunner()


def _replay_id(output: str) -> str:
    m = re.search(r"Replay id:\s*([0-9a-f]+)", output)
    assert m, f"no replay id in output:\n{output}"
    return m.group(1)


def test_save_replay_diff_flow(tmp_path):
    db = tmp_path / "p.db"
    with Store(db) as store:
        run_sample_agent(store)

    # save
    r = runner.invoke(app, ["save", "g", "--db", str(db)])
    assert r.exit_code == 0
    assert "Saved golden" in r.stdout

    # replay with default policy (payment -> needs_approval)
    r1 = runner.invoke(app, ["replay", "g", "--db", str(db)])
    assert r1.exit_code == 0
    id1 = _replay_id(r1.stdout)

    # replay with strict policy (payment -> block) — a dangerous direction change
    r2 = runner.invoke(
        app, ["replay", "g", "--db", str(db), "--payment-block-threshold", "1000"]
    )
    assert r2.exit_code == 0
    id2 = _replay_id(r2.stdout)

    # diff strict(before=block) -> default(after=needs_approval) = more permissive => regression
    d = runner.invoke(app, ["diff", id2, id1, "--db", str(db)])
    assert d.exit_code == 2  # regression detected -> non-zero exit
    assert "DANGER" in d.stdout


def test_diff_no_changes_when_same_policy(tmp_path):
    db = tmp_path / "p.db"
    with Store(db) as store:
        run_sample_agent(store)
    runner.invoke(app, ["save", "g", "--db", str(db)])
    id1 = _replay_id(runner.invoke(app, ["replay", "g", "--db", str(db)]).stdout)
    id2 = _replay_id(runner.invoke(app, ["replay", "g", "--db", str(db)]).stdout)
    d = runner.invoke(app, ["diff", id1, id2, "--db", str(db)])
    assert d.exit_code == 0
    assert "No changes" in d.stdout
