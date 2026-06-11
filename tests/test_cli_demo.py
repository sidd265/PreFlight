"""Phase 3: `preflight demo` is opt-in and never calls the network in CI."""

from __future__ import annotations

from typer.testing import CliRunner

from preflight.cli import app

runner = CliRunner()


def test_demo_refuses_without_live_flag(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "should-not-be-used")
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 1
    assert "Refusing to call the live judge" in result.stdout


def test_demo_requires_key_when_live(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(app, ["demo", "--live"])
    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY is not set" in result.stdout
