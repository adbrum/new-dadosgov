---
name: ticket
description: Work a Jira LEDG ticket end to end — read it, plan, implement point by point, verify, open the PR and hand off to the PR-watch loop. Detects an in-flight ticket and resumes instead of re-planning.
---

Ticket: $ARGUMENTS

Normalize to the `LEDG-<n>` key — `LEDG-2296` as is, a bare `2296` as `LEDG-2296`, and a
`https://ticapp.atlassian.net/browse/LEDG-2296` URL down to its key. Empty → ask which ticket.

## First action: is this ticket already in flight?

```bash
python3 .claude/hooks/ticket-state.py status LEDG-<n>
git -C backend branch --list "*ledg-<n>-*"; git -C frontend branch --list "*ledg-<n>-*"
gh pr list --repo amagovpt/udata-pt --state all --search "ledg-<n>" --limit 5
gh pr list --repo amagovpt/dadosgov-fe --state all --search "ledg-<n>" --limit 5
```

- **Nothing found** → invoke `jira-ticket-workflow` and run it from Phase 1.
- **Anything found** → this is a **resume**, not a restart. Show a short status (fase, branch,
  pontos feitos/total, critérios resolvidos/total, PR) and continue at the recorded phase.
  Do not re-read the ticket, do not re-plan, and do not re-implement a point that already has
  a commit. **Git is the authority on what happened**; the state file supplies the approved
  plan and the criteria. If they disagree, say so and ask.

Then follow `jira-ticket-workflow` to Phase 10.

## The two gates

- **Phase 4 is an approval gate** — no code before the user says ok. It is enforced: a
  `PreToolUse` guard denies writes into `backend/` and `frontend/` until `plan-approved`.
  A resume that lands in Phase 6 with no approved plan goes back through Phase 4 first.
- **Phase 9 is a human gate** — the Jira transition is applied only after the user confirms.

**Phase 4 runs on Fable 5** (delegated subagent); everything that touches the repo runs on
Opus 5.
