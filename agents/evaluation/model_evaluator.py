"""Model evaluation framework for probability estimation accuracy."""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agents.evaluation.llm_providers import LLMProvider, LLMResponse, get_provider


@dataclass
class PredictionRecord:
    """A single prediction for evaluation."""

    scenario_id: str
    news_headline: str
    news_summary: str
    market_question: str
    market_yes_price: float
    market_no_price: float
    actual_outcome: str  # "YES" or "NO"
    category: Optional[str] = None  # e.g., "politics", "crypto", "sports"
    resolution_date: Optional[str] = None


@dataclass
class ModelPrediction:
    """A model's prediction for a scenario."""

    scenario_id: str
    model: str
    direction: str  # "YES" or "NO"
    estimated_prob: float  # probability for the predicted direction
    confidence: int  # 1-10
    reasoning: str
    latency_ms: float
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None


@dataclass
class EvaluationResult:
    """Aggregated evaluation results for a model."""

    model: str
    num_predictions: int
    brier_score: float  # Lower is better (0 = perfect, 1 = worst)
    calibration_error: float  # Average |predicted - actual|
    accuracy: float  # % of correct directional predictions
    avg_confidence: float
    avg_latency_ms: float
    p95_latency_ms: float
    total_cost_usd: float
    predictions: list[ModelPrediction] = field(default_factory=list)

    # Category-specific metrics
    category_brier: dict[str, float] = field(default_factory=dict)
    category_accuracy: dict[str, float] = field(default_factory=dict)


_JSON_BLOCK_RE = re.compile(r"(\{.*\})", re.DOTALL)


def _parse_prediction_response(response: str) -> dict:
    """Parse JSON from LLM response."""
    text = response.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    return {}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class ModelEvaluator:
    """Evaluate LLM models on probability estimation for prediction markets."""

    SYSTEM_PROMPT = "You output strict JSON and nothing else."

    def __init__(self, scenarios: Optional[list[PredictionRecord]] = None):
        self.scenarios = scenarios or []
        self._results: dict[str, list[ModelPrediction]] = {}

    def add_scenario(self, scenario: PredictionRecord) -> None:
        """Add a scenario for evaluation."""
        self.scenarios.append(scenario)

    def load_scenarios_from_file(self, path: str | Path) -> int:
        """Load scenarios from a JSON file. Returns count loaded."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        scenarios_raw = data.get("scenarios", [])
        count = 0
        for s in scenarios_raw:
            self.scenarios.append(
                PredictionRecord(
                    scenario_id=str(s.get("scenario_id", f"s{count}")),
                    news_headline=str(s.get("news_headline", "")),
                    news_summary=str(s.get("news_summary", "")),
                    market_question=str(s.get("market_question", "")),
                    market_yes_price=float(s.get("market_yes_price", 0.5)),
                    market_no_price=float(s.get("market_no_price", 0.5)),
                    actual_outcome=str(s.get("actual_outcome", "")).upper(),
                    category=s.get("category"),
                    resolution_date=s.get("resolution_date"),
                )
            )
            count += 1
        return count

    def build_prompt(self, scenario: PredictionRecord) -> str:
        """Build the probability estimation prompt for a scenario."""
        return (
            "You are analyzing a prediction market. Given breaking news and a related market, "
            "estimate the probability of the market resolving YES.\n\n"
            f'**Breaking News:**\n"{scenario.news_headline}"\n"{scenario.news_summary}"\n\n'
            f"**Market Question:** {scenario.market_question}\n"
            f"**Current YES Price:** {scenario.market_yes_price:.2f}\n"
            f"**Current NO Price:** {scenario.market_no_price:.2f}\n\n"
            "**Task:** Estimate the probability (0.0-1.0) that the market resolves YES.\n\n"
            "Return JSON:\n"
            "{\n"
            '  "direction": "YES" or "NO" (which side to bet),\n'
            '  "estimated_prob": 0.75 (probability for that direction),\n'
            '  "confidence": 8 (1-10),\n'
            '  "reasoning": "brief explanation"\n'
            "}\n"
        )

    def evaluate_model(self, model: str, max_scenarios: Optional[int] = None) -> list[ModelPrediction]:
        """
        Run evaluation for a single model across all scenarios.

        Args:
            model: Model identifier (e.g., 'gpt-4o', 'claude-sonnet-4')
            max_scenarios: Limit number of scenarios (for testing)

        Returns:
            List of predictions made by the model
        """
        try:
            provider = get_provider(model)
        except ValueError as e:
            # Return error predictions if provider unavailable
            return [
                ModelPrediction(
                    scenario_id=s.scenario_id,
                    model=model,
                    direction="",
                    estimated_prob=0.5,
                    confidence=0,
                    reasoning="",
                    latency_ms=0,
                    error=str(e),
                )
                for s in self.scenarios[:max_scenarios]
            ]

        predictions: list[ModelPrediction] = []
        scenarios_to_eval = self.scenarios[:max_scenarios] if max_scenarios else self.scenarios

        for scenario in scenarios_to_eval:
            prompt = self.build_prompt(scenario)
            try:
                response = provider.invoke(prompt, system=self.SYSTEM_PROMPT)
                parsed = _parse_prediction_response(response.content)

                direction = str(parsed.get("direction", "")).upper()
                if direction not in ("YES", "NO"):
                    direction = "YES"  # Default

                estimated_prob = _clamp(float(parsed.get("estimated_prob", 0.5)), 0.0, 1.0)
                confidence = int(_clamp(float(parsed.get("confidence", 5)), 1.0, 10.0))
                reasoning = str(parsed.get("reasoning", ""))

                predictions.append(
                    ModelPrediction(
                        scenario_id=scenario.scenario_id,
                        model=model,
                        direction=direction,
                        estimated_prob=estimated_prob,
                        confidence=confidence,
                        reasoning=reasoning,
                        latency_ms=response.latency_ms,
                        input_tokens=response.input_tokens,
                        output_tokens=response.output_tokens,
                        cost_usd=response.cost_usd,
                    )
                )

            except Exception as e:
                predictions.append(
                    ModelPrediction(
                        scenario_id=scenario.scenario_id,
                        model=model,
                        direction="",
                        estimated_prob=0.5,
                        confidence=0,
                        reasoning="",
                        latency_ms=0,
                        error=str(e),
                    )
                )

        self._results[model] = predictions
        return predictions

    def calculate_metrics(self, model: str) -> EvaluationResult:
        """Calculate evaluation metrics for a model's predictions."""
        predictions = self._results.get(model, [])
        if not predictions:
            return EvaluationResult(
                model=model,
                num_predictions=0,
                brier_score=1.0,
                calibration_error=1.0,
                accuracy=0.0,
                avg_confidence=0.0,
                avg_latency_ms=0.0,
                p95_latency_ms=0.0,
                total_cost_usd=0.0,
            )

        scenario_map = {s.scenario_id: s for s in self.scenarios}

        brier_scores: list[float] = []
        calibration_errors: list[float] = []
        correct_count = 0
        confidences: list[float] = []
        latencies: list[float] = []
        total_cost = 0.0

        # Category tracking
        category_brier: dict[str, list[float]] = {}
        category_correct: dict[str, tuple[int, int]] = {}  # (correct, total)

        valid_predictions = [p for p in predictions if not p.error]

        for pred in valid_predictions:
            scenario = scenario_map.get(pred.scenario_id)
            if not scenario:
                continue

            # Actual outcome as probability (1.0 for YES, 0.0 for NO)
            actual_yes_prob = 1.0 if scenario.actual_outcome == "YES" else 0.0

            # Model's estimated probability for YES
            if pred.direction == "YES":
                estimated_yes_prob = pred.estimated_prob
            else:
                estimated_yes_prob = 1.0 - pred.estimated_prob

            # Brier score: (predicted - actual)^2
            brier = (estimated_yes_prob - actual_yes_prob) ** 2
            brier_scores.append(brier)

            # Calibration error: |predicted - actual|
            calibration_errors.append(abs(estimated_yes_prob - actual_yes_prob))

            # Accuracy: did model predict correct direction?
            predicted_outcome = pred.direction
            if predicted_outcome == scenario.actual_outcome:
                correct_count += 1

            confidences.append(pred.confidence)
            latencies.append(pred.latency_ms)

            if pred.cost_usd:
                total_cost += pred.cost_usd

            # Category tracking
            cat = scenario.category or "unknown"
            if cat not in category_brier:
                category_brier[cat] = []
                category_correct[cat] = (0, 0)

            category_brier[cat].append(brier)
            c, t = category_correct[cat]
            category_correct[cat] = (
                c + (1 if predicted_outcome == scenario.actual_outcome else 0),
                t + 1,
            )

        num_valid = len(valid_predictions)

        # Calculate p95 latency
        sorted_latencies = sorted(latencies) if latencies else [0.0]
        p95_idx = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]

        return EvaluationResult(
            model=model,
            num_predictions=num_valid,
            brier_score=statistics.mean(brier_scores) if brier_scores else 1.0,
            calibration_error=statistics.mean(calibration_errors) if calibration_errors else 1.0,
            accuracy=(correct_count / num_valid) if num_valid else 0.0,
            avg_confidence=statistics.mean(confidences) if confidences else 0.0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0.0,
            p95_latency_ms=p95_latency,
            total_cost_usd=total_cost,
            predictions=predictions,
            category_brier={
                cat: statistics.mean(scores) for cat, scores in category_brier.items()
            },
            category_accuracy={
                cat: (counts[0] / counts[1]) if counts[1] else 0.0
                for cat, counts in category_correct.items()
            },
        )

    def compare_models(self, models: list[str], max_scenarios: Optional[int] = None) -> list[EvaluationResult]:
        """
        Evaluate multiple models and return comparative results.

        Args:
            models: List of model identifiers to evaluate
            max_scenarios: Limit scenarios per model (for testing/cost control)

        Returns:
            List of EvaluationResult, sorted by Brier score (best first)
        """
        results: list[EvaluationResult] = []

        for model in models:
            self.evaluate_model(model, max_scenarios=max_scenarios)
            result = self.calculate_metrics(model)
            results.append(result)

        # Sort by Brier score (lower is better)
        results.sort(key=lambda r: r.brier_score)
        return results

    def generate_report(self, results: list[EvaluationResult]) -> str:
        """Generate a markdown comparison report."""
        lines = [
            "# Model Evaluation Report",
            "",
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
            f"**Scenarios:** {len(self.scenarios)}",
            "",
            "## Summary (sorted by Brier Score)",
            "",
            "| Model | Brier Score | Accuracy | Avg Latency | P95 Latency | Cost |",
            "|-------|-------------|----------|-------------|-------------|------|",
        ]

        for r in results:
            cost_str = f"${r.total_cost_usd:.4f}" if r.total_cost_usd else "N/A"
            lines.append(
                f"| {r.model} | {r.brier_score:.4f} | {r.accuracy:.1%} | "
                f"{r.avg_latency_ms:.0f}ms | {r.p95_latency_ms:.0f}ms | {cost_str} |"
            )

        lines.extend(["", "## Interpretation", ""])
        lines.append("- **Brier Score:** 0.0 = perfect, 1.0 = worst. Lower is better.")
        lines.append("- **Accuracy:** Percentage of correct directional predictions.")
        lines.append("- **Latency:** Time to generate probability estimate.")

        # Category breakdown if available
        if results and results[0].category_brier:
            lines.extend(["", "## Category Breakdown (Brier Score)", ""])

            categories = set()
            for r in results:
                categories.update(r.category_brier.keys())

            header = "| Model | " + " | ".join(sorted(categories)) + " |"
            sep = "|-------|" + "|".join(["-------"] * len(categories)) + "|"
            lines.append(header)
            lines.append(sep)

            for r in results:
                row = f"| {r.model} |"
                for cat in sorted(categories):
                    score = r.category_brier.get(cat, 1.0)
                    row += f" {score:.4f} |"
                lines.append(row)

        # Winner summary
        if results:
            best = results[0]
            lines.extend([
                "",
                "## Recommendation",
                "",
                f"**Best Overall:** {best.model} (Brier: {best.brier_score:.4f}, Accuracy: {best.accuracy:.1%})",
            ])

            # Find best value (Brier * cost tradeoff)
            value_scores = []
            for r in results:
                if r.total_cost_usd and r.total_cost_usd > 0:
                    # Lower is better: Brier * (1 + log(cost))
                    import math

                    value = r.brier_score * (1 + math.log10(max(r.total_cost_usd, 0.0001)))
                    value_scores.append((value, r))

            if value_scores:
                value_scores.sort(key=lambda x: x[0])
                best_value = value_scores[0][1]
                if best_value.model != best.model:
                    lines.append(
                        f"**Best Value:** {best_value.model} "
                        f"(Brier: {best_value.brier_score:.4f}, Cost: ${best_value.total_cost_usd:.4f})"
                    )

        return "\n".join(lines)

    def save_results(self, path: str | Path, results: list[EvaluationResult]) -> None:
        """Save evaluation results to JSON."""
        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "num_scenarios": len(self.scenarios),
            "results": [
                {
                    "model": r.model,
                    "brier_score": r.brier_score,
                    "calibration_error": r.calibration_error,
                    "accuracy": r.accuracy,
                    "avg_confidence": r.avg_confidence,
                    "avg_latency_ms": r.avg_latency_ms,
                    "p95_latency_ms": r.p95_latency_ms,
                    "total_cost_usd": r.total_cost_usd,
                    "category_brier": r.category_brier,
                    "category_accuracy": r.category_accuracy,
                    "num_predictions": r.num_predictions,
                }
                for r in results
            ],
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
