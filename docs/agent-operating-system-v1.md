# BAGER SITE LINK — controlled three-agent delivery system v1

## Goal
Deliver a verifiable customer demo and then a safe real-world pilot for one excavator and two trucks. Optimize verified outcomes, not agent count or activity.

## Coordinator and three independent workstreams
- **Engineer:** one scoped change per branch; fixes code, assets and regressions. Produces a diff, test and rollback plan.
- **QA:** independent adversarial tests; does not approve own changes; records exact commit, test environment and failures.
- **Designer:** compares every role's mobile header, original approved logo, Bulgarian copy and responsive layouts against screenshots; never fabricates asset approval.
- **Coordinator:** prioritizes blockers, assigns owners, resolves conflicts, checks evidence and requests human approval before merging, production deployment or handling customer data.

These are role specifications, not evidence of autonomous workers. Do not claim parallel execution without actual agent jobs and logs.

## Execution protocol
1. **Intake:** create a GitHub issue with reproducible defect, expected behavior, risk, and acceptance criteria.
2. **Engineer:** implement minimal change in isolated branch; link issue and exact commit.
3. **Automated gate:** dependency checks, syntax, isolated API tests, security checks when available. A green CI run does not certify the UI or field operations.
4. **Independent QA and design:** record actual evidence, device, URL and role; reject missing or broken original logo.
5. **Human gate:** owner approves any merge/deploy, pricing, permissions, production database, or real customer-data use.
6. **Staging smoke:** validate public HTTPS, image response, login, roles, two-truck lifecycle, GPS consent, tickets, photos, reports and errors.
7. **Field pilot:** one excavator and two trucks, supervised; collect time, quantity and defect evidence.
8. **Release:** documented rollback, database backup/restore proof, customer sign-off.

## Current blockers and priority
P0 — Approved logo binary absent/unverified in main; HTML path alone is insufficient. Do not replace with generated branding.
P0 — Public Render revision and customer-visible interface not verified on real phones.
P0 — Production persistence and tested restore not verified.
P1 — Role authorization, invitations, GPS consent, photos, PDF, weak-network behavior need evidence.
P1 — Field pilot and first customer demo acceptance outstanding.

## Performance metrics (weekly)
- Lead time: issue accepted to verified resolution.
- Escaped defects: critical defects found after release.
- Automated test pass rate: passing exact-commit runs / all completed exact-commit runs.
- Demo readiness: accepted checks / required checks (unverified = not passed).
- Human time spent and tool cost per accepted change.

No speculative speedup factor; compare against measured baseline after at least several completed tasks.

## Guardrails
No secrets in logs or commits. Least privilege and no autonomous production deployment. Use synthetic data in CI. Maintain original approved logo exactly. EUR-only pricing. Keep all release claims evidence-linked.
