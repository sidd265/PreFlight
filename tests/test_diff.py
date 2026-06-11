"""Phase 2: diff detects injected changes; regression flags dangerous flips only."""

from __future__ import annotations

from preflight.diff import diff_decisions
from preflight.regression import find_regressions
from preflight.replay import ReplayDecision


def _dec(seq, kind, risk, verdict, fp=None) -> ReplayDecision:
    return ReplayDecision(
        seq=seq,
        action_id=f"a{seq}",
        kind=kind,
        risk=risk,
        verdict=verdict,
        fingerprint=fp or f"fp{seq}",
    )


def test_diff_detects_verdict_change():
    before = [_dec(0, "payment", "high", "block")]
    after = [_dec(0, "payment", "high", "allow")]
    changes = diff_decisions(before, after)
    verdict_changes = [c for c in changes if c.field == "verdict"]
    assert len(verdict_changes) == 1
    assert verdict_changes[0].before == "block"
    assert verdict_changes[0].after == "allow"


def test_diff_quiet_when_identical():
    runs = [_dec(0, "tool_call", "low", "allow")]
    assert diff_decisions(runs, list(runs)) == []


def test_diff_detects_added_action():
    before = [_dec(0, "tool_call", "low", "allow")]
    after = [_dec(0, "tool_call", "low", "allow"), _dec(1, "payment", "high", "block")]
    changes = diff_decisions(before, after)
    assert any(c.field == "presence" for c in changes)


def test_regression_fires_on_high_risk_block_to_allow():
    before = [_dec(0, "payment", "high", "block")]
    after = [_dec(0, "payment", "high", "allow")]
    regs = find_regressions(diff_decisions(before, after))
    assert len(regs) == 1
    assert regs[0].before == "block"
    assert regs[0].after == "allow"


def test_regression_quiet_on_low_risk_flip():
    before = [_dec(0, "tool_call", "low", "block")]
    after = [_dec(0, "tool_call", "low", "allow")]
    assert find_regressions(diff_decisions(before, after)) == []


def test_regression_quiet_when_more_restrictive():
    # allow -> block on high risk is SAFER, not a regression.
    before = [_dec(0, "payment", "high", "allow")]
    after = [_dec(0, "payment", "high", "block")]
    assert find_regressions(diff_decisions(before, after)) == []


def test_regression_fires_needs_approval_to_allow():
    before = [_dec(0, "payment", "high", "needs_approval")]
    after = [_dec(0, "payment", "high", "allow")]
    assert len(find_regressions(diff_decisions(before, after))) == 1
