---
name: ci
description: Check and summarize CI status for a PR (or the current branch's PR) in either dadosgov repo
---

Arguments: $ARGUMENTS — a PR number, a repo name, both, or nothing.

1. Resolve the repo: `backend` → `amagovpt/udata-pt`, `frontend` → `amagovpt/dadosgov-fe`. If not given, infer from which submodule has the current working branch.
2. Resolve the PR: the given number, else `gh pr list --repo <repo> --head $(git -C <dir> branch --show-current)`.
3. `gh pr checks <n> --repo <repo>`
4. For each failing check: `gh run view <run-id> --repo <repo> --log-failed` and summarize the **actual failing step and assertion** — not just "tests failed".
5. State clearly whether the PR is mergeable, and what would have to change. Do not fix code unless asked.
