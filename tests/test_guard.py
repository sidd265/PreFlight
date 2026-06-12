"""Phase 4: spend guard + declarative policy. Guards must fail CLOSED (S3).

The five PRD tests (PRD §Phase 4):
  1. over-budget action halted
  2. under-budget proceeds
  3. policy rules allow/deny as written
  4. a guard error blocks rather than allows  (S3 — the important one)
  5. no false stops within limits
plus: kill switch latches; policy loads from YAML via safe_load (no code exec, S7).
"""

from __future__ import annotations

import pytest

from preflight import guard as guard_mod
from preflight.guard import Guard, GuardPolicy, PolicyRule, evaluate_policy, load_policy
from preflight.schema import Action, Context


def _action(kind: str = "tool_call", amount: float | None = None, risk: str = "low") -> Action:
    payload: dict = {} if amount is None else {"amount": amount}
    ctx = Context(inputs={}, model="m", prompt_hash="h")
    return Action(id="a", kind=kind, payload=payload, risk=risk, reversible=True, context=ctx)


# 1. over-budget action halted ------------------------------------------------
def test_over_budget_action_halted():
    g = Guard(GuardPolicy(budget_usd=1.0))
    g.check(_action(), cost_usd=0.80)  # spend 0.80, under budget
    result = g.check(_action(), cost_usd=0.50)  # would reach 1.30 > 1.00
    assert result.verdict == "block"
    assert "budget" in result.reason.lower()


# 2. under-budget proceeds ----------------------------------------------------
def test_under_budget_proceeds():
    g = Guard(GuardPolicy(budget_usd=10.0))
    result = g.check(_action(), cost_usd=2.50)
    assert result.verdict == "allow"
    assert result.spent_usd == pytest.approx(2.50)


# 3. policy rules allow/deny as written --------------------------------------
def test_policy_rules_deny_as_written():
    policy = GuardPolicy(
        rules=[PolicyRule(name="big-payment", kind="payment", max_amount=1_000, effect="block")]
    )
    g = Guard(policy)
    assert g.check(_action("payment", amount=5_000), cost_usd=0.0).verdict == "block"


def test_policy_rules_allow_as_written():
    policy = GuardPolicy(
        rules=[PolicyRule(name="big-payment", kind="payment", max_amount=1_000, effect="block")]
    )
    g = Guard(policy)
    # A small payment doesn't match the >= 1000 rule -> default allow.
    assert g.check(_action("payment", amount=10), cost_usd=0.0).verdict == "allow"


def test_policy_rule_needs_approval_effect():
    rule = PolicyRule(name="mid-payment", kind="payment", max_amount=1_000, effect="needs_approval")
    policy = GuardPolicy(rules=[rule])
    verdict, _reason, _checked = evaluate_policy(_action("payment", amount=2_000), policy)
    assert verdict == "needs_approval"


# 4. a guard error blocks rather than allows (S3 — fail closed) ---------------
def test_guard_error_blocks_not_allows(monkeypatch):
    """If policy evaluation itself raises, the action must be BLOCKED, never allowed."""

    def boom(action, policy):
        raise RuntimeError("policy engine exploded")

    monkeypatch.setattr(guard_mod, "evaluate_policy", boom)
    g = Guard(GuardPolicy(budget_usd=100.0))
    result = g.check(_action(), cost_usd=0.01)
    assert result.verdict == "block"
    assert "error" in result.reason.lower()


def test_corrupt_cost_fails_closed():
    """A non-numeric cost (corrupt accounting) must block, not slip through."""
    g = Guard(GuardPolicy(budget_usd=100.0))
    result = g.check(_action(), cost_usd=None)  # type: ignore[arg-type]
    assert result.verdict == "block"


# 5. no false stops within limits --------------------------------------------
def test_no_false_stops_within_limits():
    g = Guard(GuardPolicy(budget_usd=10.0))
    for _ in range(5):
        assert g.check(_action(), cost_usd=1.0).verdict == "allow"  # 5.0 total, well under
    assert not g.tripped


# kill switch latches ---------------------------------------------------------
def test_kill_switch_latches():
    g = Guard(GuardPolicy(budget_usd=1.0))
    breached = g.check(_action(), cost_usd=5.0)  # blows the budget immediately
    assert breached.verdict == "block"
    assert g.tripped
    # Even a tiny, otherwise-fine action is now refused.
    after = g.check(_action(), cost_usd=0.0001)
    assert after.verdict == "block"
    assert "kill switch" in after.reason.lower()


# policy-as-code is declarative data, loaded with safe_load (S7) -------------
def test_load_policy_from_yaml(tmp_path):
    p = tmp_path / "preflight.yaml"
    p.write_text(
        "budget_usd: 5.0\n"
        "default_effect: allow\n"
        "rules:\n"
        "  - name: block-big-payments\n"
        "    kind: payment\n"
        "    max_amount: 10000\n"
        "    effect: block\n",
        encoding="utf-8",
    )
    policy = load_policy(p)
    assert policy.budget_usd == 5.0
    assert policy.rules[0].effect == "block"
    assert Guard(policy).check(_action("payment", amount=50_000), cost_usd=0.0).verdict == "block"


def test_load_policy_rejects_code_execution(tmp_path):
    """safe_load must not construct arbitrary Python objects (no !!python tags)."""
    p = tmp_path / "evil.yaml"
    p.write_text("budget_usd: !!python/object/apply:os.system ['echo hi']\n", encoding="utf-8")
    with pytest.raises(Exception):  # noqa: B017 - safe_load refuses the tag; any failure is fine
        load_policy(p)
