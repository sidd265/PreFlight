"""Token -> cost math (PRD §5 Context.cost_usd; CLAUDE.md: per-model pricing).

Prices are USD per 1,000,000 tokens, (input, output). These are approximate list
prices and are intentionally easy to read and override — keep them current per the
provider's pricing page. Unknown models fall back to a conservative default rather
than silently costing $0 (which would hide spend).
"""

from __future__ import annotations

# USD per 1M tokens: model -> (input_price, output_price)
PRICING: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-opus-4-8": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    # OpenAI (illustrative)
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
}

# Used when a model is not in the table. Conservative (non-zero) so unknown spend
# is visible rather than hidden.
DEFAULT_PRICING: tuple[float, float] = (3.0, 15.0)

_PER_TOKEN = 1_000_000.0


def price_for(model: str) -> tuple[float, float]:
    return PRICING.get(model, DEFAULT_PRICING)


def cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    """Cost in USD for a call with the given token counts under `model`'s pricing."""
    in_price, out_price = price_for(model)
    return (tokens_in * in_price + tokens_out * out_price) / _PER_TOKEN
