"""Phase 3 / S6: dry-run is structurally incapable of a real side effect.

This test FAILS if a dry-run ever triggers the executor.
"""

from __future__ import annotations

import pytest

from preflight.dryrun import DryRunResult, execute_action
from preflight.schema import Action, Context


def _action() -> Action:
    return Action(
        id="a",
        kind="payment",
        payload={"amount": 5000, "api_key": "sk-ant-DRYRUNSECRET0123456789"},
        risk="high",
        reversible=False,
        context=Context(inputs={}, model="m", prompt_hash="h"),
    )


def test_dry_run_never_executes():
    side_effects: list[str] = []

    def real_executor(action: Action):
        side_effects.append("EXECUTED")  # a real side effect
        return "done"

    result = execute_action(_action(), real_executor, dry_run=True)
    assert side_effects == []  # nothing happened
    assert isinstance(result, DryRunResult)
    assert result.would_execute is True


def test_dry_run_executor_that_raises_is_never_called():
    def exploding_executor(action: Action):
        raise AssertionError("dry-run must NEVER call the executor")

    # If dry-run touched the executor, this would raise and fail the test.
    result = execute_action(_action(), exploding_executor, dry_run=True)
    assert isinstance(result, DryRunResult)


def test_real_run_does_execute():
    side_effects: list[str] = []

    def real_executor(action: Action):
        side_effects.append("EXECUTED")
        return "done"

    result = execute_action(_action(), real_executor, dry_run=False)
    assert side_effects == ["EXECUTED"]
    assert result == "done"


def test_dry_run_description_has_no_secret():
    result = execute_action(_action(), lambda a: None, dry_run=True)
    assert "sk-ant-DRYRUNSECRET0123456789" not in result.description


def test_real_run_propagates_executor_error():
    def boom(action: Action):
        raise ValueError("real failure")

    with pytest.raises(ValueError):
        execute_action(_action(), boom, dry_run=False)
