# Phase 4: Signal Generation (News Speed Strategy)

**Dependencies:** Phase 1 (Models), Phase 3 (News)

**Tasks:** 2 (must run sequentially: 4.1 then 4.2)

---

## Task 4.1: Create Base Strategy Interface

**Goal:** Define abstract base class for strategies.

**Files to create:**
- `agents/strategies/base_strategy.py`

**Requirements:**
```python
from abc import ABC, abstractmethod
from agents.utils.models import Signal
from agents.connectors.news_sources import NewsArticle

class BaseStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for logging."""

    @abstractmethod
    def generate_signals(
        self,
        articles: list[NewsArticle],
        markets: list[dict]
    ) -> list[Signal]:
        """
        Analyze inputs and generate trading signals.

        Args:
            articles: New news articles since last check
            markets: Current Polymarket markets with odds

        Returns:
            List of trading signals (may be empty)
        """
```

**Design Rationale:**
- Abstract base allows multiple strategies (news_speed, arbitrage, sentiment)
- Each strategy implements its own signal generation logic
- Strategies are stateless - they receive inputs and return signals
- The agent loop orchestrates which strategies to run

**Success criteria:**
- [ ] Abstract base class defined
- [ ] Clear interface for generate_signals

---

## Task 4.2: Implement News Speed Strategy

**Goal:** Map news to markets and estimate probability shifts using LLM.

**Files to create:**
- `agents/strategies/news_speed.py`

**Requirements:**
```python
from langchain_openai import ChatOpenAI
from agents.strategies.base_strategy import BaseStrategy
from agents.utils.models import Signal

class NewsSpeedStrategy(BaseStrategy):
    def __init__(self, config: Config):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.min_confidence = 6  # 1-10 scale

    @property
    def name(self) -> str:
        return "news_speed"

    def generate_signals(
        self,
        articles: list[NewsArticle],
        markets: list[dict]
    ) -> list[Signal]:
        """
        For each article:
        1. Ask LLM which markets are affected
        2. Get probability shift estimate
        3. Calculate edge vs current odds
        4. Return signals that pass min_edge threshold
        """

    def _build_prompt(self, article: NewsArticle, markets: list[dict]) -> str:
        """Build the LLM prompt for signal extraction."""

    def _parse_llm_response(self, response: str) -> list[dict]:
        """Parse JSON response from LLM."""
```

**LLM Prompt Template:**
```
Given this breaking news:
"{headline}"
"{summary}"

And these active Polymarket markets:
{market_list}

Tasks:
1. Which markets (if any) are directly affected by this news?
2. For each affected market:
   - Direction: Does this make YES or NO more likely?
   - Magnitude: How much should probability shift? (1-5 scale)
   - Confidence: How certain are you? (1-10)
   - Reasoning: Brief explanation

Return JSON format:
{
  "affected_markets": [
    {
      "market_id": "...",
      "direction": "YES",
      "magnitude": 3,
      "confidence": 8,
      "estimated_prob": 0.75,
      "reasoning": "..."
    }
  ]
}

If no markets are affected, return: {"affected_markets": []}
```

**Edge Calculation:**
```python
# Market shows YES at 60 cents ($0.60)
# LLM estimates true probability is 75%
# Edge = 0.75 - 0.60 = 0.15 (15% edge)

edge = estimated_prob - current_market_odds
if edge > min_edge:
    # Generate signal
```

**Signal Flow:**
```
News Article
     │
     ▼
┌─────────────┐
│  LLM Call   │ "Which markets affected?"
└─────────────┘
     │
     ▼
┌─────────────┐
│ Parse JSON  │ Extract market_id, direction, prob
└─────────────┘
     │
     ▼
┌─────────────┐
│ Calc Edge   │ estimated_prob - market_odds
└─────────────┘
     │
     ▼
┌─────────────┐
│ Filter      │ edge > 5%? confidence > 6?
└─────────────┘
     │
     ▼
   Signal
```

**Success criteria:**
- [ ] Prompts LLM correctly
- [ ] Parses JSON response
- [ ] Calculates edge (estimated_prob - market_prob)
- [ ] Returns Signal objects
- [ ] Test: Pass mock article + markets, get signals

---

## Codex Assignment

**Run sequentially:**
1. Task 4.1: Base Strategy (defines interface)
2. Task 4.2: News Speed Strategy (implements interface)

Task 4.2 depends on 4.1 being complete first.
