"""Streamlit dashboard for Sentinel — real-time breach response monitoring."""

import sys
from pathlib import Path

# Ensure sentinel package is importable when run via `streamlit run`
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import asyncio
import time
from datetime import datetime, timezone

import streamlit as st

st.set_page_config(
    page_title="Sentinel — Breach Response",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ──────────────────────────────────────────────────────
# Comprehensive dark theme with accent system:
#   Critical = #FF3B3B (red)    Warning = #FFB020 (amber)
#   Safe     = #00E676 (green)  Info    = #448AFF (blue)
#   Surface  = #0F1318 / #161B22 / #1C2128
st.markdown("""
<style>
/* ── Import fonts ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Global resets ────────────────────────────────────────── */
.stApp {
    background: #0B0E13;
    font-family: 'Inter', -apple-system, sans-serif;
}

/* Remove default Streamlit padding for cleaner layout */
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}

/* Hide Streamlit hamburger + footer */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {
    background: transparent !important;
}

/* ── Scrollbar styling ────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0B0E13; }
::-webkit-scrollbar-thumb { background: #2D333B; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #444C56; }

/* ── Header ───────────────────────────────────────────────── */
.sentinel-header {
    background: linear-gradient(135deg, #0D1117 0%, #161B22 50%, #0D1117 100%);
    border: 1px solid #21262D;
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}

.sentinel-header::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #FF3B3B, #FFB020, #00E676, transparent);
}

.sentinel-header::after {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(255,59,59,0.03) 0%, transparent 70%);
    pointer-events: none;
}

.header-content {
    display: flex;
    align-items: center;
    gap: 20px;
}

.shield-icon {
    font-size: 48px;
    filter: drop-shadow(0 0 12px rgba(255,59,59,0.4));
    line-height: 1;
}

.header-text h1 {
    font-family: 'Inter', sans-serif;
    font-weight: 800;
    font-size: 32px;
    color: #F0F6FC;
    margin: 0;
    letter-spacing: -0.5px;
    line-height: 1.1;
}

.header-text .subtitle {
    font-family: 'Inter', sans-serif;
    font-weight: 400;
    font-size: 14px;
    color: #8B949E;
    margin-top: 4px;
    letter-spacing: 0.3px;
}

.header-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255,59,59,0.1);
    border: 1px solid rgba(255,59,59,0.25);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 11px;
    font-weight: 600;
    color: #FF6B6B;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 8px;
}

/* ── Metric cards ─────────────────────────────────────────── */
.metric-card {
    background: linear-gradient(145deg, #161B22, #1C2128);
    border: 1px solid #21262D;
    border-radius: 12px;
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
    min-height: 120px;
}

.metric-card:hover {
    border-color: #30363D;
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.metric-card .metric-icon {
    font-size: 28px;
    margin-bottom: 8px;
    display: block;
}

.metric-card .metric-value {
    font-family: 'Inter', sans-serif;
    font-weight: 800;
    font-size: 36px;
    line-height: 1;
    margin-bottom: 4px;
}

.metric-card .metric-label {
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: #8B949E;
}

/* Card accent variants */
.metric-card.critical {
    border-left: 3px solid #FF3B3B;
}
.metric-card.critical .metric-value { color: #FF3B3B; }
.metric-card.critical::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: radial-gradient(ellipse at top left, rgba(255,59,59,0.06) 0%, transparent 60%);
    pointer-events: none;
}

.metric-card.warning {
    border-left: 3px solid #FFB020;
}
.metric-card.warning .metric-value { color: #FFB020; }
.metric-card.warning::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: radial-gradient(ellipse at top left, rgba(255,176,32,0.06) 0%, transparent 60%);
    pointer-events: none;
}

.metric-card.safe {
    border-left: 3px solid #00E676;
}
.metric-card.safe .metric-value { color: #00E676; }
.metric-card.safe::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: radial-gradient(ellipse at top left, rgba(0,230,118,0.06) 0%, transparent 60%);
    pointer-events: none;
}

.metric-card.info {
    border-left: 3px solid #448AFF;
}
.metric-card.info .metric-value { color: #448AFF; }
.metric-card.info::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: radial-gradient(ellipse at top left, rgba(68,138,255,0.06) 0%, transparent 60%);
    pointer-events: none;
}

.metric-card.neutral .metric-value { color: #F0F6FC; }

/* ── Phase timeline ───────────────────────────────────────── */
.phase-timeline {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    padding: 20px 0;
    margin: 0 auto;
    max-width: 800px;
}

.phase-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    position: relative;
    z-index: 2;
    min-width: 110px;
}

.phase-circle {
    width: 52px;
    height: 52px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    font-weight: 700;
    transition: all 0.4s ease;
    position: relative;
}

.phase-circle.pending {
    background: #161B22;
    border: 2px solid #30363D;
    color: #484F58;
}

.phase-circle.active {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border: 2px solid #448AFF;
    color: #448AFF;
    box-shadow: 0 0 20px rgba(68,138,255,0.3), 0 0 40px rgba(68,138,255,0.1);
    animation: pulse-glow 2s ease-in-out infinite;
}

.phase-circle.done {
    background: linear-gradient(135deg, #0a2e1a, #0d3320);
    border: 2px solid #00E676;
    color: #00E676;
    box-shadow: 0 0 12px rgba(0,230,118,0.2);
}

.phase-circle.error {
    background: linear-gradient(135deg, #2e0a0a, #331010);
    border: 2px solid #FF3B3B;
    color: #FF3B3B;
    box-shadow: 0 0 12px rgba(255,59,59,0.2);
}

@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 20px rgba(68,138,255,0.3), 0 0 40px rgba(68,138,255,0.1); }
    50% { box-shadow: 0 0 30px rgba(68,138,255,0.5), 0 0 60px rgba(68,138,255,0.2); }
}

.phase-label {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #8B949E;
    text-align: center;
}

.phase-label.active { color: #448AFF; }
.phase-label.done { color: #00E676; }

.phase-connector {
    flex: 1;
    height: 2px;
    min-width: 60px;
    max-width: 120px;
    margin: 0 -6px;
    margin-bottom: 26px;
    position: relative;
    z-index: 1;
}

.phase-connector.pending { background: #21262D; }
.phase-connector.done { background: linear-gradient(90deg, #00E676, #00E676); }
.phase-connector.active {
    background: linear-gradient(90deg, #00E676, #448AFF);
    animation: connector-pulse 2s ease-in-out infinite;
}

@keyframes connector-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}

/* ── Event log (terminal style) ───────────────────────────── */
.event-log-container {
    background: #0D1117;
    border: 1px solid #21262D;
    border-radius: 12px;
    overflow: hidden;
}

.event-log-header {
    background: #161B22;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid #21262D;
}

.terminal-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}
.terminal-dot.red { background: #FF5F57; }
.terminal-dot.yellow { background: #FEBC2E; }
.terminal-dot.green { background: #28C840; }

.event-log-header .title {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 500;
    font-size: 12px;
    color: #8B949E;
    margin-left: 8px;
}

.event-log-body {
    padding: 16px;
    max-height: 500px;
    overflow-y: auto;
}

.event-line {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12.5px;
    line-height: 1.6;
    padding: 4px 8px;
    border-radius: 4px;
    margin: 2px 0;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    transition: background 0.2s;
}

.event-line:hover {
    background: rgba(255,255,255,0.03);
}

.event-timestamp {
    color: #484F58;
    white-space: nowrap;
    flex-shrink: 0;
    font-size: 11px;
    margin-top: 1px;
}

.event-tag {
    display: inline-block;
    padding: 1px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    white-space: nowrap;
    flex-shrink: 0;
    min-width: 72px;
    text-align: center;
}

.event-tag.setup    { background: rgba(68,138,255,0.15); color: #448AFF; }
.event-tag.ingest   { background: rgba(187,134,252,0.15); color: #BB86FC; }
.event-tag.matching { background: rgba(255,176,32,0.15); color: #FFB020; }
.event-tag.research { background: rgba(3,218,198,0.15); color: #03DAC6; }
.event-tag.lockdown { background: rgba(255,59,59,0.15); color: #FF3B3B; }
.event-tag.notify   { background: rgba(255,176,32,0.15); color: #FFB020; }
.event-tag.complete { background: rgba(0,230,118,0.15); color: #00E676; }
.event-tag.error    { background: rgba(255,59,59,0.25); color: #FF3B3B; }

.event-message {
    color: #C9D1D9;
    word-break: break-word;
}

/* ── Incident report panel ────────────────────────────────── */
.report-panel {
    background: linear-gradient(145deg, #161B22, #1C2128);
    border: 1px solid #21262D;
    border-radius: 12px;
    padding: 24px;
    position: relative;
    overflow: hidden;
}

.report-panel::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, #FF3B3B, #FFB020);
}

.report-field {
    margin-bottom: 14px;
    padding-bottom: 14px;
    border-bottom: 1px solid rgba(33,38,45,0.8);
}
.report-field:last-child {
    margin-bottom: 0;
    padding-bottom: 0;
    border-bottom: none;
}

.report-label {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #484F58;
    margin-bottom: 4px;
}

.report-value {
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    font-size: 14px;
    color: #E6EDF3;
}

.report-value code {
    font-family: 'JetBrains Mono', monospace;
    background: rgba(255,59,59,0.1);
    border: 1px solid rgba(255,59,59,0.2);
    border-radius: 4px;
    padding: 2px 8px;
    color: #FF6B6B;
    font-size: 13px;
}

.severity-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 12px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.5px;
}
.severity-badge.critical {
    background: rgba(255,59,59,0.15);
    border: 1px solid rgba(255,59,59,0.3);
    color: #FF3B3B;
}
.severity-badge.high {
    background: rgba(255,176,32,0.15);
    border: 1px solid rgba(255,176,32,0.3);
    color: #FFB020;
}

.patch-item {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    color: #C9D1D9;
    padding: 6px 0 6px 16px;
    position: relative;
    line-height: 1.5;
}
.patch-item::before {
    content: '';
    position: absolute;
    left: 0;
    top: 12px;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #00E676;
}

/* ── Performance card ─────────────────────────────────────── */
.perf-card {
    background: linear-gradient(145deg, #161B22, #1C2128);
    border: 1px solid #21262D;
    border-radius: 12px;
    padding: 20px 24px;
    margin-top: 16px;
    display: flex;
    align-items: center;
    gap: 20px;
}

.perf-stat {
    text-align: center;
    flex: 1;
}

.perf-stat .value {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 24px;
    color: #F0F6FC;
}

.perf-stat .label {
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #484F58;
    margin-top: 2px;
}

.perf-divider {
    width: 1px;
    height: 40px;
    background: #21262D;
}

/* ── Status badge (complete/running/error) ────────────────── */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.status-badge.running {
    background: rgba(68,138,255,0.12);
    border: 1px solid rgba(68,138,255,0.3);
    color: #448AFF;
}
.status-badge.complete {
    background: rgba(0,230,118,0.12);
    border: 1px solid rgba(0,230,118,0.3);
    color: #00E676;
}
.status-badge.error {
    background: rgba(255,59,59,0.12);
    border: 1px solid rgba(255,59,59,0.3);
    color: #FF3B3B;
}

/* ── Section headers ──────────────────────────────────────── */
.section-header {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 16px;
    color: #E6EDF3;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid #21262D;
}

.section-header .icon {
    font-size: 18px;
}

/* ── Sidebar styling ──────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #0D1117 !important;
    border-right: 1px solid #21262D !important;
}

section[data-testid="stSidebar"] .stMarkdown h2 {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 14px;
    color: #E6EDF3;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Sidebar trigger button */
section[data-testid="stSidebar"] button[kind="primary"] {
    background: linear-gradient(135deg, #FF3B3B, #CC2E2E) !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 1px !important;
    padding: 12px 20px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(255,59,59,0.25) !important;
}

section[data-testid="stSidebar"] button[kind="primary"]:hover {
    background: linear-gradient(135deg, #FF5252, #E03E3E) !important;
    box-shadow: 0 6px 25px rgba(255,59,59,0.4) !important;
    transform: translateY(-1px) !important;
}

/* ── Integration status items ─────────────────────────────── */
.integration-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: rgba(22,27,34,0.6);
    border: 1px solid #21262D;
    border-radius: 8px;
    margin-bottom: 6px;
    transition: all 0.2s ease;
}

.integration-item:hover {
    border-color: #30363D;
    background: rgba(22,27,34,0.9);
}

.integration-name {
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    font-size: 13px;
    color: #C9D1D9;
}

.integration-role {
    font-family: 'Inter', sans-serif;
    font-weight: 400;
    font-size: 10px;
    color: #484F58;
    margin-top: 1px;
}

.integration-status {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}
.integration-status.active {
    background: #00E676;
    box-shadow: 0 0 6px rgba(0,230,118,0.5);
}
.integration-status.partial {
    background: #FFB020;
    box-shadow: 0 0 6px rgba(255,176,32,0.5);
}
.integration-status.inactive {
    background: #484F58;
}

/* ── Empty state ──────────────────────────────────────────── */
.empty-state {
    text-align: center;
    padding: 60px 40px;
    max-width: 600px;
    margin: 0 auto;
}

.empty-state .shield {
    font-size: 72px;
    margin-bottom: 20px;
    filter: drop-shadow(0 0 20px rgba(255,59,59,0.3));
    animation: shield-float 3s ease-in-out infinite;
}

@keyframes shield-float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
}

.empty-state h2 {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 24px;
    color: #E6EDF3;
    margin-bottom: 12px;
}

.empty-state p {
    font-family: 'Inter', sans-serif;
    font-weight: 400;
    font-size: 14px;
    color: #8B949E;
    line-height: 1.7;
    margin-bottom: 24px;
}

.step-list {
    text-align: left;
    max-width: 420px;
    margin: 0 auto;
}

.step-item {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 10px 0;
    border-bottom: 1px solid rgba(33,38,45,0.5);
}

.step-item:last-child { border-bottom: none; }

.step-number {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: rgba(68,138,255,0.12);
    border: 1px solid rgba(68,138,255,0.3);
    color: #448AFF;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 12px;
    flex-shrink: 0;
}

.step-text {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    color: #C9D1D9;
    line-height: 1.5;
    padding-top: 4px;
}

.step-text strong {
    color: #F0F6FC;
}

/* ── Running overlay indicator ────────────────────────────── */
.running-banner {
    background: linear-gradient(90deg, rgba(68,138,255,0.08), rgba(68,138,255,0.15), rgba(68,138,255,0.08));
    border: 1px solid rgba(68,138,255,0.25);
    border-radius: 12px;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 20px;
    animation: running-pulse 2s ease-in-out infinite;
}

@keyframes running-pulse {
    0%, 100% { border-color: rgba(68,138,255,0.25); }
    50% { border-color: rgba(68,138,255,0.5); }
}

.running-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #448AFF;
    animation: blink 1s ease-in-out infinite;
}

@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

.running-text {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 13px;
    color: #448AFF;
    letter-spacing: 0.3px;
}

/* ── Streamlit element overrides ──────────────────────────── */
/* File uploader */
section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    border-color: #21262D !important;
}

/* Checkbox */
section[data-testid="stSidebar"] .stCheckbox label {
    color: #8B949E !important;
    font-size: 13px !important;
}

/* Dividers */
hr {
    border-color: #21262D !important;
    margin: 16px 0 !important;
}

/* Hide default metric styling */
[data-testid="stMetricValue"] { display: none !important; }
[data-testid="stMetricLabel"] { display: none !important; }
[data-testid="stMetric"] { display: none !important; }

/* Fix column gaps */
[data-testid="stHorizontalBlock"] {
    gap: 12px !important;
}
</style>
""", unsafe_allow_html=True)


# ── Header ───────────────────────────────────────────────────────
st.markdown("""
<div class="sentinel-header">
    <div class="header-content">
        <div class="shield-icon">&#x1F6E1;&#xFE0F;</div>
        <div class="header-text">
            <h1>SENTINEL</h1>
            <div class="subtitle">Autonomous Breach Response Agent</div>
            <div class="header-badge">
                <span>&#x26A1;</span> Deep Agents Hackathon 2026
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── State ────────────────────────────────────────────────────────
if "running" not in st.session_state:
    st.session_state.running = False
if "events" not in st.session_state:
    st.session_state.events = []
if "result" not in st.session_state:
    st.session_state.result = None
if "phase" not in st.session_state:
    st.session_state.phase = "idle"


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
    st.markdown("""
    <div style="text-align:center; padding: 8px 0 16px 0;">
        <span style="font-size:32px; filter: drop-shadow(0 0 8px rgba(255,59,59,0.4));">&#x1F6E1;&#xFE0F;</span>
        <div style="font-family:'Inter',sans-serif; font-weight:800; font-size:18px; color:#F0F6FC; letter-spacing:2px; margin-top:4px;">SENTINEL</div>
        <div style="font-family:'Inter',sans-serif; font-size:10px; color:#484F58; letter-spacing:2px; text-transform:uppercase;">Control Panel</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown('<p style="font-family:\'Inter\',sans-serif; font-weight:700; font-size:11px; color:#8B949E; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:12px;">&#x26A1; Breach Input</p>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload breach CSV", type=["csv"], label_visibility="collapsed")
    if uploaded_file:
        st.markdown(f'<div style="font-family:\'JetBrains Mono\',monospace; font-size:11px; color:#00E676; padding:4px 0;">Loaded: {uploaded_file.name}</div>', unsafe_allow_html=True)

    use_sample = st.checkbox("Use sample breach data", value=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if st.button("TRIGGER SENTINEL", type="primary", use_container_width=True):
        st.session_state.running = True
        st.session_state.phase = "ingest"

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
            with st.spinner("Sentinel is running..."):
                result, events = run_pipeline(csv_content)
                st.session_state.result = result
                st.session_state.events = events
                st.session_state.running = False
                st.session_state.phase = "complete"

    st.markdown("---")

    # ── Sponsor Integrations (sidebar) ────────────────────────────
    st.markdown('<p style="font-family:\'Inter\',sans-serif; font-weight:700; font-size:11px; color:#8B949E; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:12px;">&#x1F50C; Integrations</p>', unsafe_allow_html=True)

    sponsors = [
        ("Ghost DB", "Core database", "active"),
        ("Auth0", "Account lockdown", "active"),
        ("Bland AI", "Voice notifications", "active"),
        ("Overmind", "Decision tracing", "active"),
        ("Truefoundry", "LLM gateway", "active"),
        ("Aerospike", "Fast KV lookup", "partial"),
        ("Senso", "Context retrieval", "partial"),
        ("Airbyte", "Data ingestion", "partial"),
    ]

    for name, role, status in sponsors:
        st.markdown(f"""
        <div class="integration-item">
            <div>
                <div class="integration-name">{name}</div>
                <div class="integration-role">{role}</div>
            </div>
            <div class="integration-status {status}"></div>
        </div>
        """, unsafe_allow_html=True)

    # Legend
    st.markdown("""
    <div style="display:flex; gap:16px; margin-top:12px; padding:0 12px;">
        <div style="display:flex; align-items:center; gap:5px;">
            <div style="width:6px; height:6px; border-radius:50%; background:#00E676;"></div>
            <span style="font-size:10px; color:#484F58;">Active</span>
        </div>
        <div style="display:flex; align-items:center; gap:5px;">
            <div style="width:6px; height:6px; border-radius:50%; background:#FFB020;"></div>
            <span style="font-size:10px; color:#484F58;">Partial</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Bottom branding
    st.markdown("""
    <div style="position:fixed; bottom:16px; left:16px; right:16px; max-width:260px;">
        <div style="border-top:1px solid #21262D; padding-top:12px; text-align:center;">
            <div style="font-family:'JetBrains Mono',monospace; font-size:10px; color:#30363D;">
                v1.0.0 &middot; Deep Agents Hackathon &middot; 2026
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Helper: Determine phase states ───────────────────────────────
def _get_phase_states(result, running):
    """Return a dict mapping phase names to states: pending/active/done/error."""
    if running:
        return {"ingest": "active", "research": "pending", "respond": "pending"}

    if result is None:
        return {"ingest": "pending", "research": "pending", "respond": "pending"}

    if result.status == "error":
        # Figure out how far we got
        if result.total_breach_records == 0:
            return {"ingest": "error", "research": "pending", "respond": "pending"}
        if not result.incident_report:
            return {"ingest": "done", "research": "error", "respond": "pending"}
        return {"ingest": "done", "research": "done", "respond": "error"}

    if result.status in ("complete", "complete_no_matches"):
        return {"ingest": "done", "research": "done", "respond": "done"}

    return {"ingest": "pending", "research": "pending", "respond": "pending"}


def _render_phase_timeline(phases):
    """Render the 3-phase pipeline timeline."""
    phase_config = [
        ("ingest", "Ingest", "&#x1F4E5;"),
        ("research", "Research", "&#x1F52C;"),
        ("respond", "Respond", "&#x1F6E1;&#xFE0F;"),
    ]

    icons_done = "&#x2713;"

    nodes_html = []
    for i, (key, label, icon) in enumerate(phase_config):
        state = phases[key]
        display_icon = icons_done if state == "done" else icon
        circle_class = state
        label_class = state if state in ("active", "done") else ""

        nodes_html.append(f"""
        <div class="phase-node">
            <div class="phase-circle {circle_class}">{display_icon}</div>
            <div class="phase-label {label_class}">{label}</div>
        </div>
        """)

        if i < len(phase_config) - 1:
            next_key = phase_config[i + 1][0]
            next_state = phases[next_key]
            if state == "done" and next_state == "done":
                conn_class = "done"
            elif state == "done" and next_state in ("active",):
                conn_class = "active"
            else:
                conn_class = "pending"
            nodes_html.append(f'<div class="phase-connector {conn_class}"></div>')

    return f'<div class="phase-timeline">{"".join(nodes_html)}</div>'


def _render_metric_card(icon, value, label, variant="neutral"):
    """Render a single styled metric card."""
    return f"""
    <div class="metric-card {variant}">
        <span class="metric-icon">{icon}</span>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """


def _format_timestamp(ts):
    """Format a unix timestamp as HH:MM:SS.mmm."""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%H:%M:%S") + f".{int(dt.microsecond / 1000):03d}"


# ── Main Dashboard ───────────────────────────────────────────────
if st.session_state.result:
    r = st.session_state.result

    # Phase timeline
    phases = _get_phase_states(r, st.session_state.running)
    st.markdown(_render_phase_timeline(phases), unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Top metrics row ──────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(_render_metric_card("&#x1F4CA;", r.total_breach_records, "Breach Records", "info"), unsafe_allow_html=True)
    with col2:
        st.markdown(_render_metric_card("&#x1F50D;", r.total_matches, "Matches Found", "warning"), unsafe_allow_html=True)
    with col3:
        st.markdown(_render_metric_card("&#x1F534;", r.critical_count, "Critical", "critical"), unsafe_allow_html=True)
    with col4:
        st.markdown(_render_metric_card("&#x1F512;", r.accounts_locked, "Accts Locked", "safe"), unsafe_allow_html=True)
    with col5:
        st.markdown(_render_metric_card("&#x1F4DE;", r.calls_initiated, "Users Called", "warning"), unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Two columns: Event Log + Incident Report ─────────────────
    left, right = st.columns([3, 2], gap="medium")

    with left:
        # Section header
        st.markdown('<div class="section-header"><span class="icon">&#x1F9E0;</span> Agent Reasoning Stream</div>', unsafe_allow_html=True)

        # Build event log lines
        event_lines = []
        for evt in st.session_state.events:
            ts = _format_timestamp(evt.get("timestamp", time.time()))
            evt_type = evt["type"]
            msg = evt["message"]

            event_lines.append(f"""
            <div class="event-line">
                <span class="event-timestamp">{ts}</span>
                <span class="event-tag {evt_type}">{evt_type}</span>
                <span class="event-message">{msg}</span>
            </div>
            """)

        events_html = "\n".join(event_lines)

        st.markdown(f"""
        <div class="event-log-container">
            <div class="event-log-header">
                <span class="terminal-dot red"></span>
                <span class="terminal-dot yellow"></span>
                <span class="terminal-dot green"></span>
                <span class="title">sentinel &mdash; agent output</span>
            </div>
            <div class="event-log-body">
                {events_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with right:
        # Incident Report
        st.markdown('<div class="section-header"><span class="icon">&#x1F4CB;</span> Incident Report</div>', unsafe_allow_html=True)

        if r.incident_report:
            report = r.incident_report

            severity = report.get("severity", "HIGH")
            sev_class = "critical" if severity == "CRITICAL" else "high"

            patches_html = ""
            patches = report.get("recommended_patches", [])
            if patches:
                patches_html = "".join(f'<div class="patch-item">{p}</div>' for p in patches)
                patches_html = f"""
                <div class="report-field">
                    <div class="report-label">Recommended Patches</div>
                    {patches_html}
                </div>
                """

            summary = report.get("summary", "")
            summary_html = ""
            if summary:
                summary_html = f"""
                <div class="report-field">
                    <div class="report-label">Executive Summary</div>
                    <div class="report-value" style="font-size:13px; line-height:1.7; color:#8B949E;">{summary}</div>
                </div>
                """

            st.markdown(f"""
            <div class="report-panel">
                <div class="report-field">
                    <div class="report-label">CVE Identifier</div>
                    <div class="report-value"><code>{report.get('cve_id', 'N/A')}</code></div>
                </div>
                <div class="report-field">
                    <div class="report-label">Attack Vector</div>
                    <div class="report-value">{report.get('attack_vector', 'N/A')}</div>
                </div>
                <div class="report-field">
                    <div class="report-label">Affected Software</div>
                    <div class="report-value">{report.get('affected_software', 'N/A')} {report.get('affected_version', '')}</div>
                </div>
                <div class="report-field">
                    <div class="report-label">Severity Assessment</div>
                    <div class="report-value">
                        <span class="severity-badge {sev_class}">&#x26A0;&#xFE0F; {severity}</span>
                    </div>
                </div>
                {patches_html}
                {summary_html}
            </div>
            """, unsafe_allow_html=True)

        # Performance card
        status = r.status.upper()
        status_class = "complete" if "COMPLETE" in status else ("error" if status == "ERROR" else "running")

        st.markdown(f"""
        <div class="perf-card">
            <div class="perf-stat">
                <div class="value">{r.duration_seconds:.1f}s</div>
                <div class="label">Total Duration</div>
            </div>
            <div class="perf-divider"></div>
            <div class="perf-stat">
                <div class="value"><span class="status-badge {status_class}">{status}</span></div>
                <div class="label">Pipeline Status</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

else:
    # ── Empty state ──────────────────────────────────────────────
    # Show idle timeline
    phases = _get_phase_states(None, st.session_state.running)
    st.markdown(_render_phase_timeline(phases), unsafe_allow_html=True)

    st.markdown("""
    <div class="empty-state">
        <div class="shield">&#x1F6E1;&#xFE0F;</div>
        <h2>Ready to Detect</h2>
        <p>Upload a breach CSV or use sample data, then click <strong>TRIGGER SENTINEL</strong> to start the autonomous response pipeline.</p>
        <div class="step-list">
            <div class="step-item">
                <div class="step-number">1</div>
                <div class="step-text"><strong>Ingest</strong> breach credentials and cross-reference against user database</div>
            </div>
            <div class="step-item">
                <div class="step-number">2</div>
                <div class="step-text"><strong>Research</strong> the attack vector, CVE, and recommended patches via Claude</div>
            </div>
            <div class="step-item">
                <div class="step-number">3</div>
                <div class="step-text"><strong>Lock</strong> compromised accounts (Auth0) and <strong>call</strong> affected users (Bland AI)</div>
            </div>
            <div class="step-item">
                <div class="step-number">4</div>
                <div class="step-text"><strong>Trace</strong> every decision for full audit trail (Overmind)</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
