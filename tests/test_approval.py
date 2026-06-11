"""Phase 3: human approval gate blocks until input and fails closed."""

from __future__ import annotations

from preflight.approval import request_approval
from preflight.schema import Action, Context


def _action() -> Action:
    return Action(
        id="a",
        kind="payment",
        payload={"amount": 5000},
        risk="high",
        reversible=False,
        context=Context(inputs={}, model="m", prompt_hash="h"),
    )


def test_yes_approves():
    res = request_approval(_action(), reader=lambda _p: "y", approver="alice")
    assert res.approved is True
    assert res.approved_by == "alice"


def test_no_denies():
    res = request_approval(_action(), reader=lambda _p: "n")
    assert res.approved is False
    assert res.approved_by is None


def test_empty_input_fails_closed():
    res = request_approval(_action(), reader=lambda _p: "")
    assert res.approved is False


def test_eof_fails_closed():
    def raising(_prompt):
        raise EOFError

    res = request_approval(_action(), reader=raising)
    assert res.approved is False


def test_gate_blocks_until_reader_called():
    calls = []

    def reader(prompt):
        calls.append(prompt)
        return "yes"

    request_approval(_action(), reader=reader)
    assert len(calls) == 1  # the gate consulted the human exactly once
