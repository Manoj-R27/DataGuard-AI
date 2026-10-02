from src.data_loader import load_baseline
from src.drift import detect_drift
from src.simulate import simulate_days


def test_clean_baseline_not_flagged():
    frame = load_baseline(); report = detect_drift(frame, frame.copy())
    assert not report["drifted"]


def test_known_injections_are_detected():
    baseline = load_baseline()
    for name, frame, truth in simulate_days(baseline)[1:]:
        report = detect_drift(baseline, frame)
        assert report["drifted"], name
        assert any(event["column"] in truth["injections"][0]["columns"] for event in report["columns"] if event["flagged"])


def test_multivariate_score_is_higher_for_multiple_changes():
    baseline = load_baseline()
    days = simulate_days(baseline)
    single_score = detect_drift(baseline, days[1][1])["multivariate_anomaly_rate"]
    multiple_score = detect_drift(baseline, days[-1][1])["multivariate_anomaly_rate"]
    assert days[-1][2]["injections"][0]["columns"] == ["hours_per_week", "occupation", "workclass"]
    assert multiple_score > single_score
