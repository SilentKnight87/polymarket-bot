"""Unified interface for LLM providers supporting probability estimation."""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    latency_ms: float
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None


# Pricing per 1M tokens (as of Jan 2026)
MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    # Anthropic
    "claude-opus-4-5": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    # xAI
    "grok-4": {"input": 3.00, "output": 15.00},
    "grok-4-fast": {"input": 0.00, "output": 0.00},  # Free tier
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """Estimate cost in USD for a model call."""
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return None
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'openai', 'anthropic', 'xai')."""
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """Model identifier."""
        ...

    @abstractmethod
    def invoke(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        """Invoke the LLM with a prompt and optional system message."""
        ...


class OpenAIProvider(LLMProvider):
    """OpenAI GPT models via langchain."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.0):
        from langchain_openai import ChatOpenAI

        self._model = model
        self._temperature = temperature
        self._llm = ChatOpenAI(model=model, temperature=temperature)

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def invoke(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        start = time.perf_counter()
        result = self._llm.invoke(messages)
        latency_ms = (time.perf_counter() - start) * 1000

        content = getattr(result, "content", str(result))

        # Extract token usage if available
        usage = getattr(result, "response_metadata", {}).get("usage", {})
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")

        cost = None
        if input_tokens and output_tokens:
            cost = estimate_cost(self._model, input_tokens, output_tokens)

        return LLMResponse(
            content=content,
            latency_ms=latency_ms,
            model=self._model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )


class AnthropicProvider(LLMProvider):
    """Anthropic Claude models via langchain."""

    def __init__(self, model: str = "claude-sonnet-4", temperature: float = 0.0):
        from langchain_anthropic import ChatAnthropic

        self._model = model
        self._temperature = temperature
        self._llm = ChatAnthropic(model=model, temperature=temperature)

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    def invoke(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        start = time.perf_counter()
        result = self._llm.invoke(messages)
        latency_ms = (time.perf_counter() - start) * 1000

        content = getattr(result, "content", str(result))

        # Extract token usage
        usage = getattr(result, "response_metadata", {}).get("usage", {})
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")

        cost = None
        if input_tokens and output_tokens:
            cost = estimate_cost(self._model, input_tokens, output_tokens)

        return LLMResponse(
            content=content,
            latency_ms=latency_ms,
            model=self._model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )


class XAIProvider(LLMProvider):
    """xAI Grok models via OpenAI-compatible API."""

    def __init__(self, model: str = "grok-4", temperature: float = 0.0):
        from langchain_openai import ChatOpenAI

        self._model = model
        self._temperature = temperature

        # xAI uses OpenAI-compatible API
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError("XAI_API_KEY environment variable required for Grok models")

        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=api_key,
            openai_api_base="https://api.x.ai/v1",
        )

    @property
    def name(self) -> str:
        return "xai"

    @property
    def model(self) -> str:
        return self._model

    def invoke(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        start = time.perf_counter()
        result = self._llm.invoke(messages)
        latency_ms = (time.perf_counter() - start) * 1000

        content = getattr(result, "content", str(result))

        usage = getattr(result, "response_metadata", {}).get("usage", {})
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")

        cost = None
        if input_tokens and output_tokens:
            cost = estimate_cost(self._model, input_tokens, output_tokens)

        return LLMResponse(
            content=content,
            latency_ms=latency_ms,
            model=self._model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )


@dataclass
class ProviderConfig:
    """Configuration for instantiating a provider."""

    provider_class: type
    model: str
    temperature: float = 0.0


# Registry of available models
MODEL_REGISTRY: dict[str, ProviderConfig] = {
    # OpenAI
    "gpt-4o": ProviderConfig(OpenAIProvider, "gpt-4o"),
    "gpt-4o-mini": ProviderConfig(OpenAIProvider, "gpt-4o-mini"),
    "gpt-4-turbo": ProviderConfig(OpenAIProvider, "gpt-4-turbo"),
    # Anthropic
    "claude-opus-4-5": ProviderConfig(AnthropicProvider, "claude-opus-4-5"),
    "claude-sonnet-4": ProviderConfig(AnthropicProvider, "claude-sonnet-4"),
    "claude-3-5-haiku": ProviderConfig(AnthropicProvider, "claude-3-5-haiku"),
    # xAI
    "grok-4": ProviderConfig(XAIProvider, "grok-4"),
    "grok-4-fast": ProviderConfig(XAIProvider, "grok-4-fast"),
}


def get_provider(model: str, temperature: float = 0.0) -> LLMProvider:
    """Get an LLM provider instance by model name."""
    config = MODEL_REGISTRY.get(model)
    if not config:
        available = ", ".join(sorted(MODEL_REGISTRY.keys()))
        raise ValueError(f"Unknown model: {model}. Available: {available}")

    return config.provider_class(model=config.model, temperature=temperature)


def list_available_models() -> list[str]:
    """List all available model identifiers."""
    return sorted(MODEL_REGISTRY.keys())
