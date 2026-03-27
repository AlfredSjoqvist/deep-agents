Verify all sponsor tool integrations are working:

1. **Ghost DB**: Run a test SQL query against the configured database
2. **Auth0**: Fetch user list via Management API
3. **Bland AI**: Check API key validity
4. **Overmind**: Verify init() succeeds
5. **Truefoundry**: Make a test completion call
6. **Aerospike**: Connect and read/write a test key
7. **Senso**: Upload a test document and query it
8. **Airbyte**: Check API connectivity

For each integration, report: CONNECTED / FAILED / NOT CONFIGURED
Suggest fixes for any failures.
