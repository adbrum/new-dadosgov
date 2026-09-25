---
name: ticket
description: Work a Jira LEDG ticket end to end — read it, plan, implement point by point, verify, open the PR and hand off to the PR-watch loop. Detects an in-flight ticket and resumes instead of re-planning.
model: opus[1m]
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

One ticket per session, and one ticket per submodule checkout at a time. **The flow does not
create worktrees.** `claim` refuses a second active ticket in the same repo and names the one
holding it: pause that one (`ticket-state.py pause LEDG-<other>` — a ticket whose PR is
already open no longer needs the checkout) or ask the user which goes first.

Trees left by earlier sessions are cleanup only:

```bash
python3 .claude/hooks/ticket-worktree.py list   # leftover trees and whether they are dirty
python3 .claude/hooks/ticket-worktree.py gc     # reclaim the ones whose work is pushed
```

Both refuse over uncommitted or unpushed work rather than deleting it.

## The two gates

- **Phase 4 is an approval gate** — no code before the user says ok. It is enforced: a
  `PreToolUse` guard denies writes into `backend/` and `frontend/` until `plan-approved`.
  A resume that lands in Phase 6 with no approved plan goes back through Phase 4 first.
- **Phase 9 is a human gate** — the Jira transition is applied only after the user confirms.

The push gate reads one green per repo: lint plus `verify … --impacted` (the tests the diff
can break; the resolver escalates to the whole suite when the diff has no area, and says
which file forced it). The full suite for the branch is the CI run on the PR — do not repeat
it locally out of habit. A CHANGELOG- or docs-only commit no longer invalidates that green;
a code commit still does.

**Phase 4 runs in a fresh Plan subagent on the latest Opus** (no more Fable); everything
that touches the repo runs on the latest Opus too (alias `opus[1m]` in this command's
frontmatter — follows new releases without an edit here).

## If this session creates a ticket

Any new ticket — a follow-up from the review, a split of scope — is created **signed by the
logged-in Jira user**: reporter *and* assignee set to the accountId resolved from
`atlassianUserInfo` + `lookupJiraAccountId`, never the MCP connection's default identity — and
**in the currently open sprint**, whose id is read at creation time from
`sprint in openSprints()` (field `customfield_10020`). Neither is asked: report the key and the
sprint name it landed in. Details in `jira-ticket-workflow`.
