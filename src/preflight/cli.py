"""Preflight CLI entry point (Typer)."""

from __future__ import annotations

from pathlib import Path

import typer

from preflight import __version__
from preflight.decision import DecisionPolicy
from preflight.diff import diff_decisions
from preflight.golden import save_golden
from preflight.paths import default_db_path
from preflight.regression import find_regressions
from preflight.replay import load_replay_decisions, replay
from preflight.report import build_report, render_html, render_text
from preflight.store import Store

app = typer.Typer(
    name="preflight",
    help="Watch your AI agents: catch risky actions, prove decisions, measure waste.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"preflight {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the Preflight version and exit.",
    ),
) -> None:
    """Preflight — security and audit tooling for AI agents."""


@app.command()
def report(
    db: Path = typer.Option(
        None, "--db", help="Path to the Preflight DB (default: ./.preflight/preflight.db)."
    ),
    run: str = typer.Option(None, "--run", help="Run id to report on (default: latest run)."),
    html_out: Path = typer.Option(
        None, "--html", help="Also write a self-contained HTML report to this file."
    ),
) -> None:
    """Waste & ROI report: real vs wasted actions, $ spent, $ wasted."""
    db_path = db or default_db_path()
    if not db_path.exists():
        typer.echo(f"No Preflight data found at {db_path}. Record a run first.")
        raise typer.Exit(code=1)

    with Store(db_path) as store:
        run_row = store.get_run(run) if run else store.latest_run()
        if run_row is None:
            typer.echo("No runs recorded yet.")
            raise typer.Exit(code=1)
        rows = store.actions_for_run(run_row["run_id"])
        report_obj = build_report(run_row["run_id"], run_row["name"], rows)
        render_text(report_obj)

        if html_out is not None:
            out = html_out.resolve()
            # Confine output: refuse to write outside the current working directory tree (S7).
            cwd = Path.cwd().resolve()
            if not str(out).startswith(str(cwd)):
                typer.echo("Refusing to write HTML outside the working directory.")
                raise typer.Exit(code=1)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render_html(report_obj, rows), encoding="utf-8")
            typer.echo(f"HTML report written to {out}")


def _open_store(db: Path | None) -> tuple[Store, Path]:
    db_path = db or default_db_path()
    if not db_path.exists():
        typer.echo(f"No Preflight data found at {db_path}. Record a run first.")
        raise typer.Exit(code=1)
    return Store(db_path), db_path


@app.command()
def save(
    name: str = typer.Argument(..., help="Name for the golden snapshot."),
    db: Path = typer.Option(None, "--db", help="Path to the Preflight DB."),
    run: str = typer.Option(None, "--run", help="Run id to snapshot (default: latest)."),
) -> None:
    """Snapshot a recorded run into the golden set."""
    store, _ = _open_store(db)
    with store:
        count = save_golden(store, name, run)
    typer.echo(f"Saved golden '{name}' with {count} frozen actions.")


@app.command(name="replay")
def replay_cmd(
    name: str = typer.Argument(..., help="Golden name to replay."),
    db: Path = typer.Option(None, "--db", help="Path to the Preflight DB."),
    payment_block_threshold: float = typer.Option(
        10_000.0, "--payment-block-threshold", help="Block payments at/above this amount."
    ),
    payment_approval_threshold: float = typer.Option(
        1_000.0, "--payment-approval-threshold", help="Require approval at/above this amount."
    ),
) -> None:
    """Deterministically replay a golden and print the decisions."""
    store, _ = _open_store(db)
    policy = DecisionPolicy(
        payment_block_threshold=payment_block_threshold,
        payment_approval_threshold=payment_approval_threshold,
    )
    with store:
        result = replay(store, name, policy)
    for d in result.decisions:
        typer.echo(f"  [{d.seq}] {d.kind} (risk={d.risk}) -> {d.verdict}")
    typer.echo(f"Replay id: {result.replay_id}")


@app.command(name="diff")
def diff_cmd(
    replay_a: str = typer.Argument(..., help="First replay id (before)."),
    replay_b: str = typer.Argument(..., help="Second replay id (after)."),
    db: Path = typer.Option(None, "--db", help="Path to the Preflight DB."),
) -> None:
    """Diff two replay runs and flag dangerous verdict flips."""
    store, _ = _open_store(db)
    with store:
        before = load_replay_decisions(store, replay_a)
        after = load_replay_decisions(store, replay_b)
    changes = diff_decisions(before, after)
    regressions = find_regressions(changes)

    if not changes:
        typer.echo("No changes between the two runs.")
    for c in changes:
        typer.echo(f"  [{c.seq}] {c.kind} {c.field}: {c.before} -> {c.after}")
    if regressions:
        typer.echo("\nDANGER — regressions detected:")
        for r in regressions:
            typer.echo(f"  [{r.seq}] {r.kind} (risk={r.risk}): {r.reason}")
        raise typer.Exit(code=2)


if __name__ == "__main__":
    app()
