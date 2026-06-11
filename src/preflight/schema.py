"""Core data model — the spine of Preflight (PRD §5).

These typed records feed all three outputs: the waste report, the regression diff,
and the audit log. Do NOT change these casually — a schema change can break the hash
chain and stored data (CLAUDE.md golden rule #8).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Risk = Literal["low", "medium", "high"]
Verdict = Literal["allow", "block", "needs_approval"]


class Context(BaseModel):
    """What the agent saw. `inputs` is REDACTED before persist (see redaction module)."""

    inputs: dict = Field(default_factory=dict)
    model: str
    prompt_hash: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


class Action(BaseModel):
    """A high-stakes thing an agent is about to do. `payload` is REDACTED before persist."""

    id: str
    kind: str  # "payment" | "db_write" | "send_po" | "tool_call" | ...
    payload: dict = Field(default_factory=dict)
    risk: Risk
    reversible: bool
    context: Context


class Decision(BaseModel):
    """The verdict on an action, plus the hash-chain fields that make it tamper-evident."""

    action: Action
    verdict: Verdict
    judge_score: float | None = None  # 0..1 "would a human sign off?"
    judge_rationale: str | None = None
    approved_by: str | None = None  # human, if gated
    policy_checked: list[str] = Field(default_factory=list)
    prev_hash: str
    content_hash: str
    hash: str  # sha256(prev_hash + content_hash)
    timestamp: datetime


class Waste(BaseModel):
    """Real vs wasted work, and what the waste cost."""

    real_actions: int = 0
    wasted_actions: int = 0
    wasted_cost_usd: float = 0.0
    wasted_ratio: float = 0.0
