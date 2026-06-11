"""Dry-run (Phase 3 / PRD S6).

A dry-run must be STRUCTURALLY INCAPABLE of triggering a real side effect. The
`dry_run` branch below never references the `executor`, so there is no code path by
which a dry-run can invoke real work. A test plants a side-effecting executor and
asserts it is never called in dry-run mode (test fails if it is).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from preflight.redaction import redact
from preflight.schema import Action


class DryRunResult(BaseModel):
    would_execute: bool
    kind: str
    risk: str
    reversible: bool
    description: str


def describe(action: Action) -> DryRunResult:
    """Describe what an action WOULD do, using only redacted data."""
    safe_keys = sorted(redact(action.payload).keys())
    return DryRunResult(
        would_execute=True,
        kind=action.kind,
        risk=action.risk,
        reversible=action.reversible,
        description=(
            f"Would perform '{action.kind}' (risk={action.risk}, "
            f"reversible={action.reversible}) with payload fields {safe_keys}"
        ),
    )


def execute_action(
    action: Action,
    executor: Callable[[Action], Any],
    *,
    dry_run: bool,
) -> Any:
    """Run `executor(action)` for real, OR — in dry-run — describe it without
    executing. In the dry-run branch `executor` is never referenced."""
    if dry_run:
        return describe(action)
    return executor(action)
