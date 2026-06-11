"""Regression detection (Phase 2): flag dangerous verdict flips.

The dangerous case is a verdict becoming MORE PERMISSIVE on a high-risk action —
e.g. block -> allow, or needs_approval -> allow, or block -> needs_approval. A
change that becomes more restrictive (allow -> block) is safer, not a regression.
Low-risk changes are benign noise.
"""

from __future__ import annotations

from pydantic import BaseModel

from preflight.decision import PERMISSIVENESS
from preflight.diff import Change
from preflight.schema import Verdict

# Risk levels we treat as high-stakes for regression purposes.
DANGEROUS_RISKS = {"high"}


class Regression(BaseModel):
    seq: int
    kind: str
    risk: str
    before: Verdict
    after: Verdict
    reason: str


def _more_permissive(before: str, after: str) -> bool:
    try:
        return PERMISSIVENESS[after] > PERMISSIVENESS[before]  # type: ignore[index]
    except KeyError:
        return False


def find_regressions(changes: list[Change]) -> list[Regression]:
    """Return the dangerous verdict flips among a diff's changes."""
    regressions: list[Regression] = []
    for c in changes:
        if c.field != "verdict":
            continue
        if c.risk not in DANGEROUS_RISKS:
            continue
        if _more_permissive(c.before, c.after):
            regressions.append(
                Regression(
                    seq=c.seq,
                    kind=c.kind,
                    risk=c.risk,
                    before=c.before,  # type: ignore[arg-type]
                    after=c.after,  # type: ignore[arg-type]
                    reason=f"high-risk verdict relaxed: {c.before} -> {c.after}",
                )
            )
    return regressions
