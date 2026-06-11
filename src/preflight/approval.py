"""Human approval gate (Phase 3).

For actions whose verdict is `needs_approval`, pause and ask a human. The gate
FAILS CLOSED: only an explicit affirmative grants approval; anything else (a "no",
empty input, or EOF/cancelled prompt) is treated as NOT approved (CLAUDE.md S3).
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel

from preflight.schema import Action

_AFFIRMATIVE = {"y", "yes"}


class ApprovalResult(BaseModel):
    approved: bool
    approved_by: str | None = None


def request_approval(
    action: Action,
    *,
    reader: Callable[[str], str] = input,
    approver: str = "cli-user",
) -> ApprovalResult:
    """Block on `reader` for a human decision. Default-deny on anything but an
    explicit yes."""
    prompt = (
        f"Approve {action.kind} (risk={action.risk}, reversible={action.reversible})? [y/N]: "
    )
    try:
        answer = reader(prompt)
    except (EOFError, KeyboardInterrupt):
        return ApprovalResult(approved=False, approved_by=None)

    if str(answer).strip().lower() in _AFFIRMATIVE:
        return ApprovalResult(approved=True, approved_by=approver)
    return ApprovalResult(approved=False, approved_by=None)
