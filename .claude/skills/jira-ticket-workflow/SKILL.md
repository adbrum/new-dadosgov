---
name: jira-ticket-workflow
description: >
  Ticket-to-PR workflow for the dadosgov monorepo (dados.gov.pt). Triggers on a Jira key
  from project LEDG (e.g. LEDG-2296), or when the user says "trabalhar no ticket",
  "pega no ticket", "implementa LEDG-XXXX", "work on ticket". Reads the ticket from Jira,
  searches precedents, picks the right submodule repo, gets a written plan approved before
  any code, branches from develop, implements point by point with one commit each, gates on
  lint+tests, opens the PR into develop and closes the loop back in Jira.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent, ExitPlanMode, mcp__atlassian__getJiraIssue, mcp__atlassian__searchJiraIssuesUsingJql, mcp__atlassian__getTransitionsForJiraIssue, mcp__atlassian__transitionJiraIssue, mcp__atlassian__addCommentToJiraIssue, mcp__atlassian__addWorklogToJiraIssue
---

# Ticket → PR — dadosgov

Disciplined, incremental delivery on the **dadosgov** monorepo. One concern at a time,
always committed, always verified. The philosophy: the plan is agreed before any code is
written, each implementation point gets its own commit before moving on, and nothing is
reported as done that was not verified.

## Constants

| Item | Value |
| --- | --- |
| Jira site | `ticapp.atlassian.net` |
| Jira cloudId | `0d1d9259-29f0-46ff-bb50-522a373f8daf` |
| Jira project | `LEDG` — "L11 - Evol&Man.dados.gov" |
| Backend repo | `amagovpt/udata-pt` → `backend/` (udata, Flask, MongoEngine, Celery) |
| Frontend repo | `amagovpt/dadosgov-fe` → `frontend/` (Next.js App Router, TypeScript) |
| Environment branches | `develop` → `tst` → `ppr` → `main` (both repos, independently) |
| `gh` CLI | check with `gh auth status` — present on some team machines, not all |
| Planning model | **Fable 5** (`claude-fable-5`) — Phase 4 only |
| Implementation model | **Opus 5** (`claude-opus-5`) — every other phase |

`backend/` and `frontend/` are **independent git repositories** mounted as submodules.
Always target one explicitly (`git -C backend …`) — never assume the cwd repo.

> A `PreToolUse` hook (`.claude/hooks/guard-protected-branch.py`) **denies** any commit,
> push, merge or rebase on `develop|tst|ppr|main` in either submodule, and denies
> force-push everywhere. If you get that denial, you forgot to create the working branch.

## Model split — plan with Fable 5, code with Opus 5

**The plan (Phase 4) is written by Fable 5. Everything that touches the repo — Phases 5 to 10
— runs on Opus 5.** Two different models read the same ticket differently; the split is there
so the plan is not written by the same head that is about to defend it in code.

The session itself stays on **Opus 5**. Phase 4 is delegated to a Fable subagent:

```
Agent(subagent_type: "Plan", model: "fable", description: "Plan LEDG-<n>",
      prompt: "<ticket restatement + Phase 2 precedents + Phase 3 repo decision + the plan
               template and rules from Phase 4>")
```

- The subagent has **no conversation context** — the prompt must carry the ticket, the
  precedents you found and the repo decision, or it will plan blind.
- The plan comes back as a report; **you** present it to the user for approval and **you**
  implement it. Never let the planner write code, and never start coding on Opus before the
  Fable plan is approved.
- If the user prefers to drive the split by hand (`/model fable` → plan → `/model opus` →
  code), that is equivalent — say which mode you are using.
- If Fable is unavailable, say so explicitly and ask whether to plan on Opus instead. Do not
  silently downgrade the split.

---

## Phase 1 — Load the ticket

If the user gave a key (`LEDG-2296`), fetch it:

```
mcp__atlassian__getJiraIssue(cloudId: "0d1d9259-29f0-46ff-bb50-522a373f8daf", issueIdOrKey: "LEDG-2296")
```

If the user gave no key, ask for it — do not guess. To find one, search:

```
mcp__atlassian__searchJiraIssuesUsingJql(cloudId: …, jql: "project = LEDG AND sprint in openSprints() AND assignee = currentUser() ORDER BY rank")
```

Parse and restate, in the ticket's own language:

- **Descrição / contexto**
- **O que deve ser feito** — number the implementation points yourself if the ticket does not
- **Critérios de aceitação** — these are the exit gate; if the ticket has none, ask the user
  what "done" means before writing code

Fallback when Jira is unreachable: the local backlog `docs/jira-tickets-frontend-backend.md`
(header format `## TICKET-XX: <title>`). Say explicitly that you used the fallback.

**Confirm the restatement with the user before touching code.**

## Phase 2 — Search precedents (mandatory, never skip)

This codebase has repeated fixes for the same classes of bug. Before designing anything:

```bash
git -C backend log --all --grep=<keyword> --oneline | head -20
git -C frontend log --all --grep=<keyword> --oneline | head -20
git -C <repo> log --all --oneline -- <suspected/file/path>
grep -rn "<symbol>" backend/udata frontend/src
gh pr list --repo amagovpt/<repo> --state all --search "<keyword>" --limit 10
```

Also grep for existing wrapper/guard patterns before writing a new one — e.g. `Isolated*`,
`Safe*`, `BaseBackend.get/head/post` for harvester HTTP, `listingCache.ts` for shared SSR
caching, server-side CSRF minting for authenticated POSTs.

Report what you found. **If a working fix pattern exists, replicate it.** If you believe you
can improve on it, say so explicitly and get agreement before diverging.

## Phase 3 — Which repo(s)?

Derive it from the work, then state the conclusion — only ask the user if genuinely ambiguous:

- API contract, model, serialization, permissions, harvesters, Celery → `backend/`
- Page, component, route, SSR/ISR, types, fetch functions → `frontend/`
- **Both** → two branches, two PRs, and you must state the **deploy order** in the PR bodies
  (which side must land first so the other does not 500). Backend-first when the frontend
  consumes a new field/endpoint; frontend-first when the backend starts requiring something
  the UI must send.

Only the repo(s) actually changed go through the promotion flow. The other stays untouched.

## Phase 4 — Plan (approval gate)

Write the plan **before creating the branch**. A plan rejected on paper costs a paragraph;
a plan rejected after three commits costs the commits. If you are in plan mode, this phase
ends with `ExitPlanMode`; otherwise post the plan and wait for an explicit "ok".

**This phase runs on Fable 5** — see *Model split* above. Delegate it, then review what comes
back before showing it to the user: a plan naming a file that does not exist is your error to
catch, not the user's.

The plan is the bridge between the ticket (Phase 1) and the code: every numbered point gets
a concrete landing site in the repo, justified by what Phase 2 found.

```
## Plano — LEDG-<number>

**Repo(s):** backend | frontend | ambos (backend primeiro)

### Ponto 1 — <resumo do ponto do ticket>
- **Ficheiros:** `backend/udata/core/<x>/api.py` (`<função/símbolo>`), …
- **Alteração:** <a mudança mais pequena que satisfaz o ponto>
- **Precedente:** <commit/PR/ficheiro que já resolve isto assim> — ou "sem precedente"
- **Prova:** <teste que passa a existir/correr, ou o passo manual no browser>
- **Commit:** `<type>(<scope>): <descrição>`

### Ponto 2 — …

### Fora de âmbito
- <o que o ticket parece pedir mas não vais fazer, e porquê>

### Riscos / dúvidas
- <o que pode partir, migrações necessárias, ordem de deploy entre repos>
```

Rules for the plan:

- **One point, one commit, one proof.** If a point has no test and no browser step that
  proves it, say so in the plan — that is a gap the user should see before you code, not a
  detail to discover at Phase 7.
- **Name real files and symbols**, verified by reading them in Phases 2–3. A plan that says
  "ajustar as permissões" without a path is not a plan.
- **Carry the precedent forward.** If Phase 2 found a working pattern, the plan says which
  point replicates it. If you intend to diverge, the plan is where you argue for it.
- **State what you are not doing.** Scope the user did not ask for is scope you do not add.
- **Fold every open question into this one message** — including whether commits are
  automatic per point or approved one by one (Phase 6). This should be the last round-trip
  before code.
- Keep it proportional: a one-line CSS fix gets a three-line plan, not this template.

If the plan changes mid-implementation — a point turns out to be impossible, or a fourth
point appears — **stop and say so** with the revised plan. Silently drifting from an approved
plan is the failure this phase exists to prevent.

## Phase 5 — Working branch

```bash
git -C <repo> fetch origin
git -C <repo> checkout develop && git -C <repo> pull origin develop
git -C <repo> checkout -b <type>/ledg-<number>-<short-english-description>
```

- Types: `feature/` `bugfix/` `hotfix/` `chore/` `release/`
- `kebab-case`, **English only**, ticket number included — e.g.
  `bugfix/ledg-2296-harvester-producer-admin-scope`
- State the name and create it — do not spend a round-trip confirming it. Renaming before the
  PR is `git branch -m`, so a wrong guess costs nothing; say so when you state it. Any genuine
  choice (approach, commit strategy) belongs in the Phase 4 plan, not in a question here.

## Phase 6 — Implement, point by point

For each numbered point:

1. Read the existing code around it first; follow the patterns already there.
2. Implement the smallest change that satisfies the point.
3. The `PostToolUse` lint hook runs ruff/eslint on each file you write — if it reports
   problems, fix them before moving on.
4. Run the narrow test for that point (see Phase 7 commands).
5. Commit — one point, one commit.
6. Tell the user: `✅ Ponto N feito: <resumo>. A começar o ponto N+1: <resumo>`.

**Commit message** — Conventional Commits, English, and **never any `Co-Authored-By` or AI
attribution**:

```
<type>(<scope>): <imperative description>

<why, if not obvious>

Refs: LEDG-<number>
```

The commit strategy — **automatic** per point or **approve** each one — was settled with the
plan in Phase 4; do not ask again. If approve: show `git -C <repo> diff --stat` plus the
proposed message and a short "como testar no browser" (URL to open, what to click, what to
expect), then wait.

**`CHANGELOG.md` is mandatory in BOTH repos** — `backend/CHANGELOG.md` and
`frontend/CHANGELOG.md` carry the same convention. Once the implementation is done, add an
entry at the top of `## Unreleased`: bold one-line summary plus indented sub-bullets explaining
the why/how. Never reference a PR number or a Jira id there (no `LEDG-XXXX`), and never edit an
entry that was already promoted — that is what makes the same line diverge between environment
branches and turn an auto-mergeable entry into a conflict.

## Phase 7 — Verification gate

| | Command |
| --- | --- |
| Backend, narrow | `cd backend && uv run pytest <path/to/test_file.py> -x` |
| Backend, full | `cd backend && uv run pytest` |
| Backend lint | `cd backend && uv run ruff check . && uv run ruff format --check .` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend unit | `cd frontend && npm test` (vitest) |
| Frontend e2e | `cd frontend && npm run test:e2e` |
| Frontend types | `cd frontend && npx tsc --noEmit` |

udata is **Flask + MongoEngine**, not Django — there is no `django_db` marker. Mongo for
tests runs on port 27018 (`docker-compose.test.yml`).

Then walk the **critérios de aceitação** one by one and mark `[x]` / `[ ]`, each with the
file, function or test that satisfies it. An unsatisfied criterion is reported as
unsatisfied — never silently dropped.

## Phase 7.5 — Independent review (advisory)

Run this on the diff **before pushing**. A finding after the PR is open costs a force-push or
a follow-up commit and spends the human reviewer's attention on something the machine could
have caught.

1. **`/code-review`** over the diff. Delegate it to a **fresh-context subagent** — you just
   wrote this code and will tend to defend your own choices; a reviewer that never saw the
   decisions being made is a qualitatively different read. Frame it adversarially: ask it to
   refute that the change is correct.
2. **`/security-review`, but only when the diff touches a sensitive surface.** This fork's
   incident history is concentrated: harvester HTTP (SSRF), authenticated POSTs (CSRF/session),
   the `/r/<id>` download proxy, uploads, SAML, permissions. Trigger on paths matching
   `auth`, `saml`, `upload`, `proxy`, `harvest`, `permissions`, `csrf` — otherwise skip it and
   say you skipped it.
3. **Advisory, not blocking.** A finding is a judgement, not a fact. Fix the ones you agree
   with; for the ones you reject, say so **with the reason** in the report and the PR body. A
   gate that blocks on judgements is a gate people learn to route around.
4. **Never resolve a finding by removing the check that raised it.** That is the same
   degeneration as weakening a test, in different clothing — if the honest fix is bigger than
   the ticket, report it as a follow-up instead of neutering the signal.
5. After the PR exists, `/code-review --comment <pr>` is optional: it leaves the findings
   inline so the human reviewer starts on cleared ground.

Report what the review found, what you changed because of it, and what you deliberately did
not — that last part is the one worth reading.

## Phase 8 — PR into develop

```bash
git -C <repo> push -u origin <branch>
gh pr create --repo amagovpt/<repo> --base develop --head <branch> \
  --title "<type>(<scope>): <description>" --body "<body>"
```

PR body: what changed and why, the ticket key, how to test manually, the acceptance-criteria
checklist, and — when both repos changed — the required deploy order. No AI attribution.

Then watch CI: `gh pr checks <number> --repo amagovpt/<repo> --watch`.

## Phase 9 — Close the loop in Jira

1. Comment on the ticket with the PR URL and a one-paragraph summary
   (`mcp__atlassian__addCommentToJiraIssue`).
2. Log the time spent if the user gives it (`mcp__atlassian__addWorklogToJiraIssue`).
3. Transition the ticket — read the available transitions first
   (`getTransitionsForJiraIssue`), then apply the one the user confirms. Do not invent
   status names.

## Phase 10 — Final report

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
PR para `tst` depois de validado em develop (`/promote <repo> tst`).
```

---

## Rules

- **Never** commit, push or merge on `develop|tst|ppr|main` — the hook blocks it anyway.
- **Never** write code before the Phase 4 plan is approved, and never drift from it in
  silence — a changed plan is re-stated and re-approved.
- **Never** plan and code on the same model: Phase 4 is Fable 5, Phases 5–10 are Opus 5.
- **Never** batch two ticket points into one commit unless they are genuinely inseparable;
  if they are, say why.
- **Never** put Portuguese in branch names, commit messages or PR titles. Code, comments and
  git history are English. User-facing conversation follows the user's language.
- **Never** add `Co-Authored-By` or any AI attribution anywhere in git history or PRs.
- Always read before writing; always follow the existing pattern over a new one.
- If a point is ambiguous, ask — do not invent scope.
- If tests fail, fix before the next point. Never report done with red tests.
- Promotion beyond `develop` is a separate, explicit step (`/promote`), never automatic.
