# Phase 1: Configuration & Infrastructure

**Dependencies:** None (start here)

**Tasks:** 3 (can run in parallel)

---

## Task 1.1: Create Configuration System

**Goal:** Set up YAML-based configuration with environment variable support.

**Files to create:**
- `config/settings.yaml` - Main bot configuration
- `config/strategies.yaml` - Strategy parameters
- `agents/utils/config.py` - Config loader with env var interpolation

**Requirements:**
```python
# config.py should provide:
class Config:
    def __init__(self, config_path: str = "config/settings.yaml"):
        ...

    @property
    def trading_mode(self) -> str:  # "backtest", "paper", "live"

    @property
    def bankroll(self) -> float:

    @property
    def max_bet_pct(self) -> float:

    @property
    def min_edge(self) -> float:

    @property
    def kelly_fraction(self) -> float:
```

**Config structure (settings.yaml):**
```yaml
polymarket:
  api_key: ${POLYMARKET_API_KEY}
  wallet_address: ${WALLET_ADDRESS}

trading:
  mode: paper  # backtest, paper, live
  bankroll: 500.0
  max_bet_pct: 0.05
  max_daily_loss_pct: 0.10
  min_edge: 0.05
  kelly_fraction: 0.5

news:
  sources:
    - rss_politics
    - rss_crypto
  check_interval_seconds: 60

strategies:
  news_speed:
    enabled: true
    weight: 1.0
```

**Success criteria:**
- [ ] Config loads from YAML
- [ ] Environment variables interpolated (${VAR} syntax)
- [ ] Defaults work if config missing
- [ ] Test: `python -c "from agents.utils.config import Config; c = Config(); print(c.trading_mode)"`

---

## Task 1.2: Create Logging Infrastructure

**Goal:** Set up structured JSONL logging for bets, signals, and performance.

**Files to create:**
- `agents/tracking/logger.py` - Structured logger
- `data/logs/.gitkeep` - Ensure logs directory exists

**Requirements:**
```python
# logger.py should provide:
class BotLogger:
    def __init__(self, log_dir: str = "data/logs"):
        ...

    def log_signal(self, signal: dict) -> None:
        """Log to signals/YYYY-MM-DD.jsonl"""

    def log_bet(self, bet: dict) -> None:
        """Log to bets/YYYY-MM-DD.jsonl"""

    def log_performance(self, metrics: dict) -> None:
        """Log to performance/daily_summary.json"""
```

**Log format (JSONL):**
```json
{"timestamp": "2026-01-08T12:00:00Z", "market_id": "123", "direction": "YES", "edge": 0.15, "confidence": 8}
```

**Success criteria:**
- [ ] Logs written to correct date-stamped files
- [ ] JSONL format (one JSON per line)
- [ ] Logs directory auto-created if missing
- [ ] Test: Log a signal, verify file created

---

## Task 1.3: Create Data Models

**Goal:** Define Pydantic models for signals, bets, positions, and markets.

**Files to create:**
- `agents/utils/models.py` - Data models

**Requirements:**
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal

class Signal(BaseModel):
    timestamp: datetime
    market_id: str
    market_question: str
    direction: Literal["YES", "NO"]
    current_odds: float
    estimated_prob: float
    edge: float
    confidence: int  # 1-10
    reasoning: str
    news_headline: str

class Bet(BaseModel):
    timestamp: datetime
    market_id: str
    direction: Literal["YES", "NO"]
    amount_usd: float
    odds_at_execution: float
    estimated_prob: float
    kelly_fraction: float
    mode: Literal["backtest", "paper", "live"]
    signal_id: Optional[str] = None

class Position(BaseModel):
    market_id: str
    direction: Literal["YES", "NO"]
    shares: float
    avg_price: float
    current_price: float
    unrealized_pnl: float

class PerformanceMetrics(BaseModel):
    date: str
    total_pnl: float
    win_rate: float
    num_bets: int
    avg_edge: float
    max_drawdown: float
```

**Success criteria:**
- [ ] All models validate correctly
- [ ] JSON serialization works
- [ ] Test: Create Signal, serialize to JSON

---

## Codex Assignment

**Run these 3 tasks in parallel:**
- Task 1.1: Config System
- Task 1.2: Logging
- Task 1.3: Data Models

**Estimated completion:** All 3 can run simultaneously since they have no interdependencies.
