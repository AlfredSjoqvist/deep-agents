"""Sentinel Dashboard — Flask backend serving the HTML dashboard + API endpoints."""

import sys, os, json, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from src import db
from src.agent import run_sentinel

app = Flask(__name__)
CORS(app)

try: db.init_tables()
except: pass


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/api/state")
def get_state():
    """Return full dashboard state — polled by frontend every 1-2s."""
    breach = db.get_latest_breach()
    if not breach:
        return jsonify({"status": "idle", "breach": None, "logs": [], "actions": []})

    logs = db.get_agent_logs(breach["id"])
    actions = db.get_response_actions(breach["id"])

    return jsonify({
        "status": breach["status"],
        "breach": {
            "id": breach["id"],
            "total_records": breach.get("total_records", 0),
            "critical_users": breach.get("critical_users", 0),
            "warned_users": breach.get("warned_users", 0),
            "locked_count": breach.get("locked_count", 0),
            "called_count": breach.get("called_count", 0),
            "started_at": breach["started_at"].isoformat() if breach.get("started_at") else None,
            "completed_at": breach["completed_at"].isoformat() if breach.get("completed_at") else None,
        },
        "logs": [
            {
                "timestamp": l["timestamp"].isoformat() if l.get("timestamp") else "",
                "phase": l.get("phase", ""),
                "message": l.get("message", ""),
                "log_type": l.get("log_type", "info"),
            }
            for l in logs
        ],
        "actions": [
            {
                "user_email": a.get("user_email", ""),
                "user_name": a.get("user_name", ""),
                "action_type": a.get("action_type", ""),
                "severity": a.get("severity", ""),
                "status": a.get("status", ""),
            }
            for a in actions
        ],
    })


@app.route("/api/trigger", methods=["POST"])
def trigger():
    """Trigger breach response with uploaded CSV or default breach file."""
    # Reset DB
    try: db.reset_for_demo()
    except: pass

    # Use uploaded file or fallback to default breach CSV
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "breach_data.csv")

    if "file" in request.files:
        f = request.files["file"]
        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb")
        tmp.write(f.read())
        tmp.close()
        csv_path = tmp.name

    # Run agent in background
    threading.Thread(target=run_sentinel, args=(csv_path,), daemon=True).start()

    return jsonify({"status": "started"})


@app.route("/api/reset", methods=["POST"])
def reset():
    """Reset all state for a fresh demo."""
    try:
        db.reset_for_demo()
        return jsonify({"status": "reset"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8888, debug=False)
