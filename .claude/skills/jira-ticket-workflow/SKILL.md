---
name: jira-ticket-workflow
description: >
  Ticket-to-PR workflow for the dadosgov monorepo (dados.gov.pt). Triggers on a Jira key
  from project LEDG (e.g. LEDG-2296), or when the user says "trabalhar no ticket",
  "pega no ticket", "implementa LEDG-XXXX", "work on ticket". Reads the ticket from Jira,
  searches precedents, picks the right submodule repo, gets a written plan approved before
  any code, branches from develop, implements point by point with one commit each, gates on
  lint+tests, opens the PR into develop and closes the loop back in Jira. Not for sprint
  triage, promotion or CI questions — those are /triage-sprint, /promote and /ci.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent, ExitPlanMode, mcp__atlassian__getJiraIssue, mcp__atlassian__searchJiraIssuesUsingJql, mcp__atlassian__getTransitionsForJiraIssue, mcp__atlassian__transitionJiraIssue, mcp__atlassian__addCommentToJiraIssue, mcp__atlassian__addWorklogToJiraIssue, mcp__atlassian__atlassianUserInfo, mcp__atlassian__lookupJiraAccountId, mcp__atlassian__createJiraIssue, mcp__atlassian__editJiraIssue
---

# Ticket → PR — dadosgov

One concern at a time, always committed, always verified: the plan is approved before any
code, each point gets its own commit and its own proof, and nothing is reported as done that
was not verified.

Jira constants (site, cloudId, project), both repo names and the promotion flow live in
`CLAUDE.md`, which is always loaded — they are not repeated here. `backend/` and `frontend/`
are **independent git repositories**: always target one explicitly (`git -C backend …`).

## The state file is the loop's memory

Every phase records what it did through `.claude/hooks/ticket-state.py`, which writes
`.claude/state/ticket-<KEY>.json`. This is not bookkeeping — it is what makes the loop
**resumable** (a cleared session picks up where it stopped) and what a `PreToolUse` guard
reads to enforce the rules below. `python3 .claude/hooks/ticket-state.py status <KEY>` at any
time; the file prevails over your memory of the conversation, and git prevails over the file.

Two things are enforced, not requested — expect a denial rather than a reminder:

- **No writes into `backend/` or `frontend/` until the plan is approved** (`plan-approved`).
- **No `git push`** until the suites ran green on the current HEAD, the CHANGELOG has an
  entry, every acceptance criterion is resolved and the review was recorded.

`guard-protected-branch.py` separately denies any commit/push/merge on `develop|tst|ppr|main`
and any force-push. That denial means you forgot to create the working branch.

## Several tickets at once

One ticket per session. Two tickets can share the monorepo, but not a submodule checkout —
one checkout is one branch, and two backend suites share one Mongo test database.

- `claim LEDG-<n> --repos <repos>` at Phase 3 is what frees the other submodule for another
  session, and what refuses a second ticket aiming at the same checkout.
- When it refuses, give this ticket its own tree:
  `python3 .claude/hooks/ticket-worktree.py create LEDG-<n> --repos <repos>`. It creates a
  worktree per submodule, links the untracked `.env` files the suites need, installs
  dependencies, and records the path as `workdir`.
- **The session still runs from the monorepo root.** The worktree is a path in the ticket's
  state, not a second project — the guards, the suites and the lint hook all read it from
  there. `ticket-state.py doctor` prints where everything resolved to.
- **A tree is created with the ticket and dies with it.** Each one carries its own `.venv`
  or `node_modules` — about a gigabyte — so `ticket-state.py end` at Phase 10 removes it,
  and `ticket-worktree.py gc` sweeps whatever earlier sessions left behind. Neither can
  delete work: a tree with uncommitted changes, or with commits on no `origin` ref, is kept
  and the reason printed. `list` shows every tree and which are already reclaimable.

## Language — one rule

**English** in every git artefact: branch names, commit messages, PR titles **and bodies**,
code, comments, CHANGELOG entries. **The ticket's language** (Portuguese) everywhere a human
reads the loop: restatement, plan, progress messages, final report, Jira comments. Acceptance
criteria quoted into the PR body stay in the ticket's language, because they are quotations.
Never any `Co-Authored-By` or AI attribution, anywhere.

## Creating a ticket — signed by the logged-in user, in the open sprint

Every ticket this loop creates — a follow-up from Phase 7.5, a split of scope the user asked
for, a ticket dictated mid-session — is **signed by whoever is logged in to Jira**, never left
to whatever identity the MCP connection defaults to. Resolve that identity first, in the same
message as the other Jira reads:

```
mcp__atlassian__atlassianUserInfo()                                 # name + email of the logged-in user
mcp__atlassian__lookupJiraAccountId(searchString: "<that email>")   # → accountId
```

Then create the ticket with **both** identity fields set to that accountId:

```
mcp__atlassian__createJiraIssue(
  projectKey: "LEDG", issueTypeName: "<Task|Bug|Story>", summary: "…", description: "…",
  assignee_account_id: "<accountId>",
  additional_fields: { "reporter": { "id": "<accountId>" },
                       "customfield_10020": <sprintId> })     # the open sprint — see below
```

- **Reporter** is the ticket's author, so set it explicitly even though the OAuth connection
  usually infers it — a shared or re-authenticated connection would otherwise sign the ticket
  to someone who never wrote it. Jira refuses the field without *Modify Reporter* permission:
  when it does, create the ticket without it and **say** that the reporter stayed as Jira
  assigned it. Never drop the reporter silently.
- **Assignee** is that same user, so no ticket is born unowned. Another assignee only when the
  user names one — and even then the reporter stays the logged-in user.
- **Resolve the accountId per session.** Never hardcode one and never reuse one read from an
  earlier transcript: it is the identity of *that* session's user, not this one's.
- Say the ticket was created, with its key and the sprint it landed in.

### The sprint is always the open one

**Do not ask which sprint** — it is the currently open sprint of the LEDG board (`352`), every
time. Read its id immediately before creating: sprints rotate every two weeks, so any id in
this file, in a state file or in an earlier transcript is already stale.

```
mcp__atlassian__searchJiraIssuesUsingJql(
  jql: "project = LEDG AND sprint in openSprints() ORDER BY created DESC",
  fields: ["customfield_10020"], maxResults: 1)
```

`customfield_10020` is the Sprint field on this site. The array it returns can carry closed
sprints alongside the live one, so take the entry whose `state` is `"active"` — never the first
by position. (Shape, not a value to reuse: `{"id": 18843, "name": "LEDG Sprint 35", "state":
"active", "boardId": 352}`.)

- **No active sprint came back** — between sprints, or the board was reconfigured — is the one
  case where you ask, saying why the automatic answer was unavailable. Never fall back to a
  closed sprint or to an id you remember.
- **Jira refuses the field on create** (it is not on the create screen for that issue type) →
  create the ticket, then set it with
  `editJiraIssue(fields: { "customfield_10020": <sprintId> })`. A ticket left in the backlog
  when it should be in the sprint is a silent failure: verify the field came back set, and say
  so if it did not.
- The field takes the sprint **id** (a number), never its name.

## Model split — plan with Fable 5, code with Opus 5

Phase 4 is written by a **Fable 5** subagent; the session and every phase that touches the
repo stay on **Opus 5**. The plan should not be written by the same head that is about to
defend it in code. Record the delegation (`plan-delegated`) — without it, `plan-approved`
refuses and demands an explicit, logged `--planned-on opus --reason`. If Fable is
unavailable, say so and ask; never downgrade in silence.

---

## Phase 1 — Load the ticket

`getJiraIssue` with the key. No key given → ask; to find one,
`searchJiraIssuesUsingJql("project = LEDG AND sprint in openSprints() AND assignee = currentUser() ORDER BY rank")`.

Restate, in the ticket's language: **descrição/contexto**, **o que deve ser feito** (number
the points yourself if the ticket does not), **critérios de aceitação**.

**Do not stop for confirmation here.** The restatement travels verbatim at the top of the
Phase 4 plan — one gate, not two. Stop now only if the ticket has no acceptance criteria and
none can be inferred: ask what "done" means, because that is the exit gate of everything else.

Then persist what was agreed — this is what survives a cleared session:

```bash
python3 .claude/hooks/ticket-state.py start LEDG-<n> --title "<título>" --source jira
python3 .claude/hooks/ticket-state.py criteria LEDG-<n> --add "<critério 1>" --add "<critério 2>"
```

From here the guard denies writes into both submodules until the plan is approved.

Jira unreachable → fall back to `docs/jira-tickets-frontend-backend.md` (`## TICKET-XX:`
headers) with `--source fallback-doc`, and say explicitly that you used it.

## Phase 2 — Precedents (mandatory, never skip)

This codebase has repeated fixes for the same classes of bug. **Do not run the searches in
this context** — delegate them, in the *same message* as the other Phase 1 follow-ups, so
everything runs in parallel:

```
Agent(subagent_type: "explorer-dadosgov", description: "Precedents LEDG-<n>",
      prompt: "<ticket title + the numbered points + suspected paths>.
               1) Prior commits, PRs and existing wrapper/guard patterns that already solve
                  this class of problem.
               2) Which repo(s) the change lands in — backend/, frontend/ or both — with
                  the evidence.
               Report compactly: path:line / commit / PR per finding, and what you did NOT
               find and where you looked.")
```

…alongside `getTransitionsForJiraIssue` (Phase 9 needs it) and `gh auth status` (Phase 8
needs it). The explorer owns the search commands and the wrapper-pattern list; two explorers
in parallel when the ticket clearly spans both repos.

**If a working fix pattern exists, replicate it.** If you can improve on it, argue for that
inside the plan — not in a separate round-trip.

## Phase 3 — Which repo(s)?

Derive it from the explorer's evidence and **state** the conclusion; ask only if genuinely
ambiguous. API contract, model, serialization, permissions, harvesters, Celery → `backend/`.
Page, component, route, SSR/ISR, types, fetch functions → `frontend/`. **Both** → two
branches, two PRs, and a **deploy order** stated in both PR bodies: backend first when the
frontend consumes a new field or endpoint, frontend first when the backend starts requiring
something the UI must send. Only the repo(s) actually changed enter the promotion flow.

Record the conclusion immediately — it is what stops this ticket from locking the repo it
does not touch, and therefore what lets another session work that repo at the same time:

```bash
python3 .claude/hooks/ticket-state.py claim LEDG-<n> --repos backend
```

If it refuses, another ticket already holds that checkout: give this one its own tree with
`ticket-worktree.py create LEDG-<n> --repos <repos>` and pass `--workdir`.

## Phase 4 — Plan (the approval gate)

The plan is written **before the branch exists**: rejected on paper it costs a paragraph,
rejected after three commits it costs the commits. Delegate it, then review what comes back
before showing it — a plan naming a file that does not exist is your error to catch, not the
user's.

```
Agent(subagent_type: "Plan", model: "fable", description: "Plan LEDG-<n>",
      prompt: "<the restatement, the explorer's precedents, the repo decision, and the
               template + rules below>")
python3 .claude/hooks/ticket-state.py plan-delegated LEDG-<n> --model fable
```

The subagent has **no conversation context** — the prompt must carry everything or it plans
blind. It never writes code.

```
## Plano — LEDG-<number>

<o restatement do ticket: contexto, pontos, critérios de aceitação>

**Repo(s):** backend | frontend | ambos (backend primeiro)

### Ponto 1 — <resumo do ponto do ticket>
- **Ficheiros:** `backend/udata/core/<x>/api.py` (`<função/símbolo>`, `+<símbolo novo>`), …
- **Superfície de teste:** `<caminho de teste>` — <porque é legítimo>   ← só quando aplicável
- **Alteração:** <a mudança mais pequena que satisfaz o ponto>
- **Precedente:** <commit/PR/ficheiro que já resolve isto assim> — ou "sem precedente"
- **Prova:** <teste que passa a existir/correr, ou o passo manual no browser>
- **Commit:** `<type>(<scope>): <english imperative description>`

### Ponto 2 — …

### Fora de âmbito
- <o que o ticket parece pedir mas não vais fazer, e porquê>

### Riscos / dúvidas
- <o que pode partir, migrações necessárias, ordem de deploy entre repos>
```

Rules for the plan:

- **One point, one commit, one proof.** A point with no test and no browser step that proves
  it is a gap the user should see now, not discover at Phase 7.
- **Name real files and symbols**, verified by reading them. "Ajustar as permissões" without
  a path is not a plan. A symbol the point **adds** to an existing file is written `` `+nome` ``
  — the audit then checks it does *not* already exist, which catches a plan written from a
  stale reading of the tree. A qualified name (`Classe.campo`) resolves by its components.
- **Touching a test file needs a declared reason.** The audit rejects a test path by default,
  because editing a test is the degenerate way to make a point pass. Two exceptions are
  legitimate and both must be declared on a `**Superfície de teste:**` line naming the file and
  saying why: removing an `xfail(strict=True)` marker whose cause the same commit fixes (this
  project requires it — a strict XPASS is red), and adding coverage that does not exist yet.
  Changing an existing assertion is neither; if a test is wrong, that is a decision for the
  user, not a line in a plan.
- **Carry the precedent forward**; if you intend to diverge, this is where you argue for it.
- **State what you are not doing.** Scope the user did not ask for is scope you do not add.
- **Fold every open question into this one message.** It is the last round-trip before code.
- Keep it proportional: a one-line CSS fix gets a three-line plan, not this template.

### Audit it before showing it

Two halves, and neither is the user's job:

```bash
python3 .claude/hooks/ticket-state.py plan-audit LEDG-<n> --repos <repos> <<'PLAN'
<o plano tal como veio do subagente>
PLAN
```

That settles the mechanical half deterministically — every path and symbol exists, every
point has a **Prova** and a **Commit** line the Phase 6 gate will accept, no undeclared path in
the test surface, no path outside the ticket's repos. It exits 1 with the list; fix the plan and
audit again. `plan-approved` refuses without a `pass` **on that exact plan text**, so a plan
edited after its audit has to be re-audited.

For the half a script cannot decide — right approach, precedent replicated, scope, whether
the proofs prove anything — delegate to the read-only auditor, in the same message:

```
Agent(subagent_type: "plan-auditor", description: "Audit plan LEDG-<n>",
      prompt: "<the plan, the ticket's criteria, the explorer's precedents, the repo decision>")
```

Show the user the plan **and** the auditor's verdict together. A REPROVADO you agree with is
fixed before they read it; one you disagree with is presented with your reason — never
silently dropped.

In plan mode this ends with `ExitPlanMode`; otherwise post it and wait for an explicit "ok".
**Only when the user approves**, record it — the plan text goes on stdin so its digest can
catch drift later, and this is what unlocks the repos:

```bash
python3 .claude/hooks/ticket-state.py plan-approved LEDG-<n> \
  --repos backend --point "<resumo do ponto 1>" --point "<resumo do ponto 2>" <<'PLAN'
<o plano aprovado, colado integralmente>
PLAN
```

If the plan changes mid-implementation — a point turns out impossible, a fourth point appears
— run `ticket-state.py replan LEDG-<n> --reason "…"` **first**. It re-locks the repos, so
drifting in silence stops being an available move; then present the revised plan for approval.

## Phase 5 — Working branch

`<tree>` below is this ticket's checkout: `<repo>` normally, or `<workdir>/<repo>` when the
ticket has its own worktree — `ticket-state.py status LEDG-<n>` shows which.

```bash
git -C <tree> fetch origin
git -C <tree> checkout -b <type>/ledg-<number>-<short-english-description> origin/develop
python3 .claude/hooks/ticket-state.py branch LEDG-<number> <repo> <branch>
```

**Never `checkout develop` here.** Branching straight off `origin/develop` is one command
instead of two, and worktrees share the ref namespace: with a second checkout in play,
`checkout develop` fails with *"develop is already checked out"*.

`feature|bugfix|hotfix|chore|release`, kebab-case, English, ticket number included — e.g.
`bugfix/ledg-2296-harvester-producer-admin-scope`. State the name and create it; renaming
before the PR is `git branch -m`, so a wrong guess costs nothing. The guard rejects a
malformed name, so you find out immediately.

## Phase 6 — Implement, point by point

For each numbered point:

1. Read the existing code around it first; follow the patterns already there.
2. Implement the smallest change that satisfies the point.
3. Fix whatever the `PostToolUse` lint hook reports before moving on.
4. Run the **narrow** test for that point.
5. Commit — one point, one commit — and record the mapping:
   ```bash
   python3 .claude/hooks/ticket-state.py point LEDG-<n> done <N> --commit <sha> \
     --proof "test:<caminho>::<teste>"     # ou "manual:<URL, cliques, resultado esperado>"
   ```
   The sha is checked against git: a point without a real commit does not count as done.
6. Tell the user: `✅ Ponto N feito: <resumo>. A começar o ponto N+1: <resumo>`.

Commits are **automatic per point** — that was settled with the plan; do not ask again.
Message format, English, no attribution:

```
<type>(<scope>): <imperative description>

<why, if not obvious>

Refs: LEDG-<number>
```

A point blocked on a decision only the user can make:
`ticket-state.py point LEDG-<n> blocked <N> --reason "…"`, then move to the next independent
point — or stop and ask, if none is independent. A blocked point surfaces in the PR body and
the final report; it is never silently absorbed.

**`CHANGELOG.md` is mandatory in every changed repo** before the push — top of `## Unreleased`,
bold one-line summary plus indented sub-bullets on the why/how, following the convention in
that repo's `CLAUDE.md`. Never reference a PR number or a Jira id, never edit an entry that
was already promoted. The push gate checks all three.

**Both repos changed?** Delegate each repo's points to `udata-backend` / `next-frontend` in
parallel, prompt = that repo's section of the approved plan. They cannot ask the user
anything, so only delegate points the plan marked unambiguous.

## Phase 7 — Verification gate

The commands live in `backend/CLAUDE.md`, `frontend/CLAUDE.md` and the two agent files. What
this phase decides is **when** each level runs:

- **Per point: narrow only.** The test file(s) named in that point's *Prova*, with `-x`.
- **Once, before the push: full.** Start it in the background and, while it runs, write the
  CHANGELOG entries, draft the PR body and launch the Phase 7.5 review. The push depends on
  its exit code, not the other way round.
- **Never two pytest runs against the same Mongo test databases.** `_clean_db` truncates
  every collection between tests, so two runs sharing a database name wipe each other's
  fixtures. `verify` reserves the suite (pid + timestamp) and **refuses** rather than waits:
  end the turn and run it again in a few minutes. A reservation whose process died is taken
  over automatically, so a killed session never blocks anyone.
  A ticket with its own worktree gets its own databases (`UDATA_TEST_MONGO_PREFIX`, honoured
  by `udata/tests/plugin.py`) and then runs in parallel with the others — `verify` checks
  that the tree really honours the variable before it stops serialising, because a worktree
  cut before that change landed would share `udata-test` while believing otherwise.

The run that counts is the one the gate reads, and it must be green on the **final** HEAD —
any later commit invalidates it:

```bash
python3 .claude/hooks/ticket-state.py verify LEDG-<n> <repo>
```

**Red that does not fall to one honest attempt → `/fix-loop <repo> <caminho/do/teste>`**,
which freezes the test surface and requires a proven red-to-green transition. Never iterate
freely against a red suite, and never make a test pass by weakening it. If `/fix-loop` ends
REPROVADO, that diagnosis is the answer — report it and stop.

Then resolve **every** acceptance criterion in the state file, with evidence:

```bash
python3 .claude/hooks/ticket-state.py criteria LEDG-<n> --set 1 --status met --evidence "tests/test_x.py::test_y"
python3 .claude/hooks/ticket-state.py criteria LEDG-<n> --set 2 --status unmet --evidence "<razão>"
```

An `unmet` with a written reason is an honest outcome and passes the gate. A `pending` is a
criterion nobody looked at, and blocks the push.

## Phase 7.5 — Independent review (advisory, before pushing)

A finding after the PR is open costs a force-push and spends the human reviewer's attention
on what a machine could have caught.

1. **`/code-review`** over the diff, delegated to a **fresh-context subagent** — you just
   wrote this code and will defend your own choices. Frame it adversarially: ask it to refute
   that the change is correct. Sonnet by default; Opus when the diff touches the sensitive
   surface below.
2. **`/security-review` only when the diff touches this fork's concentrated incident surface**
   — paths matching `auth`, `saml`, `upload`, `proxy`, `harvest`, `permissions`, `csrf`.
   Otherwise skip it and say you skipped it.
3. **Advisory, not blocking.** Fix what you agree with; for what you reject, say so *with the
   reason*. A gate that blocks on judgements is one people learn to route around.
4. **Never resolve a finding by removing the check that raised it** — that is weakening a test
   in different clothing. If the honest fix is bigger than the ticket, report it as follow-up — a
   ticket opened for it is created signed, per the section above.
5. Record it, or it evaporates with the session — and the push gate refuses until it exists:
   ```bash
   python3 .claude/hooks/ticket-state.py review LEDG-<n> \
     --accepted "<o que corrigiste>" --rejected "<achado> :: <razão da rejeição>"   # ou --none
   ```
   The gate checks only that the review **happened**, never its conclusions.

## Phase 8 — PR into develop

Check `gh auth status` **before** pushing — the CLI is on some team machines and not others.

```bash
python3 .claude/hooks/ticket-state.py pr-body LEDG-<n>    # criteria, points→commits, review
git -C <repo> push -u origin <branch>
gh pr create --repo amagovpt/<repo> --base develop --head <branch> --title "…" --body "<body>"
python3 .claude/hooks/ticket-state.py pr LEDG-<n> <repo> <url>
```

No `gh`? Push anyway and hand over the compare URL
`https://github.com/amagovpt/<repo>/compare/develop...<branch>?expand=1` plus the `pr-body`
output to paste. PR body: what changed and why, the ticket key, how to test manually, the
criteria checklist, and the deploy order when both repos changed.

The push passes through the ticket gate. If it denies, it names exactly what is missing.

Take **one** CI snapshot (`gh pr checks <n> --repo amagovpt/<repo>`) and move on — do not sit
in `--watch`, which pins this session for the whole run doing nothing.

## Phase 9 — Close the loop in Jira

1. Comment the PR URL and a one-paragraph summary (`addCommentToJiraIssue`).
2. Log the time if the user gives it (`addWorklogToJiraIssue`).
3. Transition the ticket: read the available transitions (fetched back in Phase 2) and apply
   **the one the user confirms**. Never invent status names.

## Phase 10 — Final report and hand-off

```
## ✅ LEDG-<number> — <título>

**Repo(s):** backend | frontend
**Branch:** <branch>
**PR:** <url>  (CI: passou | falhou | a correr)

### Commits
1. <type>(<scope>): …

### Critérios de aceitação
- [x] <criterion> — <ficheiro/teste que o satisfaz>
- [ ] <criterion> — NÃO satisfeito: <razão>

### Próximo passo
`/loop 8m /watch-pr <repo> <pr>` — vermelho é diagnosticado por `/ci` e reparado por
`/fix-loop`; depois do merge, `/promote <repo> tst`.
```

Build the criteria and review sections from `pr-body`/`status`, never from memory. Then close
the state: `python3 .claude/hooks/ticket-state.py end LEDG-<n>`.

`end` also **removes this ticket's worktree**, if it had one — the PR is open, so the commits
are on `origin` and the checkout has nothing left to hold. It refuses if anything would be
lost and says what; then it is a real question for the user, not something to force. Say in
the report which tree was reclaimed, and run `ticket-worktree.py gc` when the session start
announced trees left over from tickets that never reached this phase.

---

## Failure modes — decided in advance, not improvised

- **Jira down.** Try `docs/jira-tickets-frontend-backend.md`; if the ticket is not there
  either, ask the user to paste it (`--source user-dictated`). Never reconstruct a ticket from
  the key alone — an invented requirement implemented perfectly is still wrong.
- **No acceptance criteria.** Ask what "done" means and register the answer. `plan-approved`
  refuses with zero criteria unless `--no-criteria-confirmed`, which asserts that conversation
  happened.
- **The plan proves wrong at point k.** `replan --reason` immediately; keep the points already
  committed (they were approved), present the revised remainder. Never revert approved and
  committed work without being asked.
- **A point has no possible narrow test.** The plan already had to say so. Record
  `--proof "manual:<URL, cliques, resultado>"`; it flows into the PR's "how to test".
- **`gh` absent or unauthenticated.** Detected at Phase 8 entry, before pushing. The push
  still works; the PR goes through the compare URL.
- **CI red after the PR.** One fix commit per root cause — which invalidates the recorded
  green, so `verify` runs again before the next push. Same check red twice for the same cause
  → stop and report. A failing test goes to `/fix-loop`. Never close and recreate the PR to
  reset CI.
- **Both repos with a deploy order.** Record it, state it in **both** PR bodies, and open the
  dependent PR as `--draft` until the prerequisite merges — a draft cannot be merged out of
  order by a well-meaning reviewer.
- **A point blocked on the user.** `point blocked --reason`, continue with independent points,
  otherwise stop with the question stated.
- **The session dies before Phase 10.** Its worktree stays on disk with nothing pointing at
  it — a gigabyte per ticket, and they add up unnoticed. The next session start names them;
  `ticket-worktree.py gc` collects the ones whose tickets are closed and whose work is
  pushed, and keeps the rest with the reason. Never `--force` a tree you did not check.

## Rules

- **Never** write code before the plan is approved, and never drift from it in silence — a
  changed plan is re-stated and re-approved (`replan` enforces the re-locking).
- **Never** batch two ticket points into one commit unless they are genuinely inseparable; if
  they are, say why.
- Always read before writing; always follow the existing pattern over a new one.
- If a point is ambiguous, ask — do not invent scope.
- If tests fail, fix before the next point. Never report done with red tests.
- **A ticket created by this loop is signed by the logged-in Jira user** — reporter *and*
  assignee — never the MCP connection's default identity, and it goes straight into the
  **open sprint**, read at creation time. Neither is a question for the user.
- Promotion beyond `develop` is a separate, explicit step (`/promote`), never automatic.
