# Contributing & Branching Strategy

## Branching model

Every sprint's work lands on `main` through a feature branch and a pull
request — no commits go directly to `main`.

**Branch naming:**

```
feat/[issue-number]-[short-description]
fix/[issue-number]-[short-description]
style/[issue-number]-[short-description]
docs/[issue-number]-[short-description]
chore/[issue-number]-[short-description]
```

The `[issue-number]` is the first (lowest-numbered) issue the branch closes,
so a branch that spans a whole sprint's worth of issues is still traceable
back to a specific issue and milestone.

## Sprint branches and pull requests

| Sprint | Branch | PR |
|---|---|---|
| 1 — Foundation: Data Models & Scaffolding | `feat/1-django-data-models` | [#48](../../pull/48) |
| 2 — Authentication & Login | `feat/4-jwt-authentication` | [#49](../../pull/49) |
| 3 — M-Pesa Payments Integration | `feat/7-mpesa-payments` | [#50](../../pull/50) |
| 4 — Demand Forecasting & Dashboard | `feat/10-demand-forecasting-dashboard` | [#51](../../pull/51) |
| 5 — Anomaly Detection & Reporting | `feat/13-anomaly-detection-reporting` | [#52](../../pull/52) |
| 6 — Kitchen Operations & Parent Services | `feat/17-kitchen-parent-services` | [#53](../../pull/53) |
| 7 — Super Admin Multi-School Oversight | `feat/24-super-admin-oversight` | [#54](../../pull/54) |
| 8 — QR Code Meal Serving | `feat/27-qr-code-serving` | [#55](../../pull/55) |
| 9 — Performance & Scalability | `chore/29-performance-scalability` | [#56](../../pull/56) |
| 10 — ML Model Enhancement | `feat/31-ml-model-enhancement` | [#57](../../pull/57) |
| 11 — Parent Mobile Experience | `feat/35-parent-mobile-experience` | [#58](../../pull/58) |

Each PR's description lists the issue(s) it closes. Feature branches are
deleted after merge; the merge commit and the closed PR are the permanent
record.

## Issues, milestones and the project board

- Every sprint has a **milestone** on GitHub, and every feature or notable
  fix within that sprint has an **issue** linked to it, closed with a
  reference to the pull request that implemented it.
- Forward-looking work (not yet built) is tracked as **open issues** under
  the `Backlog — Security Hardening` milestone, so the board reflects real
  planned work, not just a closed history.
- All issues are tracked on the repository's [project board](../../projects),
  groupable by the built-in Milestone field to read as sprint swimlanes.

## Commit messages

Commit messages explain *why*, not just *what* — see the existing history for
the expected level of detail. A commit message should let a reader understand
the change and its motivation without re-reading the diff.
