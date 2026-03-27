import sys, os, time, threading, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from src import db
from src.agent import run_sentinel

st.set_page_config(page_title="Sentinel", page_icon="🛡", layout="wide", initial_sidebar_state="collapsed")


def run_agent_bg(path):
    try:
        run_sentinel(path)
    except Exception as e:
        import traceback; traceback.print_exc()
    finally:
        try: os.unlink(path)
        except: pass


def main():
    try: db.init_tables()
    except: pass

    if "agent_running" not in st.session_state:
        st.session_state.agent_running = False
    if "csv_path" not in st.session_state:
        st.session_state.csv_path = None

    breach = db.get_latest_breach()
    is_active = breach and breach["status"] not in ("idle", "complete")
    is_complete = breach and breach["status"] == "complete"

    # ── HEADER ──
    st.title("🛡 SENTINEL")

    if is_active:
        st.error("RESPONDING — Breach response in progress")
    elif is_complete:
        started = breach.get("started_at")
        completed = breach.get("completed_at")
        if started and completed:
            elapsed = (completed - started).total_seconds()
            st.success(f"COMPLETE — Responded in {elapsed:.1f} seconds")
        else:
            st.success("COMPLETE")

    # ── UPLOAD (idle state) ──
    if not is_active and not is_complete:
        uploaded = st.file_uploader("Upload breach data CSV", type=["csv"])

        if uploaded:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb")
            tmp.write(uploaded.getvalue())
            tmp.close()
            st.session_state.csv_path = tmp.name

        if st.session_state.csv_path and not st.session_state.agent_running:
            if st.button("🚨 BEGIN BREACH RESPONSE", type="primary", use_container_width=True):
                try: db.reset_for_demo()
                except: pass
                st.session_state.agent_running = True
                threading.Thread(target=run_agent_bg, args=(st.session_state.csv_path,), daemon=True).start()
                time.sleep(1)
                st.rerun()
        return

    # ── STATS ──
    total = breach.get("total_records", 0)
    critical = breach.get("critical_users", 0)
    warning = breach.get("warned_users", 0)
    locked = breach.get("locked_count", 0)
    called = breach.get("called_count", 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Leaked Records", total)
    c2.metric("🔴 Critical", critical)
    c3.metric("🟡 Warning", warning)
    c4.metric("🔒 Locked", locked)
    c5.metric("📞 Called", called)

    st.divider()

    # ── TWO COLUMNS ──
    left, right = st.columns([2, 1])

    with left:
        st.subheader("Agent Reasoning")
        logs = db.get_agent_logs(breach["id"])
        with st.container(height=420):
            if not logs:
                st.caption("Waiting for agent...")
            for log in logs:
                ts = log["timestamp"].strftime("%H:%M:%S") if log.get("timestamp") else ""
                lt = log.get("log_type", "info")
                msg = log["message"]
                if lt == "decision":
                    st.warning(f"`{ts}` 🤖 {msg}")
                elif lt == "action":
                    st.success(f"`{ts}` ⚡ {msg}")
                elif lt == "error":
                    st.error(f"`{ts}` ❌ {msg}")
                else:
                    st.info(f"`{ts}` {msg}")

    with right:
        st.subheader("Response Log")
        actions = db.get_response_actions(breach["id"])
        with st.container(height=420):
            if not actions:
                st.caption("No actions yet")
            else:
                users = {}
                for a in actions:
                    k = a["user_email"]
                    if k not in users:
                        users[k] = {"name": a["user_name"], "actions": []}
                    users[k]["actions"].append(a)

                for email, data in users.items():
                    is_locked = any(a["action_type"] == "account_locked" for a in data["actions"])
                    is_called = any(a["action_type"] == "call_made" for a in data["actions"])
                    is_warned = any(a["action_type"] == "flagged_warning" for a in data["actions"])

                    tags = []
                    if is_locked: tags.append("🔒 Locked")
                    if is_called: tags.append("📞 Called")
                    if is_warned: tags.append("⚠️ Warned")

                    st.markdown(f"**{data['name']}** {'  '.join(tags)}  \n`{email}`")
                    st.divider()

    # ── FOOTER ──
    st.caption("Anthropic · Ghost · Auth0 · Bland AI · Airbyte · Aerospike · Overmind · Truefoundry")

    # ── AUTO REFRESH ──
    if is_active:
        time.sleep(2)
        st.rerun()
    elif is_complete and st.session_state.get("agent_running"):
        st.session_state.agent_running = False
        st.session_state.csv_path = None
        st.rerun()


if __name__ == "__main__":
    main()
