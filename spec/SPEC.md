# Prediction Markets Bot - Technical Specification

**Version:** 1.4
**Created:** 2026-01-08
**Status:** Draft - Ready to Build
**Priority:** HIGH - Focused Sprint

---

## Executive Summary

A fully autonomous prediction market trading bot for Polymarket. The system identifies opportunities, calculates edge, and executes bets automatically using Kelly criterion sizing.

**Core Philosophy:** Narrow scope, fast iteration, data-driven edge discovery. Ship fast, validate with backtests, paper trade briefly, then deploy real capital.

---

## Scope Boundaries (IMPORTANT)

### What This Project IS:
- Single platform (Polymarket)
- Fully autonomous execution
- Multiple edge strategies tested in parallel
- Kelly criterion position sizing
- Fast validation cycle (backtest → paper → real)

### What This Project IS NOT:
- Comprehensive research platform (that's Alpha Research System)
- Multi-platform arbitrage (future expansion)
- Human-in-the-loop research (this is autonomous)
- Complex position management (binary outcomes = simple)

---

## System Overview

### How It Works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  DATA INGESTION │────►│  EDGE DETECTION │────►│    EXECUTION    │
│                 │     │                 │     │                 │
│ • News feeds    │     │ • News → Signal │     │ • Kelly sizing  │
│ • Market data   │     │ • Probability   │     │ • Polymarket API│
│ • Social        │     │ • Sentiment     │     │ • Risk limits   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────┐
                    │  PERFORMANCE TRACKER │
                    │                     │
                    │ • P&L by strategy   │
                    │ • Edge validation   │
                    │ • Strategy ranking  │
                    └─────────────────────┘
```

### The Agent Loop (Core Execution Cycle)

The agent loop is the heartbeat of the bot - a continuous cycle that runs every 60 seconds:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AGENT LOOP (every 60 seconds)                    │
└─────────────────────────────────────────────────────────────────────┘

    ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
    │  SENSE   │────►│  THINK   │────►│   ACT    │────►│  TRACK   │
    │          │     │          │     │          │     │          │
    │ Fetch    │     │ Analyze  │     │ Execute  │     │ Log      │
    │ news +   │     │ signals  │     │ bets     │     │ results  │
    │ markets  │     │ + edge   │     │ (if any) │     │          │
    └──────────┘     └──────────┘     └──────────┘     └──────────┘
         │                                                   │
         └───────────────── SLEEP 60s ◄──────────────────────┘
```

**Detailed Loop Steps:**

```
WHILE bot_running:

    1. SENSE - Gather fresh data
       ├── Fetch new news articles (since last check)
       ├── Fetch current market state (odds, volume, liquidity)
       └── Check existing positions

    2. THINK - Analyze and generate signals
       ├── For each new article:
       │   ├── Map to relevant Polymarket markets (via LLM)
       │   ├── Estimate probability shift
       │   └── Calculate edge (our_prob - market_prob)
       └── Filter signals by MIN_EDGE threshold (5%)

    3. ACT - Execute trades (if signals pass checks)
       ├── Apply risk management rules
       ├── Calculate Kelly criterion bet size
       └── Place order (live) or simulate (paper)

    4. TRACK - Monitor and log
       ├── Check for resolved markets
       ├── Calculate P&L for closed positions
       └── Update daily performance summary

    5. SLEEP - Wait for next cycle (60 seconds)

    REPEAT
```

**Key Characteristics:**
- **News-driven:** Bot only acts when NEW news arrives that affects a market
- **Most cycles = no action:** If no news → no signals → no bets
- **Always monitoring:** Even idle cycles track positions and check resolutions
- **Configurable frequency:** 60s default, can adjust based on news velocity

### Edge Strategies to Test

The system will test multiple strategies in parallel to find what works:

| Strategy | Edge Type | Data Source | Complexity |
|----------|-----------|-------------|------------|
| **News Speed** | React to breaking news faster | AI News Aggregator | Medium |
| **Probability Mispricing** | Find odds that don't match reality | Market analysis + fundamentals | High |
| **Sentiment Divergence** | Social sentiment vs market odds | Twitter/Reddit | Medium |
| **Volume/Momentum** | Follow smart money | Polymarket order flow | Low |

**Initial Focus:** Start with News Speed (leverages existing AI News Aggregator)

---

## Architecture

### Components (Polymarket/agents Fork)

```
polymarket-agents/                  # Fork of Polymarket/agents
├── agents/
│   ├── application/
│   │   ├── creator.py             # [existing] Market creation
│   │   ├── cron.py                # [existing] Scheduling
│   │   ├── executor.py            # [existing] LLM execution - MODIFY
│   │   ├── prompts.py             # [existing] LLM prompts - MODIFY
│   │   ├── trade.py               # [existing] Trade logic - MODIFY
│   │   ├── agent_loop.py          # [ADD] Continuous agent loop
│   │   └── kelly_sizing.py        # [ADD] Kelly criterion sizing
│   ├── connectors/
│   │   ├── chroma.py              # [existing] RAG/vector DB
│   │   └── news_sources.py        # [ADD] News feed integration
│   ├── polymarket/
│   │   ├── gamma.py               # [existing] Gamma API client
│   │   ├── polymarket.py          # [existing] Polymarket API
│   │   └── objects.py             # [existing] Data models
│   ├── strategies/                # [ADD] Strategy implementations
│   │   ├── base_strategy.py       # [ADD] Strategy interface
│   │   ├── news_speed.py          # [ADD] News → Signal strategy
│   │   └── risk_manager.py        # [ADD] Risk limits
│   ├── tracking/                  # [ADD] Performance tracking
│   │   ├── performance.py         # [ADD] P&L tracking
│   │   ├── backtest.py            # [ADD] Historical testing
│   │   └── paper_trade.py         # [ADD] Simulated execution
│   └── utils/
│       └── objects.py             # [existing] Utilities
├── scripts/
│   ├── python/
│   │   └── cli.py                 # [existing] CLI interface
│   └── bash/
│       └── build-docker.sh        # [existing] Docker scripts
├── config/                        # [ADD] Configuration
│   ├── settings.yaml              # [ADD] Bot settings
│   └── strategies.yaml            # [ADD] Strategy parameters
├── data/                          # [ADD] Data storage
│   ├── historical/                # [ADD] Backtest data
│   └── logs/                      # [ADD] Execution logs
├── .env                           # API keys (not committed)
├── requirements.txt               # [existing] Dependencies
└── README.md                      # [existing] Documentation
```

**Legend:** `[existing]` = from fork, `[ADD]` = we build, `[MODIFY]` = we extend

### Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Runtime | Python 3.9+ | Matches Polymarket/agents base |
| LLM Framework | LangChain | Model flexibility, existing infra from fork |
| Default Model | OpenAI GPT (repo default) | Already integrated, swap later if needed |
| RAG | Chroma | Already integrated in Polymarket/agents |
| Data Storage | SQLite (MVP) | Simple, no infra needed |
| Scheduling | APScheduler | In-process scheduling |
| Hosting | Local homelab | Full control, no costs |

---

## Data Integrations

### Polymarket API

**Capabilities Needed:**
- [ ] Read market data (odds, volume, liquidity)
- [ ] Read order book
- [ ] Place orders (buy YES/NO shares)
- [ ] Read positions
- [ ] Read historical data (for backtesting)

**Research Required:** Explore Polymarket API/SDK before building

**Known Options:**
- Polymarket API (official)
- py-clob-client (Python SDK)
- Direct CLOB interaction

**Operational Constraints (validate during implementation):**
- Expect strict rate limits on some endpoints; implement caching, backoff, and batching where possible.
- Treat order-book reads and trade placement as separate concerns: reads can be throttled, writes must be guarded by risk controls + idempotency.

### News Ingestion

**Option 1: Integrate AI News Aggregator (evaluate first)**
- Existing project at `~/Documents/Code/ai-news-aggregator-agent`
- Already aggregates AI/tech news
- May need expansion for politics/crypto/sports

**Option 2: Fresh Build**
- RSS feeds (politics, crypto, sports)
- NewsAPI or similar
- Twitter/X via Grok

**Evaluation Criteria:**
- Does existing aggregator cover Polymarket-relevant categories?
- How fast is the news latency?
- Can it be easily adapted?

### Market Categories (Polymarket)

| Category | News Sources | Priority |
|----------|--------------|----------|
| Politics/Elections | Political news, polls | High |
| Crypto | Crypto news, SEC, ETFs | High |
| Sports | Sports news, injury reports | Medium |
| Entertainment | Celebrity, pop culture | Low |
| Science/Tech | Tech news, AI | Medium |

---

## Edge Strategy: News Speed (MVP)

### How It Works

```
1. NEWS ARRIVES
   └── AI News Aggregator detects breaking news

2. RELEVANCE MAPPING
   └── LLM determines which Polymarket markets are affected
   └── Assesses impact direction (YES more likely or NO?)

3. PROBABILITY SHIFT ESTIMATION
   └── Estimates new probability given the news
   └── Compares to current market odds

4. EDGE CALCULATION
   └── If estimated prob differs significantly from market → edge exists
   └── Calculate expected value

5. EXECUTION
   └── If EV positive and passes risk checks → place bet
   └── Kelly criterion sizing based on edge magnitude
```

### Example Flow

```
News: "SEC Chair confirms Bitcoin ETF approval decision by Friday"

1. Relevance: Maps to "Bitcoin ETF approved by Jan 15?" market
2. Impact: Positive for YES (approval more likely)
3. Current odds: 65% YES
4. Estimated: 80% YES (based on news sentiment)
5. Edge: 15 percentage points
6. Action: Buy YES shares, Kelly-sized bet
```

### Signal Extraction Prompt (LLM)

```
Given this breaking news:
"{news_headline}"
"{news_summary}"

And these active Polymarket markets:
{market_list}

Tasks:
1. Which markets (if any) are directly affected by this news?
2. For each affected market:
   - Direction: Does this make YES or NO more likely?
   - Magnitude: How much should probability shift? (1-5 scale)
   - Confidence: How certain are you? (1-10)
   - Reasoning: Brief explanation

Return JSON format.
```

---

## Execution Engine

### Kelly Criterion Sizing

```python
def kelly_fraction(prob_win: float, odds: float) -> float:
    """
    Calculate optimal bet size using Kelly criterion.

    prob_win: Our estimated probability of winning
    odds: Market odds (e.g., 2.0 for even money)

    Returns: Fraction of bankroll to bet
    """
    q = 1 - prob_win
    kelly = (prob_win * odds - q) / odds

    # Half-Kelly for safety
    return max(0, kelly * 0.5)
```

### Risk Management

| Rule | Value | Rationale |
|------|-------|-----------|
| Max bet per market | 5% of bankroll | Diversification |
| Max daily loss | 10% of bankroll | Stop-loss |
| Min edge to bet | 5% | Avoid noise |
| Max concurrent positions | 10 | Concentration limit |
| Liquidity check | Bet < 10% of market volume | Slippage protection |

**Important:** Treat “edge” as *after-fee expected value*, not just `estimated_prob - market_prob`.
- For a YES share bought at price `p` with estimated probability `q`, a simple (fee-free) EV per $1 risked is: `EV = q*(1-p) - (1-q)*p`.
- On a CLOB, replace `p` with the expected fill price (best ask + slippage) and subtract taker fees / other applicable fees.

### Execution Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| **Backtest** | Simulate on historical data | Strategy validation |
| **Paper** | Real signals, simulated execution | Final validation |
| **Live** | Real execution | Production |

---

## Validation Pipeline

### Phase 1: Backtest
- Load historical Polymarket data
- Load historical news data
- Run strategy on past events
- Measure: Win rate, ROI, edge consistency

**Success Criteria:** Strategy shows positive edge in backtest

### Phase 2: Paper Trade (1-3 days)
- Run bot in paper mode
- Real signals, simulated execution
- Measure: Signal quality, execution timing

**Success Criteria:** Signals are timely and relevant

### Phase 3: Live Trading ($100-500)
- Deploy with small capital
- Real execution
- Run for 30 days

**Success Criteria:** Positive ROI, validated edge

---

## Performance Tracking

### Metrics to Track

| Metric | Purpose |
|--------|---------|
| Total P&L | Overall performance |
| P&L by strategy | Which edge works best |
| Win rate | Accuracy |
| Average edge | Size of advantage |
| Sharpe ratio | Risk-adjusted returns |
| Max drawdown | Risk measurement |
| Bets per day | Activity level |

### Logging

```
logs/
├── bets/
│   └── 2026-01-08.jsonl    # All bets with rationale
├── signals/
│   └── 2026-01-08.jsonl    # All signals (even non-executed)
└── performance/
    └── daily_summary.json   # Daily P&L summary
```

---

## MVP Roadmap

### Phase 1: Foundation (Days 1-3)

**Goal:** Get data flowing

- [ ] Research Polymarket API capabilities
- [ ] Set up project structure
- [ ] Implement Polymarket market data fetching
- [ ] Implement basic news ingestion (evaluate AI News Aggregator)
- [ ] Store historical data for backtesting

**Deliverable:** Can fetch markets and news

### Phase 2: Signal Generation (Days 4-6)

**Goal:** Detect opportunities

- [ ] Implement news → market relevance mapping
- [ ] Implement probability shift estimation
- [ ] Implement edge calculation
- [ ] Build signal output format

**Deliverable:** System generates signals from news

### Phase 3: Backtesting (Days 7-9)

**Goal:** Validate strategy

- [ ] Build backtesting framework
- [ ] Load historical data
- [ ] Run backtest on news speed strategy
- [ ] Analyze results

**Deliverable:** Know if strategy has edge

### Phase 4: Execution (Days 10-12)

**Goal:** Trade capability

- [ ] Implement Polymarket order placement
- [ ] Implement Kelly sizing
- [ ] Implement risk management
- [ ] Paper trading mode

**Deliverable:** Can execute (paper) trades

### Phase 5: Paper Trading (Days 13-15)

**Goal:** Final validation

- [ ] Run in paper mode for 1-3 days
- [ ] Monitor signals and execution
- [ ] Fix issues
- [ ] Prepare for live

**Deliverable:** System ready for real capital

### Phase 6: Live Deployment

**Goal:** Make money

- [ ] Deploy with $100-500
- [ ] Monitor for 30 days
- [ ] Track performance
- [ ] Iterate on strategy

**Deliverable:** Working autonomous trading bot

---

## Configuration

### settings.yaml

```yaml
# Polymarket settings
polymarket:
  api_key: ${POLYMARKET_API_KEY}
  wallet_address: ${WALLET_ADDRESS}

# Trading settings
trading:
  mode: paper  # backtest, paper, live
  bankroll: 500.0  # Starting capital
  max_bet_pct: 0.05  # 5% max per market
  max_daily_loss_pct: 0.10  # 10% daily stop
  min_edge: 0.05  # 5% minimum edge to bet
  kelly_fraction: 0.5  # Half-Kelly

# News settings
news:
  sources:
    - ai_news_aggregator  # If integrated
    - rss_politics
    - rss_crypto
  check_interval_seconds: 60

# Strategies
strategies:
  news_speed:
    enabled: true
    weight: 1.0
  probability:
    enabled: false  # Enable after news_speed validated
    weight: 0.0
  sentiment:
    enabled: false
    weight: 0.0
```

---

## Success Criteria

### 30-Day Evaluation

| Metric | Target | Measurement |
|--------|--------|-------------|
| ROI | > 0% | (End balance - Start) / Start |
| Win rate | > 55% | Winning bets / Total bets |
| Edge validated | At least 1 strategy | Consistent positive EV |
| System uptime | > 95% | Time running / Total time |
| False signals | < 30% | Bad signals / Total signals |

### Kill Criteria

Stop and reevaluate if:
- Drawdown > 30% of bankroll
- Win rate < 45% after 50+ bets
- System errors > 5% of signals

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Polymarket API changes | Abstract API layer, monitor for changes |
| News latency | Optimize ingestion, cache nothing |
| Overfitting in backtest | Out-of-sample validation |
| Liquidity issues | Check liquidity before betting |
| Regulatory | Polymarket only, monitor legal status |
| Edge decay | Continuous monitoring, adapt strategies |

---

## Future Expansion (NOT MVP)

After 30-day validation:
- Add more strategies (probability, sentiment, arbitrage)
- Add Kalshi for multi-platform arbitrage
- Integrate with Alpha Research System
- Build Telegram alerts for monitoring
- Add more sophisticated ML models
- Multi-model consensus for higher confidence signals

**See:** `PLANNING.md` for research queue and exploration items.

---

## Related Files

- `03_Projects/Prediction_Markets_Bot/PLANNING.md` - Research queue & future exploration
- `03_Projects/Prediction_Markets_Agent.md` - Original idea doc
- `03_Projects/Alpha_Research_System/SPEC.md` - Broader research system (future)
- `~/Documents/Code/ai-news-aggregator-agent/` - Potential news source

---

## Implementation Base

**Starting Point:** Fork of [Polymarket/agents](https://github.com/Polymarket/agents) (official repo)

**Why this base:**
- Official Polymarket repo, MIT license
- Python 3.9, well-structured architecture
- Built-in: API integration, RAG support, LLM tools, news sourcing
- Uses `py-clob-client` (official Python SDK)
- CLI interface for trading

**What we add:**
- Agent loop automation (continuous execution)
- News speed strategy implementation
- Kelly criterion sizing
- Backtesting framework
- Paper trading mode
- Performance tracking

**Evaluated & Rejected:**
- `llSourcell/Poly-Trader` - Demo only, fake "AI" (random numbers), no real strategy
- Building from scratch - Would duplicate existing solid infrastructure

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-08 | 1.0 | Initial specification |
| 2026-01-08 | 1.1 | Added agent loop definition, multi-model consensus (future), implementation base |
| 2026-01-08 | 1.2 | Created PLANNING.md for research items, moved exploration items out of SPEC |
| 2026-01-08 | 1.3 | Finalized tech stack: LangChain + OpenAI GPT default (swappable), not Claude Agent SDK |
| 2026-01-08 | 1.4 | Updated folder structure to match Polymarket/agents fork, fixed prompt heading |

---

*Ship fast, validate with data, iterate.*
