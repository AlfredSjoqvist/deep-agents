Run a full end-to-end demo test of the Sentinel agent:

1. Check that all required environment variables are set in .env
2. Verify Ghost DB connection and tables exist
3. Run the agent orchestrator with the breach_data.csv
4. Verify: breach data ingested, users matched, accounts locked in Auth0
5. Verify: Bland AI call was triggered (check call status)
6. Verify: Overmind traces are being sent
7. Check Streamlit dashboard is running and showing data

Report pass/fail for each step. If any step fails, suggest the fix.
