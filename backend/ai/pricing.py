"""List prices in USD per million tokens (Anthropic first-party API, 2026-10).

Cache writes (5-minute TTL) cost 1.25x input; cache reads are much cheaper than
input, which is what makes sending the same evidence once per section affordable.
Verify against the live price list before relying on these for billing.
"""
from decimal import Decimal

PRICES = {
    # model: (input, output, cache_read)
    "claude-opus-5-5": (Decimal("4"), Decimal("20"), Decimal("0.20")),
    "claude-opus-5": (Decimal("5"), Decimal("25"), Decimal("0.50")),
    "claude-sonnet-5-5": (Decimal("2"), Decimal("10"), Decimal("0.20")),
    "claude-sonnet-5": (Decimal("2"), Decimal("10"), Decimal("0.20")),
    "claude-haiku-5-5": (Decimal("0.10"), Decimal("0.50"), Decimal("0.01")),
}
CACHE_WRITE_MULTIPLIER = Decimal("1.25")
MILLION = Decimal(1_000_000)


def cost_usd(model, input_tokens=0, output_tokens=0, cache_read_tokens=0, cache_write_tokens=0):
    if model not in PRICES:
        return None  # unknown model: usage is still recorded, cost is not guessed
    input_price, output_price, cache_read_price = PRICES[model]
    total = (
        input_tokens * input_price
        + output_tokens * output_price
        + cache_read_tokens * cache_read_price
        + cache_write_tokens * input_price * CACHE_WRITE_MULTIPLIER
    ) / MILLION
    return total.quantize(Decimal("0.000001"))
