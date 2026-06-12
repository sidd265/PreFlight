"""Spend guard + declarative policy-as-code (Phase 4).

Adds the automatic guardrails that need no human or LLM:

  * Per-run **budget** checked BEFORE an action executes.
  * **Kill switch**: once the budget is breached the guard latches; every
    subsequent action is blocked.
  * **Policy-as-code**: allow/deny/needs_approval rules expressed as DATA
    (Pydantic models loaded from YAML with ``yaml.safe_load``) — never executed
    code. No ``eval``/``exec``/``pickle`` (CLAUDE.md S7).

Security (CLAUDE.md golden rule #2 / PRD S3): guards **fail CLOSED**. Any error in
the budget check or policy evaluation results in ``block`` — never ``allow``. A broken
guard must stop the agent, not wave it through.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from preflight.decision import PERMISSIVENESS
from preflight.schema import Action, Risk, Verdict


def _amount(payload: dict[str, Any], field: str) -> float | None:
    value = payload.get(field)
    if isinstance(value, bool):  # bool is an int subclass; not a money amount
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


class PolicyRule(BaseModel):
    """One declarative rule. A rule matches an action when every set condition holds;
    the first matching rule (in order) decides the verdict."""

    name: str | None = None
    kind: str | None = None  # match this action kind (e.g. "payment")
    risk: Risk | None = None  # match this risk level
    amount_field: str = "amount"  # where the money amount lives in the payload
    max_amount: float | None = None  # match when payload[amount_field] >= this
    effect: Verdict  # what to do when matched

    def matches(self, action: Action) -> bool:
        if self.kind is not None and action.kind != self.kind:
            return False
        if self.risk is not None and action.risk != self.risk:
            return False
        if self.max_amount is not None:
            amt = _amount(action.payload, self.amount_field)
            if amt is None or amt < self.max_amount:
                return False
        return True


class GuardPolicy(BaseModel):
    """Declarative policy: a budget plus ordered rules. Pure data — no executable code."""

    budget_usd: float | None = None  # per-run cumulative cap; None = unlimited
    default_effect: Verdict = "allow"  # verdict when no rule matches
    rules: list[PolicyRule] = Field(default_factory=list)


class GuardResult(BaseModel):
    verdict: Verdict
    reason: str
    tripped: bool = False  # kill switch engaged?
    spent_usd: float = 0.0
    rules_checked: list[str] = Field(default_factory=list)


def evaluate_policy(action: Action, policy: GuardPolicy) -> tuple[Verdict, str, list[str]]:
    """Pure function: first matching rule wins, else the default effect."""
    checked: list[str] = []
    for i, rule in enumerate(policy.rules):
        name = rule.name or f"rule[{i}]"
        checked.append(name)
        if rule.matches(action):
            return rule.effect, f"matched policy rule '{name}'", checked
    return policy.default_effect, "no policy rule matched (default)", checked


def _more_restrictive(a: Verdict, b: Verdict) -> Verdict:
    return a if PERMISSIVENESS[a] <= PERMISSIVENESS[b] else b


def load_policy(path: str | Path) -> GuardPolicy:
    """Load a policy from YAML. Uses ``safe_load`` so no Python objects can be
    constructed from the file (S7), then validates via Pydantic."""
    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError("policy file must be a YAML mapping")
    return GuardPolicy(**data)


class Guard:
    """Stateful spend guard for a single run. Fails closed on any internal error."""

    def __init__(self, policy: GuardPolicy):
        self.policy = policy
        self._spent = 0.0
        self._tripped = False

    @property
    def tripped(self) -> bool:
        return self._tripped

    @property
    def spent_usd(self) -> float:
        return self._spent

    def check(self, action: Action, cost_usd: float) -> GuardResult:
        """Decide an action BEFORE it executes. Returns block on any error (fail closed)."""
        try:
            return self._check(action, cost_usd)
        except Exception as exc:  # noqa: BLE001 - a broken guard must stop the agent
            # A guard we cannot trust is a breach: latch the kill switch and block.
            self._tripped = True
            return GuardResult(
                verdict="block",
                reason=f"guard error (failing closed): {type(exc).__name__}",
                tripped=True,
                spent_usd=self._spent,
            )

    def _check(self, action: Action, cost_usd: float) -> GuardResult:
        if self._tripped:
            return GuardResult(
                verdict="block",
                reason="kill switch engaged (budget previously breached)",
                tripped=True,
                spent_usd=self._spent,
                rules_checked=["kill_switch"],
            )

        cost = float(cost_usd)  # corrupt/None cost -> TypeError -> caught -> fail closed

        policy_verdict, reason, checked = evaluate_policy(action, self.policy)

        # Budget is checked BEFORE execution. A breach halts AND trips the kill switch.
        if self.policy.budget_usd is not None:
            prospective = self._spent + cost
            if prospective > self.policy.budget_usd:
                self._tripped = True
                return GuardResult(
                    verdict="block",
                    reason=(
                        f"budget exceeded: ${prospective:.4f} would exceed "
                        f"${self.policy.budget_usd:.4f}"
                    ),
                    tripped=True,
                    spent_usd=self._spent,
                    rules_checked=[*checked, "budget"],
                )

        verdict = _more_restrictive(policy_verdict, "allow")
        # Only count spend for actions that are permitted to proceed.
        if verdict in ("allow", "needs_approval"):
            self._spent += cost

        return GuardResult(
            verdict=verdict,
            reason=reason,
            tripped=False,
            spent_usd=self._spent,
            rules_checked=checked,
        )
