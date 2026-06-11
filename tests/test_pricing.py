"""Phase 1: token -> cost math is correct (CLAUDE.md: per-model pricing)."""

from __future__ import annotations

from preflight.pricing import DEFAULT_PRICING, cost_usd


def test_known_model_cost():
    # claude-haiku-4-5 = (1.0, 5.0) per 1M tokens.
    # 1,000,000 in + 1,000,000 out = 1.0 + 5.0 = 6.0
    assert cost_usd("claude-haiku-4-5", 1_000_000, 1_000_000) == 6.0


def test_partial_tokens():
    # 200 in, 80 out at (1.0, 5.0)/1M = (200*1 + 80*5)/1e6 = 600/1e6
    assert cost_usd("claude-haiku-4-5", 200, 80) == 600 / 1_000_000


def test_zero_tokens_zero_cost():
    assert cost_usd("claude-haiku-4-5", 0, 0) == 0.0


def test_unknown_model_uses_nonzero_default():
    in_p, out_p = DEFAULT_PRICING
    expected = (1_000_000 * in_p + 1_000_000 * out_p) / 1_000_000
    assert cost_usd("some-unknown-model", 1_000_000, 1_000_000) == expected
    assert expected > 0  # unknown spend must not be hidden as $0
