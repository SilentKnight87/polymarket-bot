# Phase 8: Backtesting Framework

**Dependencies:** Phase 4 (Strategy), Phase 7 (Performance)

**Tasks:** 1

---

## Task 8.1: Create Backtest Runner

**Goal:** Run strategies on historical data.

**Files to create:**
- `agents/tracking/backtest.py`

**Requirements:**
```python
from datetime import datetime
from dataclasses import dataclass
from agents.strategies.base_strategy import BaseStrategy
from agents.tracking.performance import PerformanceTracker

@dataclass
class BacktestResult:
    total_pnl: float
    win_rate: float
    num_trades: int
    sharpe_ratio: float
    max_drawdown: float
    trades: list[dict]

class BacktestRunner:
    def __init__(
        self,
        strategy: BaseStrategy,
        start_date: datetime,
        end_date: datetime,
        initial_bankroll: float = 500.0
    ):
        self.strategy = strategy
        self.start_date = start_date
        self.end_date = end_date
        self.initial_bankroll = initial_bankroll
        self.trades = []
        self.equity_curve = [initial_bankroll]

    def load_historical_data(self):
        """Load historical news and market data."""

    def run(self) -> BacktestResult:
        """
        Run backtest simulation.

        For each day in range:
        1. Get news articles for that day
        2. Get market state at that time
        3. Generate signals
        4. Simulate execution
        5. Check resolutions
        6. Track P&L
        """

    def get_results(self) -> BacktestResult:
        """Return backtest metrics and trade log."""
```

**Backtest Flow:**
```
┌─────────────────────────────────────────────────────────┐
│                   BACKTEST RUNNER                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  for each day in (start_date → end_date):               │
│                                                         │
│  1. Load historical news for this day                   │
│     └─ From data/historical/news/YYYY-MM-DD.json        │
│                                                         │
│  2. Load market snapshots for this day                  │
│     └─ From data/historical/markets/YYYY-MM-DD.json     │
│                                                         │
│  3. Run strategy.generate_signals(news, markets)        │
│                                                         │
│  4. For each signal:                                    │
│     ├─ Apply risk checks                                │
│     ├─ Calculate Kelly bet size                         │
│     └─ Simulate execution at historical odds            │
│                                                         │
│  5. Check for resolutions                               │
│     └─ Did any markets we bet on resolve today?         │
│                                                         │
│  6. Update equity curve                                 │
│     └─ equity_curve.append(current_bankroll)            │
│                                                         │
│  return BacktestResult(...)                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Historical Data Format:**

**News (data/historical/news/YYYY-MM-DD.json):**
```json
{
  "date": "2025-12-01",
  "articles": [
    {
      "headline": "Fed announces rate decision",
      "summary": "Federal Reserve holds rates steady...",
      "source": "reuters",
      "published_at": "2025-12-01T14:30:00Z",
      "category": "politics"
    }
  ]
}
```

**Markets (data/historical/markets/YYYY-MM-DD.json):**
```json
{
  "date": "2025-12-01",
  "markets": [
    {
      "market_id": "abc123",
      "question": "Will Fed raise rates in December?",
      "yes_price": 0.35,
      "no_price": 0.65,
      "volume_24h": 150000,
      "resolved": false,
      "outcome": null
    }
  ]
}
```

**Resolutions (data/historical/resolutions/YYYY-MM-DD.json):**
```json
{
  "date": "2025-12-01",
  "resolutions": [
    {
      "market_id": "xyz789",
      "outcome": "YES",
      "resolved_at": "2025-12-01T18:00:00Z"
    }
  ]
}
```

**Example Usage:**
```python
from agents.tracking.backtest import BacktestRunner
from agents.strategies.news_speed import NewsSpeedStrategy
from agents.utils.config import Config
from datetime import datetime

config = Config()
strategy = NewsSpeedStrategy(config)

runner = BacktestRunner(
    strategy=strategy,
    start_date=datetime(2025, 11, 1),
    end_date=datetime(2025, 12, 1),
    initial_bankroll=500.0
)

# Load historical data
runner.load_historical_data()

# Run backtest
result = runner.run()

# Print results
print(f"Total P&L: ${result.total_pnl:.2f}")
print(f"Win Rate: {result.win_rate:.1%}")
print(f"Num Trades: {result.num_trades}")
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
print(f"Max Drawdown: {result.max_drawdown:.1%}")
```

**CLI Integration:**
```bash
# Run backtest
python scripts/python/cli.py backtest \
    --strategy news_speed \
    --start 2025-11-01 \
    --end 2025-12-01 \
    --bankroll 500

# Output
Backtest Results: news_speed
─────────────────────────────
Period: 2025-11-01 to 2025-12-01
Initial Bankroll: $500.00
Final Bankroll: $623.45
─────────────────────────────
Total P&L: $123.45
Win Rate: 58.3%
Num Trades: 24
Sharpe Ratio: 1.45
Max Drawdown: 8.2%
```

**Note:** Historical data collection is a separate concern. This task assumes data exists in `data/historical/`. A future task could automate data collection.

**Success criteria:**
- [ ] Simulates strategy over date range
- [ ] Calculates accurate P&L
- [ ] Returns comprehensive results
- [ ] Test: Run backtest on sample data

---

## Codex Assignment

**Run Task 8.1** - This is the final phase, enabling strategy validation before paper/live trading.
