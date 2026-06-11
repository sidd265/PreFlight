"""Recording SDK (Phase 1).

Capture every high-stakes agent action *with* its context, running everything
through the redaction pass BEFORE it is persisted (CLAUDE.md §1 / PRD S1). Nothing
raw ever reaches the store.

Usage:

    with Recorder(store) as rec:                 # or Recorder(store).run("nightly")
        rec.record_action(
            kind="payment",
            payload={"amount": 5000, "vendor": "Acme", "api_key": "sk-..."},
            risk="high",
            reversible=False,
            model="claude-haiku-4-5",
            tokens_in=120, tokens_out=40,
            inputs={"prompt": "pay the invoice"},
            outcome="ok",
        )

The decorator form wraps a tool function and records each call:

    @rec.record(kind="tool_call", risk="low")
    def search(query): ...
"""

from __future__ import annotations

import functools
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal

from preflight.hashchain import content_hash
from preflight.pricing import cost_usd
from preflight.redaction import redact
from preflight.schema import Action, Context, Risk
from preflight.store import Store

Outcome = Literal["ok", "no_op", "error"]


def _prompt_hash(inputs: dict[str, Any], model: str) -> str:
    """Fingerprint of the (redacted) inputs + model, for replay/comparison."""
    return content_hash({"inputs": inputs, "model": model})


def action_fingerprint(kind: str, redacted_payload: dict[str, Any]) -> str:
    """Stable fingerprint of an action by kind + redacted payload.

    Computed from already-redacted payload so it never depends on raw secrets.
    Used by waste detection to spot duplicate/looping actions.
    """
    return content_hash({"kind": kind, "payload": redacted_payload})


class Recorder:
    """Records actions into a Store, grouped under a single run."""

    def __init__(self, store: Store, run_name: str = "default"):
        self._store = store
        self._run_name = run_name
        self.run_id: str | None = None

    # --- run lifecycle ---
    def run(self, name: str) -> Recorder:
        self._run_name = name
        return self

    def _ensure_run(self) -> str:
        if self.run_id is None:
            self.run_id = uuid.uuid4().hex
            self._store.create_run(
                self.run_id, self._run_name, datetime.now(UTC).isoformat()
            )
        return self.run_id

    def __enter__(self) -> Recorder:
        self._ensure_run()
        return self

    def __exit__(self, *exc: object) -> None:
        # Nothing to flush — each action is persisted immediately.
        return None

    # --- recording ---
    def record_action(
        self,
        *,
        kind: str,
        payload: dict[str, Any] | None = None,
        risk: Risk = "low",
        reversible: bool = True,
        model: str = "unknown",
        tokens_in: int = 0,
        tokens_out: int = 0,
        inputs: dict[str, Any] | None = None,
        outcome: Outcome = "ok",
        action_id: str | None = None,
    ) -> Action:
        """Redact, build, and persist one Action. Returns the redacted Action."""
        run_id = self._ensure_run()

        # REDACT BEFORE ANYTHING IS BUILT OR PERSISTED.
        redacted_payload = redact(payload or {})
        redacted_inputs = redact(inputs or {})

        cost = cost_usd(model, tokens_in, tokens_out)
        context = Context(
            inputs=redacted_inputs,
            model=model,
            prompt_hash=_prompt_hash(redacted_inputs, model),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
        )
        action = Action(
            id=action_id or uuid.uuid4().hex,
            kind=kind,
            payload=redacted_payload,
            risk=risk,
            reversible=reversible,
            context=context,
        )

        fingerprint = action_fingerprint(kind, redacted_payload)
        self._store.add_recorded_action(
            run_id=run_id,
            action_json=json.dumps(action.model_dump(), sort_keys=True, default=str),
            outcome=outcome,
            fingerprint=fingerprint,
            cost_usd=cost,
        )
        return action

    def record(
        self,
        *,
        kind: str,
        risk: Risk = "low",
        reversible: bool = True,
        model: str = "unknown",
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator: record each call of a tool function as an action.

        The function's keyword arguments are captured as the payload (redacted).
        If the call raises, it is recorded with outcome="error" and re-raised.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                outcome: Outcome = "ok"
                try:
                    result = func(*args, **kwargs)
                    if result is None:
                        outcome = "no_op"
                    return result
                except Exception:
                    outcome = "error"
                    raise
                finally:
                    self.record_action(
                        kind=kind,
                        payload=dict(kwargs),
                        risk=risk,
                        reversible=reversible,
                        model=model,
                        outcome=outcome,
                    )

            return wrapper

        return decorator
