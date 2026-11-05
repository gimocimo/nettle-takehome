from decimal import Decimal

from ai.pricing import cost_usd


def test_cost_counts_cache_reads_and_writes_at_their_own_prices():
    cost = cost_usd(
        "claude-opus-5-5",
        input_tokens=1_000_000,
        output_tokens=100_000,
        cache_read_tokens=1_000_000,
        cache_write_tokens=1_000_000,
    )
    # 4 + 2 + 0.20 + 5 (1.25 x input)
    assert cost == Decimal("11.200000")


def test_unknown_models_are_not_priced():
    assert cost_usd("some-future-model", input_tokens=10) is None
