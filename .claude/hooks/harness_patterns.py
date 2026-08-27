#!/usr/bin/env python3
"""The three patterns more than one hook has to agree on.

They were duplicated, and a duplicated rule drifts: the commit shape enforced at commit
time would stop matching the one enforced at push time, or the frozen surface a fix-loop
defends would stop matching the one a plan is audited against. One definition, imported.
"""

import re

# Conventional Commits 1.0.0, the subset this project uses.
CONVENTIONAL = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?: \S"
)

# Never in this project's history, in any repo.
ATTRIBUTION = re.compile(r"(?i)co-authored-by\s*:|generated with [^\n]{0,30}claude|\U0001F916")

# The test surface: the tests themselves and everything that decides which tests run.
# Narrowing the runner's selection removes failures just as effectively as deleting an
# assertion, so the runner config is frozen alongside the tests.
FROZEN = re.compile(
    r"("
    r"/tests?/|/__tests__/|(^|[\s/=\"'])test_[^/\s]*\.py|(^|[\s/=\"'])conftest\.py"
    r"|\.spec\.(ts|tsx|js)\b|\.test\.(ts|tsx|js|py)\b"
    r"|(^|[\s/=\"'])vitest\.config\.[cm]?ts|(^|[\s/=\"'])playwright\.config\.[cm]?ts"
    r"|(^|[\s/=\"'])jest\.config|(^|[\s/=\"'])pyproject\.toml|(^|[\s/=\"'])pytest\.ini"
    r"|(^|[\s/=\"'])setup\.cfg|(^|[\s/=\"'])tox\.ini|(^|[\s/=\"'])coverage\.rc"
    r"|(^|[\s/=\"'])factories\.py"
    r")"
)

# The same list, anchored for git path names instead of shell text: `git diff --name-only`
# yields `udata/tests/test_x.py`, never a quoted fragment. Two shapes, one inventory --
# add an entry to both or the write-time guard and the verify-time check stop agreeing.
FROZEN_PATH = re.compile(
    r"("
    r"/tests?/|/__tests__/|(^|/)test_[^/]*\.py|(^|/)conftest\.py"
    r"|\.spec\.(ts|tsx|js)|\.test\.(ts|tsx|js|py)"
    r"|(^|/)vitest\.config\.[cm]?ts|(^|/)playwright\.config\.[cm]?ts|(^|/)jest\.config"
    r"|(^|/)pyproject\.toml|(^|/)pytest\.ini|(^|/)setup\.cfg|(^|/)tox\.ini|(^|/)coverage\.rc"
    r"|(^|/)factories\.py"
    r")"
)
