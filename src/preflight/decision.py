"""Deterministic decision function (Phase 2).

Replay must be deterministic (CLAUDE.md: no live tool calls, no unfrozen
randomness/seed/model/prompt). So a decision here is a PURE function of the frozen
action + a declarative policy: same input -> same verdict, always. The LLM judge
(Phase 3) and richer policy-as-code (Phase 4) layer on top of this later; they do
not replace its determinism.

This is intentionally small. It exists so replay can re-derive a verdict and diff
can compare two runs.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from preflight.schema import Action, Verdict

# Permissiveness ordering, used by regression detection (block is most restrictive).
PERMISSIVENESS: dict[Verdict, int] = {"block": 0, "needs_approval": 1, "allow": 2}


class DecisionPolicy(BaseModel):
    """Declarative knobs for the deterministic decider. Frozen per replay so the
    same policy always yields the same verdict."""

    payment_block_threshold: float = 10_000.0
    payment_approval_threshold: float = 1_000.0


def _amount(payload: dict[str, Any]) -> float | None:
    value = payload.get("amount")
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def decide(action: Action, policy: DecisionPolicy | None = None) -> Verdict:
    """Pure, deterministic verdict for an action under a policy."""
    policy = policy or DecisionPolicy()

    if action.kind == "payment":
        amount = _amount(action.payload)
        if amount is not None:
            if amount >= policy.payment_block_threshold:
                return "block"
            if amount >= policy.payment_approval_threshold:
                return "needs_approval"

    if action.risk == "high" and not action.reversible:
        return "needs_approval"

    return "allow"
