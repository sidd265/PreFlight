"""Phase 5: `preflight guard` writes an audit trail; `verify` and `export` read it."""

from __future__ import annotations

from examples.sample_agent import run_sample_agent
from typer.testing import CliRunner

from preflight.cli import app
from preflight.store import Store

runner = CliRunner()


def _seed_and_guard(tmp_path):
    db = tmp_path / "preflight.db"
    store = Store(db)
    run_sample_agent(store)
    store.close()
    policy = tmp_path / "preflight.yaml"
    policy.write_text("budget_usd: 1000.0\ndefault_effect: allow\nrules: []\n", encoding="utf-8")
    runner.invoke(app, ["guard", "--policy", str(policy), "--db", str(db)])
    return db


def test_verify_passes_on_intact_chain(tmp_path):
    db = _seed_and_guard(tmp_path)
    result = runner.invoke(app, ["verify", "--db", str(db)])
    assert result.exit_code == 0
    assert "audit chain intact" in result.stdout


def test_export_writes_file(tmp_path, monkeypatch):
    db = _seed_and_guard(tmp_path)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "exported"
    result = runner.invoke(app, ["export", "--out", str(out), "--format", "html", "--db", str(db)])
    assert result.exit_code == 0
    assert (out / "audit.html").exists()
