from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.application.kelly_sizing import calculate_bet_size, kelly_fraction
from agents.strategies.risk_manager import RiskManager
from agents.utils.config import Config
from agents.utils.models import Signal


def test_kelly_fraction_half_kelly_example() -> None:
    fraction = kelly_fraction(0.6, 2.0)
    assert abs(fraction - 0.1) < 1e-6


def test_calculate_bet_size_caps_at_max_pct() -> None:
    bet = calculate_bet_size(
        bankroll=1000.0,
        estimated_prob=0.8,
        market_odds=2.0,
        max_bet_pct=0.05,
        kelly_fraction=0.5,
    )
    assert abs(bet - 50.0) < 1e-6


def test_risk_manager_min_edge_check() -> None:
    config = Config()
    risk = RiskManager(config)
    signal = Signal(
        timestamp=datetime.now(timezone.utc),
        market_id="m1",
        market_question="Test market",
        direction="YES",
        current_odds=0.5,
        estimated_prob=0.53,
        edge=0.03,
        confidence=7,
        reasoning="test",
        news_headline="test",
    )
    passed, reason = risk.check_signal(signal)
    assert not passed
    assert "min_edge" in reason
