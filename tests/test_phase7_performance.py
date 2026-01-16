from __future__ import annotations

import sys
from datetime import date
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.tracking.performance import PerformanceTracker


def test_performance_tracker_all_time_metrics() -> None:
    tracker = PerformanceTracker(db_path=":memory:")

    tracker.record_bet_result("b1", pnl=10.0, edge_at_entry=0.1, outcome="win")
    tracker.record_bet_result("b2", pnl=-5.0, edge_at_entry=0.05, outcome="lose")
    tracker.record_bet_result("b3", pnl=5.0, edge_at_entry=0.2, outcome="win")

    metrics = tracker.get_all_time_metrics()
    assert metrics.num_bets == 3
    assert abs(metrics.total_pnl - 10.0) < 1e-9
    assert abs(metrics.win_rate - (2 / 3)) < 1e-9
    assert metrics.avg_edge > 0
    assert metrics.max_drawdown >= 0


def test_performance_tracker_daily_metrics_default() -> None:
    tracker = PerformanceTracker(db_path=":memory:")
    tracker.record_bet_result("b1", pnl=1.0)
    metrics = tracker.get_daily_metrics(datetime.now(timezone.utc).date())
    assert metrics.num_bets == 1
    assert abs(metrics.total_pnl - 1.0) < 1e-9
