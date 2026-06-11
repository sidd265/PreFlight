"""Sample agent — the fixture every later phase tests against (PRD §8).

It deliberately:
  * does some REAL work (distinct, useful actions),
  * WASTES effort (a repeated/looping action and a no-op dead end),
  * carries a PLANTED FAKE API KEY in its context, so tests can prove redaction
    keeps it out of everything Preflight stores.

The planted key below is fake and exists only to exercise redaction. Do NOT put a
real secret here.
"""

from __future__ import annotations

from preflight.recorder import Recorder
from preflight.store import Store

# Fake, non-functional credential used purely to test redaction. Not a real secret.
PLANTED_FAKE_API_KEY = "sk-ant-PLANTEDFAKEKEY0123456789ABCDEF"  # noqa: S105


def run_sample_agent(store: Store, run_name: str = "sample") -> str:
    """Run the deterministic sample agent against a store. Returns the run id."""
    rec = Recorder(store, run_name)
    with rec:
        # The agent's "context" includes secrets it saw — these must be redacted.
        agent_context = {
            "prompt": "Process the vendor invoice and pay it.",
            "api_key": PLANTED_FAKE_API_KEY,
            "auth_header": f"Bearer {PLANTED_FAKE_API_KEY}",
        }

        # 1) REAL: look up the invoice.
        rec.record_action(
            kind="tool_call",
            payload={"tool": "lookup_invoice", "invoice_id": "INV-1001"},
            risk="low",
            reversible=True,
            model="claude-haiku-4-5",
            tokens_in=200,
            tokens_out=80,
            inputs=agent_context,
            outcome="ok",
        )

        # 2) REAL: check the vendor.
        rec.record_action(
            kind="tool_call",
            payload={"tool": "check_vendor", "vendor": "Acme"},
            risk="low",
            reversible=True,
            model="claude-haiku-4-5",
            tokens_in=150,
            tokens_out=60,
            inputs=agent_context,
            outcome="ok",
        )

        # 3) WASTE: loop — repeats the exact same vendor check twice more.
        for _ in range(2):
            rec.record_action(
                kind="tool_call",
                payload={"tool": "check_vendor", "vendor": "Acme"},
                risk="low",
                reversible=True,
                model="claude-haiku-4-5",
                tokens_in=150,
                tokens_out=60,
                inputs=agent_context,
                outcome="ok",
            )

        # 4) WASTE: a no-op dead end that produced nothing.
        rec.record_action(
            kind="tool_call",
            payload={"tool": "search_notes", "query": "discount?"},
            risk="low",
            reversible=True,
            model="claude-haiku-4-5",
            tokens_in=300,
            tokens_out=0,
            inputs=agent_context,
            outcome="no_op",
        )

        # 5) REAL: the high-stakes payment.
        rec.record_action(
            kind="payment",
            payload={"amount": 5000, "vendor": "Acme", "api_key": PLANTED_FAKE_API_KEY},
            risk="high",
            reversible=False,
            model="claude-haiku-4-5",
            tokens_in=400,
            tokens_out=120,
            inputs=agent_context,
            outcome="ok",
        )

    if rec.run_id is None:  # pragma: no cover - run() always assigns an id
        raise RuntimeError("sample agent run failed to start")
    return rec.run_id
