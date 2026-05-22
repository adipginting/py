"""Tests for TokenUsage value object."""

from py_coding_agent.domain.token_usage import TokenUsage


def test_token_usage_starts_at_zero() -> None:
    """Default TokenUsage has zero input and output tokens."""
    usage = TokenUsage()

    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.total_tokens == 0


def test_token_usage_addition() -> None:
    """Adding two TokenUsage values sums their components."""
    first = TokenUsage(input_tokens=10, output_tokens=5)
    second = TokenUsage(input_tokens=3, output_tokens=2)

    result = first + second

    assert result.input_tokens == 13
    assert result.output_tokens == 7
    assert result.total_tokens == 20


def test_token_usage_addition_is_immutable() -> None:
    """Adding TokenUsage values does not mutate the originals."""
    first = TokenUsage(input_tokens=10, output_tokens=5)
    second = TokenUsage(input_tokens=3, output_tokens=2)

    _ = first + second

    assert first.input_tokens == 10
    assert second.output_tokens == 2
