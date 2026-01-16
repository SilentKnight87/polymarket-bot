# Phase 5: Agent Loop

**Dependencies:** Phase 2 (Risk), Phase 3 (News), Phase 4 (Strategy)

**Tasks:** 2 (must run sequentially: 5.1 then 5.2)

---

## Task 5.1: Implement Main Agent Loop

**Goal:** Create the continuous SENSE -> THINK -> ACT -> TRACK loop.

**Files to create:**
- `agents/application/agent_loop.py`

**Requirements:**
```python
from apscheduler.schedulers.blocking import BlockingScheduler
from agents.utils.config import Config
from agents.connectors.news_sources import NewsAggregator
from agents.strategies.news_speed import NewsSpeedStrategy
from agents.strategies.risk_manager import RiskManager
from agents.application.kelly_sizing import calculate_bet_size
from agents.tracking.logger import BotLogger

class AgentLoop:
    def __init__(self, config: Config):
        self.config = config
        self.news = NewsAggregator(config)
        self.strategy = NewsSpeedStrategy(config)
        self.risk = RiskManager(config)
        self.logger = BotLogger()
        self.scheduler = BlockingScheduler()

    def run(self):
        """Start the agent loop."""
        self.scheduler.add_job(
            self._tick,
            'interval',
            seconds=self.config.check_interval
        )
        self.scheduler.start()

    def _tick(self):
        """One iteration of the agent loop."""
        # 1. SENSE
        articles = self.news.fetch_new_articles()
        markets = self._fetch_markets()
        positions = self._fetch_positions()

        # 2. THINK
        signals = self.strategy.generate_signals(articles, markets)

        # 3. ACT
        for signal in signals:
            passed, reason = self.risk.check_signal(signal)
            if passed:
                self._execute_signal(signal)
            else:
                self.logger.log_signal({**signal.dict(), "rejected": reason})

        # 4. TRACK
        self._check_resolutions()
        self._update_performance()

    def _fetch_markets(self) -> list[dict]:
        """Fetch current markets from Polymarket."""

    def _fetch_positions(self) -> list:
        """Fetch current positions."""

    def _execute_signal(self, signal: Signal):
        """Execute trade based on signal and mode (paper/live)."""

    def _check_resolutions(self):
        """Check if any positions have resolved."""

    def _update_performance(self):
        """Update daily performance metrics."""
```

**Agent Loop Diagram:**
```
┌─────────────────────────────────────────────────────────┐
│                     AGENT LOOP (60s)                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. SENSE                                               │
│     ├─ Fetch new RSS articles                           │
│     ├─ Fetch active Polymarket markets                  │
│     └─ Fetch current positions                          │
│                                                         │
│  2. THINK                                               │
│     ├─ Run NewsSpeedStrategy                            │
│     ├─ LLM: Map news → affected markets                 │
│     ├─ Calculate edge vs market odds                    │
│     └─ Generate signals (if edge > threshold)           │
│                                                         │
│  3. ACT                                                 │
│     ├─ Risk check each signal                           │
│     ├─ Calculate Kelly bet size                         │
│     └─ Execute trade (paper or live)                    │
│                                                         │
│  4. TRACK                                               │
│     ├─ Check for market resolutions                     │
│     ├─ Update P&L on resolved positions                 │
│     └─ Log performance metrics                          │
│                                                         │
│  5. SLEEP (60 seconds)                                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Error Handling:**
- Wrap `_tick()` in try/except - never crash the loop
- Log errors but continue running
- Implement exponential backoff for API failures

**Success criteria:**
- [ ] Loop runs on schedule (60s default)
- [ ] All 4 phases (SENSE/THINK/ACT/TRACK) implemented
- [ ] Graceful error handling (don't crash on one bad tick)
- [ ] Test: Run loop for 5 minutes in paper mode

---

## Task 5.2: Create CLI Entry Point

**Goal:** Update CLI to run the agent loop.

**Files to modify:**
- `scripts/python/cli.py` - Add new commands

**New Commands:**
```bash
# Run agent loop
python scripts/python/cli.py run --mode paper

# Run single tick (for testing)
python scripts/python/cli.py tick

# Check status
python scripts/python/cli.py status
```

**Implementation:**
```python
import typer
from agents.application.agent_loop import AgentLoop
from agents.utils.config import Config

app = typer.Typer()

@app.command()
def run(mode: str = "paper"):
    """Start the agent loop."""
    config = Config()
    config.trading_mode = mode

    loop = AgentLoop(config)
    print(f"Starting agent loop in {mode} mode...")
    loop.run()

@app.command()
def tick():
    """Run a single tick (for testing)."""
    config = Config()
    loop = AgentLoop(config)
    loop._tick()

@app.command()
def status():
    """Show current bot status."""
    # Show: positions, today's P&L, last signal time
    ...

if __name__ == "__main__":
    app()
```

**Success criteria:**
- [ ] `run` command starts agent loop
- [ ] `--mode` flag works (paper/live)
- [ ] Ctrl+C gracefully stops
- [ ] Test: `python scripts/python/cli.py run --mode paper`

---

## Codex Assignment

**Run sequentially:**
1. Task 5.1: Agent Loop (core loop logic)
2. Task 5.2: CLI Entry Point (exposes loop to command line)

Task 5.2 depends on 5.1 being complete.
