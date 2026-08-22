---
name: ticket
description: Work a Jira LEDG ticket end to end — read it, find precedents, branch from develop, implement point by point, verify, open the PR and close the loop in Jira
---

Ticket: $ARGUMENTS

Invoke the `jira-ticket-workflow` skill and follow it from Phase 1 to Phase 9.

If `$ARGUMENTS` is empty, ask which ticket. If it is a bare number (`2296`), read it as
`LEDG-2296`.
