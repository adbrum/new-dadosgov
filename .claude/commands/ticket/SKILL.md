---
name: ticket
description: Work a Jira LEDG ticket end to end — read it, find precedents, branch from develop, implement point by point, verify, open the PR and close the loop in Jira
---

Ticket: $ARGUMENTS

Invoke the `jira-ticket-workflow` skill and follow it from Phase 1 to Phase 9.

Accept any of these forms in `$ARGUMENTS` and normalize to the `LEDG-<n>` key:

- `LEDG-2296` — use as is
- `2296` — a bare number is read as `LEDG-2296`
- `https://ticapp.atlassian.net/browse/LEDG-2296` — take the key from the URL

If `$ARGUMENTS` is empty, ask which ticket.
