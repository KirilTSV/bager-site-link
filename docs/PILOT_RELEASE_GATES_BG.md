# BAGER SITE LINK — PILOT RELEASE GATES

Status: 2026-11-11. **NOT APPROVED FOR PRODUCTION OR PAID PILOT.** This is an engineering acceptance register, not evidence of a completed field test.

## Gate A — Code and isolated integration
- [x] Operations site/assignment API exists in feature/live-operations-v1.
- [x] Trip destination snapshots and unload GPS classification exist in feature branch.
- [x] SQLite + PostgreSQL CI run configured for marketplace, branding, and trip destination tests.
- [ ] Verify final branch HEAD CI green after any further changes. Record run URL, SHA and date.
- [ ] Expand tests: authorized/unauthorized role matrix, project isolation, GPS near/far/stale/inaccurate, invalid transitions, simultaneous trip creation, assignment change and audit immutability.
- [ ] Validate migrations against a copy of the production schema; current model creation is not a production migration plan.
- [ ] Validate backup/restore and rollback on a nonproduction copy.

## Gate B — Operational correctness
- [ ] UI: supervisor can approve disposal sites and create daily assignments for each truck.
- [ ] UI: driver sees today's assigned site and relevant trips.
- [ ] UI: investor read-only progress and verified-vs-estimated quantities; no subcontractor prices.
- [ ] Change-of-site requires supervisor approval, reason, timestamp and append-only audit; completed trip snapshots remain unchanged.
- [ ] Operational site approval must NOT be represented as legal disposal authorization; independently verify permit/acceptance evidence.
- [ ] Document in-situ vs loose m3 vs tonnes and legal truck load limits.
- [ ] Confirm prime-contractor commercial wording, contract and invoice flow; marketplace intermediary disclaimers must be removed before external release.

## Gate C — Real Android acceptance
- [ ] At least two different Android devices; driver and dispatcher sessions.
- [ ] GPS permission accepted/denied, foreground/background, locked screen, network loss/recovery, time drift, stale and inaccurate positions.
- [ ] Simulated route to site and alternate location; inspect server GPS evidence and trip state.
- [ ] One bagger and two trucks, full day-cycle with manual independent count of trips.
- [ ] Field safety: do not operate a phone while driving; test with parked vehicles or a passenger.

## Gate D — Hosting, security and data
- [ ] Verified production DB backup AND successful restore to isolated DB.
- [ ] Render free Postgres expires 2026-12-09T14:35:01Z; decide paid or alternative persistent hosting before pilot.
- [ ] Check roles, session expiry, invitation token handling, privacy notice, GPS retention, access logs and rate limiting.
- [ ] Verify TLS, secure cookies and secrets configuration.
- [ ] Rollback tested, monitoring and incident contacts assigned.
- [ ] Production deploy only after written go/no-go approval; keep main untouched until gates pass.

## Gate E — First client acceptance
- [ ] Written scope, engineering estimate, subcontractor availability, price and payment terms.
- [ ] Site safety, disposal legal compliance, truck documents and insurances reviewed by competent people.
- [ ] Trial report reconciles GPS, load tickets, weighbridge/receipts where available, quantity basis and actual costs.
- [ ] Client-facing report reviewed and signed off by responsible human.

## Evidence policy
For every checked item record date, test environment, actor, input, expected result, actual result, link to log or signed document, and approver. No checkbox can be marked solely because code was committed or a CI workflow existed.
