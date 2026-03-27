"""Generate fake users and breach data for the demo."""

import csv
import hashlib
import random
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Your team's real phone numbers for the demo (agent will call these)
# Replace with actual numbers — these get the live calls during presentation
DEMO_PHONE_NUMBERS = [
    "+1XXXXXXXXXX",  # TODO: Replace with teammate 1 phone
    "+1XXXXXXXXXX",  # TODO: Replace with teammate 2 phone (or your own)
]


def hash_password(password):
    """Simple hash for demo purposes."""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_users(n=100):
    """Generate n fake users."""
    users = []
    passwords = {}  # Store plaintext to create matching breach records

    for i in range(n):
        name = fake.name()
        email = f"{name.lower().replace(' ', '.').replace('-', '')}@acme.com"
        password = fake.password(length=12)
        pwd_hash = hash_password(password)

        # First few users get demo phone numbers (for live call)
        if i < len(DEMO_PHONE_NUMBERS):
            phone = DEMO_PHONE_NUMBERS[i]
        else:
            phone = fake.phone_number()

        users.append({
            "name": name,
            "email": email,
            "phone": phone,
            "password_hash": pwd_hash,
            "auth0_user_id": f"auth0|demo_{i:03d}",
        })
        passwords[email] = {"password": password, "hash": pwd_hash}

    return users, passwords


def generate_breach_data(users, passwords, total=500, n_critical=12, n_warning=28):
    """
    Generate breach CSV with:
    - n_critical records that match email AND password hash (reused passwords)
    - n_warning records that match email but different hash
    - remaining records are random (no match)
    """
    breach = []

    # Pick critical users (first n_critical — these include demo phone numbers)
    critical_users = users[:n_critical]
    for user in critical_users:
        breach.append({
            "leaked_email": user["email"],
            "leaked_password_hash": user["password_hash"],  # SAME hash = critical
            "source": "darkweb_forum_x",
        })

    # Pick warning users (next n_warning)
    warning_users = users[n_critical : n_critical + n_warning]
    for user in warning_users:
        breach.append({
            "leaked_email": user["email"],
            "leaked_password_hash": hash_password(fake.password()),  # DIFFERENT hash
            "source": "darkweb_forum_x",
        })

    # Fill remaining with random emails (no match)
    n_random = total - n_critical - n_warning
    for _ in range(n_random):
        breach.append({
            "leaked_email": fake.email(),
            "leaked_password_hash": hash_password(fake.password()),
            "source": "darkweb_forum_x",
        })

    random.shuffle(breach)
    return breach


def save_users_csv(users):
    path = os.path.join(DATA_DIR, "users.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "email", "phone", "password_hash", "auth0_user_id"])
        writer.writeheader()
        writer.writerows(users)
    print(f"Saved {len(users)} users to {path}")
    return path


def save_breach_csv(breach):
    path = os.path.join(DATA_DIR, "breach_data.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["leaked_email", "leaked_password_hash", "source"])
        writer.writeheader()
        writer.writerows(breach)
    print(f"Saved {len(breach)} breach records to {path}")
    return path


def seed_ghost_db(users):
    """Insert users into Ghost Postgres DB."""
    from src.db import get_connection, init_tables

    init_tables()
    conn = get_connection()
    cur = conn.cursor()

    # Clear existing users
    cur.execute("DELETE FROM response_actions;")
    cur.execute("DELETE FROM agent_log;")
    cur.execute("DELETE FROM breach_events;")
    cur.execute("DELETE FROM users;")

    for user in users:
        cur.execute(
            """INSERT INTO users (name, email, phone, password_hash, auth0_user_id, status)
               VALUES (%s, %s, %s, %s, %s, 'active')
               ON CONFLICT (email) DO NOTHING;""",
            (user["name"], user["email"], user["phone"],
             user["password_hash"], user["auth0_user_id"]),
        )

    cur.close()
    print(f"Seeded {len(users)} users into Ghost DB")


if __name__ == "__main__":
    print("=== Sentinel Data Generator ===\n")

    users, passwords = generate_users(100)
    breach = generate_breach_data(users, passwords, total=500, n_critical=12, n_warning=28)

    save_users_csv(users)
    save_breach_csv(breach)

    # Try to seed Ghost DB (skip if not connected)
    try:
        seed_ghost_db(users)
        print("\nGhost DB seeded successfully!")
    except Exception as e:
        print(f"\nCould not seed Ghost DB ({e})")
        print("Run this again after setting GHOST_DB_URL in .env")

    print(f"\n--- Summary ---")
    print(f"Users: {len(users)}")
    print(f"Breach records: {len(breach)}")
    print(f"Critical matches: 12 (password hash match)")
    print(f"Warning matches: 28 (email only)")
    print(f"Safe records: 460 (no match)")
    print(f"\nFirst 2 critical users get demo phone calls:")
    for u in users[:2]:
        print(f"  {u['name']} — {u['email']} — {u['phone']}")
