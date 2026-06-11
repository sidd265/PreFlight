"""Phase 1: recording captures actions through redaction; outcomes captured."""

from __future__ import annotations

import json

from preflight.recorder import Recorder
from preflight.store import Store


def test_record_action_persists_redacted(tmp_path):
    with Store(tmp_path / "p.db") as store:
        rec = Recorder(store, "t")
        with rec:
            rec.record_action(
                kind="payment",
                payload={"amount": 5000, "api_key": "sk-ant-SECRET0123456789abcd"},
                risk="high",
                reversible=False,
                model="claude-haiku-4-5",
                tokens_in=100,
                tokens_out=50,
                inputs={"prompt": "pay", "token": "sk-ant-SECRET0123456789abcd"},
            )
        rows = store.actions_for_run(rec.run_id)
    assert len(rows) == 1
    blob = rows[0]["action_json"]
    assert "sk-ant-SECRET0123456789abcd" not in blob
    parsed = json.loads(blob)
    assert parsed["payload"]["api_key"] == "[REDACTED]"
    assert parsed["risk"] == "high"


def test_cost_is_recorded(tmp_path):
    with Store(tmp_path / "p.db") as store:
        rec = Recorder(store, "t")
        with rec:
            rec.record_action(
                kind="tool_call",
                model="claude-haiku-4-5",
                tokens_in=200,
                tokens_out=80,
            )
        rows = store.actions_for_run(rec.run_id)
    assert rows[0]["cost_usd"] == 600 / 1_000_000


def test_decorator_records_outcomes(tmp_path):
    with Store(tmp_path / "p.db") as store:
        rec = Recorder(store, "t")
        with rec:

            @rec.record(kind="tool_call")
            def do_work(x):
                return x * 2

            @rec.record(kind="tool_call")
            def noop(x):
                return None

            @rec.record(kind="tool_call")
            def boom(x):
                raise ValueError("nope")

            assert do_work(x=3) == 6
            assert noop(x=1) is None
            try:
                boom(x=1)
            except ValueError:
                pass

        rows = store.actions_for_run(rec.run_id)
    outcomes = [r["outcome"] for r in rows]
    assert outcomes == ["ok", "no_op", "error"]


def test_decorator_payload_is_redacted(tmp_path):
    with Store(tmp_path / "p.db") as store:
        rec = Recorder(store, "t")
        with rec:

            @rec.record(kind="tool_call")
            def call(api_key, q):
                return q

            call(api_key="sk-ant-DECOSECRET0123456789", q="hi")

        rows = store.actions_for_run(rec.run_id)
    assert "sk-ant-DECOSECRET0123456789" not in rows[0]["action_json"]
