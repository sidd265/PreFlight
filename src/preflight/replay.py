"""Deterministic replay (Phase 2).

Load a frozen golden, run each action through the pure decision function under a
frozen policy, and produce a list of decisions. Determinism guarantee: the same
golden + same policy yields byte-identical decisions every time (no network, no
randomness, no live tool calls).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel

from preflight.decision import DecisionPolicy, decide
from preflight.golden import load_golden_actions
from preflight.recorder import action_fingerprint
from preflight.schema import Risk, Verdict
from preflight.store import Store


class ReplayDecision(BaseModel):
    seq: int
    action_id: str
    kind: str
    risk: Risk
    verdict: Verdict
    fingerprint: str


class ReplayResult(BaseModel):
    replay_id: str
    golden_name: str
    policy: DecisionPolicy
    decisions: list[ReplayDecision]

    def digest(self) -> str:
        """Stable hash of the decisions — equal iff replay reproduced identically."""
        payload = json.dumps(
            [d.model_dump() for d in self.decisions], sort_keys=True, default=str
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def replay(
    store: Store, name: str, policy: DecisionPolicy | None = None, *, persist: bool = True
) -> ReplayResult:
    """Replay a golden deterministically under `policy`."""
    policy = policy or DecisionPolicy()
    actions = load_golden_actions(store, name)

    decisions: list[ReplayDecision] = []
    for seq, action in enumerate(actions):
        verdict = decide(action, policy)
        decisions.append(
            ReplayDecision(
                seq=seq,
                action_id=action.id,
                kind=action.kind,
                risk=action.risk,
                verdict=verdict,
                fingerprint=action_fingerprint(action.kind, action.payload),
            )
        )

    result = ReplayResult(
        replay_id=uuid.uuid4().hex,
        golden_name=name,
        policy=policy,
        decisions=decisions,
    )

    if persist:
        store.save_replay(
            replay_id=result.replay_id,
            golden_name=name,
            policy_json=policy.model_dump_json(),
            decisions_json=json.dumps([d.model_dump() for d in decisions], default=str),
            created_at=datetime.now(UTC).isoformat(),
        )
    return result


def load_replay_decisions(store: Store, replay_id: str) -> list[ReplayDecision]:
    row = store.get_replay(replay_id)
    if row is None:
        raise ValueError(f"replay '{replay_id}' not found")
    return [ReplayDecision.model_validate(d) for d in json.loads(row["decisions_json"])]
