# Phase 7: Performance Tracking

**Dependencies:** Phase 6 (Paper Trading)

**Tasks:** 1

---

## Task 7.1: Implement Performance Tracker

**Goal:** Calculate and store performance metrics.

**Files to create:**
- `agents/tracking/performance.py`

**Requirements:**
```python
from agents.utils.models import PerformanceMetrics
from datetime import date
import sqlite3
import math

class PerformanceTracker:
    def __init__(self, db_path: str = "data/performance.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        """Create performance tables."""

    def record_bet_result(self, bet_id: str, pnl: float):
        """Record outcome of a bet."""

    def get_daily_metrics(self, d: date = None) -> PerformanceMetrics:
        """Get metrics for a specific day."""

    def get_all_time_metrics(self) -> PerformanceMetrics:
        """Get cumulative metrics."""

    def calculate_sharpe_ratio(self, daily_returns: list[float]) -> float:
        """Calculate Sharpe ratio from daily returns."""

    def calculate_max_drawdown(self, equity_curve: list[float]) -> float:
        """Calculate maximum drawdown."""
```

**Database Schema:**
```sql
-- Daily performance snapshots
CREATE TABLE IF NOT EXISTS daily_performance (
    date TEXT PRIMARY KEY,
    starting_bankroll REAL,
    ending_bankroll REAL,
    total_pnl REAL,
    num_bets INTEGER,
    wins INTEGER,
    losses INTEGER,
    avg_edge REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Individual bet results
CREATE TABLE IF NOT EXISTS bet_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bet_id TEXT UNIQUE,
    market_id TEXT,
    direction TEXT,
    amount REAL,
    odds REAL,
    outcome TEXT,  -- 'win', 'lose'
    pnl REAL,
    edge_at_entry REAL,
    resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Metrics to Track:**

| Metric | Formula | Target |
|--------|---------|--------|
| Total P&L | Sum of all bet P&L | Positive |
| Win Rate | Wins / Total Bets | > 55% |
| Average Edge | Mean edge at entry | > 5% |
| Sharpe Ratio | Mean return / Std dev | > 1.0 |
| Max Drawdown | Largest peak-to-trough | < 20% |
| Bets per Day | Count of bets | 5-20 |

**Sharpe Ratio Calculation:**
```python
def calculate_sharpe_ratio(self, daily_returns: list[float]) -> float:
    """
    Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns

    Assuming risk-free rate = 0 for simplicity
    Annualized: multiply by sqrt(365)
    """
    if len(daily_returns) < 2:
        return 0.0

    mean_return = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return 0.0

    daily_sharpe = mean_return / std_dev
    annualized_sharpe = daily_sharpe * math.sqrt(365)

    return annualized_sharpe
```

**Max Drawdown Calculation:**
```python
def calculate_max_drawdown(self, equity_curve: list[float]) -> float:
    """
    Max Drawdown = (Peak - Trough) / Peak

    Returns percentage (0.0 to 1.0)
    """
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve[0]
    max_dd = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak
        if drawdown > max_dd:
            max_dd = drawdown

    return max_dd
```

**Example Usage:**
```python
from agents.tracking.performance import PerformanceTracker
from datetime import date

tracker = PerformanceTracker()

# Record bet results
tracker.record_bet_result("bet_001", pnl=15.50)
tracker.record_bet_result("bet_002", pnl=-10.00)
tracker.record_bet_result("bet_003", pnl=8.25)

# Get today's metrics
metrics = tracker.get_daily_metrics(date.today())
print(f"Today's P&L: ${metrics.total_pnl:.2f}")
print(f"Win Rate: {metrics.win_rate:.1%}")

# Get all-time metrics
all_time = tracker.get_all_time_metrics()
print(f"All-time P&L: ${all_time.total_pnl:.2f}")
print(f"Max Drawdown: {all_time.max_drawdown:.1%}")
```

**Success criteria:**
- [ ] All metrics calculated correctly
- [ ] Data persisted to SQLite
- [ ] Test: Record 10 bets, verify metrics

---

## Codex Assignment

**Run Task 7.1** - Can run in parallel with Task 6.1 since they use separate databases.
