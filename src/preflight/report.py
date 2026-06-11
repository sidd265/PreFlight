"""Waste & ROI report rendering — text (Rich) and self-contained HTML (Phase 1)."""

from __future__ import annotations

import html
import sqlite3
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

from preflight.judge import JudgeVerdict
from preflight.schema import Waste
from preflight.waste import classify, compute_waste


@dataclass(frozen=True)
class RunReport:
    run_id: str
    name: str
    waste: Waste
    total_cost_usd: float


def build_report(run_id: str, name: str, rows: list[sqlite3.Row]) -> RunReport:
    waste = compute_waste(rows)
    total_cost = round(sum(float(r["cost_usd"]) for r in rows), 6)
    return RunReport(run_id=run_id, name=name, waste=waste, total_cost_usd=total_cost)


def render_text(report: RunReport, console: Console | None = None) -> None:
    console = console or Console()
    w = report.waste
    real_cost = round(report.total_cost_usd - w.wasted_cost_usd, 6)

    table = Table(title=f"Preflight Waste & ROI — run '{report.name}'")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Real actions", str(w.real_actions))
    table.add_row("Wasted actions", str(w.wasted_actions))
    table.add_row("Wasted ratio", f"{w.wasted_ratio * 100:.1f}%")
    table.add_row("Total spent", f"${report.total_cost_usd:.6f}")
    table.add_row("Real spend", f"${real_cost:.6f}")
    table.add_row("Wasted spend", f"${w.wasted_cost_usd:.6f}")
    console.print(table)


def render_html(report: RunReport, rows: list[sqlite3.Row]) -> str:
    """Self-contained HTML (no external assets) — safe-escaped."""
    w = report.waste
    real_cost = round(report.total_cost_usd - w.wasted_cost_usd, 6)
    name = html.escape(report.name)
    run_id = html.escape(report.run_id)

    detail_rows = []
    for c in classify(rows):
        color = "#1a7f37" if c.label == "real" else "#cf222e"
        detail_rows.append(
            f"<tr><td>{c.seq}</td><td>{html.escape(c.kind)}</td>"
            f'<td style="color:{color};font-weight:600">{c.label}</td>'
            f"<td>{html.escape(c.reason)}</td>"
            f"<td style='text-align:right'>${c.cost_usd:.6f}</td></tr>"
        )
    detail_html = "\n".join(detail_rows)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Preflight Waste &amp; ROI — {name}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1f2328; }}
  h1 {{ font-size: 1.4rem; }}
  .muted {{ color: #656d76; font-size: 0.85rem; }}
  table {{ border-collapse: collapse; margin-top: 1rem; }}
  th, td {{ border: 1px solid #d0d7de; padding: 0.4rem 0.8rem; }}
  th {{ background: #f6f8fa; text-align: left; }}
  .summary td:last-child {{ text-align: right; font-variant-numeric: tabular-nums; }}
</style></head><body>
<h1>Preflight Waste &amp; ROI</h1>
<p class="muted">Run: {name} &middot; <code>{run_id}</code></p>
<table class="summary">
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Real actions</td><td>{w.real_actions}</td></tr>
  <tr><td>Wasted actions</td><td>{w.wasted_actions}</td></tr>
  <tr><td>Wasted ratio</td><td>{w.wasted_ratio * 100:.1f}%</td></tr>
  <tr><td>Total spent</td><td>${report.total_cost_usd:.6f}</td></tr>
  <tr><td>Real spend</td><td>${real_cost:.6f}</td></tr>
  <tr><td>Wasted spend</td><td>${w.wasted_cost_usd:.6f}</td></tr>
</table>
<h2 style="font-size:1.1rem;margin-top:1.5rem">Actions</h2>
<table>
  <tr><th>#</th><th>Kind</th><th>Label</th><th>Reason</th><th>Cost</th></tr>
  {detail_html}
</table>
</body></html>
"""


def render_judge_html(scenarios: list[tuple[str, JudgeVerdict]]) -> str:
    """Self-contained HTML for a set of (scenario_name, JudgeVerdict) results."""
    rows = []
    for name, v in scenarios:
        color = {"allow": "#1a7f37", "block": "#cf222e", "needs_approval": "#9a6700"}.get(
            v.verdict, "#1f2328"
        )
        score = "—" if v.score is None else f"{v.score:.2f}"
        rows.append(
            f"<tr><td>{html.escape(name)}</td>"
            f'<td style="color:{color};font-weight:600">{html.escape(v.verdict)}</td>'
            f"<td style='text-align:right'>{score}</td>"
            f"<td>{html.escape(v.rationale)}</td>"
            f"<td>{'yes' if v.available else 'no (failed closed)'}</td></tr>"
        )
    body = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Preflight Judge Demo</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1f2328; }}
  table {{ border-collapse: collapse; margin-top: 1rem; }}
  th, td {{ border: 1px solid #d0d7de; padding: 0.4rem 0.8rem; }}
  th {{ background: #f6f8fa; text-align: left; }}
</style></head><body>
<h1>Preflight Judge — Demo</h1>
<p style="color:#656d76;font-size:0.85rem">Live LLM-judge verdicts. Recorded content
was wrapped as untrusted data; injection attempts must not flip the verdict to allow.</p>
<table>
  <tr><th>Scenario</th><th>Verdict</th><th>Score</th><th>Rationale</th><th>Judge available</th></tr>
  {body}
</table>
</body></html>
"""
