from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.tracking.logger import BotLogger
from agents.utils.config import Config
from agents.utils.models import Bet, PerformanceMetrics, Position, Signal


def test_config_loads_from_yaml_and_env(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        """
polymarket:
  api_key: ${POLYMARKET_API_KEY}
trading:
  mode: backtest
  bankroll: 123.45
  max_bet_pct: 0.02
  min_edge: 0.07
  kelly_fraction: 0.4
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("POLYMARKET_API_KEY", "test-key")

    config = Config(config_path=str(config_path))

    assert config.trading_mode == "backtest"
    assert config.bankroll == 123.45
    assert config.max_bet_pct == 0.02
    assert config.min_edge == 0.07
    assert config.kelly_fraction == 0.4
    assert config.settings["polymarket"]["api_key"] == "test-key"


def test_logger_writes_jsonl_and_summary(tmp_path: Path) -> None:
    logger = BotLogger(log_dir=str(tmp_path))

    logger.log_signal({"market_id": "123", "direction": "YES", "edge": 0.1})
    logger.log_bet({"market_id": "456", "direction": "NO", "amount_usd": 12.5})
    logger.log_performance({"total_pnl": 5.5, "num_bets": 1})

    signal_files = list((tmp_path / "signals").glob("*.jsonl"))
    bet_files = list((tmp_path / "bets").glob("*.jsonl"))
    performance_path = tmp_path / "performance" / "daily_summary.json"

    assert len(signal_files) == 1
    assert len(bet_files) == 1
    assert performance_path.exists()

    signal_entry = json.loads(signal_files[0].read_text(encoding="utf-8").strip())
    bet_entry = json.loads(bet_files[0].read_text(encoding="utf-8").strip())
    perf_entries = json.loads(performance_path.read_text(encoding="utf-8"))

    assert signal_entry["market_id"] == "123"
    assert bet_entry["market_id"] == "456"
    assert isinstance(perf_entries, list)
    assert perf_entries[0]["total_pnl"] == 5.5


def test_models_serialize() -> None:
    now = datetime.now(timezone.utc)

    signal = Signal(
        timestamp=now,
        market_id="abc",
        market_question="Will it rain?",
        direction="YES",
        current_odds=0.42,
        estimated_prob=0.6,
        edge=0.18,
        confidence=7,
        reasoning="Test",
        news_headline="Breaking",
    )
    bet = Bet(
        timestamp=now,
        market_id="abc",
        direction="YES",
        amount_usd=10.0,
        odds_at_execution=0.42,
        estimated_prob=0.6,
        kelly_fraction=0.5,
        mode="paper",
    )
    position = Position(
        market_id="abc",
        direction="YES",
        shares=5.0,
        avg_price=0.4,
        current_price=0.45,
        unrealized_pnl=0.25,
    )
    performance = PerformanceMetrics(
        date="2026-01-09",
        total_pnl=1.0,
        win_rate=0.5,
        num_bets=2,
        avg_edge=0.1,
        max_drawdown=0.2,
    )

    assert "market_id" in signal.model_dump_json()
    assert "amount_usd" in bet.model_dump_json()
    assert position.model_dump()["shares"] == 5.0
    assert performance.model_dump()["date"] == "2026-01-09"
