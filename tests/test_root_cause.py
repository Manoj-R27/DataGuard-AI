from src.data_loader import load_baseline
from src.drift import detect_drift
from src.root_cause import rank_root_causes
from src.simulate import simulate_days


def test_root_cause_identifies_injected_column():
    baseline = load_baseline()
    for _, frame, truth in simulate_days(baseline)[1:]:
        causes = rank_root_causes(detect_drift(baseline, frame))
        assert causes and causes[0]["column"] in truth["injections"][0]["columns"]
