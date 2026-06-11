"""Phase 0: schema validation round-trips."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from preflight.schema import Action, Context, Decision, Waste


def _context() -> Context:
    return Context(
        inputs={"q": "ship it"},
        model="claude-haiku-4-5",
        prompt_hash="abc123",
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.001,
    )


def _action() -> Action:
    return Action(
        id="act-1",
        kind="payment",
        payload={"amount": 5000, "vendor": "Acme"},
        risk="high",
        reversible=False,
        context=_context(),
    )


def test_context_round_trip():
    c = _context()
    assert Context.model_validate(c.model_dump()) == c


def test_action_round_trip():
    a = _action()
    assert Action.model_validate(a.model_dump()) == a


def test_decision_round_trip():
    d = Decision(
        action=_action(),
        verdict="needs_approval",
        judge_score=0.8,
        judge_rationale="looks risky",
        approved_by=None,
        policy_checked=["spend_limit"],
        prev_hash="0" * 64,
        content_hash="a" * 64,
        hash="b" * 64,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert Decision.model_validate(d.model_dump()) == d


def test_waste_defaults():
    w = Waste()
    assert w.real_actions == 0
    assert w.wasted_ratio == 0.0


def test_invalid_risk_rejected():
    with pytest.raises(ValidationError):
        Action(
            id="x",
            kind="payment",
            payload={},
            risk="catastrophic",  # not in Literal
            reversible=True,
            context=_context(),
        )


def test_invalid_verdict_rejected():
    with pytest.raises(ValidationError):
        Decision(
            action=_action(),
            verdict="maybe",  # not in Literal
            prev_hash="0" * 64,
            content_hash="a" * 64,
            hash="b" * 64,
            timestamp=datetime.now(UTC),
        )
