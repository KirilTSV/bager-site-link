# BAGER SITE LINK — RELEASE FREEZE / v1.0 acceptance

**State:** FROZEN — stabilization only. **Not approved for production.**

## Scope control
No new features, UI redesign, or unverified dependencies. Allowed changes: defect fixes, security, data integrity, tests, deployment/rollback, observability, and documentation. Production `main` and production Render service/database are untouched until acceptance gates pass.

## Release gates (all required)
1. One exact staging commit, all required client/server files present, no unreviewed divergence from the validated local archive.
2. GitHub Actions: complete JS and isolated Python tests pass for that exact SHA; artifact or run URL recorded.
3. Database: migrations/schema tested against a separate PostgreSQL instance; uniqueness, transaction rollback, restart, and backup/restore validated.
4. Browser: login, invitation, role isolation, shift lifecycle, trip lifecycle, quantities, dispatcher map; no JS console errors.
5. GPS: durable write before network upload, offline/reconnect, duplicate ID handling, rejected data retention, shift restoration, stop, two devices, clock skew.
6. Security: authorization on every endpoint, cross-project access denied, secrets only in environment, cookies secure, origin/CSRF review, rate limits, privacy/retention policy.
7. Deployment: isolated staging Render service and database; health check, smoke tests, logs, rollback tested; no changes to production during validation.
8. Field acceptance: real Android device, GPS permission, active movement, background/lock limitations documented, offline recovery and server-side persisted points verified.
9. Operational readiness: owner access, backups, recovery runbook, monitoring, incident response, expiration of free PostgreSQL reviewed.

## Evidence rules
- `code written` != `test passed` != `field validated`.
- Each gate must have reproducible command, exact commit SHA, date, output or log, and reviewer decision.
- A missing result is **NOT PASSED**, never inferred from a local archive or unrelated commit.
- Production promotion is prohibited until all gates are evidenced and approved.

## Current verified evidence
- Local v0.3.4 archive: 34 JS tests passed and isolated Python tests passed (not staging SHA).
- GitHub staging contains GPS client and API code, test files and CI workflow, but full CI result and PostgreSQL/Android verification are not established.
- Release status: **BLOCKED**.

## Immediate execution order
Synchronize missing regression assets; run CI on exact SHA; fix defects; provision isolated staging only after CI green; PostgreSQL + browser + field checks; then explicit release decision.
