from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.tracking.paper_trade import PaperTradeExecutor
from agents.utils.models import Bet


def test_paper_trade_execute_and_resolve(tmp_path: Path) -> None:
    db_path = tmp_path / "paper.db"
    executor = PaperTradeExecutor(db_path=str(db_path), initial_bankroll=100.0)

    bet = Bet(
        timestamp=datetime.now(timezone.utc),
        market_id="m1",
        direction="YES",
        amount_usd=10.0,
        odds_at_execution=0.5,
        estimated_prob=0.6,
        kelly_fraction=0.5,
        mode="paper",
    )

    trade_id = executor.execute_trade(bet)
    assert trade_id is not None
    assert abs(executor.get_bankroll() - 90.0) < 1e-9

    positions = executor.get_positions()
    assert len(positions) == 1
    assert positions[0].market_id == "m1"
    assert abs(positions[0].shares - 20.0) < 1e-9

    pnl = executor.resolve_position("m1", outcome="YES")
    assert abs(pnl - 10.0) < 1e-9
    assert abs(executor.get_bankroll() - 110.0) < 1e-9
    assert executor.get_positions() == []

