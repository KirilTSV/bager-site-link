# Customer demo release — coordinated AI work board

Status as of 2026-11-12. This board defines three specialized AI workstreams; creating these instructions does not start autonomous agents or grant background execution.

| Workstream | First deliverable | Acceptance | Status |
| --- | --- | --- | --- |
| Engineer | Exact approved logo file in static assets, and reliable loading | Original bytes present; correct response type; CI on exact commit | BLOCKED: binary asset not committed |
| QA | Independent two-truck and role test evidence | CI green, plus recorded real-phone checks for each role | PARTIAL: isolated API test passed; phone checks missing |
| Designer | Header/logo acceptance on all role views | Approved logo visible and uncropped on Android/iPhone | BLOCKED: missing deployed asset and device evidence |

## Release gate

1. Confirm production revision and staging environment.
2. Preserve existing customer data and verify backups and restore.
3. Merge only reviewed, green changes; never auto-deploy unverified feature branches.
4. Verify public HTTPS, login, invites, GPS consent, tickets, photos and daily reports on actual phones.
5. Conduct supervised one-excavator/two-truck pilot, record defects, obtain user sign-off.

**Do not advertise as customer-ready until all gates are met.**
