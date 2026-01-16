# Phase 2: Kelly Sizing & Risk Management

**Dependencies:** Phase 1 (Config, Models)

**Tasks:** 2 (can run in parallel)

---

## Task 2.1: Implement Kelly Criterion

**Goal:** Calculate optimal bet sizes using Kelly criterion.

**Files to create:**
- `agents/application/kelly_sizing.py`

**Requirements:**
```python
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

def calculate_bet_size(
    bankroll: float,
    estimated_prob: float,
    market_odds: float,
    max_bet_pct: float = 0.05,
    kelly_fraction: float = 0.5
) -> float:
    """
    Calculate actual USD bet size with risk limits.

    Returns:
        Amount in USD to bet
    """
```

**Kelly Formula:**
```
kelly = (p * b - q) / b

where:
  p = probability of winning
  q = probability of losing (1 - p)
  b = odds received on the bet (decimal odds - 1)
```

**Example:**
- Estimated prob: 60% (p = 0.6)
- Market odds: 2.0 (even money, b = 1.0)
- Kelly = (0.6 * 1.0 - 0.4) / 1.0 = 0.2 (20% of bankroll)
- Half-Kelly = 0.1 (10% of bankroll)

**Success criteria:**
- [ ] Kelly formula correct: kelly = (p*b - q) / b where q = 1-p
- [ ] Returns 0 for negative edge
- [ ] Respects max_bet_pct cap
- [ ] Half-Kelly by default
- [ ] Test: kelly_fraction(0.6, 2.0) should return ~0.1

---

## Task 2.2: Implement Risk Manager

**Goal:** Enforce risk limits before executing trades.

**Files to create:**
- `agents/strategies/risk_manager.py`

**Requirements:**
```python
from agents.utils.config import Config
from agents.utils.models import Signal, Position

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

    def check_position_limits(self, positions: list[Position]) -> tuple[bool, str]:
        """Check if we can open new positions."""

    def check_daily_loss(self, daily_pnl: float, bankroll: float) -> tuple[bool, str]:
        """Check if daily loss limit hit."""

    def check_liquidity(self, bet_size: float, market_volume: float) -> tuple[bool, str]:
        """Check if bet is too large relative to market."""
```

**Risk Rules:**

| Rule | Value | Description |
|------|-------|-------------|
| Max bet per market | 5% of bankroll | No single bet > $25 on $500 bankroll |
| Max daily loss | 10% of bankroll | Stop trading if down $50 today |
| Min edge to bet | 5% | Only bet if edge > 5% |
| Max concurrent positions | 10 | Diversification limit |
| Max bet vs market volume | 10% | Avoid moving the market |

**Success criteria:**
- [ ] All risk checks implemented
- [ ] Returns clear pass/fail with reason
- [ ] Test: Signal with 3% edge should fail min_edge check

---

## Codex Assignment

**Run these 2 tasks in parallel:**
- Task 2.1: Kelly Sizing
- Task 2.2: Risk Manager

**Note:** Both depend on Phase 1 models/config, but are independent of each other.
