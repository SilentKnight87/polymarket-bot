# Phase 11: Model Selection Evaluation

**Status:** ✅ Complete
**Priority:** Post-MVP Enhancement
**Date:** 2026-01-24

---

## Overview

Framework for comparing LLM models on probability estimation accuracy for prediction markets. Enables data-driven model selection based on calibration (Brier score), accuracy, latency, and cost.

## Deliverables

### 1. LLM Provider Abstraction

**File:** `agents/evaluation/llm_providers.py`

Unified interface for multiple LLM providers:
- `OpenAIProvider` - GPT-4o, GPT-4o-mini, GPT-4-turbo
- `AnthropicProvider` - Claude Opus 4.5, Claude Sonnet 4, Claude 3.5 Haiku
- `XAIProvider` - Grok 4, Grok 4 Fast

Features:
- Consistent `invoke()` interface across providers
- Latency tracking (response time in ms)
- Token usage tracking (input/output)
- Cost estimation using model pricing table
- Model registry with `get_provider(model)` factory

### 2. Model Evaluator

**File:** `agents/evaluation/model_evaluator.py`

Core evaluation logic:
- `PredictionRecord` - Scenario data structure (news, market, outcome)
- `ModelPrediction` - Model's prediction for a scenario
- `EvaluationResult` - Aggregated metrics for a model
- `ModelEvaluator` - Main evaluation class

Key metrics:
- **Brier Score** - Calibration measure (0 = perfect, 1 = worst)
- **Accuracy** - Directional prediction correctness
- **Calibration Error** - Average |predicted - actual|
- **Latency** - p50 and p95 response times
- **Cost** - Total cost in USD

Category-specific breakdown:
- Politics, Crypto, Sports, Tech, Economics, Geopolitics

### 3. Sample Evaluation Dataset

**File:** `data/evaluation/sample_scenarios.json`

12 realistic scenarios across categories:
- News headline + summary
- Market question + prices
- Actual resolution outcome
- Category classification

### 4. Evaluation CLI

**File:** `scripts/python/evaluate_models.py`

```bash
# List available models
PYTHONPATH=. python scripts/python/evaluate_models.py --list-models

# Compare models (default: gpt-4o vs claude-sonnet-4)
PYTHONPATH=. python scripts/python/evaluate_models.py

# Specific models
PYTHONPATH=. python scripts/python/evaluate_models.py --models gpt-4o grok-4

# Limit scenarios (cost control)
PYTHONPATH=. python scripts/python/evaluate_models.py --max-scenarios 3

# Save results
PYTHONPATH=. python scripts/python/evaluate_models.py --output data/evaluation/results.json
```

### 5. Tests

**File:** `tests/test_model_evaluation.py`

18 tests covering:
- LLM provider abstraction
- Cost estimation
- Brier score calculation
- Category breakdown
- Report generation
- File I/O

---

## Usage Guide

### Running a Model Comparison

```python
from agents.evaluation import ModelEvaluator, get_provider

# Load scenarios
evaluator = ModelEvaluator()
evaluator.load_scenarios_from_file("data/evaluation/sample_scenarios.json")

# Compare models
results = evaluator.compare_models(
    models=["gpt-4o", "claude-sonnet-4", "grok-4"],
    max_scenarios=5  # Limit for cost control
)

# Generate report
report = evaluator.generate_report(results)
print(report)

# Save results
evaluator.save_results("results.json", results)
```

### Adding Custom Scenarios

```python
from agents.evaluation import ModelEvaluator, PredictionRecord

evaluator = ModelEvaluator()

# Add from historical data
evaluator.add_scenario(PredictionRecord(
    scenario_id="custom-001",
    news_headline="Major announcement",
    news_summary="Details of announcement...",
    market_question="Will X happen by Y?",
    market_yes_price=0.65,
    market_no_price=0.35,
    actual_outcome="YES",
    category="politics"
))
```

### Interpreting Results

| Metric | Excellent | Good | Poor |
|--------|-----------|------|------|
| Brier Score | < 0.10 | 0.10-0.25 | > 0.25 |
| Accuracy | > 70% | 50-70% | < 50% |
| Calibration | < 0.15 | 0.15-0.30 | > 0.30 |

---

## Environment Variables

Required API keys in `.env`:
```
OPENAI_API_KEY=sk-...          # For GPT models
ANTHROPIC_API_KEY=sk-ant-...   # For Claude models
XAI_API_KEY=xai-...            # For Grok models
```

---

## Success Criteria

- [x] Unified LLM provider interface
- [x] Brier score calculation verified correct
- [x] Category-specific metrics
- [x] Latency and cost tracking
- [x] CLI for running evaluations
- [x] Sample evaluation dataset
- [x] All tests passing (18/18)

---

## Next Steps

1. **Collect Historical Data** - Build larger evaluation dataset from actual Polymarket resolutions
2. **Run Live Comparison** - Execute evaluation with real API calls to benchmark models
3. **Integrate with Strategy** - Use findings to select optimal model for `NewsSpeedStrategy`
4. **Add Streaming Support** - Evaluate models with streaming for lower time-to-first-token
