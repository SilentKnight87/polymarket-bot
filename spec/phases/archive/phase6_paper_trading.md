# Phase 6: Paper Trading Mode

**Dependencies:** Phase 5 (Agent Loop)

**Tasks:** 1

---

## Task 6.1: Implement Paper Trade Executor

**Goal:** Simulate trades without real execution.

**Files to create:**
- `agents/tracking/paper_trade.py`

**Requirements:**
```python
from agents.utils.models import Bet, Position
import sqlite3

class PaperTradeExecutor:
    def __init__(self, db_path: str = "data/paper_trades.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        """Create tables for paper positions and trades."""

    def execute_trade(self, bet: Bet) -> bool:
        """
        Simulate trade execution.
        - Deduct from paper bankroll
        - Add to paper positions
        - Log the trade
        """

    def get_positions(self) -> list[Position]:
        """Get all open paper positions."""

    def get_bankroll(self) -> float:
        """Get current paper bankroll."""

    def resolve_position(self, market_id: str, outcome: str) -> float:
        """
        Resolve a position when market settles.
        Returns P&L.
        """
```

**Database Schema:**
```sql
-- Paper bankroll tracking
CREATE TABLE IF NOT EXISTS bankroll (
    id INTEGER PRIMARY KEY,
    amount REAL NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Paper trades
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    market_id TEXT NOT NULL,
    direction TEXT NOT NULL,  -- 'YES' or 'NO'
    amount_usd REAL NOT NULL,
    odds_at_execution REAL NOT NULL,
    shares REAL NOT NULL,
    status TEXT DEFAULT 'open',  -- 'open', 'resolved'
    outcome TEXT,  -- 'win', 'lose' (null until resolved)
    pnl REAL  -- null until resolved
);

-- Paper positions (derived from trades, but cached for speed)
CREATE TABLE IF NOT EXISTS positions (
    market_id TEXT PRIMARY KEY,
    direction TEXT NOT NULL,
    shares REAL NOT NULL,
    avg_price REAL NOT NULL,
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Paper Trade Flow:**
```
Signal arrives
     │
     ▼
┌─────────────────┐
│ Check bankroll  │ Do we have enough?
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ Calculate shares│ shares = amount / odds
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ Deduct bankroll │ bankroll -= amount
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ Insert trade    │ Record in trades table
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ Update position │ Add to positions table
└─────────────────┘
```

**Resolution Flow:**
```
Market resolves (YES wins)
     │
     ▼
┌─────────────────┐
│ Find position   │ Get our position for this market
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ Calculate P&L   │ If we bet YES: pnl = shares * 1.0 - cost
│                 │ If we bet NO: pnl = -cost (lost)
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ Update bankroll │ bankroll += shares (if won)
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ Close position  │ Remove from positions, update trade status
└─────────────────┘
```

**Example Usage:**
```python
from agents.tracking.paper_trade import PaperTradeExecutor
from agents.utils.models import Bet
from datetime import datetime

executor = PaperTradeExecutor()

# Execute a paper trade
bet = Bet(
    timestamp=datetime.now(),
    market_id="abc123",
    direction="YES",
    amount_usd=25.0,
    odds_at_execution=0.60,
    estimated_prob=0.75,
    kelly_fraction=0.5,
    mode="paper"
)

executor.execute_trade(bet)
print(f"Bankroll: ${executor.get_bankroll():.2f}")
print(f"Positions: {executor.get_positions()}")

# Later, when market resolves
pnl = executor.resolve_position("abc123", outcome="YES")
print(f"P&L: ${pnl:.2f}")
```

**Success criteria:**
- [ ] Trades recorded in SQLite
- [ ] Bankroll tracked correctly
- [ ] Positions updated on resolution
- [ ] Test: Execute paper trade, verify position created

---

## Codex Assignment

**Run Task 6.1** - This enables safe testing before going live.
