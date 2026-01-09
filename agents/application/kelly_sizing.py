from __future__ import annotations


def kelly_fraction(prob_win: float, odds: float, fraction: float = 0.5) -> float:
    """
    Calculate Kelly criterion bet size.

    Args:
        prob_win: Our estimated probability of winning (0-1)
        odds: Decimal odds (e.g., 2.0 for even money)
        fraction: Kelly fraction (0.5 = half-Kelly for safety)

    Returns:
        Fraction of bankroll to bet (0-1)
    """
    if odds <= 1 or prob_win <= 0 or prob_win >= 1 or fraction <= 0:
        return 0.0

    b = odds - 1.0
    q = 1.0 - prob_win
    kelly = (prob_win * b - q) / b

    if kelly <= 0:
        return 0.0

    scaled = kelly * fraction
    return min(max(scaled, 0.0), 1.0)


_kelly_fraction_fn = kelly_fraction


def calculate_bet_size(
    bankroll: float,
    estimated_prob: float,
    market_odds: float,
    max_bet_pct: float = 0.05,
    kelly_fraction: float = 0.5,
) -> float:
    """
    Calculate actual USD bet size with risk limits.

    Returns:
        Amount in USD to bet
    """
    if bankroll <= 0 or max_bet_pct <= 0 or kelly_fraction <= 0:
        return 0.0

    kelly = _kelly_fraction_fn(estimated_prob, market_odds, kelly_fraction)

    if kelly <= 0:
        return 0.0

    bet_fraction = min(kelly, max_bet_pct)
    return bankroll * bet_fraction
