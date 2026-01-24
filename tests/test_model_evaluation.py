"""Tests for the model evaluation framework."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.evaluation.llm_providers import (
    LLMProvider,
    LLMResponse,
    estimate_cost,
    get_provider,
    list_available_models,
)
from agents.evaluation.model_evaluator import (
    EvaluationResult,
    ModelEvaluator,
    ModelPrediction,
    PredictionRecord,
)


class TestLLMProviders:
    """Tests for LLM provider abstraction."""

    def test_estimate_cost_known_model(self):
        """Should calculate cost for known models."""
        cost = estimate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
        assert cost is not None
        # gpt-4o: $2.50/1M input, $10.00/1M output
        expected = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
        assert abs(cost - expected) < 0.0001

    def test_estimate_cost_unknown_model(self):
        """Should return None for unknown models."""
        cost = estimate_cost("unknown-model-xyz", input_tokens=1000, output_tokens=500)
        assert cost is None

    def test_list_available_models(self):
        """Should list all registered models."""
        models = list_available_models()
        assert "gpt-4o" in models
        assert "claude-sonnet-4" in models
        # Should be sorted
        assert models == sorted(models)

    def test_get_provider_unknown_model_raises(self):
        """Should raise ValueError for unknown model."""
        with pytest.raises(ValueError, match="Unknown model"):
            get_provider("nonexistent-model")


class TestPredictionRecord:
    """Tests for prediction record data structure."""

    def test_create_record(self):
        """Should create a prediction record."""
        record = PredictionRecord(
            scenario_id="test-001",
            news_headline="Test headline",
            news_summary="Test summary",
            market_question="Will X happen?",
            market_yes_price=0.65,
            market_no_price=0.35,
            actual_outcome="YES",
            category="test",
        )
        assert record.scenario_id == "test-001"
        assert record.actual_outcome == "YES"


class TestModelEvaluator:
    """Tests for the model evaluator."""

    @pytest.fixture
    def sample_scenarios(self) -> list[PredictionRecord]:
        """Create sample scenarios for testing."""
        return [
            PredictionRecord(
                scenario_id="s1",
                news_headline="Good news for X",
                news_summary="Positive development",
                market_question="Will X happen?",
                market_yes_price=0.50,
                market_no_price=0.50,
                actual_outcome="YES",
                category="test",
            ),
            PredictionRecord(
                scenario_id="s2",
                news_headline="Bad news for Y",
                news_summary="Negative development",
                market_question="Will Y happen?",
                market_yes_price=0.70,
                market_no_price=0.30,
                actual_outcome="NO",
                category="test",
            ),
        ]

    @pytest.fixture
    def evaluator(self, sample_scenarios) -> ModelEvaluator:
        """Create evaluator with sample scenarios."""
        return ModelEvaluator(scenarios=sample_scenarios)

    def test_add_scenario(self):
        """Should add scenarios to evaluator."""
        evaluator = ModelEvaluator()
        assert len(evaluator.scenarios) == 0

        evaluator.add_scenario(
            PredictionRecord(
                scenario_id="new",
                news_headline="New",
                news_summary="Summary",
                market_question="Question?",
                market_yes_price=0.5,
                market_no_price=0.5,
                actual_outcome="YES",
            )
        )
        assert len(evaluator.scenarios) == 1

    def test_load_scenarios_from_file(self, tmp_path):
        """Should load scenarios from JSON file."""
        data = {
            "scenarios": [
                {
                    "scenario_id": "file-001",
                    "news_headline": "Headline",
                    "news_summary": "Summary",
                    "market_question": "Question?",
                    "market_yes_price": 0.6,
                    "market_no_price": 0.4,
                    "actual_outcome": "YES",
                    "category": "test",
                }
            ]
        }
        path = tmp_path / "scenarios.json"
        path.write_text(json.dumps(data))

        evaluator = ModelEvaluator()
        count = evaluator.load_scenarios_from_file(path)

        assert count == 1
        assert len(evaluator.scenarios) == 1
        assert evaluator.scenarios[0].scenario_id == "file-001"

    def test_build_prompt(self, evaluator, sample_scenarios):
        """Should build proper prompt for scenario."""
        prompt = evaluator.build_prompt(sample_scenarios[0])

        assert "Good news for X" in prompt
        assert "Will X happen?" in prompt
        assert "0.50" in prompt  # YES price
        assert "JSON" in prompt

    def test_calculate_metrics_perfect_predictions(self, sample_scenarios):
        """Should calculate metrics for perfect predictions."""
        evaluator = ModelEvaluator(scenarios=sample_scenarios)

        # Manually set perfect predictions
        evaluator._results["test-model"] = [
            ModelPrediction(
                scenario_id="s1",
                model="test-model",
                direction="YES",
                estimated_prob=1.0,  # Perfect confidence in YES
                confidence=10,
                reasoning="Correct",
                latency_ms=100,
            ),
            ModelPrediction(
                scenario_id="s2",
                model="test-model",
                direction="NO",
                estimated_prob=1.0,  # Perfect confidence in NO
                confidence=10,
                reasoning="Correct",
                latency_ms=150,
            ),
        ]

        result = evaluator.calculate_metrics("test-model")

        assert result.num_predictions == 2
        assert result.accuracy == 1.0  # 100% directional accuracy
        assert result.brier_score == 0.0  # Perfect Brier score
        assert result.avg_latency_ms == 125.0

    def test_calculate_metrics_wrong_predictions(self, sample_scenarios):
        """Should calculate metrics for wrong predictions."""
        evaluator = ModelEvaluator(scenarios=sample_scenarios)

        # Set completely wrong predictions
        evaluator._results["bad-model"] = [
            ModelPrediction(
                scenario_id="s1",
                model="bad-model",
                direction="NO",  # Wrong - actual is YES
                estimated_prob=1.0,
                confidence=10,
                reasoning="Wrong",
                latency_ms=100,
            ),
            ModelPrediction(
                scenario_id="s2",
                model="bad-model",
                direction="YES",  # Wrong - actual is NO
                estimated_prob=1.0,
                confidence=10,
                reasoning="Wrong",
                latency_ms=100,
            ),
        ]

        result = evaluator.calculate_metrics("bad-model")

        assert result.accuracy == 0.0  # 0% accuracy
        assert result.brier_score == 1.0  # Worst possible Brier score

    def test_calculate_metrics_handles_errors(self, sample_scenarios):
        """Should handle predictions with errors gracefully."""
        evaluator = ModelEvaluator(scenarios=sample_scenarios)

        evaluator._results["error-model"] = [
            ModelPrediction(
                scenario_id="s1",
                model="error-model",
                direction="",
                estimated_prob=0.5,
                confidence=0,
                reasoning="",
                latency_ms=0,
                error="API Error",
            ),
        ]

        result = evaluator.calculate_metrics("error-model")
        assert result.num_predictions == 0  # Error predictions not counted

    def test_calculate_metrics_category_breakdown(self):
        """Should calculate per-category metrics."""
        scenarios = [
            PredictionRecord(
                scenario_id="pol1",
                news_headline="Political news",
                news_summary="Summary",
                market_question="Political question?",
                market_yes_price=0.5,
                market_no_price=0.5,
                actual_outcome="YES",
                category="politics",
            ),
            PredictionRecord(
                scenario_id="cry1",
                news_headline="Crypto news",
                news_summary="Summary",
                market_question="Crypto question?",
                market_yes_price=0.5,
                market_no_price=0.5,
                actual_outcome="NO",
                category="crypto",
            ),
        ]
        evaluator = ModelEvaluator(scenarios=scenarios)

        evaluator._results["test"] = [
            ModelPrediction(
                scenario_id="pol1",
                model="test",
                direction="YES",
                estimated_prob=0.8,
                confidence=8,
                reasoning="",
                latency_ms=100,
            ),
            ModelPrediction(
                scenario_id="cry1",
                model="test",
                direction="NO",
                estimated_prob=0.9,
                confidence=9,
                reasoning="",
                latency_ms=100,
            ),
        ]

        result = evaluator.calculate_metrics("test")

        assert "politics" in result.category_brier
        assert "crypto" in result.category_brier
        assert result.category_accuracy["politics"] == 1.0
        assert result.category_accuracy["crypto"] == 1.0

    def test_generate_report(self, evaluator):
        """Should generate markdown report."""
        evaluator._results["model-a"] = [
            ModelPrediction(
                scenario_id="s1",
                model="model-a",
                direction="YES",
                estimated_prob=0.8,
                confidence=8,
                reasoning="",
                latency_ms=100,
            ),
            ModelPrediction(
                scenario_id="s2",
                model="model-a",
                direction="NO",
                estimated_prob=0.7,
                confidence=7,
                reasoning="",
                latency_ms=150,
            ),
        ]

        results = [evaluator.calculate_metrics("model-a")]
        report = evaluator.generate_report(results)

        assert "# Model Evaluation Report" in report
        assert "model-a" in report
        assert "Brier Score" in report
        assert "Accuracy" in report

    def test_save_results(self, evaluator, tmp_path):
        """Should save results to JSON."""
        evaluator._results["test"] = [
            ModelPrediction(
                scenario_id="s1",
                model="test",
                direction="YES",
                estimated_prob=0.7,
                confidence=7,
                reasoning="",
                latency_ms=100,
            ),
        ]

        results = [evaluator.calculate_metrics("test")]
        path = tmp_path / "results.json"
        evaluator.save_results(path, results)

        assert path.exists()
        data = json.loads(path.read_text())
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["model"] == "test"


class TestBrierScoreCalculation:
    """Focused tests for Brier score accuracy."""

    def test_brier_score_perfect_yes(self):
        """Brier score for perfect YES prediction should be 0."""
        evaluator = ModelEvaluator(
            scenarios=[
                PredictionRecord(
                    scenario_id="s1",
                    news_headline="",
                    news_summary="",
                    market_question="",
                    market_yes_price=0.5,
                    market_no_price=0.5,
                    actual_outcome="YES",
                )
            ]
        )
        evaluator._results["model"] = [
            ModelPrediction(
                scenario_id="s1",
                model="model",
                direction="YES",
                estimated_prob=1.0,  # 100% confident YES
                confidence=10,
                reasoning="",
                latency_ms=100,
            )
        ]

        result = evaluator.calculate_metrics("model")
        assert result.brier_score == 0.0

    def test_brier_score_perfect_no(self):
        """Brier score for perfect NO prediction should be 0."""
        evaluator = ModelEvaluator(
            scenarios=[
                PredictionRecord(
                    scenario_id="s1",
                    news_headline="",
                    news_summary="",
                    market_question="",
                    market_yes_price=0.5,
                    market_no_price=0.5,
                    actual_outcome="NO",
                )
            ]
        )
        evaluator._results["model"] = [
            ModelPrediction(
                scenario_id="s1",
                model="model",
                direction="NO",
                estimated_prob=1.0,  # 100% confident NO
                confidence=10,
                reasoning="",
                latency_ms=100,
            )
        ]

        result = evaluator.calculate_metrics("model")
        assert result.brier_score == 0.0

    def test_brier_score_uncertain(self):
        """Brier score for 50/50 prediction should be 0.25."""
        evaluator = ModelEvaluator(
            scenarios=[
                PredictionRecord(
                    scenario_id="s1",
                    news_headline="",
                    news_summary="",
                    market_question="",
                    market_yes_price=0.5,
                    market_no_price=0.5,
                    actual_outcome="YES",
                )
            ]
        )
        evaluator._results["model"] = [
            ModelPrediction(
                scenario_id="s1",
                model="model",
                direction="YES",
                estimated_prob=0.5,  # 50/50
                confidence=5,
                reasoning="",
                latency_ms=100,
            )
        ]

        result = evaluator.calculate_metrics("model")
        # (0.5 - 1.0)^2 = 0.25
        assert abs(result.brier_score - 0.25) < 0.001


class TestIntegrationWithSampleData:
    """Integration test using sample scenarios file."""

    def test_load_sample_scenarios(self):
        """Should load sample scenarios from data file."""
        sample_path = Path(__file__).parent.parent / "data" / "evaluation" / "sample_scenarios.json"

        if not sample_path.exists():
            pytest.skip("Sample scenarios file not found")

        evaluator = ModelEvaluator()
        count = evaluator.load_scenarios_from_file(sample_path)

        assert count > 0
        assert len(evaluator.scenarios) == count

        # Check categories
        categories = {s.category for s in evaluator.scenarios}
        assert "politics" in categories
        assert "crypto" in categories
