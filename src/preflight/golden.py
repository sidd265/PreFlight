"""Golden set (Phase 2): freeze a known-good run so it can be replayed exactly.

A snapshot freezes the run's recorded actions in order, each already REDACTED
(they were redacted at record time in Phase 1). Freezing the action — including its
context (model, prompt_hash, inputs, tokens) — is what makes replay deterministic.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from preflight.schema import Action
from preflight.store import Store


def _snapshot_from_rows(rows: list[Any]) -> list[dict[str, Any]]:
    return [json.loads(r["action_json"]) for r in rows]


def save_golden(store: Store, name: str, run_id: str | None = None) -> int:
    """Freeze a recorded run into the golden set under `name`.

    Uses the given run, or the latest recorded run if `run_id` is None.
    Returns the number of frozen actions.
    """
    run_row = store.get_run(run_id) if run_id else store.latest_run()
    if run_row is None:
        raise ValueError("no run to save (record a run first)")

    rows = store.actions_for_run(run_row["run_id"])
    snapshot = {
        "name": name,
        "source_run_id": run_row["run_id"],
        "actions": _snapshot_from_rows(rows),
    }
    store.save_golden(
        name, json.dumps(snapshot, sort_keys=True, default=str), datetime.now(UTC).isoformat()
    )
    return len(rows)


def load_golden_actions(store: Store, name: str) -> list[Action]:
    """Load a golden's frozen actions as validated Action models."""
    row = store.get_golden(name)
    if row is None:
        raise ValueError(f"golden '{name}' not found")
    snapshot = json.loads(row["snapshot_json"])
    return [Action.model_validate(a) for a in snapshot["actions"]]
