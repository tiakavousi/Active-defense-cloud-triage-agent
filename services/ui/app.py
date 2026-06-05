"""Cloud Triage dashboard."""
from __future__ import annotations

import os
import json
from datetime import datetime

import httpx
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

API_HOST = os.environ.get("API_HOST", "http://api:8000")
st.set_page_config(page_title="Cloud Triage", layout="wide")

SEVERITY_COLORS = {
    "critical": "#b3001b",
    "high":     "#e85d04",
    "medium":   "#f0a202",
    "low":      "#5a9367",
    "unknown":  "#888888",
}


@st.cache_data(ttl=2)
def fetch(path: str, params: dict | None = None):
    with httpx.Client(base_url=API_HOST, timeout=15.0) as c:
        r = c.get(path, params=params or {})
        r.raise_for_status()
        return r.json()


def header_stats():
    try:
        stats = fetch("/stats")
    except Exception as e:
        st.error(f"API unreachable: {e}")
        return
    cols = st.columns(5)
    cols[0].metric("Total logs", f"{stats['total_logs']:,}")
    cols[1].metric("Baselines learned", stats["baselines"])
    cols[2].metric("Flagged events", stats["flagged_logs"])
    cols[3].metric("Pending investigation", stats["pending_investigation"])
    cols[4].metric("Incidents", stats["incidents"])


def live_feed_tab():
    st.subheader("Live event feed")
    auto = st.checkbox("Auto-refresh (3s)", value=True, key="live_auto")
    if auto:
        st_autorefresh(interval=3000, key="live_refresh")
    rows = fetch("/logs/recent", params={"limit": 200})
    if not rows:
        st.info("Waiting for events...")
        return
    df = pd.DataFrame(rows)
    df = df[[
        "ts", "user_id", "geo_country", "source_ip", "action",
        "bytes_out", "status", "mfa_used", "anomaly_score",
        "flagged", "is_anomaly_truth", "anomaly_kind",
    ]]
    df["ts"] = pd.to_datetime(df["ts"]).dt.strftime("%H:%M:%S")

    def style_score(v):
        if v is None or (isinstance(v, float) and v != v):
            return ""
        if v >= 0.75:
            return "background-color: #b3001b; color: white;"
        if v >= 0.5:
            return "background-color: #e85d04; color: white;"
        if v >= 0.25:
            return "background-color: #f0a202;"
        return ""

    styled = df.style.applymap(style_score, subset=["anomaly_score"])
    st.dataframe(styled, use_container_width=True, hide_index=True, height=600)


def incidents_tab():
    st.subheader("Agent incident reports")
    auto = st.checkbox("Auto-refresh (5s)", value=True, key="inc_auto")
    if auto:
        st_autorefresh(interval=5000, key="inc_refresh")
    severity = st.selectbox("Filter severity", ["(all)", "critical", "high", "medium", "low"])
    params = {"limit": 200}
    if severity != "(all)":
        params["severity"] = severity
    incidents = fetch("/incidents", params=params)
    if not incidents:
        st.info("No incidents yet — once baselines are learned and the agent investigates, reports will appear here.")
        return

    for inc in incidents:
        sev = inc["severity"]
        color = SEVERITY_COLORS.get(sev, "#888888")
        with st.container(border=True):
            top = st.columns([1, 1, 1, 1, 3])
            top[0].markdown(
                f"<span style='background:{color};color:white;padding:3px 10px;border-radius:6px;font-weight:600'>{sev.upper()}</span>",
                unsafe_allow_html=True,
            )
            top[1].metric("Confidence", f"{inc['confidence']:.2f}")
            top[2].write(f"**User**: `{inc['user_id']}`")
            top[3].write(f"**Status**: {inc['status']}")
            top[4].caption(f"Created: {inc['created_at']}")
            st.markdown(f"**Summary** — {inc.get('summary') or '_(none)_'}")
            st.markdown(f"**Recommended action** — {inc.get('recommended_action') or '_(none)_'}")
            with st.expander("Reasoning trace"):
                trace = inc.get("reasoning_trace") or []
                for step in trace:
                    st.markdown(f"#### Step: `{step.get('step', '?')}`")
                    if "tool_invocations" in step:
                        st.write("**Tool calls:**")
                        for tc in step["tool_invocations"]:
                            st.code(f"{tc['name']}({json.dumps(tc.get('args', {}))})", language="text")
                    if "finding" in step:
                        st.markdown(f"_{step['finding']}_")
                    if "report" in step:
                        st.json(step["report"])
                    if "user_role" in step:
                        st.caption(f"Role loaded: {step.get('user_role')} · baseline_present={step.get('baseline_present')}")


def baselines_tab():
    st.subheader("Per-user baselines")
    if st.button("Refresh"):
        st.cache_data.clear()
    baselines = fetch("/baselines")
    if not baselines:
        st.info("No baselines yet — they appear once each user has ~20 events.")
        return
    for b in baselines:
        with st.expander(f"`{b['user_id']}` · sample={b['sample_size']} · updated {b['updated_at']}"):
            c1, c2 = st.columns(2)
            c1.write(f"**Typical hours:** {b['typical_hours']}")
            c1.write(f"**Typical countries:** {b['typical_countries']}")
            c1.write(f"**Typical IPs:** {b['typical_ips']}")
            c2.write(f"**Typical UAs:** {b['typical_user_agents']}")
            c2.write(f"**Bytes mean/sd:** {b['mean_bytes_out']:.0f} / {b['stddev_bytes_out']:.0f}")
            c2.write(f"**Actions:** {b['action_counts']}")


def main():
    st.title("Cloud Triage")
    st.caption("Synthetic cloud-log anomaly detection with autonomous LangGraph investigator")
    header_stats()
    st.divider()
    feed, inc, bl = st.tabs(["Live feed", "Incidents", "Baselines"])
    with feed:
        live_feed_tab()
    with inc:
        incidents_tab()
    with bl:
        baselines_tab()


if __name__ == "__main__":
    main()
