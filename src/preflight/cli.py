"""Preflight CLI entry point (Typer)."""

from __future__ import annotations

from pathlib import Path

import typer

from preflight import __version__
from preflight.paths import default_db_path
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


if __name__ == "__main__":
    app()
