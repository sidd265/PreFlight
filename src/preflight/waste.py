"""Waste detection (Phase 1).

Classify each recorded action as REAL (advanced the task) or WASTED (loops,
no-ops, duplicates, dead ends) and total the wasted cost. Heuristics start simple
and deterministic (PRD §11: "start simple, refine with real traces").

Rules, applied in order per action within a run:
  1. outcome == "error"  -> wasted (dead end)
  2. outcome == "no_op"   -> wasted (produced nothing)
  3. fingerprint already seen earlier in the run -> wasted (duplicate / loop)
  4. otherwise -> real
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from preflight.schema import Waste


@dataclass(frozen=True)
class Classified:
    seq: int
    kind: str
    label: str  # "real" | "wasted"
    reason: str  # "ok" | "error" | "no_op" | "duplicate"
    cost_usd: float


def classify(rows: list[sqlite3.Row]) -> list[Classified]:
    """Label each recorded-action row as real or wasted with a reason."""
    seen: set[str] = set()
    out: list[Classified] = []
    for row in rows:
        outcome = row["outcome"]
        fingerprint = row["fingerprint"]
        cost = float(row["cost_usd"])
        kind = _kind_of(row)

        if outcome == "error":
            label, reason = "wasted", "error"
        elif outcome == "no_op":
            label, reason = "wasted", "no_op"
        elif fingerprint in seen:
            label, reason = "wasted", "duplicate"
        else:
            label, reason = "real", "ok"
            seen.add(fingerprint)

        out.append(
            Classified(
                seq=row["seq"], kind=kind, label=label, reason=reason, cost_usd=cost
            )
        )
    return out


def _kind_of(row: sqlite3.Row) -> str:
    import json

    try:
        return json.loads(row["action_json"]).get("kind", "unknown")
    except (ValueError, TypeError):
        return "unknown"


def compute_waste(rows: list[sqlite3.Row]) -> Waste:
    """Aggregate a run's classified actions into a Waste summary."""
    classified = classify(rows)
    real = sum(1 for c in classified if c.label == "real")
    wasted = sum(1 for c in classified if c.label == "wasted")
    wasted_cost = sum(c.cost_usd for c in classified if c.label == "wasted")
    total = real + wasted
    ratio = (wasted / total) if total else 0.0
    return Waste(
        real_actions=real,
        wasted_actions=wasted,
        wasted_cost_usd=round(wasted_cost, 6),
        wasted_ratio=round(ratio, 4),
    )
