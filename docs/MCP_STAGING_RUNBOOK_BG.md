# BAGER SITE LINK — MCP staging runbook

## Status
Isolated MCP server source is present in `app/mcp_server.py` on `feature/live-operations-v1`. It is NOT deployed, not connected to ChatGPT, and not verified end-to-end. The production FastAPI application is unchanged.

## Isolation
Use a separate virtual environment, separate process and separate HTTPS host. Install `requirements-mcp.txt` there only. Do not add the MCP server to `app/main.py` or the production start command.

## Required configuration (never commit actual values)
- `DATABASE_URL`: existing read-only database credentials, ideally a dedicated database role restricted to SELECT on required tables.
- `BAGER_MCP_OAUTH_ISSUER`: trusted HTTPS OAuth issuer.
- `BAGER_MCP_OAUTH_AUDIENCE`: audience for this resource server.
- `BAGER_MCP_OAUTH_JWKS_URL`: trusted HTTPS JWKS endpoint.
- `BAGER_MCP_SUBJECT_MAP_JSON`: server-side mapping of validated OAuth subjects to existing BAGER participant IDs, e.g. `{"subject-from-identity-provider":"participant-uuid"}`. Treat as secret configuration; keep out of Git.

## Test gate
1. In isolated staging: `pip install -r requirements-mcp.txt`.
2. `python -m unittest tests.test_chatgpt_connector_readonly tests.test_mcp_auth_boundary -v`.
3. `uvicorn app.mcp_server:app --factory --host 127.0.0.1 --port 8765` (behind an HTTPS reverse proxy).
4. Verify no credentials => startup fails; missing bearer => HTTP 401; invalid signature, issuer, audience, expiration or scope => HTTP 401; unknown OAuth subject => HTTP 401.
5. Verify tenant isolation, client-viewer restrictions, and no mutation of business tables.
6. Confirm OAuth discovery/authorization server metadata and MCP protocol interoperability with a real ChatGPT client. **These are not implemented by this initial code** and are required before claiming a functional ChatGPT connection.
7. Check security controls: HTTPS, trusted proxy headers, origin policy, rate limits, secret rotation, audit-log retention and production-grade monitoring.

## Important implementation limitations
- JWT validator currently supports RS256 only and expects `scope` to contain `bager:read`. It requires a compatible identity provider.
- The code has not been runtime-tested against the official MCP Python SDK in this environment.
- The connector uses the existing SQLAlchemy application models and read-only functions; no write tools are exposed.
- Metadata-only tool audit is emitted to process logs, not to an immutable centralized audit store.
- No background scan, model inference, automated dispatch, cost prediction or financial writes.
- Never expose this service publicly until the staging and OAuth compatibility gates pass.
