---
name: fix-loop
description: Run a guarded fix loop — freeze the test surface, prove a red-to-green transition on a test identified beforehand, and stop with a diagnosis rather than weakening the suite
---

Arguments: $ARGUMENTS — `<backend|frontend> [caminho/do/teste ...]`. Ask if the repo is missing.

A loop told to make tests pass has a degenerate solution: change the tests. This command
removes the ability instead of asking for restraint. **Follow it literally — the value is in
the order.**

## The protocol

1. **`python3 .claude/hooks/fix-loop-state.py start <repo> [scope...]`**

   Captures the baseline *before* any source change: which tests fail (by identity), how many
   tests exist, the exact commit. Then takes the lock that freezes every test file.

   If it refuses because nothing fails, that is the correct answer: **write the failing test
   first**, outside the loop, where test files are still editable. A loop with no red test
   cannot prove anything — any change would look green.

2. **Fix source only.** The `PreToolUse` guard denies writes — via Edit, Write and Bash — to
   test files *and* to the runner configuration (`vitest.config.ts`, `pyproject.toml`,
   `conftest.py`, `factories.py`, …), because narrowing what runs removes failures just as
   effectively as deleting an assertion. If you conclude the *test* is wrong, that is a legitimate
   finding but **not your call**: stop and report it to the user with the reasoning.

3. **`... verify`**. Each call consumes one of the four attempts and refuses past the cap.
   It enforces, and prints a verdict:
   - **the suite exits 0** — the runner's exit code is the authority, never a parsed summary
   - no test file or runner config touched since the baseline commit (asked of git, so it
     catches writes made outside the hook too; a git failure aborts rather than passing)
   - no weakening markers inside the frozen surface (`.skip`, `.only`, `xfail`, `--ignore`, …)
   - the collected-test count did not drop and the skipped count did not rise

4. **`... end`** to release the lock. Never leave a session with the lock held — it blocks
   legitimate test editing for whoever comes next. If `status` shows a stale lock, end it.

## When verify says REPROVADO

Read the problems and fix the *source*. If the attempts run out, **stop and write the
diagnosis**: what you tried, what the failure actually says, and your hypothesis. A written
"I could not fix this" is a legitimate final answer and the whole reason the cap exists —
insisting past it is how a loop degenerates into weakening the suite.

## What this does and does not guarantee

It guarantees the test was not adulterated: the suite that was red is green, with the test
files and the runner configuration untouched. Two things it does **not** guarantee. First,
this process can release its own lock (`end`) — cheating is visible and effortful, not
impossible, which is why releases are logged and why the real authority is the CI job that
compares test counts against the base branch. Second, it does not guarantee the source fix is
good — a loop can satisfy a correct
test with bad code (a hardcoded return, a swallowed exception, a widened type). Say so when
reporting, and leave the PR review in place: that is where this class of problem is caught.
