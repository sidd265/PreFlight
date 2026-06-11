"""Phase 1: waste detection flags loops, no-ops, errors; real work counted."""

from __future__ import annotations

from preflight.recorder import Recorder
from preflight.store import Store
from preflight.waste import classify, compute_waste


def _record_run(store, actions):
    rec = Recorder(store, "t")
    with rec:
        for kind, payload, outcome in actions:
            rec.record_action(
                kind=kind,
                payload=payload,
                model="claude-haiku-4-5",
                tokens_in=100,
                tokens_out=50,
                outcome=outcome,
            )
    return rec.run_id


def test_duplicate_action_is_wasted(tmp_path):
    with Store(tmp_path / "p.db") as store:
        run_id = _record_run(
            store,
            [
                ("tool_call", {"tool": "a"}, "ok"),
                ("tool_call", {"tool": "a"}, "ok"),  # exact loop -> wasted
            ],
        )
        rows = store.actions_for_run(run_id)
    labels = [c.label for c in classify(rows)]
    assert labels == ["real", "wasted"]


def test_no_op_and_error_are_wasted(tmp_path):
    with Store(tmp_path / "p.db") as store:
        run_id = _record_run(
            store,
            [
                ("tool_call", {"tool": "a"}, "ok"),
                ("tool_call", {"tool": "b"}, "no_op"),
                ("tool_call", {"tool": "c"}, "error"),
            ],
        )
        rows = store.actions_for_run(run_id)
    w = compute_waste(rows)
    assert w.real_actions == 1
    assert w.wasted_actions == 2
    assert w.wasted_ratio == round(2 / 3, 4)


def test_distinct_real_actions_not_wasted(tmp_path):
    with Store(tmp_path / "p.db") as store:
        run_id = _record_run(
            store,
            [
                ("tool_call", {"tool": "a"}, "ok"),
                ("tool_call", {"tool": "b"}, "ok"),
                ("payment", {"amount": 1}, "ok"),
            ],
        )
        rows = store.actions_for_run(run_id)
    w = compute_waste(rows)
    assert w.wasted_actions == 0
    assert w.real_actions == 3
    assert w.wasted_ratio == 0.0


def test_wasted_cost_summed(tmp_path):
    with Store(tmp_path / "p.db") as store:
        run_id = _record_run(
            store,
            [
                ("tool_call", {"tool": "a"}, "ok"),
                ("tool_call", {"tool": "a"}, "ok"),  # duplicate, cost wasted
            ],
        )
        rows = store.actions_for_run(run_id)
    w = compute_waste(rows)
    # _record_run uses 100 in / 50 out at (1.0, 5.0)/1M = (100 + 250)/1e6 = 0.00035
    per_action = (100 * 1.0 + 50 * 5.0) / 1_000_000
    assert w.wasted_cost_usd == round(per_action, 6)
