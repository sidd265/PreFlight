"""Phase 1: end-to-end against the sample agent.

Covers the headline Phase 1 exit criteria:
  * the planted fake API key NEVER appears anywhere stored (S1),
  * the wasteful loop + no-op are flagged as waste,
  * the report renders as text and HTML.
"""

from __future__ import annotations

from examples.sample_agent import PLANTED_FAKE_API_KEY, run_sample_agent
from typer.testing import CliRunner

from preflight.cli import app
from preflight.report import build_report, render_html
from preflight.store import Store
from preflight.waste import compute_waste

runner = CliRunner()


def test_planted_key_never_persisted(tmp_path):
    """S1: plant a fake key in agent context; assert it appears NOWHERE in storage."""
    db = tmp_path / "p.db"
    with Store(db) as store:
        run_sample_agent(store)

    # Scan the entire raw DB file on disk — not just parsed rows.
    raw_bytes = db.read_bytes()
    assert PLANTED_FAKE_API_KEY.encode() not in raw_bytes
    # The distinctive secret body must not survive in any form.
    assert b"PLANTEDFAKEKEY" not in raw_bytes


def test_waste_flagged_for_sample_agent(tmp_path):
    db = tmp_path / "p.db"
    with Store(db) as store:
        run_id = run_sample_agent(store)
        rows = store.actions_for_run(run_id)
    w = compute_waste(rows)
    # 5 distinct intents recorded as 6 actions: 2 duplicate vendor checks + 1 no-op.
    # real: lookup_invoice, check_vendor(first), payment = 3
    # wasted: 2 duplicate vendor checks + 1 no-op = 3
    assert w.real_actions == 3
    assert w.wasted_actions == 3
    assert w.wasted_cost_usd > 0


def test_report_renders_html(tmp_path):
    db = tmp_path / "p.db"
    with Store(db) as store:
        run_id = run_sample_agent(store)
        rows = store.actions_for_run(run_id)
        report = build_report(run_id, "sample", rows)
        html = render_html(report, rows)
    assert "<html" in html
    assert "Waste" in html
    # The secret must not leak into the HTML either.
    assert PLANTED_FAKE_API_KEY not in html


def test_cli_report_runs(tmp_path, monkeypatch):
    db = tmp_path / ".preflight" / "preflight.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    with Store(db) as store:
        run_sample_agent(store)

    result = runner.invoke(app, ["report", "--db", str(db)])
    assert result.exit_code == 0
    assert "Waste & ROI" in result.stdout


def test_cli_report_html_confined(tmp_path, monkeypatch):
    db = tmp_path / "preflight.db"
    with Store(db) as store:
        run_sample_agent(store)

    monkeypatch.chdir(tmp_path)
    out = tmp_path / "report.html"
    result = runner.invoke(app, ["report", "--db", str(db), "--html", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    assert PLANTED_FAKE_API_KEY not in out.read_text(encoding="utf-8")
