from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from agents.utils.models import Bet, Position


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(path: str) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        return raw
    return _repo_root() / raw


class PaperTradeExecutor:
    def __init__(self, db_path: str = "data/paper_trades.db", initial_bankroll: float = 500.0):
        self.db_path = db_path
        if db_path == ":memory:":
            self.conn = sqlite3.connect(":memory:")
        else:
            resolved = _resolve_path(db_path)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(resolved))
        self.conn.row_factory = sqlite3.Row
        self._init_db()
        self._ensure_bankroll(float(initial_bankroll))

    def _init_db(self) -> None:
        cur = self.conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bankroll (
                id INTEGER PRIMARY KEY,
                amount REAL NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                market_id TEXT NOT NULL,
                direction TEXT NOT NULL,
                amount_usd REAL NOT NULL,
                odds_at_execution REAL NOT NULL,
                shares REAL NOT NULL,
                status TEXT DEFAULT 'open',
                outcome TEXT,
                pnl REAL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS positions (
                market_id TEXT PRIMARY KEY,
                direction TEXT NOT NULL,
                shares REAL NOT NULL,
                avg_price REAL NOT NULL,
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        self.conn.commit()

    def _ensure_bankroll(self, initial_bankroll: float) -> None:
        cur = self.conn.cursor()
        cur.execute("SELECT amount FROM bankroll WHERE id = 1")
        row = cur.fetchone()
        if row is None:
            cur.execute("INSERT INTO bankroll (id, amount) VALUES (1, ?)", (initial_bankroll,))
            self.conn.commit()

    def execute_trade(self, bet: Bet) -> Optional[int]:
        """
        Simulate trade execution.
        - Deduct from paper bankroll
        - Add to paper positions
        - Log the trade
        """
        price = float(bet.odds_at_execution)
        if price <= 0:
            return None

        bankroll = self.get_bankroll()
        if bankroll < bet.amount_usd:
            return None

        shares = float(bet.amount_usd) / price

        cur = self.conn.cursor()
        cur.execute("UPDATE bankroll SET amount = amount - ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (bet.amount_usd,))

        cur.execute(
            """
            INSERT INTO trades (timestamp, market_id, direction, amount_usd, odds_at_execution, shares)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                bet.timestamp.isoformat(),
                bet.market_id,
                bet.direction,
                float(bet.amount_usd),
                price,
                shares,
            ),
        )
        trade_id = int(cur.lastrowid)

        cur.execute("SELECT shares, avg_price, direction FROM positions WHERE market_id = ?", (bet.market_id,))
        existing = cur.fetchone()
        if existing is None:
            cur.execute(
                """
                INSERT INTO positions (market_id, direction, shares, avg_price)
                VALUES (?, ?, ?, ?)
                """,
                (bet.market_id, bet.direction, shares, price),
            )
        else:
            existing_shares = float(existing["shares"])
            existing_avg = float(existing["avg_price"])
            existing_direction = str(existing["direction"])

            if existing_direction != bet.direction:
                # MVP: disallow mixing directions in one market (would be a separate strategy).
                self.conn.rollback()
                return None

            new_shares = existing_shares + shares
            new_avg = (existing_shares * existing_avg + shares * price) / new_shares
            cur.execute(
                "UPDATE positions SET shares = ?, avg_price = ? WHERE market_id = ?",
                (new_shares, new_avg, bet.market_id),
            )

        self.conn.commit()
        return trade_id

    def get_positions(self) -> list[Position]:
        cur = self.conn.cursor()
        cur.execute("SELECT market_id, direction, shares, avg_price FROM positions")
        rows = cur.fetchall()

        positions: list[Position] = []
        for row in rows:
            shares = float(row["shares"])
            avg_price = float(row["avg_price"])
            positions.append(
                Position(
                    market_id=str(row["market_id"]),
                    direction=str(row["direction"]),  # type: ignore[arg-type]
                    shares=shares,
                    avg_price=avg_price,
                    current_price=avg_price,
                    unrealized_pnl=0.0,
                )
            )
        return positions

    def get_trades(self, *, market_id: Optional[str] = None, status: Optional[str] = None) -> list[dict]:
        cur = self.conn.cursor()
        clauses: list[str] = []
        params: list[object] = []
        if market_id is not None:
            clauses.append("market_id = ?")
            params.append(market_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)

        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        cur.execute(
            f"SELECT id, timestamp, market_id, direction, amount_usd, odds_at_execution, shares, status, outcome, pnl FROM trades {where} ORDER BY id ASC",
            tuple(params),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_bankroll(self) -> float:
        cur = self.conn.cursor()
        cur.execute("SELECT amount FROM bankroll WHERE id = 1")
        row = cur.fetchone()
        return float(row["amount"]) if row is not None else 0.0

    def resolve_position(self, market_id: str, outcome: str) -> float:
        """
        Resolve a position when market settles.
        Returns total P&L across the market's open trades.
        """
        outcome_norm = str(outcome).strip().upper()
        if outcome_norm not in {"YES", "NO"}:
            raise ValueError("outcome must be YES or NO")

        cur = self.conn.cursor()
        cur.execute("SELECT market_id, direction, shares, avg_price FROM positions WHERE market_id = ?", (market_id,))
        position = cur.fetchone()
        if position is None:
            return 0.0

        direction = str(position["direction"]).strip().upper()
        shares = float(position["shares"])
        avg_price = float(position["avg_price"])
        cost = shares * avg_price
        payout = shares if direction == outcome_norm else 0.0
        pnl_total = payout - cost if direction == outcome_norm else -cost

        # Update bankroll: cost was already deducted at entry, so add payout only.
        cur.execute("UPDATE bankroll SET amount = amount + ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (payout,))

        # Resolve underlying trades.
        cur.execute(
            "SELECT id, direction, amount_usd, shares FROM trades WHERE market_id = ? AND status = 'open'",
            (market_id,),
        )
        trades = cur.fetchall()
        for trade in trades:
            trade_direction = str(trade["direction"]).strip().upper()
            trade_amount = float(trade["amount_usd"])
            trade_shares = float(trade["shares"])
            if trade_direction == outcome_norm:
                trade_pnl = trade_shares - trade_amount
                trade_outcome = "win"
            else:
                trade_pnl = -trade_amount
                trade_outcome = "lose"
            cur.execute(
                "UPDATE trades SET status = 'resolved', outcome = ?, pnl = ? WHERE id = ?",
                (trade_outcome, trade_pnl, int(trade["id"])),
            )

        cur.execute("DELETE FROM positions WHERE market_id = ?", (market_id,))
        self.conn.commit()
        return float(pnl_total)
