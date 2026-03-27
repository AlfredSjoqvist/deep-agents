"""Generate and seed 100 fake users into Ghost DB."""

import asyncio
import hashlib
import random

from faker import Faker

from sentinel.integrations import ghost_db

fake = Faker()
Faker.seed(42)
random.seed(42)

COMPANY_DOMAIN = "acme.com"


def _hash_password(password: str) -> str:
    """Simple hash for demo purposes."""
    return hashlib.sha256(password.encode()).hexdigest()


async def seed_users(count: int = 100):
    """Generate and insert fake users."""
    await ghost_db.init_tables()

    # Clear existing seed data
    await ghost_db.execute("DELETE FROM response_log")
    await ghost_db.execute("DELETE FROM breach_events")
    await ghost_db.execute("DELETE FROM research_cache")
    await ghost_db.execute("DELETE FROM users")

    users = []
    for i in range(count):
        first = fake.first_name().lower()
        last = fake.last_name().lower()
        email = f"{first}.{last}@{COMPANY_DOMAIN}"
        phone = f"+1{random.randint(2000000000, 9999999999)}"
        password = fake.password(length=12)

        users.append({
            "name": f"{first.title()} {last.title()}",
            "email": email,
            "phone": phone,
            "password_hash": _hash_password(password),
            "password_plain": password,  # kept in memory only for breach CSV
        })

    # Insert into Ghost DB
    for user in users:
        await ghost_db.execute(
            """INSERT INTO users (name, email, phone, password_hash)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (email) DO NOTHING""",
            user["name"],
            user["email"],
            user["phone"],
            user["password_hash"],
        )

    inserted = await ghost_db.fetchval("SELECT COUNT(*) FROM users")
    print(f"Seeded {inserted} users into Ghost DB")
    return users


async def generate_breach_csv(users: list[dict], total_rows: int = 500) -> str:
    """Generate a breach CSV. ~40 emails match users, ~12 with matching password hashes."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["leaked_email", "leaked_password_hash", "source"])
    writer.writeheader()

    source = "DarkForum_X"

    # Pick 40 users to include in breach
    breach_users = random.sample(users, min(40, len(users)))

    for i, user in enumerate(breach_users):
        if i < 12:
            # CRITICAL: same password hash (reused password)
            writer.writerow({
                "leaked_email": user["email"],
                "leaked_password_hash": user["password_hash"],
                "source": source,
            })
        else:
            # WARNING: email matches but different password hash
            writer.writerow({
                "leaked_email": user["email"],
                "leaked_password_hash": _hash_password(fake.password()),
                "source": source,
            })

    # Fill remaining rows with random emails
    for _ in range(total_rows - len(breach_users)):
        writer.writerow({
            "leaked_email": fake.email(),
            "leaked_password_hash": _hash_password(fake.password()),
            "source": source,
        })

    csv_content = output.getvalue()
    print(f"Generated breach CSV: {total_rows} rows ({len(breach_users)} matching, 12 critical)")
    return csv_content


async def run_seed():
    """Full seed: create users and breach CSV."""
    users = await seed_users(100)
    csv_content = generate_breach_csv(users, 500)

    # Write CSV to file
    from pathlib import Path
    csv_path = Path(__file__).parent / "breach_data.csv"
    csv_path.write_text(csv_content)
    print(f"Breach CSV written to {csv_path}")

    await ghost_db.close()


if __name__ == "__main__":
    asyncio.run(run_seed())
