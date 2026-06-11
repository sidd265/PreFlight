"""Phase 0: CLI runs and reports its version."""

from __future__ import annotations

from typer.testing import CliRunner

from preflight import __version__
from preflight.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
