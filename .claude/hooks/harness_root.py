#!/usr/bin/env python3
"""Which checkout's `.claude/` owns this run — resolved the same way by every hook.

Every hook used to compute its own `ROOT` from `__file__`, and `os.path.abspath`
normalises *lexically*: the answer was whatever string was used to invoke the script.
`.claude/settings.json` invokes the hooks as `"${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/X.py"`
while the skill invokes the CLI as `.claude/hooks/ticket-state.py` from the session's cwd —
two sources of truth that nothing forced to agree.

That mattered because of *how* they fail when they disagree. A guard pointed at the wrong
state directory does not error: it finds no active ticket and no fix-loop lock, which reads
exactly like "there is nothing to enforce". The gates go inert in silence, which is the one
failure mode this harness cannot afford.

Order: `CLAUDE_HARNESS_ROOT` (explicit; how the test suite runs against a throwaway tree),
then `CLAUDE_PROJECT_DIR` (what Claude Code exports to hook processes), then the directory
this file sits in. An environment candidate is only believed when it really holds a
`.claude/hooks` — a stale variable must not silently move the state directory.
"""

import os

ENV_VARS = ("CLAUDE_HARNESS_ROOT", "CLAUDE_PROJECT_DIR")
FILE_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)


def is_harness(path) -> bool:
    return bool(path) and os.path.isdir(os.path.join(path, ".claude", "hooks"))


def candidates() -> list:
    """Every source, in precedence order, for `doctor` to print and compare."""
    found = [(var, os.environ.get(var)) for var in ENV_VARS]
    return found + [("__file__", FILE_ROOT)]


def harness_root() -> str:
    for _, value in candidates():
        if is_harness(value):
            return os.path.abspath(value)
    return FILE_ROOT


def state_dir() -> str:
    return os.path.join(harness_root(), ".claude", "state")
