"""Side-by-side diff of two replay runs (Phase 2).

Both runs are aligned by position (replays of the same golden share order). Each
differing field becomes a Change. Regression detection (see regression.py) then
flags the dangerous ones.
"""

from __future__ import annotations

from pydantic import BaseModel

from preflight.replay import ReplayDecision


class Change(BaseModel):
    seq: int
    kind: str
    risk: str
    field: str  # "verdict" | "action" | "presence"
    before: str
    after: str


def diff_decisions(
    before: list[ReplayDecision], after: list[ReplayDecision]
) -> list[Change]:
    """Compare two decision lists position-by-position."""
    changes: list[Change] = []
    n = max(len(before), len(after))
    for i in range(n):
        b = before[i] if i < len(before) else None
        a = after[i] if i < len(after) else None

        if b is None and a is not None:
            changes.append(
                Change(seq=i, kind=a.kind, risk=a.risk, field="presence",
                       before="(absent)", after=a.kind)
            )
            continue
        if a is None and b is not None:
            changes.append(
                Change(seq=i, kind=b.kind, risk=b.risk, field="presence",
                       before=b.kind, after="(absent)")
            )
            continue
        if b is None or a is None:  # both-None: nothing to compare
            continue

        # Different underlying action at this position.
        if b.fingerprint != a.fingerprint:
            changes.append(
                Change(seq=i, kind=a.kind, risk=a.risk, field="action",
                       before=b.kind, after=a.kind)
            )

        # Verdict change on the same position.
        if b.verdict != a.verdict:
            changes.append(
                Change(seq=i, kind=a.kind, risk=a.risk, field="verdict",
                       before=b.verdict, after=a.verdict)
            )

    return changes
