---
name: triage-sprint
description: Triage the current LEDG sprint — tickets missing acceptance criteria or estimates, stale in-progress items, and what is pending promotion in each repo. Read-only report.
---

Scope: $ARGUMENTS (default: the current open sprint of project `LEDG`).

Jira: site `ticapp.atlassian.net`, cloudId `0d1d9259-29f0-46ff-bb50-522a373f8daf`.

1. Fetch the sprint:
   `searchJiraIssuesUsingJql(jql: "project = LEDG AND sprint in openSprints() ORDER BY status, rank")`
2. Flag, in a compact table — key, summary, assignee, and the problem:
   - no acceptance criteria in the description
   - no estimate
   - `In Progress` with no update in over 5 days
   - no assignee while the sprint is running
3. For each repo (`backend/` → `amagovpt/udata-pt`, `frontend/` → `amagovpt/dadosgov-fe`),
   list what sits in one environment and has not been promoted:
   `git -C <dir> fetch origin && git -C <dir> log --oneline origin/<next>..origin/<current>`
   for `develop→tst`, `tst→ppr`, `ppr→main`.
4. List open PRs older than 3 days in both repos.

**Read-only.** Do not transition tickets, comment, open PRs or merge anything — report and let
the user decide. Keep the whole output under roughly 40 lines.
