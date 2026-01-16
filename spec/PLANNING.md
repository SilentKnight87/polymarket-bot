# Prediction Markets Bot - Planning & Research

**Purpose:** Research items, future exploration, and ideas not yet ready for SPEC.md. Items graduate to SPEC once validated.

**Last Updated:** 2026-01-15

---

## Research Queue

### 1. Arbitrage Detection Strategy

**Status:** To Research

**Context:** Spotted on Twitter - bot allegedly turned $300 → $109k in 7 days using Dutch book arbitrage on XRP micro-markets.

**The Concept:**
```
If YES price + NO price < $1.00
   → Buy both sides
   → Guaranteed profit when market resolves
```

**Research Questions:**
- [ ] How often do these mispricings occur on Polymarket?
- [ ] What latency is required to capture them?
- [ ] Can we monitor via WebSocket for real-time detection?
- [ ] What's the realistic profit margin after fees?
- [ ] How crowded is this strategy? (HFT competition)

**Challenges:**
- Opportunities last milliseconds
- Heavy HFT competition
- Requires different infrastructure (speed vs reasoning)
- Capital tied up until resolution

**Validation Notes (2026-01-15):**
- "YES + NO < $1" only implies a lock-in if you can fill both legs at those prices and your all-in cost is < $1 *after* fees; on an order book this usually means `best_ask_yes + best_ask_no + fees < 1.0` (and sufficient size available at those asks).
- Fees are market/product-dependent; incorporate *taker fees*, any settlement/market fees, and slippage into the arbitrage threshold.
- Main failure modes: partial fills, queue position/latency, and “looks like < 1” due to tiny size at top-of-book.
- Capital is tied up until resolution, so even “guaranteed” profit can be a low annualized return unless turnover is high.

**Measurement Plan (lightweight, no trading):**
- Build a scanner that periodically pulls order books for a universe of markets and logs occurrences where `best_ask_yes + best_ask_no < 1 - fee_buffer`, along with available size and how long it persists.
- Use this to decide if arbitrage is worth building (and whether we need websockets / lower-latency infra).

**Verdict:** Interesting but likely NOT MVP priority. News speed strategy has less competition and leverages AI reasoning (our strength) over raw speed.

**Source:** https://polymarket.com/@AIRules247

---

### 2. Multi-Model Consensus

**Status:** To Explore (Post-MVP)

**Concept:** Run probability estimation through multiple LLMs, weight by agreement for higher confidence signals.

```
News Article
     │
     ├──► Claude ──► 75% probability
     │
     ├──► GPT-4 ───► 72% probability
     │
     └──► Grok 4 ──► 78% probability
              │
              ▼
     ┌─────────────────────┐
     │ CONSENSUS: 75% avg  │
     │ Agreement: HIGH     │
     │ → Higher confidence │
     └─────────────────────┘
```

**Benefits:**
- Reduces single-model bias
- High agreement = higher confidence signals
- Low agreement = potential noise, reduce bet size

**Implementation Ideas:**
- Run same prompt through 2-3 models
- Weight by historical accuracy per model
- Use agreement level to adjust Kelly fraction

**Why Defer:** Adds latency and cost. Validate single-model approach first, add consensus if edge needs improvement.

**Validation Notes (2026-01-15):**
- For a “news speed” strategy, multi-model calls can kill latency; if we use an ensemble, prefer a *cascaded* design:
  - fast/cheap model for (1) market retrieval + (2) coarse direction,
  - slower/stronger model only for the top K candidates (probability + reasoning),
  - optional second opinion only when edge is large enough to justify latency/cost.

**Research Questions:**
- [ ] What's the latency cost of multi-model calls?
- [ ] Which models perform best on probability estimation?
- [ ] Is agreement a reliable confidence signal?

---

### 3. Model Selection for Prediction Markets

**Status:** Active Research

**Context:** Different benchmarks show different winners:
- **Alpha Arena (stock trading):** Grok 4.2 won (+12% return)
- **STOCKBENCH:** Kimi-K2 won
- But stock trading ≠ prediction markets

**Key Question:** Which model is best for prediction market tasks?
- News interpretation
- Probability estimation
- Event outcome reasoning

**Models to Evaluate:**
| Model | Availability | Notes |
|-------|--------------|-------|
| Claude Opus 4.5 | API | Strong reasoning, our default |
| Claude Sonnet 4 | API | Faster, cheaper |
| GPT-4o | API | Good baseline |
| Grok 4 | api.x.ai | Won stock trading benchmark |
| Grok 4 Fast | api.x.ai (free tier) | Speed optimized |

**Research Questions:**
- [ ] Can we build a simple eval comparing models on probability estimation?
- [ ] Is stock trading performance predictive of prediction market performance?
- [ ] What's the cost/latency trade-off for each model?

**Validation Notes (2026-01-15):**
- Use prediction-market-specific metrics (not stock-trading leaderboards):
  - Calibration (Brier score) vs market-implied probability at decision time
  - “Would-have-traded” P&L in paper/backtest (after fees + slippage assumptions)
  - Latency (p50/p95 end-to-end) and token cost per actionable signal

**Current Plan:** Start with OpenAI GPT (repo default), add model comparison later if needed.

---

### 4. Architecture Decision: LangChain vs Claude Agent SDK

**Status:** DECIDED - LangChain

**Decision Date:** 2026-01-08

**Choice:** Keep LangChain (Option A)

**Rationale:**
- Model flexibility is critical for profitability - need to test Claude, GPT, Grok
- Polymarket/agents already uses LangChain (not LangGraph - that's just an unused dependency)
- Claude Agent SDK locks you into Claude only - can't A/B test models
- Swapping models in LangChain is trivial (`ChatOpenAI` → `ChatAnthropic`)
- RAG (Chroma) already works - don't rebuild

**Implementation:**
1. Fork Polymarket/agents as-is
2. Keep OpenAI GPT as default (already integrated)
3. Keep LangChain abstractions for future model swaps
4. If GPT underperforms → swap to Claude, Grok, or others

**Rejected:** Claude Agent SDK - too much lock-in, no model flexibility

---

### 5. Stack Upgrades (ChatGPT Recommendations)

**Status:** Partially Decided

**ChatGPT suggested these upgrades over Polymarket/agents defaults:**

| Component | Current (Polymarket/agents) | Recommended | Priority | Decision |
|-----------|----------------------------|-------------|----------|----------|
| HTTP | requests | httpx + tenacity | Medium | Defer |
| DB/ORM | None (Chroma only) | SQLModel + SQLite | High | **Yes - MVP** |
| CLI | argparse | Typer + Rich | Low | Defer |
| Logging | print statements | loguru or structlog | Medium | Defer |
| Scheduling | None | APScheduler | High | **Yes - MVP** |
| Backtest Analytics | None | DuckDB or quantstats | Low | Defer |
| News/RSS | None | feedparser + trafilatura | High | **Yes - MVP** |
| Config | .env only | pydantic-settings | Medium | Defer |

**MVP Stack Additions:**
- APScheduler (agent loop)
- SQLModel + SQLite (tracking)
- feedparser (RSS ingestion)
- trafilatura (article text extraction)
- tenacity (retries - may add if needed)

**Post-MVP:**
- loguru/structlog (better logging)
- Typer + Rich (better CLI)
- quantstats (performance analytics)
- pydantic-settings (typed config)
- DuckDB (backtest analytics)

---

### 6. News Ingestion Options

**Status:** To Evaluate

**Option 1: Integrate AI News Aggregator**
- Existing project at `~/Documents/Code/ai-news-aggregator-agent`
- Already aggregates AI/tech news
- May need expansion for politics/crypto/sports

**Option 2: Fresh Build**
- RSS feeds (politics, crypto, sports)
- NewsAPI or similar
- Twitter/X via Grok

**Research Questions:**
- [ ] Does AI News Aggregator cover Polymarket-relevant categories?
- [ ] What's the news latency?
- [ ] Can it be easily adapted?

---

### 7. Polymarket MCP Server

**Status:** Noted for Reference

**Found during research:** `caiovicentino/polymarket-mcp-server`
- 45 tools for Claude + Polymarket integration
- Could be useful for development/testing
- Not for production bot (we need direct API)

**Research Questions:**
- [ ] Is this useful for rapid prototyping?
- [ ] Any tools we should port to our bot?

---

### 8. Social Sentiment: Grok Agentic Search vs Traditional APIs

**Status:** DECIDED - Grok Agentic Search

**Decision Date:** 2026-01-08

**Context:** ChatGPT recommended tweepy (Twitter API) + praw (Reddit API) for social sentiment. But X/Twitter API is expensive and rate-limited.

**Options Evaluated:**

| Approach | Pros | Cons |
|----------|------|------|
| **tweepy (Twitter API)** | Direct access, raw data | $100+/month, strict rate limits, complex auth |
| **praw (Reddit API)** | Free, good community | Noisy data, mod rules |
| **Grok Agentic Search** | Native X access, real-time, free tier available | Grok's interpretation (not raw tweets) |

**Decision: Grok Agentic Search**

**Rationale:**
- Grok (xAI) has native X/Twitter access - it's integrated with the platform
- One API (xAI) instead of managing two (OpenAI + Twitter)
- Grok 4 Fast has free tier at api.x.ai
- Real-time search built-in
- Synergy: If Grok performs well, use for both sentiment AND probability estimation
- Avoids Twitter API cost/complexity

**Implementation:**
- Use Grok API for Twitter/X sentiment queries
- Use praw for Reddit if needed (free, separate concern)
- Keep LangChain for model flexibility (can swap Grok ↔ GPT ↔ Claude)

**Trade-off accepted:** Grok interprets tweets rather than giving raw data. For sentiment analysis, this is actually fine - we want interpretation anyway.

---

## Future Expansion Ideas

These are ideas mentioned but not prioritized:

1. **Kalshi Integration** - Multi-platform arbitrage
2. **Telegram Alerts** - Monitoring notifications
3. **ML Models** - Beyond LLM prompting
4. **Whale Tracking** - Follow smart money (from Awesome-Prediction-Market-Tools)
5. **Reddit Sentiment** - Via praw (free API)

---

## Graduated to SPEC

Items that have been researched and moved to SPEC.md:

- [x] Agent Loop Definition (added 2026-01-08)
- [x] Implementation Base: Polymarket/agents fork (added 2026-01-08)
- [x] Kelly Criterion Sizing
- [x] News Speed Strategy (MVP)
- [x] Risk Management Rules

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-08 | Fork Polymarket/agents as base | Official repo, solid infrastructure, MIT license |
| 2026-01-08 | Reject Poly-Trader | Fake AI (random numbers), demo only |
| 2026-01-08 | News Speed as MVP strategy | Leverages AI reasoning, less HFT competition |
| 2026-01-08 | Defer arbitrage to post-MVP | Requires speed infrastructure we don't have |
| 2026-01-08 | LangChain over Claude Agent SDK | Model flexibility critical for profitability, SDK locks into Claude only |
| 2026-01-08 | Keep OpenAI GPT as default | Already integrated in fork, swap models later if needed |
| 2026-01-08 | Grok Agentic Search for Twitter | Native X access, avoids expensive Twitter API, free tier available |

---

*Research items here. Build items in SPEC.md.*
