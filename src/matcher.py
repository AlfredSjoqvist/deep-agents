"""Match breach records against our user database."""

import csv


def load_breach_csv(filepath):
    """Load breach data CSV into list of dicts."""
    records = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                "email": row["leaked_email"].strip().lower(),
                "password_hash": row["leaked_password_hash"].strip(),
                "source": row.get("source", "unknown"),
            })
    return records


def match_breach_data(breach_records, db_users):
    """
    Match leaked credentials against our user database.

    Returns:
        critical: list of user dicts where email AND password hash match
        warning: list of user dicts where email matches but hash differs
        safe_count: number of breach records with no match
    """
    # Build lookup by email for fast matching
    user_by_email = {u["email"].lower(): u for u in db_users}

    critical = []
    warning = []
    safe_count = 0

    for record in breach_records:
        email = record["email"]
        if email in user_by_email:
            user = user_by_email[email]
            if record["password_hash"] == user["password_hash"]:
                critical.append(user)
            else:
                warning.append(user)
        else:
            safe_count += 1

    # Deduplicate (same user could appear multiple times in breach)
    critical = list({u["id"]: u for u in critical}.values())
    warning = list({u["id"]: u for u in warning}.values())

    return {
        "critical": critical,
        "warning": warning,
        "safe_count": safe_count,
    }
