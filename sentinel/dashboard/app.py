"""Streamlit dashboard for Sentinel — real-time breach response monitoring."""

import sys
from pathlib import Path

# Ensure sentinel package is importable when run via `streamlit run`
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import asyncio
import time
import json

import streamlit as st

st.set_page_config(
    page_title="Sentinel — Breach Response",
    page_icon="🛡️",
    layout="wide",
)

# ── Styling ──────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .metric-card {
        background: #1a1d24;
        border-radius: 8px;
        padding: 20px;
        border-left: 4px solid #ff4444;
    }
    .critical { border-left-color: #ff4444 !important; }
    .warning { border-left-color: #ffaa00 !important; }
    .safe { border-left-color: #00cc66 !important; }
    .event-log {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        background: #0d1117;
        padding: 12px;
        border-radius: 6px;
        margin: 4px 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────
st.title("🛡️ Sentinel — Autonomous Breach Response")
st.caption("Real-time breach detection, research, and response pipeline")

# ── State ────────────────────────────────────────────────────────
if "running" not in st.session_state:
    st.session_state.running = False
if "events" not in st.session_state:
    st.session_state.events = []
if "result" not in st.session_state:
    st.session_state.result = None


def run_pipeline(csv_content: str):
    """Run the Sentinel pipeline (synchronous wrapper for Streamlit)."""
    from sentinel.agent.orchestrator import run_sentinel, get_events

    async def _run():
        result = await run_sentinel(
            breach_csv_content=csv_content,
            breach_source="DarkForum X",
        )
        return result, get_events()

    loop = asyncio.new_event_loop()
    result, events = loop.run_until_complete(_run())
    loop.close()
    return result, events


# ── Sidebar: Upload & Trigger ────────────────────────────────────
with st.sidebar:
    st.header("⚡ Breach Input")

    uploaded_file = st.file_uploader("Upload breach CSV", type=["csv"])

    use_sample = st.checkbox("Use sample breach data", value=True)

    if st.button("🚨 TRIGGER SENTINEL", type="primary", use_container_width=True):
        st.session_state.running = True

        if uploaded_file:
            csv_content = uploaded_file.read().decode("utf-8")
        elif use_sample:
            sample_path = Path(__file__).parent.parent / "data" / "breach_data.csv"
            if sample_path.exists():
                csv_content = sample_path.read_text()
            else:
                st.error("No sample data found. Run seed_users.py first.")
                st.session_state.running = False
                csv_content = None
        else:
            st.error("Upload a CSV or check 'Use sample data'")
            st.session_state.running = False
            csv_content = None

        if csv_content and st.session_state.running:
            with st.spinner("🔄 Sentinel is running..."):
                result, events = run_pipeline(csv_content)
                st.session_state.result = result
                st.session_state.events = events
                st.session_state.running = False

    st.divider()
    st.header("📊 Sponsor Integrations")
    sponsors = {
        "Ghost DB": "🟢" if True else "🔴",
        "Auth0": "🟢",
        "Bland AI": "🟢",
        "Overmind": "🟡",
        "Truefoundry": "🟢",
        "Aerospike": "🟡",
        "Senso": "🟡",
        "Airbyte": "🟡",
    }
    for name, status in sponsors.items():
        st.text(f"{status} {name}")

# ── Main Dashboard ───────────────────────────────────────────────
if st.session_state.result:
    r = st.session_state.result

    # Top metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Breach Records", r.total_breach_records)
    col2.metric("Matches", r.total_matches)
    col3.metric("🔴 CRITICAL", r.critical_count)
    col4.metric("🔒 Locked", r.accounts_locked)
    col5.metric("📞 Called", r.calls_initiated)

    st.divider()

    # Two columns: Agent Reasoning + Incident Report
    left, right = st.columns([3, 2])

    with left:
        st.subheader("🧠 Agent Reasoning Stream")
        for evt in st.session_state.events:
            icon_map = {
                "setup": "⚙️",
                "ingest": "📥",
                "matching": "🔍",
                "research": "🔬",
                "lockdown": "🔒",
                "notify": "📞",
                "complete": "✅",
                "error": "❌",
            }
            icon = icon_map.get(evt["type"], "•")
            st.markdown(
                f'<div class="event-log">{icon} <b>[{evt["type"].upper()}]</b> {evt["message"]}</div>',
                unsafe_allow_html=True,
            )

    with right:
        st.subheader("📋 Incident Report")
        if r.incident_report:
            report = r.incident_report
            st.markdown(f"**CVE:** `{report.get('cve_id', 'N/A')}`")
            st.markdown(f"**Attack Vector:** {report.get('attack_vector', 'N/A')}")
            st.markdown(f"**Affected Software:** {report.get('affected_software', 'N/A')} {report.get('affected_version', '')}")
            st.markdown(f"**Severity:** `{report.get('severity', 'N/A')}`")

            patches = report.get("recommended_patches", [])
            if patches:
                st.markdown("**Recommended Patches:**")
                for p in patches:
                    st.markdown(f"- {p}")

            st.markdown(f"\n**Summary:** {report.get('summary', '')}")

        st.divider()
        st.subheader("⏱️ Performance")
        st.metric("Total Duration", f"{r.duration_seconds:.1f}s")
        st.metric("Status", r.status.upper())

else:
    # Empty state
    st.markdown("---")
    st.markdown(
        "### Ready to detect.\n"
        "Upload a breach CSV or use sample data, then click **TRIGGER SENTINEL** to start.\n\n"
        "The agent will autonomously:\n"
        "1. Ingest breach credentials\n"
        "2. Match against user database\n"
        "3. Research the attack vector & CVE\n"
        "4. Lock compromised accounts (Auth0)\n"
        "5. Call affected users (Bland AI)\n"
        "6. Trace all decisions (Overmind)\n"
    )
