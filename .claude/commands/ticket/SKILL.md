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
- **`ESTACIONADO:<code>` in the status** → the previous session stopped on a decision only the
  user can make. Show `parked.question` and `parked.diagnosis` **first** and get the answer;
  then `ticket-state.py unpark LEDG-<n>` and continue at `parked.phase`. Answering the question
  is the whole task — do not start implementing around it.

## Working several tickets at once

One ticket per session, and each session needs its own checkout of the repo it touches:

```bash
python3 .claude/hooks/ticket-worktree.py list                 # what is already claimed
python3 .claude/hooks/ticket-worktree.py create LEDG-<n> --repos backend
python3 .claude/hooks/ticket-worktree.py gc                   # reclaim closed tickets' trees
```

`claim` refuses a second active ticket in the same repo without a worktree, and says which
command creates one. The session still runs from the monorepo root — the worktree is a path
recorded in the ticket's state (`workdir`), not a second project. `ticket-state.py doctor`
prints where everything resolved to if anything looks off.

A tree costs about a gigabyte, so it is reclaimed with the ticket: `ticket-state.py end`
(Phase 10) removes this one, `gc` sweeps the ones sessions that died earlier left behind.
Both refuse over uncommitted or unpushed work rather than deleting it.

Then follow `jira-ticket-workflow` to Phase 10.

## The two gates

- **Phase 4 is an approval gate** — no code before the user says ok. It is enforced: a
  `PreToolUse` guard denies writes into `backend/` and `frontend/` until `plan-approved`.
  A resume that lands in Phase 6 with no approved plan goes back through Phase 4 first.
- **Phase 9 is a human gate** — the Jira transition is applied only after the user confirms.

**Phase 4 runs on Fable 5** (delegated subagent); everything that touches the repo runs on
Opus 5.

## If this session creates a ticket

Any new ticket — a follow-up from the review, a split of scope — is created **signed by the
logged-in Jira user**: reporter *and* assignee set to the accountId resolved from
`atlassianUserInfo` + `lookupJiraAccountId`, never the MCP connection's default identity — and
**in the currently open sprint**, whose id is read at creation time from
`sprint in openSprints()` (field `customfield_10020`). Neither is asked: report the key and the
sprint name it landed in. Details in `jira-ticket-workflow`.
