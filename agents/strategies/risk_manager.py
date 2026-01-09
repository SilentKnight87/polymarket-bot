from __future__ import annotations

from agents.utils.config import Config
from agents.utils.models import Position, Signal


class RiskManager:
    def __init__(self, config: Config):
        self.max_bet_pct = config.max_bet_pct
        self.max_daily_loss_pct = config.max_daily_loss_pct
        self.min_edge = config.min_edge
        self.max_positions = 10
        self.max_market_volume_pct = 0.10

    def check_signal(self, signal: Signal) -> tuple[bool, str]:
        """
        Check if signal passes risk filters.
        Returns (passed, reason)
        """
        if signal.edge < self.min_edge:
            return False, f"edge {signal.edge:.3f} below min_edge {self.min_edge:.3f}"
        return True, "passed"

    def check_position_limits(self, positions: list[Position]) -> tuple[bool, str]:
        """Check if we can open new positions."""
        if len(positions) >= self.max_positions:
            return False, f"max positions reached ({self.max_positions})"
        return True, "passed"

    def check_daily_loss(self, daily_pnl: float, bankroll: float) -> tuple[bool, str]:
        """Check if daily loss limit hit."""
        if bankroll <= 0:
            return False, "bankroll <= 0"
        limit = -self.max_daily_loss_pct * bankroll
        if daily_pnl <= limit:
            return False, f"daily loss {daily_pnl:.2f} exceeds limit {limit:.2f}"
        return True, "passed"

    def check_liquidity(self, bet_size: float, market_volume: float) -> tuple[bool, str]:
        """Check if bet is too large relative to market."""
        if market_volume <= 0:
            return False, "market volume unavailable"
        if bet_size > self.max_market_volume_pct * market_volume:
            return (
                False,
                f"bet size {bet_size:.2f} exceeds {self.max_market_volume_pct:.0%} of market volume",
            )
        return True, "passed"
