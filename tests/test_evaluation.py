import pytest

from src.data_loader import load_baseline
from src.evaluation import calculate_metrics, evaluate_detector


def test_calculate_metrics():
    metrics = calculate_metrics(tp=10, fp=2, fn=2, tn=10)
    assert metrics["precision"] == pytest.approx(10 / 12, rel=1e-3)
    assert metrics["recall"] == pytest.approx(10 / 12, rel=1e-3)
    assert metrics["f1"] == pytest.approx(10 / 12, rel=1e-3)
    assert metrics["false_positive_rate"] == pytest.approx(2 / 12, rel=1e-3)


def test_evaluate_detector_across_severities():
    results = evaluate_detector(load_baseline(), trials=2)
    assert results["trials_per_type"] == 2
    assert "breakdown" in results
    assert "by_severity" in results
    assert "by_corruption_and_severity" in results
    assert "overall" in results
    assert "clean_control" in results
    for corruption, severities in results["by_corruption_and_severity"].items():
        assert severities["moderate"]["recall"] >= 0.8, corruption
        assert severities["obvious"]["recall"] >= 0.8, corruption
    assert results["by_corruption_and_severity"]["distribution-shift"]["subtle"]["recall"] == 0.0
    assert results["by_corruption_and_severity"]["null-spike"]["subtle"]["recall"] == 0.0
    assert results["clean_control"]["false_positive_rate"] <= 0.05
