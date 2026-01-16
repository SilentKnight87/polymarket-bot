import typer
from devtools import pprint

from agents.polymarket.polymarket import Polymarket
from agents.connectors.chroma import PolymarketRAG
from agents.connectors.news import News
from agents.connectors.news_sources import NewsAggregator
from agents.application.trade import Trader
from agents.application.executor import Executor
from agents.application.creator import Creator
from agents.application.agent_loop import AgentLoop
from agents.tracking.backtest import BacktestRunner
from agents.tracking.news_snapshot import NewsSnapshotter
from agents.strategies.news_speed import NewsSpeedStrategy
from agents.utils.config import Config

from datetime import datetime, timezone

app = typer.Typer()
polymarket = Polymarket()
newsapi_client = News()
polymarket_rag = PolymarketRAG()


@app.command()
def get_all_markets(limit: int = 5, sort_by: str = "spread") -> None:
    """
    Query Polymarket's markets
    """
    print(f"limit: int = {limit}, sort_by: str = {sort_by}")
    markets = polymarket.get_all_markets()
    markets = polymarket.filter_markets_for_trading(markets)
    if sort_by == "spread":
        markets = sorted(markets, key=lambda x: x.spread, reverse=True)
    markets = markets[:limit]
    pprint(markets)


@app.command()
def get_relevant_news(keywords: str) -> None:
    """
    Use NewsAPI to query the internet
    """
    articles = newsapi_client.get_articles_for_cli_keywords(keywords)
    pprint(articles)


@app.command()
def get_all_events(limit: int = 5, sort_by: str = "number_of_markets") -> None:
    """
    Query Polymarket's events
    """
    print(f"limit: int = {limit}, sort_by: str = {sort_by}")
    events = polymarket.get_all_events()
    events = polymarket.filter_events_for_trading(events)
    if sort_by == "number_of_markets":
        events = sorted(events, key=lambda x: len(x.markets), reverse=True)
    events = events[:limit]
    pprint(events)


@app.command()
def create_local_markets_rag(local_directory: str) -> None:
    """
    Create a local markets database for RAG
    """
    polymarket_rag.create_local_markets_rag(local_directory=local_directory)


@app.command()
def query_local_markets_rag(vector_db_directory: str, query: str) -> None:
    """
    RAG over a local database of Polymarket's events
    """
    response = polymarket_rag.query_local_markets_rag(
        local_directory=vector_db_directory, query=query
    )
    pprint(response)


@app.command()
def ask_superforecaster(event_title: str, market_question: str, outcome: str) -> None:
    """
    Ask a superforecaster about a trade
    """
    print(
        f"event: str = {event_title}, question: str = {market_question}, outcome (usually yes or no): str = {outcome}"
    )
    executor = Executor()
    response = executor.get_superforecast(
        event_title=event_title, market_question=market_question, outcome=outcome
    )
    print(f"Response:{response}")


@app.command()
def create_market() -> None:
    """
    Format a request to create a market on Polymarket
    """
    c = Creator()
    market_description = c.one_best_market()
    print(f"market_description: str = {market_description}")


@app.command()
def ask_llm(user_input: str) -> None:
    """
    Ask a question to the LLM and get a response.
    """
    executor = Executor()
    response = executor.get_llm_response(user_input)
    print(f"LLM Response: {response}")


@app.command()
def ask_polymarket_llm(user_input: str) -> None:
    """
    What types of markets do you want trade?
    """
    executor = Executor()
    response = executor.get_polymarket_llm(user_input=user_input)
    print(f"LLM + current markets&events response: {response}")


@app.command()
def run_autonomous_trader() -> None:
    """
    Let an autonomous system trade for you.
    """
    trader = Trader()
    trader.one_best_trade()


@app.command()
def run(mode: str = "paper") -> None:
    """Start the agent loop (paper mode recommended)."""
    config = Config().with_trading_mode(mode)
    loop = AgentLoop(config)
    print(f"Starting agent loop in {config.trading_mode} mode...")
    loop.run()


@app.command()
def tick(mode: str = "paper") -> None:
    """Run a single agent tick (useful for testing)."""
    config = Config().with_trading_mode(mode)
    loop = AgentLoop(config)
    loop.tick()


@app.command()
def status() -> None:
    """Show current paper trading status (bankroll + open positions)."""
    from agents.tracking.paper_trade import PaperTradeExecutor

    paper = PaperTradeExecutor()
    print(f"Paper bankroll: ${paper.get_bankroll():.2f}")
    pprint(paper.get_positions())

@app.command()
def snapshot() -> None:
    """Record a daily market snapshot to data/historical/markets."""
    from agents.tracking.market_snapshot import MarketSnapshotter
    from agents.polymarket.gamma import GammaMarketClient

    gamma = GammaMarketClient()
    settings = Config().settings.get("polymarket", {})
    limit = int(settings.get("market_fetch_limit", 200))
    markets = gamma.get_clob_tradable_markets(limit=limit)
    wrote = MarketSnapshotter().record_daily_snapshot(markets)
    print("Snapshot written." if wrote else "Snapshot already exists for today.")


@app.command()
def news_snapshot() -> None:
    """Record a daily news snapshot to data/historical/news."""
    config = Config()
    aggregator = NewsAggregator(config)
    snapshotter = NewsSnapshotter()
    since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    articles = aggregator.fetch_new_articles(since=since)
    wrote = snapshotter.record_daily_snapshot(articles, snapshot_date=since.date())
    print("News snapshot written." if wrote else "No new articles to snapshot.")


@app.command()
def paper_resolve(market_id: str, outcome: str) -> None:
    """Manually resolve a paper position and record results into performance tracking."""
    from agents.tracking.paper_trade import PaperTradeExecutor
    from agents.tracking.performance import PerformanceTracker

    paper = PaperTradeExecutor()
    pnl = paper.resolve_position(market_id, outcome=outcome)
    print(f"Resolved {market_id} as {outcome.upper()}. Total P&L: ${pnl:.2f}")

    tracker = PerformanceTracker()
    resolved_trades = paper.get_trades(market_id=market_id, status="resolved")
    for trade in resolved_trades:
        tracker.record_bet_result(
            f"paper:{trade['id']}",
            pnl=float(trade.get("pnl") or 0.0),
            market_id=str(trade.get("market_id") or ""),
            direction=str(trade.get("direction") or ""),
            amount=float(trade.get("amount_usd") or 0.0),
            odds=float(trade.get("odds_at_execution") or 0.0),
            outcome=str(trade.get("outcome") or ""),
        )


@app.command()
def backtest(
    strategy: str = "news_speed",
    start: str = "2025-11-01",
    end: str = "2025-12-01",
    bankroll: float = 500.0,
    allow_llm: bool = False,
) -> None:
    """
    Run a historical backtest over `data/historical/`.

    Note: `news_speed` calls an LLM; set `--allow-llm` only if you're OK with cost/latency.
    """
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)

    config = Config()
    strategy_name = strategy.strip().lower()
    if strategy_name == "news_speed":
        if not allow_llm:
            raise typer.BadParameter("news_speed backtest requires LLM calls; pass --allow-llm to proceed.")
        strat = NewsSpeedStrategy(config)
    else:
        raise typer.BadParameter(f"Unknown strategy: {strategy}")

    runner = BacktestRunner(
        strategy=strat,
        start_date=start_dt,
        end_date=end_dt,
        initial_bankroll=bankroll,
        config=config,
    )
    result = runner.run()
    pprint(result)


if __name__ == "__main__":
    app()
