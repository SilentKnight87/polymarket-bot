from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from agents.application.kelly_sizing import calculate_bet_size
from agents.connectors.news_sources import NewsAggregator
from agents.polymarket.gamma import GammaMarketClient
from agents.strategies.news_speed import NewsSpeedStrategy
from agents.strategies.risk_manager import RiskManager
from agents.tracking.logger import BotLogger
from agents.tracking.market_snapshot import MarketSnapshotter
from agents.tracking.news_snapshot import NewsSnapshotter
from agents.tracking.paper_trade import PaperTradeExecutor
from agents.tracking.performance import PerformanceTracker
from agents.utils.config import Config
from agents.utils.models import Bet, Signal

logger = logging.getLogger(__name__)


def _price_to_decimal_odds(price: float) -> Optional[float]:
    if price <= 0:
        return None
    return 1.0 / price


class AgentLoop:
    def __init__(
        self,
        config: Config,
        *,
        llm: Any = None,
        paper_db_path: str = "data/paper_trades.db",
        performance_db_path: str = "data/performance.db",
    ) -> None:
        self.config = config

        self.news = NewsAggregator(config)
        self.gamma = GammaMarketClient()
        self.strategy = NewsSpeedStrategy(config, llm=llm)
        self.risk = RiskManager(config)
        self.logger = BotLogger()
        self.snapshotter = MarketSnapshotter()
        self.news_snapshotter = NewsSnapshotter()
        self._last_snapshot_date: Optional[str] = None
        self._last_news_snapshot_date: Optional[str] = None

        self.paper = PaperTradeExecutor(db_path=paper_db_path, initial_bankroll=config.bankroll)
        self.performance = PerformanceTracker(db_path=performance_db_path)

    def run(self) -> None:
        """Run forever, ticking at the configured interval."""
        interval = max(1, int(self.config.check_interval_seconds))
        logger.info("Starting agent loop (mode=%s, interval=%ss)", self.config.trading_mode, interval)
        try:
            while True:
                started = time.time()
                self.tick()
                elapsed = time.time() - started
                sleep_for = max(0.0, interval - elapsed)
                time.sleep(sleep_for)
        except KeyboardInterrupt:
            logger.info("Agent loop stopped (Ctrl+C).")

    def tick(self) -> None:
        """One SENSE -> THINK -> ACT -> TRACK iteration."""
        try:
            articles = self.news.fetch_new_articles()
            markets = self._fetch_markets()
            self._record_daily_snapshot(markets)
            self._record_daily_news_snapshot(articles)
            signals = self.strategy.generate_signals(articles, markets)

            for signal in signals:
                self._handle_signal(signal, markets)

            self._check_resolutions()
            self._update_performance()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent tick failed: %s", exc)

    def _fetch_markets(self) -> list[dict]:
        # Pull a limited set for responsiveness; the strategy further narrows per-article.
        settings = self.config.settings.get("polymarket", {})
        limit = int(settings.get("market_fetch_limit", 200))
        return self.gamma.get_clob_tradable_markets(limit=limit)

    def _handle_signal(self, signal: Signal, markets: list[dict]) -> None:
        passed, reason = self.risk.check_signal(signal)
        payload = signal.model_dump()
        if not passed:
            payload["rejected"] = reason
            self.logger.log_signal(payload)
            return

        market = self._find_market(markets, signal.market_id)
        if market is None:
            payload["rejected"] = "market not found in snapshot"
            self.logger.log_signal(payload)
            return

        market_volume = float(market.get("volume24hr") or market.get("volume24hrClob") or market.get("volume") or 0.0)
        bankroll = float(self.paper.get_bankroll()) if self.config.trading_mode == "paper" else float(self.config.bankroll)

        price = float(signal.current_odds)
        decimal_odds = _price_to_decimal_odds(price)
        if decimal_odds is None:
            payload["rejected"] = "invalid market price"
            self.logger.log_signal(payload)
            return

        bet_amount = calculate_bet_size(
            bankroll=bankroll,
            estimated_prob=float(signal.estimated_prob),
            market_odds=decimal_odds,
            max_bet_pct=float(self.config.max_bet_pct),
            kelly_fraction=float(self.config.kelly_fraction),
        )

        if bet_amount <= 0:
            payload["rejected"] = "bet sizing returned 0"
            self.logger.log_signal(payload)
            return

        liquid, liquid_reason = self.risk.check_liquidity(bet_amount, market_volume)
        if not liquid:
            payload["rejected"] = liquid_reason
            self.logger.log_signal(payload)
            return

        payload["executed_amount_usd"] = bet_amount
        self.logger.log_signal(payload)

        bet = Bet(
            timestamp=signal.timestamp,
            market_id=signal.market_id,
            direction=signal.direction,
            amount_usd=bet_amount,
            odds_at_execution=price,
            estimated_prob=signal.estimated_prob,
            kelly_fraction=self.config.kelly_fraction,
            mode=self.config.trading_mode,  # type: ignore[arg-type]
        )
        self._execute_bet(bet)

    def _execute_bet(self, bet: Bet) -> None:
        if self.config.trading_mode == "paper":
            trade_id = self.paper.execute_trade(bet)
            self.logger.log_bet({**bet.model_dump(), "paper_trade_id": trade_id})
            return
        raise NotImplementedError("Live trading not implemented in MVP.")

    def _check_resolutions(self) -> None:
        if self.config.trading_mode != "paper":
            return
        positions = self.paper.get_positions()
        if not positions:
            return

        resolutions: list[dict] = []
        for position in positions:
            market_id = position.market_id
            try:
                market = self.gamma.get_market(market_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to fetch market %s for resolution: %s", market_id, exc)
                continue

            resolution = self.snapshotter.detect_resolution(market)
            if resolution is None:
                continue

            pnl = self.paper.resolve_position(market_id, resolution["outcome"])
            logger.info("Resolved paper position %s (%s): P&L %.2f", market_id, resolution["outcome"], pnl)
            self._record_performance_for_market(market_id)
            resolutions.append(resolution)

        if resolutions:
            self.snapshotter.record_resolutions(resolutions)

    def _update_performance(self) -> None:
        metrics = self.performance.get_all_time_metrics()
        self.logger.log_performance(metrics.model_dump())

    @staticmethod
    def _find_market(markets: list[dict], market_id: str) -> Optional[dict]:
        for market in markets:
            if str(market.get("id")) == str(market_id) or str(market.get("market_id")) == str(market_id):
                return market
        return None

    def _record_daily_snapshot(self, markets: list[dict]) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        if self._last_snapshot_date == today:
            return
        self.snapshotter.record_daily_snapshot(markets)
        self._last_snapshot_date = today

    def _record_daily_news_snapshot(self, articles: list) -> None:
        """Record news articles to daily snapshot for backtest replay."""
        if not articles:
            return
        today = datetime.now(timezone.utc).date().isoformat()
        # Always try to append; NewsSnapshotter handles deduplication internally
        if self.news_snapshotter.record_daily_snapshot(articles):
            self._last_news_snapshot_date = today
            logger.debug("News snapshot updated for %s (%d articles)", today, len(articles))

    def _record_performance_for_market(self, market_id: str) -> None:
        trades = self.paper.get_trades(market_id=market_id, status="resolved")
        for trade in trades:
            self.performance.record_bet_result(
                f"paper:{trade['id']}",
                pnl=float(trade.get("pnl") or 0.0),
                market_id=str(trade.get("market_id") or ""),
                direction=str(trade.get("direction") or ""),
                amount=float(trade.get("amount_usd") or 0.0),
                odds=float(trade.get("odds_at_execution") or 0.0),
                outcome=str(trade.get("outcome") or ""),
            )
