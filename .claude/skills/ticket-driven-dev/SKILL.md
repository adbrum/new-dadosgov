---
name: ticket-driven-dev
description: >
  Structured ticket-driven development workflow. Use this skill whenever the user provides a ticket ID/name
  (e.g., "ODB-5", a Linear ticket link, or says "work on ticket X"), wants to implement a feature or fix
  from a task tracker, or asks you to follow a structured dev workflow with branching, incremental
  implementation, testing, and acceptance criteria validation. Also trigger when the user says things like
  "pick up ticket", "start working on", "implement the task", or provides a Linear issue reference.
---

# Ticket-Driven Development Workflow

You are a Senior Software Engineer & Automation Agent. This skill defines a disciplined, incremental
development workflow that turns a ticket into a fully implemented, tested, and validated feature branch.

The core philosophy: **one concern at a time, always verified**. Each implementation point gets its own
tests and commit before moving on. This prevents large, hard-to-review changesets and catches issues early.

## Execution Flow

### Phase 1: Context Initialization

Ask the user for the **Ticket Name/ID**. Do not proceed until they provide it.

Once provided:

1. **Fetch the ticket** from Linear using `mcp__linear__get_issue` (or `mcp__linear__search_documentation`
   if only a name is given). If the ticket is not in Linear, ask the user to paste the ticket description.
2. **Read and understand** the full ticket:
   - Description and context
   - "What needs to be done" section (implementation points)
   - "Acceptance Criteria" section
   - Any linked documents, architectural notes, or referenced files
3. **Summarize your understanding** back to the user in a concise list. Confirm before proceeding.

### Phase 2: Branch Creation

Create a new git branch from the latest `main`:

```
git checkout main
git pull origin main
git checkout -b <branch-name>
```

**Branch naming rules:**
- **ALWAYS use English**, lowercase, with hyphens — even if the ticket title is in another language
- Format: `<username>/<ticket-id>-<short-description>`
- Example: `adrianoleal/odb-12-add-distribution-validation`
- **Translate** the ticket title/content to English to derive the description — never use non-English words in branch names
- Make it concise but descriptive

Confirm the branch name with the user before creating it.

### Phase 3: Incremental Implementation

Go to the "What needs to be done" section of the ticket. For **each point**, follow this cycle:

```
For each implementation point:
  1. Read and understand the requirement
  2. Explore the relevant codebase areas
  3. Implement the change
  4. Write tests (unit and/or integration as appropriate)
  5. Run the tests to confirm they pass
  6. Commit with a clear, descriptive message
```

**Commit message format:**
```
<type>: <concise description of what was done>

Refs: <ticket-id>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

**Testing guidelines for this project:**
- Backend: Use `pytest` with `@pytest.mark.django_db` for database tests. Run with `uv run pytest <path>`.
- Frontend: Use Playwright for E2E tests. Run with `npm run test:e2e` from the `frontend/` directory.
- Always run the specific tests for the code you just wrote before committing.

**Between points:** Briefly tell the user which point you just completed and which you're starting next.
This keeps them informed without requiring interaction at every step.

### Phase 4: Final Verification

After all implementation points are complete:

1. **Run the entire test suite:**
   ```bash
   cd backend && uv run pytest
   ```
   (And frontend tests if frontend changes were made)

2. **Validate Acceptance Criteria** — Go to the "Acceptance Criteria" section of the ticket and check
   each criterion one by one:
   - For each criterion, explain how it's satisfied (point to code, test, or run a verification)
   - Mark as `[x]` only if validation succeeds
   - Mark as `[ ]` if it fails, and explain what's missing

3. **Update the ticket in Linear** — Use `mcp__linear__save_issue` to update the ticket description,
   marking each acceptance criterion as `[x]` (done) or `[ ]` (not done) based on the validation results.
   This ensures the ticket always reflects the current implementation status.

4. **Present a summary** to the user:
   - List of commits made
   - Acceptance criteria checklist with pass/fail status
   - Any remaining issues or concerns
   - Suggest next steps (PR creation, additional review, etc.)

## Important Behaviors

- **Never skip tests.** Every implementation point needs at least one test proving it works.
- **Never batch multiple points into one commit.** One point = one commit (unless two points are genuinely
  inseparable, in which case explain why you're combining them).
- **If a point is ambiguous**, ask the user for clarification before implementing. Don't guess on
  requirements.
- **If tests fail**, fix the issue before moving to the next point. Don't accumulate broken state.
- **Read before writing.** Always read the relevant existing code before making changes. Understand
  the patterns already in use and follow them.
- **Follow project conventions** as defined in CLAUDE.md — use `uv` for Python, respect multi-tenancy
  patterns, follow the existing project structure.
