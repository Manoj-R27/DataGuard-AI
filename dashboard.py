import os

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()
st.set_page_config(page_title="DataGuard AI", page_icon="DG", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: #f6f8fb; }
    [data-testid="stSidebar"] { background: #101b2d; }
    [data-testid="stSidebar"] * { color: #e8eef7; }
    .hero { background: linear-gradient(120deg, #10233f, #1c5d67); color: white; padding: 28px 32px; border-radius: 12px; margin-bottom: 22px; }
    .hero h1 { margin: 0; font-size: 2.2rem; letter-spacing: 0; }
    .hero p { margin: 8px 0 0; color: #c7e3e5; }
    div[data-testid="stMetric"] { background: white; border: 1px solid #e1e7ef; padding: 14px 18px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

API = os.getenv("DATAGUARD_API_URL", "http://localhost:8000")
API_KEY = os.getenv("DATAGUARD_API_KEY", "")
headers = {"X-API-Key": API_KEY} if API_KEY else {}

st.sidebar.markdown("### DataGuard AI")
st.sidebar.caption("Monitoring console")

st.markdown('<div class="hero"><h1>DataGuard AI</h1><p>Reliability control room for tabular data pipelines</p></div>', unsafe_allow_html=True)


def fetch_json(path, timeout=5, authenticated=False):
    response = requests.get(f"{API}{path}", headers=headers if authenticated else {}, timeout=timeout)
    return response, response.json() if response.content else {}


try:
    health_response, health = fetch_json("/health")
    batches_response, batches_data = fetch_json("/batches?limit=100")
    alerts_response, alerts_data = fetch_json("/alerts?limit=100")
    if not health_response.ok:
        st.error("API is not healthy. Check the service before continuing.")
        st.stop()

    batches = batches_data.get("items", [])
    alerts = alerts_data.get("items", [])
    total_batches = batches_data.get("total", len(batches))
    total_alerts = alerts_data.get("total", len(alerts))
    high_alerts = sum(alert.get("severity") in {"High", "Critical"} for alert in alerts)

    kpi_columns = st.columns(4)
    kpi_columns[0].metric("Batches monitored", total_batches)
    kpi_columns[1].metric("Open alerts", total_alerts)
    kpi_columns[2].metric("High-priority alerts", high_alerts)
    kpi_columns[3].metric("Service", "Online" if health.get("status") == "ok" else "Degraded")

    ingest_tab, reports_tab, validation_tab = st.tabs(["Ingest data", "Batch reports", "Detector quality"])
    with ingest_tab:
        st.subheader("Send a new batch")
        st.caption("Upload a CSV with the same columns as the reference baseline.")
        upload_columns = st.columns([2, 1])
        with upload_columns[0]:
            uploaded_file = st.file_uploader("CSV batch", type=["csv"], label_visibility="collapsed")
        with upload_columns[1]:
            batch_id = st.text_input("Batch ID", placeholder="e.g. production-2026-10-02")
        if st.button("Analyze batch", type="primary", disabled=not uploaded_file or not batch_id):
            response = requests.post(f"{API}/ingest", params={"batch_id": batch_id}, headers=headers, files={"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}, timeout=30)
            if response.ok:
                st.success(f"Batch {batch_id} processed successfully.")
                st.rerun()
            else:
                st.error(response.json().get("detail", "Batch ingestion failed."))

    with reports_tab:
        st.subheader("Recent batches")
        if not batches:
            st.info("No batches have been ingested yet.")
        else:
            table = pd.DataFrame(batches)
            st.dataframe(table[["batch_id", "severity", "drift_score", "created_at"]], use_container_width=True, hide_index=True)
            selected = st.selectbox("Inspect batch", table["batch_id"].tolist())
            report_response, report = fetch_json(f"/batches/{selected}/report")
            if report_response.ok:
                drift = report["drift"]
                report_columns = st.columns(3)
                report_columns[0].metric("Drift score", f"{drift.get('overall_score', 0):.3f}")
                report_columns[1].metric("Multivariate anomaly rate", f"{drift.get('multivariate_anomaly_rate', 0):.1%}")
                report_columns[2].metric("Flagged columns", sum(event["flagged"] for event in drift.get("columns", [])))
                detail_tabs = st.tabs(["Column drift", "Root causes", "Impact estimate"])
                with detail_tabs[0]:
                    st.dataframe(pd.DataFrame(drift["columns"]), use_container_width=True, hide_index=True)
                with detail_tabs[1]:
                    st.dataframe(pd.DataFrame(report["root_causes"]), use_container_width=True, hide_index=True)
                with detail_tabs[2]:
                    st.json(report["impact"])

    with validation_tab:
        st.subheader("Detector quality")
        eval_response, eval_data = fetch_json("/evaluation", timeout=20, authenticated=True)
        if eval_response.ok:
            overall = eval_data.get("overall", {})
            quality_columns = st.columns(4)
            quality_columns[0].metric("Precision", f"{overall.get('precision', 0):.1%}")
            quality_columns[1].metric("Recall", f"{overall.get('recall', 0):.1%}")
            quality_columns[2].metric("F1 score", f"{overall.get('f1', 0):.1%}")
            quality_columns[3].metric("False-positive rate", f"{overall.get('false_positive_rate', 0):.1%}")
            breakdown = eval_data.get("breakdown", {})
            if breakdown:
                breakdown_df = pd.DataFrame.from_dict(breakdown, orient="index")
                columns = [column for column in ["corruption", "severity", "precision", "recall", "f1", "false_positive_rate"] if column in breakdown_df]
                st.dataframe(breakdown_df[columns], use_container_width=True)
        elif eval_response.status_code == 401:
            st.info("Enter the configured API key in the sidebar to view detector quality.")
        else:
            st.info("No evaluation result is available yet. Run the protected evaluation endpoint first.")

except requests.RequestException as exc:
    st.error(f"API unavailable at {API}. Start FastAPI before opening the dashboard.")
    st.caption(str(exc))
