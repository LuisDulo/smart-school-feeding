# Contributing & Branching Strategy

## Branching model

- **`main`** is always deployable. Sprints 1-9 were built solo, iterating directly
  on `main` with one commit per completed feature/fix — each sprint boundary is
  marked with an annotated tag (`sprint-1` … `sprint-9`, see below) so the
  history stays traceable back to the project's milestones even without a PR
  per commit from that period.
- From Sprint 10 onward, new work happens on a **feature branch** cut from
  `main` (`feature/<short-description>`), opened as a **pull request** back
  into `main`, and merged once it's reviewed and its test plan is checked off.
  See PR [#43](https://github.com/LuisDulo/smart-school-feeding/pull/43) and
  [#44](https://github.com/LuisDulo/smart-school-feeding/pull/44) for the
  pattern.
- Feature branches are deleted after merge; the merge commit and the closed
  PR are the permanent record.

## Sprint tags

Each historical sprint's boundary commit (the last commit that completed that
sprint's scope, before the next sprint's first commit) is tagged:

| Tag | Sprint |
|---|---|
| `sprint-1` | Foundation: Data Models & Scaffolding |
| `sprint-2` | Authentication & Login |
| `sprint-3` | M-Pesa Payments Integration |
| `sprint-4` | Demand Forecasting & Dashboard |
| `sprint-5` | Anomaly Detection & Reporting |
| `sprint-6` | Kitchen Operations & Parent Services |
| `sprint-7` | Super Admin Multi-School Oversight |
| `sprint-8` | QR Code Meal Serving |
| `sprint-9` | Performance & Scalability |

Sprints 10 and 11 are represented as merged pull requests instead of tags,
since they were the first work done on feature branches.

## Issues, milestones and the project board

- Every sprint has a **milestone** on GitHub, and every feature or notable
  fix within that sprint has an **issue** linked to it, closed with a
  reference to the commit(s) that implemented it.
- Forward-looking work (not yet built) is tracked as **open issues** under
  the `Backlog — Security Hardening` milestone, so the board reflects real
  planned work, not just a closed history.
- All issues are tracked on the repository's [project board](../../projects),
  grouped by sprint/milestone.

## Commit messages

Commit messages explain *why*, not just *what* — see the existing history for
the expected level of detail. A commit message should let a reader understand
the change and its motivation without re-reading the diff.
