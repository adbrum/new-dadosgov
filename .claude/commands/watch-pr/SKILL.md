---
name: watch-pr
description: One iteration of PR babysitting — check CI, report, and decide whether the loop should continue or stop. Designed to be run under /loop.
---

Arguments: $ARGUMENTS — `<backend|frontend> <pr-number>`, or nothing to pick up every open PR
authored by the current user in both repos.

This command is **one tick of a loop**. Do exactly one pass and then decide:

1. `gh pr checks <n> --repo amagovpt/<repo>` for each PR in scope.
2. Classify each PR:
   - **a correr** → nothing to report. Reply in one line and schedule the next tick as a noop.
   - **verde e aprovado** → report that it is ready to merge. Do **not** merge; merging is the user's call.
   - **verde, sem review** → report that it is waiting on review.
   - **vermelha** → run `gh run view <run-id> --repo <repo> --log-failed`, summarize the real failing assertion, and say whether it looks like a code problem or infrastructure flake.
     - By default **do not push a fix** — report and let the user decide.
     - Only when the user passed `--autofix`: route the repair through `/fix-loop <repo>`, which freezes the test surface and requires a proven red-to-green transition. Never fix a red CI by editing the failing test, and never push more than the cap allows. If `/fix-loop` ends REPROVADO, report that and stop the loop — do not keep iterating.
   - **conflitos** → name the conflicting files. `CHANGELOG.md` conflicts in `## Unreleased` are expected: keep both entries, newest first.
3. **Stop the loop** (`ScheduleWakeup stop`) when every PR in scope is merged, closed, or reported red — there is nothing left to poll.
4. Otherwise pick the next delay from what you are actually waiting for: a CI run that takes ~8 minutes deserves one ~480s check, not eight 60s ones.

Never fabricate a check result. If `gh` fails, say so and retry on the next tick.
