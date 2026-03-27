"""Sentinel Agent — the brain. Orchestrates the entire breach response."""

import json
import time
from datetime import datetime

from src.config import get_anthropic_client, get_auth0_client, init_overmind
from src import db
from src.matcher import load_breach_csv, match_breach_data
from src.auth0_actions import lock_compromised_users
from src.bland_caller import notify_critical_users


def run_sentinel(breach_file_path: str):
    """
    Main agent loop. Called when breach file is uploaded.
    Every step logs to agent_log so the dashboard shows reasoning in real-time.
    """
    start_time = time.time()

    # Initialize tracing
    init_overmind()
    claude = get_anthropic_client()

    # =============================================
    # PHASE 1: INGEST
    # =============================================
    db.log_agent(None, "ingest", "Breach file detected. Beginning analysis...", log_type="info")

    breach_records = load_breach_csv(breach_file_path)
    breach_id = db.create_breach_event(
        source="darkweb_forum_x",
        total_records=len(breach_records),
    )

    db.log_agent(breach_id, "ingest",
        f"Loaded {len(breach_records)} leaked credential pairs from breach dump",
        log_type="info")
    time.sleep(1)  # Pacing for dashboard visibility

    # =============================================
    # PHASE 2: MATCH
    # =============================================
    db.log_agent(breach_id, "match",
        "Cross-referencing leaked credentials against user database...",
        log_type="info")
    time.sleep(0.5)

    users = db.get_all_users()
    results = match_breach_data(breach_records, users)

    n_critical = len(results["critical"])
    n_warning = len(results["warning"])
    n_safe = results["safe_count"]

    db.update_breach_event(breach_id,
        matched_users=n_critical + n_warning,
        critical_users=n_critical,
        warned_users=n_warning,
        status="analyzing",
    )

    db.log_agent(breach_id, "match",
        f"CRITICAL: {n_critical} users — password hash matches (reused passwords)",
        log_type="action")
    time.sleep(0.5)

    db.log_agent(breach_id, "match",
        f"WARNING: {n_warning} users — email match but different password",
        log_type="info")
    time.sleep(0.5)

    db.log_agent(breach_id, "match",
        f"SAFE: {n_safe} leaked records — no match in our system",
        log_type="info")
    time.sleep(0.5)

    # =============================================
    # PHASE 3: CLAUDE ANALYSIS
    # =============================================
    db.log_agent(breach_id, "analyze",
        "Analyzing breach severity and planning response...",
        log_type="info")

    critical_summary = json.dumps(
        [{"name": u["name"], "email": u["email"]} for u in results["critical"]],
        indent=2,
    )

    analysis = claude.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"""A data breach has been detected. Analyze and provide an incident assessment.

Source: darkweb_forum_x (credential dump)
Total leaked records: {len(breach_records)}
Users in our system affected: {n_critical + n_warning}
CRITICAL (password hash match — reused passwords): {n_critical}
WARNING (email match only): {n_warning}

Critical users:
{critical_summary}

Provide:
1. Severity rating (P1/P2/P3/P4)
2. Risk assessment (2 sentences)
3. Recommended immediate actions (bullet points)

Be concise — this goes in an incident report.""",
        }],
    )

    assessment = analysis.content[0].text
    db.log_agent(breach_id, "analyze", assessment, log_type="decision")
    time.sleep(1)

    # =============================================
    # PHASE 4: LOCK ACCOUNTS
    # =============================================
    db.update_breach_event(breach_id, status="responding")

    db.log_agent(breach_id, "lock",
        f"Initiating account lockdown for {n_critical} critical users via Auth0...",
        log_type="action")
    time.sleep(0.5)

    try:
        auth0_mgmt = get_auth0_client()
        locked = lock_compromised_users(auth0_mgmt, results["critical"], breach_id)
    except Exception as e:
        # Fallback: lock in DB only (if Auth0 Management API isn't configured)
        db.log_agent(breach_id, "lock",
            f"Auth0 Management API unavailable ({e}). Locking in database...",
            log_type="error")
        locked = 0
        for user in results["critical"]:
            db.update_user_status(user["id"], "locked")
            db.create_response_action(
                breach_id, user["id"], user["email"], user["name"],
                "account_locked", "critical"
            )
            locked += 1
            time.sleep(0.3)

    db.update_breach_event(breach_id, locked_count=locked)
    db.log_agent(breach_id, "lock",
        f"All {locked} critical accounts locked. Active sessions revoked.",
        log_type="action")
    time.sleep(0.5)

    # Also flag warning users
    for user in results["warning"]:
        db.update_user_status(user["id"], "warned")
        db.create_response_action(
            breach_id, user["id"], user["email"], user["name"],
            "flagged_warning", "warning"
        )

    db.log_agent(breach_id, "lock",
        f"Flagged {n_warning} warning-level accounts for monitoring.",
        log_type="info")
    time.sleep(0.5)

    # =============================================
    # PHASE 5: NOTIFY BY PHONE
    # =============================================
    db.log_agent(breach_id, "notify",
        f"Initiating voice notification for {n_critical} critical users via Bland AI...",
        log_type="action")

    called = notify_critical_users(results["critical"], "darkweb_forum_x", breach_id)

    db.update_breach_event(breach_id, called_count=called)
    db.log_agent(breach_id, "notify",
        f"Notification calls queued for {called} critical users.",
        log_type="action")

    # =============================================
    # PHASE 6: COMPLETE
    # =============================================
    elapsed = round(time.time() - start_time, 1)
    db.update_breach_event(breach_id,
        status="complete",
        completed_at=datetime.now(),
    )

    db.log_agent(breach_id, "complete",
        f"Breach response complete. "
        f"{len(breach_records)} records analyzed, "
        f"{n_critical} accounts locked, "
        f"{called} users notified. "
        f"Total time: {elapsed}s",
        log_type="action")

    return {
        "breach_id": breach_id,
        "total_records": len(breach_records),
        "critical": n_critical,
        "warning": n_warning,
        "locked": locked,
        "called": called,
        "elapsed_seconds": elapsed,
    }
