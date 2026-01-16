from __future__ import annotations

import json
import os
import re
import ast
from datetime import datetime, timezone
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.connectors.news_sources import NewsArticle
from agents.strategies.base_strategy import BaseStrategy
from agents.utils.config import Config
from agents.utils.models import Signal


_JSON_BLOCK_RE = re.compile(r"(\{.*\})", re.DOTALL)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_direction(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().upper()
    if text in {"YES", "NO"}:
        return text
    return None


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    stop = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "he",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "was",
        "were",
        "will",
        "with",
    }
    return [w for w in words if w not in stop and len(w) > 2]


def _extract_yes_no_prices(market: dict) -> tuple[Optional[float], Optional[float]]:
    """
    Best-effort extraction for YES/NO prices from various market dict shapes.
    Supports:
    - {"yes_price": 0.6, "no_price": 0.4}
    - Gamma market shape with "outcomes" + "outcomePrices" (lists or stringified lists)
    - Fork shape with "outcomes" + "outcome_prices" (stringified lists)
    """
    yes = _safe_float(market.get("yes_price"))
    no = _safe_float(market.get("no_price"))
    if yes is not None and no is not None:
        return yes, no

    outcomes = market.get("outcomes") or market.get("outcome") or market.get("outcome_labels")
    prices = market.get("outcomePrices") or market.get("outcome_prices") or market.get("outcomePrice")

    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except json.JSONDecodeError:
            try:
                outcomes = ast.literal_eval(outcomes)
            except Exception:  # noqa: BLE001
                pass
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except json.JSONDecodeError:
            try:
                prices = ast.literal_eval(prices)
            except Exception:  # noqa: BLE001
                pass

    if not isinstance(outcomes, list) or not isinstance(prices, list):
        return None, None

    outcome_to_price: dict[str, float] = {}
    for idx, outcome in enumerate(outcomes):
        if idx >= len(prices):
            continue
        price = _safe_float(prices[idx])
        if price is None:
            continue
        outcome_to_price[str(outcome).strip().lower()] = price

    yes_price = None
    no_price = None
    for key, price in outcome_to_price.items():
        if key in {"yes", "y"}:
            yes_price = price
        elif key in {"no", "n"}:
            no_price = price

    return yes_price, no_price


def _market_id(market: dict) -> Optional[str]:
    for key in ("market_id", "id"):
        if key in market and market[key] is not None:
            return str(market[key])
    return None


class NewsSpeedStrategy(BaseStrategy):
    def __init__(self, config: Config, llm: Any = None) -> None:
        self.config = config

        strategy_cfg = (config.strategies or {}).get("news_speed", {})
        self.min_confidence = int(strategy_cfg.get("min_confidence", 6))
        self.max_markets_per_cycle = int(strategy_cfg.get("max_markets_per_cycle", 5))
        self.min_edge = float(config.min_edge)

        if llm is not None:
            self.llm = llm
        else:
            model = os.getenv("NEWS_SPEED_MODEL", "gpt-4o")
            self.llm = ChatOpenAI(model=model, temperature=0)

    @property
    def name(self) -> str:
        return "news_speed"

    def generate_signals(self, articles: list[NewsArticle], markets: list[dict]) -> list[Signal]:
        signals: list[Signal] = []
        if not articles or not markets:
            return signals

        for article in articles:
            candidate_markets = self._select_candidate_markets(article, markets)
            if not candidate_markets:
                continue

            prompt = self._build_prompt(article, candidate_markets)
            response = self._call_llm(prompt)
            affected = self._parse_llm_response(response)
            if not affected:
                continue

            market_by_id = {_market_id(m): m for m in candidate_markets}
            for row in affected:
                mid = row.get("market_id")
                if mid is None:
                    continue
                market = market_by_id.get(str(mid))
                if not market:
                    continue

                direction = _normalize_direction(row.get("direction"))
                if direction is None:
                    continue

                confidence = int(row.get("confidence", 0) or 0)
                if confidence < self.min_confidence:
                    continue
                confidence = int(_clamp(float(confidence), 1.0, 10.0))

                estimated_prob = _safe_float(row.get("estimated_prob"))
                if estimated_prob is None:
                    continue
                estimated_prob = _clamp(estimated_prob, 0.0, 1.0)

                yes_price, no_price = _extract_yes_no_prices(market)
                if yes_price is None or no_price is None:
                    continue

                current_odds = yes_price if direction == "YES" else no_price
                current_odds = _clamp(current_odds, 0.0, 1.0)
                edge = estimated_prob - current_odds

                if edge < self.min_edge:
                    continue

                signals.append(
                    Signal(
                        timestamp=_utc_now(),
                        market_id=str(mid),
                        market_question=str(market.get("question", "")),
                        direction=direction,  # type: ignore[arg-type]
                        current_odds=current_odds,
                        estimated_prob=estimated_prob,
                        edge=edge,
                        confidence=confidence,
                        reasoning=str(row.get("reasoning", "")).strip(),
                        news_headline=article.headline,
                    )
                )

        return signals

    def _select_candidate_markets(self, article: NewsArticle, markets: list[dict]) -> list[dict]:
        max_candidates = max(1, self.max_markets_per_cycle)
        query = f"{article.headline}\n{article.summary}"
        tokens = set(_tokenize(query))
        if not tokens:
            return markets[:max_candidates]

        scored: list[tuple[int, dict]] = []
        for market in markets:
            question = str(market.get("question", "")).strip()
            if not question:
                continue
            q_tokens = set(_tokenize(question))
            score = len(tokens & q_tokens)
            if score <= 0:
                continue
            scored.append((score, market))

        scored.sort(key=lambda x: x[0], reverse=True)
        candidates = [m for _, m in scored[:max_candidates]]
        return candidates or markets[:max_candidates]

    def _build_prompt(self, article: NewsArticle, markets: list[dict]) -> str:
        simplified_markets = []
        for market in markets:
            mid = _market_id(market)
            if not mid:
                continue
            yes_price, no_price = _extract_yes_no_prices(market)
            if yes_price is None or no_price is None:
                continue
            simplified_markets.append(
                {
                    "market_id": mid,
                    "question": market.get("question", ""),
                    "yes_price": yes_price,
                    "no_price": no_price,
                    "end_date": market.get("endDate") or market.get("end") or None,
                    "volume_24h": market.get("volume24hr") or market.get("volume24hrClob") or market.get("volume") or None,
                }
            )

        markets_json = json.dumps(simplified_markets, ensure_ascii=False)

        return (
            "You are a careful prediction market analyst. Return ONLY valid JSON.\n\n"
            f'Breaking news:\n"{article.headline}"\n"{article.summary}"\n\n'
            "Active markets (subset):\n"
            f"{markets_json}\n\n"
            "Task:\n"
            "1) Identify which markets are directly affected by this news.\n"
            "2) For each affected market, output:\n"
            '- market_id (string)\n'
            '- direction ("YES" or "NO") for the side to buy\n'
            "- estimated_prob (0.0-1.0) for that side being correct\n"
            "- confidence (1-10)\n"
            "- reasoning (short)\n\n"
            "JSON schema:\n"
            '{\n  "affected_markets": [\n    {\n      "market_id": "123",\n      "direction": "YES",\n      "estimated_prob": 0.75,\n      "confidence": 8,\n      "reasoning": "..." \n    }\n  ]\n}\n\n'
            'If none, return {"affected_markets": []}.\n'
        )

    def _call_llm(self, prompt: str) -> str:
        system = SystemMessage(content="You output strict JSON and nothing else.")
        human = HumanMessage(content=prompt)
        result = self.llm.invoke([system, human])
        return getattr(result, "content", str(result))

    def _parse_llm_response(self, response: str) -> list[dict]:
        text = response.strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = _JSON_BLOCK_RE.search(text)
            if not match:
                return []
            try:
                parsed = json.loads(match.group(1))
            except json.JSONDecodeError:
                return []

        affected = parsed.get("affected_markets")
        if not isinstance(affected, list):
            return []

        cleaned: list[dict] = []
        for row in affected:
            if isinstance(row, dict):
                cleaned.append(row)
        return cleaned
