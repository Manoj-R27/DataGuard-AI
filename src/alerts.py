def build_alert(drift: dict, causes: list[dict], impact: dict) -> dict:
    score = drift["overall_score"]
    severity = "High" if score >= .35 or impact["mean_probability_shift"] >= .1 else "Medium" if drift["drifted"] else "Low"
    return {"severity": severity, "title": "Data reliability issue detected" if drift["drifted"] else "Batch healthy", "message": causes[0]["signature"] if causes else "No material drift detected", "overall_score": score, "impact": impact}
