---
name: jira-ticket-workflow
description: >
  Structured Jira ticket-driven development workflow specific to the new-dadosgov project.
  Triggers when the user says "work on ticket", "pick up ticket", "implement TICKET-XX",
  or provides a ticket ID from the project's Jira-style backlog. Handles frontend/backend
  selection, branch creation in the correct separated repository, and incremental commits
  per ticket point.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Jira Ticket Workflow — new-dadosgov

You are a Senior Software Engineer & Automation Agent working on the **new-dadosgov** project
(Portal de Dados Abertos — dados.gov.pt). This skill defines a disciplined, incremental
development workflow: read ticket → choose repo → create branch → implement each point → commit.

The core philosophy: **one concern at a time, always committed**. Each implementation point
gets its own commit before moving on.

---

## Project Structure

```
/home/adbrum/workspace/babel/new-dadosgov/
├── frontend/     ← Next.js app (separate git repo)
│   remotes:
│     origin    → git@github.com:adbrum/udata_agora.git
│     newdadosgov → git@github.com:adbrum/new-dadosgov.git
│
└── backend/      ← udata/Flask app (separate git repo)
    remotes:
      origin    → git@github.com:amagovpt/udata-pt.git
      newdadosgov → git@github.com:adbrum/new-dadosgov.git
```

Each is an **independent git repository** with its own branches and remotes. Always `cd`
into the correct directory before running any git commands.

---

## Execution Flow

### Phase 1: Ticket Identification

**Ask the user:** "What is the ticket name or ID? (e.g. TICKET-05)"

Do not proceed until provided. Then:

1. **Search the ticket** in the project's local backlog:
   ```
   /home/adbrum/workspace/babel/new-dadosgov/docs/jira-tickets-frontend-backend.md
   ```
   Use `grep` or `Read` to find the ticket section by its ID (e.g. `## TICKET-05`).

2. **Read and parse** the full ticket:
   - **Descrição** (Description & context)
   - **Contexto Arquitetural** (Architectural context)
   - **O que deve ser feito** (What needs to be done — numbered list of implementation points)
   - **Critérios de Aceitação** (Acceptance criteria)

3. **Summarize your understanding** back to the user in a concise list. Confirm before proceeding.

> If the ticket ID is not found in the doc, inform the user and ask them to provide the
> description manually or check the ticket ID.

---

### Phase 2: Frontend or Backend?

**Ask the user:** "Is this ticket for the **frontend** or **backend**?"

- **Frontend** → work in `/home/adbrum/workspace/babel/new-dadosgov/frontend/`
  - Stack: Next.js, TypeScript
  - Tests: Playwright (`npm run test:e2e`)
  - Main files: `src/services/api.ts`, `src/types/api.ts`, `src/components/`, `src/app/`

- **Backend** → work in `/home/adbrum/workspace/babel/new-dadosgov/backend/`
  - Stack: udata / Flask / Python
  - Tests: pytest (`uv run pytest <path>`)
  - Follow existing udata module conventions

Set `REPO_DIR` to the chosen directory. All subsequent git commands run from `REPO_DIR`.

---

### Phase 3: Branch Creation

Create a new git branch from the latest `main` in the chosen repository:

```bash
cd <REPO_DIR>
git checkout main
git pull origin main
git checkout -b <branch-name>
```

**Branch naming rules:**
- **ALWAYS use English**, lowercase, with hyphens — even if the ticket title is in Portuguese
- Format: `<username>/<ticket-id>-<short-description>`
- Username to use: `adbrum`
- Example: `adbrum/ticket-05-dataset-search-api`
- **Translate** Portuguese ticket titles to English — never use non-English words in branch names
- Keep it concise but descriptive (max 5 words after the ticket ID)

**Propose the branch name to the user and confirm** before creating it.

After confirmation:
```bash
cd <REPO_DIR>
git checkout -b adbrum/<ticket-id>-<description>
```

---

### Phase 4: Commit Strategy Selection

**Ask the user:** "Do you want to commit automatically after each point, or do you want to manually review and approve each commit?"

- **Automatic**: The agent will `git add` and `git commit` automatically after implementing and testing each point.
- **Manual**: The agent will pause, show the `git status` or `git diff`, and **wait for your approval** before making the commit.

---

### Phase 5: Incremental Implementation

Go to the **"O que deve ser feito"** section of the ticket. Number each point.
For **each point**, follow this cycle:

```
For each implementation point:
  1. Read and understand the requirement
  2. Explore the relevant codebase area (read existing files first)
  3. Implement the change
  4. Run the relevant test (if applicable)
  5. If **Manual** strategy: show `git status`/diff and STOP for user approval.
  6. Commit with a clear English message
  7. Inform the user: "✅ Point N done. Starting point N+1..."
```

**Commit message format (ENGLISH ONLY):**
```
<type>: <concise description of what was done>

Refs: <TICKET-ID>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

Examples:
```bash
git add -A
git commit -m "feat: add fetchCsrfToken function to services/api.ts

Refs: TICKET-01"
```

```bash
git add -A
git commit -m "feat: implement login function with form-data POST

Refs: TICKET-01"
```

**Frontend testing guidelines:**
- Run Playwright: `npm run test:e2e` from `frontend/`
- For unit/integration tests specific to a file, run only that test

**Backend testing guidelines:**
- Run pytest: `uv run pytest <path-to-test-file>` from `backend/`
- Use `@pytest.mark.django_db` for database tests

**Between points:** Always tell the user:
> "✅ Completed point N: [brief description]. Starting point N+1: [brief description]..."

---

### Phase 6: Final Verification & Summary

After all points are complete:

1. **Run the full relevant test suite:**
   - Frontend: `cd frontend && npm run test:e2e`
   - Backend: `cd backend && uv run pytest`

2. **Validate Acceptance Criteria** — Go through **"Critérios de Aceitação"** one by one:
   - For each criterion, explain how it's satisfied (point to code or test)
   - Mark `[x]` if satisfied, `[ ]` if not

3. **Present a final summary** to the user:
   ```
   ## ✅ Ticket <TICKET-ID> — Implementation Summary

   **Branch:** adbrum/<ticket-id>-<description>
   **Repository:** frontend | backend

   ### Commits Made:
   1. feat: ...
   2. feat: ...
   3. ...

   ### Acceptance Criteria:
   - [x] Criterion 1 — satisfied by <function/file>
   - [x] Criterion 2 — satisfied by <test/code>
   - [ ] Criterion 3 — NOT satisfied: <reason>

   ### Next Steps:
   - Create a Pull Request to `main` on `origin`
   - Review and merge
   ```

---

## Important Rules

- **Respect the Commit Strategy.** If the user chose manual, you MUST wait for their approval before running `git commit`.
- **Never batch multiple ticket points into one commit.** One point = one commit.
  (Exception: if two points are genuinely inseparable, explain why they're combined.)
- **Always read before writing.** Read relevant existing code before making changes.
  Understand the patterns already in use and follow them.
- **Always work in the correct repository** (`frontend/` or `backend/`). Never mix.
- **Never use Portuguese in branch names or commit messages.** All git history must be in English.
- **If a point is ambiguous**, ask the user for clarification before implementing.
- **If tests fail**, fix the issue before moving to the next point.
- **Follow project conventions** — use `uv` for Python, `npm` for Node, follow the existing
  project structure and naming conventions.

---

## Quick Reference: Repo Git Commands

```bash
# Frontend
cd /home/adbrum/workspace/babel/new-dadosgov/frontend
git checkout main && git pull origin main
git checkout -b adbrum/ticket-XX-description
# ... implement & commit ...
git push origin adbrum/ticket-XX-description

# Backend
cd /home/adbrum/workspace/babel/new-dadosgov/backend
git checkout main && git pull origin main
git checkout -b adbrum/ticket-XX-description
# ... implement & commit ...
git push origin adbrum/ticket-XX-description
```

---

## Ticket Source File

All tickets are documented in:
```
/home/adbrum/workspace/babel/new-dadosgov/docs/jira-tickets-frontend-backend.md
```

Search using the ticket header format: `## TICKET-XX: <Title>`
