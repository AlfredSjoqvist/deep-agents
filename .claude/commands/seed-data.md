Seed the Ghost DB with test data for the Sentinel demo:

1. Create tables if they don't exist: users, breach_events, response_log, research_cache
2. Generate 100 fake users with realistic names, emails (@acme.com), phone numbers, and bcrypt password hashes
3. Generate breach_data.csv with 500 rows:
   - ~40 emails that match our user DB (some with matching hashes = CRITICAL)
   - ~460 random emails that don't match
4. Insert seed users into Ghost DB
5. Verify data by running count queries

Use the Faker library for realistic data generation.
