"""Preflight CLI entry point (Typer)."""

from __future__ import annotations

import typer

from preflight import __version__

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


if __name__ == "__main__":
    app()
