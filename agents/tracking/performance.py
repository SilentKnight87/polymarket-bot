from __future__ import annotations

import math
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from agents.utils.models import PerformanceMetrics


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(path: str) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        return raw
    return _repo_root() / raw


class PerformanceTracker:
    def __init__(self, db_path: str = "data/performance.db"):
        self.db_path = db_path
        if db_path == ":memory:":
            self.conn = sqlite3.connect(":memory:")
        else:
            resolved = _resolve_path(db_path)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(resolved))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
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
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bet_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bet_id TEXT UNIQUE,
                market_id TEXT,
                direction TEXT,
                amount REAL,
                odds REAL,
                outcome TEXT,
                pnl REAL,
                edge_at_entry REAL,
                resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def record_bet_result(
        self,
        bet_id: str,
        pnl: float,
        *,
        market_id: Optional[str] = None,
        direction: Optional[str] = None,
        amount: Optional[float] = None,
        odds: Optional[float] = None,
        outcome: Optional[str] = None,
        edge_at_entry: Optional[float] = None,
        resolved_at: Optional[datetime] = None,
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO bet_results (bet_id, market_id, direction, amount, odds, outcome, pnl, edge_at_entry, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            ON CONFLICT(bet_id) DO UPDATE SET
              market_id=excluded.market_id,
              direction=excluded.direction,
              amount=excluded.amount,
              odds=excluded.odds,
              outcome=excluded.outcome,
              pnl=excluded.pnl,
              edge_at_entry=excluded.edge_at_entry,
              resolved_at=excluded.resolved_at
            """,
            (
                bet_id,
                market_id,
                direction,
                amount,
                odds,
                outcome,
                float(pnl),
                edge_at_entry,
                resolved_at.isoformat() if resolved_at else None,
            ),
        )
        self.conn.commit()

    def get_daily_metrics(self, d: Optional[date] = None) -> PerformanceMetrics:
        d = d or date.today()
        day = d.isoformat()
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT
              COUNT(*) as num_bets,
              SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
              SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
              COALESCE(SUM(pnl), 0.0) as total_pnl,
              AVG(edge_at_entry) as avg_edge
            FROM bet_results
            WHERE substr(resolved_at, 1, 10) = ?
            """,
            (day,),
        )
        row = cur.fetchone()

        num_bets = int(row["num_bets"] or 0)
        wins = int(row["wins"] or 0)
        losses = int(row["losses"] or 0)
        total_pnl = float(row["total_pnl"] or 0.0)
        avg_edge = float(row["avg_edge"] or 0.0) if row["avg_edge"] is not None else 0.0
        win_rate = float(wins / num_bets) if num_bets else 0.0

        # With only per-bet P&L, we approximate drawdown as 0 for daily snapshots.
        return PerformanceMetrics(
            date=day,
            total_pnl=total_pnl,
            win_rate=win_rate,
            num_bets=num_bets,
            avg_edge=avg_edge,
            max_drawdown=0.0,
        )

    def get_all_time_metrics(self) -> PerformanceMetrics:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT
              COUNT(*) as num_bets,
              SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
              COALESCE(SUM(pnl), 0.0) as total_pnl,
              AVG(edge_at_entry) as avg_edge
            FROM bet_results
            """
        )
        row = cur.fetchone()
        num_bets = int(row["num_bets"] or 0)
        wins = int(row["wins"] or 0)
        total_pnl = float(row["total_pnl"] or 0.0)
        avg_edge = float(row["avg_edge"] or 0.0) if row["avg_edge"] is not None else 0.0
        win_rate = float(wins / num_bets) if num_bets else 0.0

        # Build a simple equity curve from cumulative P&L (starting at 1.0).
        cur.execute("SELECT pnl FROM bet_results ORDER BY resolved_at ASC, id ASC")
        pnl_rows = cur.fetchall()
        equity_curve = [1.0]
        current = 1.0
        for pnl_row in pnl_rows:
            current += float(pnl_row["pnl"] or 0.0)
            equity_curve.append(current)

        max_drawdown = self.calculate_max_drawdown(equity_curve)

        return PerformanceMetrics(
            date="all_time",
            total_pnl=total_pnl,
            win_rate=win_rate,
            num_bets=num_bets,
            avg_edge=avg_edge,
            max_drawdown=max_drawdown,
        )

    def calculate_sharpe_ratio(self, daily_returns: list[float]) -> float:
        if len(daily_returns) < 2:
            return 0.0

        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
        std_dev = math.sqrt(variance)
        if std_dev == 0:
            return 0.0
        daily_sharpe = mean_return / std_dev
        return daily_sharpe * math.sqrt(365)

    def calculate_max_drawdown(self, equity_curve: list[float]) -> float:
        if len(equity_curve) < 2:
            return 0.0
        peak = equity_curve[0]
        max_dd = 0.0
        for value in equity_curve:
            if value > peak:
                peak = value
            if peak <= 0:
                continue
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        return max_dd
