---
name: jira-ticket-workflow
description: >
  Ticket-to-PR workflow for the dadosgov monorepo (dados.gov.pt). Triggers on a Jira key
  from project LEDG (e.g. LEDG-2296), or when the user says "trabalhar no ticket",
  "pega no ticket", "implementa LEDG-XXXX", "work on ticket". Reads the ticket from Jira,
  searches precedents, picks the right submodule repo, branches from develop, implements
  point by point with one commit each, gates on lint+tests, opens the PR into develop and
  closes the loop back in Jira.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, mcp__atlassian__getJiraIssue, mcp__atlassian__searchJiraIssuesUsingJql, mcp__atlassian__getTransitionsForJiraIssue, mcp__atlassian__transitionJiraIssue, mcp__atlassian__addCommentToJiraIssue, mcp__atlassian__addWorklogToJiraIssue
---

# Ticket → PR — dadosgov

Disciplined, incremental delivery on the **dadosgov** monorepo. One concern at a time,
always committed, always verified. The philosophy: each implementation point gets its own
commit before moving on, and nothing is reported as done that was not verified.

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

`backend/` and `frontend/` are **independent git repositories** mounted as submodules.
Always target one explicitly (`git -C backend …`) — never assume the cwd repo.

> A `PreToolUse` hook (`.claude/hooks/guard-protected-branch.py`) **denies** any commit,
> push, merge or rebase on `develop|tst|ppr|main` in either submodule, and denies
> force-push everywhere. If you get that denial, you forgot to create the working branch.

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

## Phase 4 — Working branch

```bash
git -C <repo> fetch origin
git -C <repo> checkout develop && git -C <repo> pull origin develop
git -C <repo> checkout -b <type>/ledg-<number>-<short-english-description>
```

- Types: `feature/` `bugfix/` `hotfix/` `chore/` `release/`
- `kebab-case`, **English only**, ticket number included — e.g.
  `bugfix/ledg-2296-harvester-producer-admin-scope`
- State the name and create it — do not spend a round-trip confirming it. Renaming before the
  PR is `git branch -m`, so a wrong guess costs nothing; say so when you state it. Fold any
  genuine choice (approach, commit strategy) into a single question earlier instead.

## Phase 5 — Implement, point by point

For each numbered point:

1. Read the existing code around it first; follow the patterns already there.
2. Implement the smallest change that satisfies the point.
3. The `PostToolUse` lint hook runs ruff/eslint on each file you write — if it reports
   problems, fix them before moving on.
4. Run the narrow test for that point (see Phase 6 commands).
5. Commit — one point, one commit.
6. Tell the user: `✅ Ponto N feito: <resumo>. A começar o ponto N+1: <resumo>`.

**Commit message** — Conventional Commits, English, and **never any `Co-Authored-By` or AI
attribution**:

```
<type>(<scope>): <imperative description>

<why, if not obvious>

Refs: LEDG-<number>
```

Ask once, at the start, whether the user wants **automatic** commits per point or wants to
**approve** each one. If approve: show `git -C <repo> diff --stat` plus the proposed message
and a short "como testar no browser" (URL to open, what to click, what to expect), then wait.

**`CHANGELOG.md` is mandatory in BOTH repos** — `backend/CHANGELOG.md` and
`frontend/CHANGELOG.md` carry the same convention. Once the implementation is done, add an
entry at the top of `## Unreleased`: bold one-line summary plus indented sub-bullets explaining
the why/how. Never reference a PR number or a Jira id there (no `LEDG-XXXX`), and never edit an
entry that was already promoted — that is what makes the same line diverge between environment
branches and turn an auto-mergeable entry into a conflict.

## Phase 6 — Verification gate

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

## Phase 7 — PR into develop

```bash
git -C <repo> push -u origin <branch>
gh pr create --repo amagovpt/<repo> --base develop --head <branch> \
  --title "<type>(<scope>): <description>" --body "<body>"
```

PR body: what changed and why, the ticket key, how to test manually, the acceptance-criteria
checklist, and — when both repos changed — the required deploy order. No AI attribution.

Then watch CI: `gh pr checks <number> --repo amagovpt/<repo> --watch`.

## Phase 8 — Close the loop in Jira

1. Comment on the ticket with the PR URL and a one-paragraph summary
   (`mcp__atlassian__addCommentToJiraIssue`).
2. Log the time spent if the user gives it (`mcp__atlassian__addWorklogToJiraIssue`).
3. Transition the ticket — read the available transitions first
   (`getTransitionsForJiraIssue`), then apply the one the user confirms. Do not invent
   status names.

## Phase 9 — Final report

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
- **Never** batch two ticket points into one commit unless they are genuinely inseparable;
  if they are, say why.
- **Never** put Portuguese in branch names, commit messages or PR titles. Code, comments and
  git history are English. User-facing conversation follows the user's language.
- **Never** add `Co-Authored-By` or any AI attribution anywhere in git history or PRs.
- Always read before writing; always follow the existing pattern over a new one.
- If a point is ambiguous, ask — do not invent scope.
- If tests fail, fix before the next point. Never report done with red tests.
- Promotion beyond `develop` is a separate, explicit step (`/promote`), never automatic.
