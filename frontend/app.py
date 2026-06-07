"""Streamlit MVP dashboard for AI FinOps Platform."""

from __future__ import annotations

import json

import requests
import streamlit as st

API_BASE = st.sidebar.text_input("API URL", value="http://localhost:8000")

st.set_page_config(page_title="AI FinOps Dashboard", page_icon="💰", layout="wide")
st.title("AI FinOps Platform")
st.caption("Multi-agent household finance dashboard · LangGraph + Model Router")

tab_analyze, tab_upload, tab_costs = st.tabs(["Analyze Text", "Upload Data", "Cost & ROI"])

with tab_analyze:
    sample = (
        "May 2026 Statement\n"
        "05/01 Whole Foods -127.43\n"
        "05/03 Netflix -15.99\n"
        "05/05 Duplicate Amazon charge -49.99\n"
    )
    text = st.text_area("Financial text / transactions", value=sample, height=200)
    if st.button("Run Pipeline", type="primary"):
        with st.spinner("Running multi-agent pipeline..."):
            resp = requests.post(f"{API_BASE}/analyze", json={"text": text, "source": "dashboard"}, timeout=120)
        if resp.ok:
            data = resp.json()
            st.session_state["last_cost_summary"] = data.get("cost_summary", {})
            st.success(f"Status: {data['status']}")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Recommendation")
                st.json(data.get("recommendation", {}))
            with col2:
                st.subheader("Cost Summary")
                summary = data.get("cost_summary", {})
                st.metric("Total LLM Cost", f"${summary.get('total_cost_usd', 0):.4f}")
                st.metric("Est. Savings", f"${summary.get('total_estimated_savings_usd', 0):.2f}")
                st.metric("ROI", summary.get("aggregate_roi", "N/A"))
            with st.expander("Full response"):
                st.json(data)
        else:
            st.error(resp.text)

with tab_upload:
    st.subheader("Upload PDF or CSV")
    uploaded = st.file_uploader("Choose file", type=["pdf", "csv"])
    if uploaded and st.button("Process Upload"):
        endpoint = "pdf" if uploaded.name.endswith(".pdf") else "csv"
        files = {"file": (uploaded.name, uploaded.getvalue())}
        with st.spinner("Processing..."):
            resp = requests.post(f"{API_BASE}/ingest/{endpoint}", files=files, timeout=120)
        st.json(resp.json() if resp.ok else {"error": resp.text})

with tab_costs:
    st.subheader("Model Routing Rules")
    rules = requests.get(f"{API_BASE}/router/rules", timeout=10)
    if rules.ok:
        st.table([{"Task": k, "Model": v} for k, v in rules.json().items()])

    st.subheader("Live Cost Tracker")
    costs = requests.get(f"{API_BASE}/router/costs", timeout=10)
    summary = costs.json() if costs.ok else {}

    if summary.get("total_calls", 0) == 0:
        st.info("No pipeline runs yet. Go to **Analyze Text** and click **Run Pipeline** first.")
        if "last_cost_summary" in st.session_state:
            st.caption("Showing cost data from your last run in this session:")
            summary = st.session_state["last_cost_summary"]
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Calls", summary.get("total_calls", 0))
        col2.metric("Total LLM Cost", f"${summary.get('total_cost_usd', 0):.4f}")
        col3.metric("Aggregate ROI", summary.get("aggregate_roi", "N/A"))

    st.json(summary)
