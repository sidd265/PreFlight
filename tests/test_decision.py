"""Phase 2: the deterministic decider is a pure function of action + policy."""

from __future__ import annotations

from preflight.decision import DecisionPolicy, decide
from preflight.schema import Action, Context


def _action(kind="tool_call", payload=None, risk="low", reversible=True) -> Action:
    return Action(
        id="a",
        kind=kind,
        payload=payload or {},
        risk=risk,
        reversible=reversible,
        context=Context(inputs={}, model="m", prompt_hash="h"),
    )


def test_low_risk_allows():
    assert decide(_action()) == "allow"


def test_high_risk_irreversible_needs_approval():
    assert decide(_action(risk="high", reversible=False)) == "needs_approval"


def test_payment_over_block_threshold_blocks():
    a = _action(kind="payment", payload={"amount": 50_000}, risk="high", reversible=False)
    assert decide(a) == "block"


def test_payment_between_thresholds_needs_approval():
    a = _action(kind="payment", payload={"amount": 5_000}, risk="high", reversible=False)
    assert decide(a) == "needs_approval"


def test_policy_changes_verdict():
    a = _action(kind="payment", payload={"amount": 5_000}, risk="low", reversible=True)
    relaxed = DecisionPolicy(payment_block_threshold=10_000, payment_approval_threshold=10_000)
    strict = DecisionPolicy(payment_block_threshold=1_000, payment_approval_threshold=500)
    assert decide(a, relaxed) == "allow"
    assert decide(a, strict) == "block"


def test_decide_is_deterministic():
    a = _action(kind="payment", payload={"amount": 5_000}, risk="high", reversible=False)
    assert decide(a) == decide(a) == decide(a)
