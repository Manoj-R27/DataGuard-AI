def rank_root_causes(drift_report: dict) -> list[dict]:
    """V1 heuristic: rank detector signals and match known signatures; not causal inference."""
    return sorted([{"column": event["column"], "kind": event["kind"], "score": event["score"], "signature": _signature(event)} for event in drift_report["columns"] if event["flagged"]], key=lambda item: item["score"], reverse=True)


def _signature(event):
    if event["kind"] == "null-spike": return "null-rate spike"
    if event["kind"] == "schema-drift": return "schema change"
    if event["kind"] == "categorical-shift": return "new or missing category"
    return "numeric distribution shift"
