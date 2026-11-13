# Customer demo release — coordinated AI work board

Verified 2026-11-13 using GitHub connector. Three AI roles are instructions, not independent autonomous agents.

| Workstream | Evidence | Status |
| --- | --- | --- |
| Engineer — approved logo asset | `static/bager-site-link-logo.jpg` **exists in main and PR #4 branch**, blob `c87af9a13edc37797811e68d836ac5c01743d847`; GitHub returned base64 JPEG content. This confirms presence, **not** identity with the user-approved original. | REPOSITORY ASSET PRESENT; ORIGINAL IDENTITY UNVERIFIED |
| QA — CI | PR #4 head `9015bfdf98ec7531ab52b4eb5365a046aeb2a433` has completed successful GitHub Actions run `43174465995` (run #13), including the logo file regression guard and isolated two-truck test discovery. | CI PASS; PHONE/PRODUCTION TESTS MISSING |
| Designer — deployed logo | No verified public HTTP response, screenshots from actual current deployment, or role-by-role mobile acceptance. | BLOCKED ON DEPLOYMENT EVIDENCE |

## Pull request disposition

- [PR #2](https://github.com/KirilTSV/bager-site-link/pull/2) merged on 2026-11-12; branding code landed in main.
- [PR #3](https://github.com/KirilTSV/bager-site-link/pull/3) open draft: operator GPS/shift buttons; no device verification.
- [PR #4](https://github.com/KirilTSV/bager-site-link/pull/4) open draft: CI, agents and test guard; successful CI on exact head, **not** merged.
- [PR #1](https://github.com/KirilTSV/bager-site-link/pull/1) open draft marketplace; out of scope for current release.

## Release gate

1. Confirm deployed Render commit and HTTPS GET `/static/bager-site-link-logo.jpg` responds 200 with JPEG MIME type.
2. Compare the asset visually and/or by hash against the exact user-approved logo.
3. Verify login, invites, dispatcher, operator, driver, supervisor and client views on real phones, with screenshots and timestamps.
4. Independently validate GPS consent, tickets, photos, reports, two-truck lifecycle, persistence and backup/restore using synthetic data.
5. Supervised one-excavator/two-truck pilot and owner sign-off before any production deployment or customer-readiness claim.

**Do not advertise as customer-ready until all gates are met.**
