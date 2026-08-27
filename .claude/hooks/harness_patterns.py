#!/usr/bin/env python3
"""The patterns and git range helpers more than one hook has to agree on.

They were duplicated, and a duplicated rule drifts: the commit shape enforced at commit
time would stop matching the one enforced at push time, or the frozen surface a fix-loop
defends would stop matching the one a plan is audited against. One definition, imported.

The git helpers take a `run(cmd, cwd) -> (rc, out)` callable instead of shelling out
themselves, because each hook already has its own runner with its own timeout policy.
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


# The long-lived environment branches, closest-first resolution of "where was this cut from".
ENV_BRANCHES = ("develop", "tst", "ppr", "main")

# Paths that cannot change the outcome of any test. A commit touching only these keeps a
# recorded green alive.
#
# Pinning the green to an exact sha instead made the two things the flow *requires* before a
# push -- the CHANGELOG entry and the review's fix -- each cost a full suite: the state log
# shows three to six full runs per ticket, all of them re-proving the same code. Note what is
# NOT here: `.github/workflows/**` decides what CI runs, so it is source, not documentation.
INERT_PATH = re.compile(
    r"^(CHANGELOG|README|CONTRIBUTING|AUTHORS|LICENSE|NOTICE|CLAUDE)[^/]*$"
    r"|^docs?/"
    r"|(^|/)CHANGELOG(\.[A-Za-z0-9_-]+)?\.(md|rst|txt)$"
    r"|^\.github/(?!workflows/)"
)


def non_inert(paths) -> list:
    """The changed paths that could plausibly change a test outcome."""
    return [p for p in (str(p).strip() for p in paths) if p and not INERT_PATH.search(p)]


def range_base(run, cwd):
    """The environment branch this work was cut from -- the closest one, not always develop."""
    best, best_len = None, None
    for env in ENV_BRANCHES:
        rc, base = run(["git", "merge-base", "HEAD", f"origin/{env}"], cwd)
        base = base.strip()
        if rc != 0 or not base:
            continue
        rc, count = run(["git", "rev-list", "--count", f"{base}..HEAD"], cwd)
        if rc != 0 or not count.strip().isdigit():
            continue
        n = int(count.strip())
        if best_len is None or n < best_len:
            best, best_len = base, n
    return best


def changed_paths(run, cwd, since, until="HEAD"):
    """Paths changed between two revisions, or None when git could not answer.

    None and [] are different answers and callers must not conflate them: "I do not know
    what changed" can never be treated as "nothing changed".
    """
    rc, out = run(["git", "diff", "--name-only", f"{since}..{until}"], cwd)
    if rc != 0:
        return None
    return [line.strip() for line in out.splitlines() if line.strip()]


def source_drift(run, cwd, since, until="HEAD"):
    """Non-inert paths changed since `since`, or None when git could not answer."""
    paths = changed_paths(run, cwd, since, until)
    return None if paths is None else non_inert(paths)
