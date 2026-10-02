import pytest

from src.validation import _metrics, evaluate_detector


def test_validation_metrics_are_computed_from_confusion_counts():
    result = _metrics(8, 2, 2, 8)
    assert result["precision"] == 0.8
    assert result["recall"] == 0.8
    assert result["f1"] == pytest.approx(0.8)
    assert result["false_positive_rate"] == pytest.approx(0.2)


def test_validation_breakdown_uses_seeded_trials(monkeypatch):
    calls = []

    def fake_simulate(reference, seed):
        calls.append(seed)
        return [
            ("clean", reference, {"injections": []}),
            ("changed", reference, {"injections": [{"kind": "test-change", "columns": ["x"]}]}),
        ]

    def fake_detect(reference, current):
        return {"drifted": current is not reference}

    monkeypatch.setattr("src.validation.simulate_days", fake_simulate)
    monkeypatch.setattr("src.validation.detect_drift", fake_detect)
    result = evaluate_detector(object(), trials=3)
    assert calls == [0, 1, 2]
    assert result["breakdown"]["clean"]["true_negative"] == 3
    assert result["breakdown"]["test-change"]["false_negative"] == 3