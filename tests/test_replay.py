"""Phase 2: golden save + deterministic replay reproducibility."""

from __future__ import annotations

from examples.sample_agent import run_sample_agent

from preflight.decision import DecisionPolicy
from preflight.golden import load_golden_actions, save_golden
from preflight.replay import replay
from preflight.store import Store


def _seed_golden(store: Store, name="g") -> None:
    run_sample_agent(store)
    save_golden(store, name)


def test_save_golden_freezes_actions(tmp_path):
    with Store(tmp_path / "p.db") as store:
        run_id = run_sample_agent(store)
        count = save_golden(store, "g")
        actions = load_golden_actions(store, "g")
        recorded = store.actions_for_run(run_id)
    assert count == len(recorded) == len(actions)
    assert actions[0].kind == "tool_call"


def test_replay_is_reproducible(tmp_path):
    with Store(tmp_path / "p.db") as store:
        _seed_golden(store)
        r1 = replay(store, "g", persist=False)
        r2 = replay(store, "g", persist=False)
    # Same golden + same policy => byte-identical decisions.
    assert r1.digest() == r2.digest()
    assert [d.verdict for d in r1.decisions] == [d.verdict for d in r2.decisions]


def test_replay_high_risk_payment_not_auto_allowed(tmp_path):
    with Store(tmp_path / "p.db") as store:
        _seed_golden(store)
        result = replay(store, "g", persist=False)
    payment = [d for d in result.decisions if d.kind == "payment"][0]
    # amount 5000, high-risk irreversible -> needs_approval (never silently allowed).
    assert payment.verdict == "needs_approval"


def test_policy_change_changes_replay(tmp_path):
    with Store(tmp_path / "p.db") as store:
        _seed_golden(store)
        default = replay(store, "g", persist=False)
        strict = replay(
            store, "g", DecisionPolicy(payment_block_threshold=1_000), persist=False
        )
    pay_default = [d for d in default.decisions if d.kind == "payment"][0]
    pay_strict = [d for d in strict.decisions if d.kind == "payment"][0]
    assert pay_default.verdict == "needs_approval"
    assert pay_strict.verdict == "block"


def test_replay_persists_and_loads(tmp_path):
    from preflight.replay import load_replay_decisions

    with Store(tmp_path / "p.db") as store:
        _seed_golden(store)
        result = replay(store, "g")
        loaded = load_replay_decisions(store, result.replay_id)
    assert [d.verdict for d in loaded] == [d.verdict for d in result.decisions]
