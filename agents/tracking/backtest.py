from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from agents.application.kelly_sizing import calculate_bet_size
from agents.connectors.news_sources import NewsArticle
from agents.strategies.base_strategy import BaseStrategy
from agents.strategies.risk_manager import RiskManager
from agents.tracking.performance import PerformanceTracker
from agents.utils.config import Config
from agents.utils.models import Signal


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(path: str) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        return raw
    return _repo_root() / raw


def _parse_iso(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text).astimezone(timezone.utc)


@dataclass
class BacktestResult:
    total_pnl: float
    win_rate: float
    num_trades: int
    sharpe_ratio: float
    max_drawdown: float
    trades: list[dict]


class BacktestRunner:
    def __init__(
        self,
        strategy: BaseStrategy,
        start_date: datetime,
        end_date: datetime,
        initial_bankroll: float = 500.0,
        *,
        base_dir: str = "data/historical",
        config: Optional[Config] = None,
    ):
        self.strategy = strategy
        self.start_date = start_date
        self.end_date = end_date
        self.initial_bankroll = float(initial_bankroll)
        self.base_dir = _resolve_path(base_dir)
        self.config = config or Config()
        self.risk = RiskManager(self.config)
        self.trades: list[dict] = []
        self.equity_curve: list[float] = [self.initial_bankroll]

        self._performance_math = PerformanceTracker(db_path=":memory:")

    def load_historical_data(self) -> None:
        # Historical data is loaded on-demand per day; this method is kept for parity with the spec.
        return

    def run(self) -> BacktestResult:
        bankroll = self.initial_bankroll
        open_positions: dict[str, dict[str, Any]] = {}
        daily_returns: list[float] = []

        current_day = self.start_date.date()
        end_day = self.end_date.date()

        while current_day <= end_day:
            prev_bankroll = bankroll

            articles = self._load_news_day(current_day)
            markets = self._load_markets_day(current_day)
            signals = self.strategy.generate_signals(articles, markets)

            for signal in signals:
                passed, _ = self.risk.check_signal(signal)
                if not passed:
                    continue

                price = float(signal.current_odds)
                if price <= 0:
                    continue

                decimal_odds = 1.0 / price
                bet_amount = calculate_bet_size(
                    bankroll=bankroll,
                    estimated_prob=float(signal.estimated_prob),
                    market_odds=decimal_odds,
                    max_bet_pct=float(self.config.max_bet_pct),
                    kelly_fraction=float(self.config.kelly_fraction),
                )
                if bet_amount <= 0 or bet_amount > bankroll:
                    continue

                shares = bet_amount / price
                bankroll -= bet_amount
                open_positions[signal.market_id] = {
                    "direction": signal.direction,
                    "shares": shares,
                    "cost": bet_amount,
                    "edge": float(signal.edge),
                    "price": price,
                }

            resolutions = self._load_resolutions_day(current_day)
            for resolution in resolutions:
                market_id = str(resolution.get("market_id", ""))
                if market_id not in open_positions:
                    continue
                outcome = str(resolution.get("outcome", "")).strip().upper()
                position = open_positions.pop(market_id)

                direction = str(position["direction"]).strip().upper()
                shares = float(position["shares"])
                cost = float(position["cost"])
                edge = float(position.get("edge") or 0.0)

                won = direction == outcome
                payout = shares if won else 0.0
                pnl = payout - cost if won else -cost
                bankroll += payout

                self.trades.append(
                    {
                        "date": current_day.isoformat(),
                        "market_id": market_id,
                        "direction": direction,
                        "cost": cost,
                        "shares": shares,
                        "outcome": outcome,
                        "pnl": pnl,
                        "edge_at_entry": edge,
                    }
                )

            self.equity_curve.append(bankroll)
            if prev_bankroll > 0:
                daily_returns.append((bankroll - prev_bankroll) / prev_bankroll)
            else:
                daily_returns.append(0.0)

            current_day = (datetime.combine(current_day, datetime.min.time()) + timedelta(days=1)).date()

        return self.get_results(daily_returns=daily_returns)

    def get_results(self, *, daily_returns: Optional[list[float]] = None) -> BacktestResult:
        total_pnl = self.equity_curve[-1] - self.initial_bankroll
        num_trades = len(self.trades)
        wins = sum(1 for t in self.trades if float(t.get("pnl") or 0.0) > 0)
        win_rate = (wins / num_trades) if num_trades else 0.0

        sharpe = self._performance_math.calculate_sharpe_ratio(daily_returns or [])
        max_dd = self._performance_math.calculate_max_drawdown(self.equity_curve)

        return BacktestResult(
            total_pnl=float(total_pnl),
            win_rate=float(win_rate),
            num_trades=int(num_trades),
            sharpe_ratio=float(sharpe),
            max_drawdown=float(max_dd),
            trades=list(self.trades),
        )

    def _load_news_day(self, d) -> list[NewsArticle]:
        path = self.base_dir / "news" / f"{d.isoformat()}.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        raw_articles = data.get("articles") or []
        articles: list[NewsArticle] = []
        for raw in raw_articles:
            published = raw.get("published_at") or raw.get("publishedAt") or ""
            try:
                published_at = _parse_iso(str(published))
            except Exception:  # noqa: BLE001
                published_at = datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
            articles.append(
                NewsArticle(
                    headline=str(raw.get("headline", "")),
                    summary=str(raw.get("summary", "")),
                    source=str(raw.get("source", "")),
                    url=str(raw.get("url", "")),
                    published_at=published_at,
                    category=raw.get("category"),
                )
            )
        return articles

    def _load_markets_day(self, d) -> list[dict]:
        path = self.base_dir / "markets" / f"{d.isoformat()}.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("markets") or [])

    def _load_resolutions_day(self, d) -> list[dict]:
        path = self.base_dir / "resolutions" / f"{d.isoformat()}.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("resolutions") or [])

