# BAGER SITE LINK — ChatGPT integration, staged design (13 Nov 2026)

## Current implementation
`app/chatgpt_connector_readonly.py` exposes **internal Python service functions only**:
- `project_summary(db, verified_actor)`
- `recent_trips(db, verified_actor, limit)`
- `monitoring_alerts(db, verified_actor, limit)`

They read the existing database, restrict data to the verified actor's organization/project, and return source-labelled structured facts. They do **not** expose a public endpoint, create an MCP server, call an LLM, start background jobs, or mutate business records. Existing `main` and Render deployment are unchanged.

## Security contract before exposing tools to ChatGPT
1. Deploy a separate HTTPS MCP service only after staging tests and an explicit deployment approval.
2. Implement an OAuth 2.1 authorization flow supported by the ChatGPT connector/client; validate issuer, audience, signature, expiration, subject and scopes on every request. Never use a shared static API key as an end-user identity.
3. Map the authenticated OAuth subject to a **server-side** active BAGER participant and verify role, organization, and project membership for every tool call. Do not trust project IDs or role claims supplied in natural-language tool arguments.
4. Enforce least privilege: `client_viewer` can only see safe project aggregates and nonpersonal trip status; only owner/dispatcher/site_manager can see monitoring alerts.
5. Keep all initial tools read-only; do not grant write access to trip, GPS, cost, or participant tables. Future write tools require per-action authorization, explicit confirmation and durable audit logging.
6. Do not return GPS coordinates, phone numbers, session tokens, passwords or personal data in the initial connector.
7. Log connector tool invocations with timestamp, authenticated actor, tool, project, result status, request ID and minimal metadata; avoid storing secrets or raw sensitive payloads.
8. Rate-limit, cap response size, paginate results, and review retention/privacy requirements before launch.
9. Run tests against SQLite and staging PostgreSQL, including concurrent requests and cross-tenant authorization; validate OAuth and MCP interoperability with a real client.
10. Check the current ChatGPT plan/workspace requirements for custom MCP connections before claiming the integration is available.

## Accuracy boundaries
- Volumes derive from load tickets; do not present estimates as verified measurements.
- Monitoring history includes only previously recorded alerts; the connector does not run scans.
- No cost analysis tool exists yet because the currently inspected Trip model does not contain reliable cost fields.
- Do not claim the connector is connected to the user's ChatGPT account until an OAuth handshake and live tool call succeed.

## Deployment gate
No public route, credentials, production migrations or production branch changes without an explicit staged review and successful verification.
