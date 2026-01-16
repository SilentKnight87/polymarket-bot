# Phase 9: Historical Snapshots & Auto-Resolution

**Dependencies:** Phase 5 (Agent Loop), Phase 6 (Paper Trading)

**Tasks:** 1

---

## Task 9.1: Capture Daily Market Snapshots + Resolutions

**Goal:** Persist daily market snapshots and auto-detect paper trade resolutions so backtests can run on historical data.

**Files to create:**
- `agents/tracking/market_snapshot.py`

**Files to modify:**
- `agents/application/agent_loop.py`
- `scripts/python/cli.py`
- `agents/utils/config.py`
- `config/settings.yaml`

**Requirements:**
```python
class MarketSnapshotter:
    def record_daily_snapshot(self, markets: list[dict]) -> bool:
        """Write data/historical/markets/YYYY-MM-DD.json once per day."""

    def detect_resolution(self, market: dict) -> Optional[dict]:
        """Return {market_id, outcome, resolved_at} if resolved."""

    def record_resolutions(self, resolutions: list[dict]) -> bool:
        """Append data/historical/resolutions/YYYY-MM-DD.json."""
```

**Storage Format:**
```
data/historical/markets/YYYY-MM-DD.json
data/historical/resolutions/YYYY-MM-DD.json
```

**Success criteria:**
- [ ] Daily market snapshot written once per UTC day
- [ ] Auto-detects resolved markets for open paper positions
- [ ] Writes resolution records to historical files
- [ ] Test: verify snapshot + resolution files created

---

## Codex Assignment

**Run Task 9.1** - Enables hands-off data collection for backtesting.
