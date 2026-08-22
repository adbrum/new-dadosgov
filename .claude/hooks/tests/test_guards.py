#!/usr/bin/env python3
"""Regression tests for the harness guards — one case per code-review finding.

Run: python3 .claude/hooks/tests/test_guards.py

Each case is a real hook payload piped into the real hook, asserting DENY or PASS. The
numbered cases are bypasses an independent review found in the first implementation; they
exist so those specific holes cannot reopen silently.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HOOKS = os.path.join(ROOT, ".claude", "hooks")
LOCK = os.path.join(ROOT, ".claude", "state", "fix-loop.lock")
BRANCH_GUARD = "guard-protected-branch.py"
SURFACE_GUARD = "guard-test-surface.py"


def call(hook: str, payload: dict) -> str:
    p = subprocess.run(
        ["python3", os.path.join(HOOKS, hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return "DENY" if p.stdout.strip() else "PASS"


def current_branch(path: str) -> str:
    return subprocess.run(
        ["git", "-C", path, "branch", "--show-current"], capture_output=True, text=True
    ).stdout.strip()


def bash(cmd: str, cwd: str = ROOT) -> dict:
    return {"tool_name": "Bash", "cwd": cwd, "tool_input": {"command": cmd}}


def edit(path: str, cwd: str = ROOT) -> dict:
    return {"tool_name": "Edit", "cwd": cwd, "tool_input": {"file_path": path}}


BE, FE = os.path.join(ROOT, "backend"), os.path.join(ROOT, "frontend")

BRANCH_CASES = [
    # The target used to be guessed from the command text alone, so the most natural form of
    # all slipped through: `cd backend` in one call, `git commit` in the next.
    ("#8a  bare git commit with cwd=backend", bash("git commit -am x", BE), "DENY"),
    ("#8b  (cd backend && git commit)", bash("(cd backend && git commit -m x)"), "DENY"),
    ("#8c  git -C backend -c user.email=x commit", bash("git -C backend -c user.email=x commit -m y"), "DENY"),
    ("#8d  git add -A && git commit, cwd=backend", bash("git add -A && git commit -m x", BE), "DENY"),
    ("     git commit in the monorepo (allowed by choice)", bash("git commit -m x", ROOT), "PASS"),
    ("     git status in backend", bash("git status", BE), "PASS"),
    ("     force-push", bash("git push --force"), "DENY"),
    ("     force-push, wrapped", bash("bash -lc 'git push -f'"), "DENY"),
    # Found while writing this file: the guard denied a heredoc that merely mentions the
    # pattern, i.e. this test file itself.
    ("     heredoc that only mentions force-push is data", bash("cat > t.py <<'EOF'\ngit push --force\nEOF"), "PASS"),
]

SURFACE_CASES = [
    ("#6   sed -i on a .test.ts mid-command", bash("sed -i s/a/b/ src/lib/foo.test.ts && npx vitest run", FE), "DENY"),
    ("#6b  mv of a .test.ts", bash("mv src/lib/foo.test.ts src/lib/foo.test.ts.bak", FE), "DENY"),
    ("#7   sed -i on a submodule-relative path", bash("sed -i 's/assert x/assert True/' udata/tests/test_utils.py", BE), "DENY"),
    ("#5   Edit on vitest.config.ts", edit(os.path.join(FE, "vitest.config.ts")), "DENY"),
    ("#5b  Edit on pyproject.toml", edit(os.path.join(BE, "pyproject.toml")), "DENY"),
    ("#5c  Edit on conftest.py", edit(os.path.join(BE, "conftest.py")), "DENY"),
    ("#12  pytest <test> | tee /tmp/log is read-only", bash("uv run pytest udata/tests/test_x.py 2>&1 | tee /tmp/log", BE), "PASS"),
    ("#12b vitest <test> > /tmp/out is read-only", bash("npx vitest run src/x.test.ts > /tmp/out", FE), "PASS"),
    ("#12c grep in a test > /tmp/o is read-only", bash("grep -n assert udata/tests/test_x.py > /tmp/o", BE), "PASS"),
    ("     Edit on source", edit(os.path.join(FE, "src/components/X.tsx")), "PASS"),
    ("     running the suite", bash("npx vitest run", FE), "PASS"),
    ("     redirect INTO a test file is a write", bash("echo x > src/lib/foo.test.ts", FE), "DENY"),
]


def run_group(title: str, hook: str, cases: list, with_lock: bool) -> int:
    if with_lock:
        os.makedirs(os.path.dirname(LOCK), exist_ok=True)
        with open(LOCK, "w") as fh:
            json.dump({"repo": "frontend", "attempts": 0}, fh)
    elif os.path.exists(LOCK):
        os.remove(LOCK)

    print(f"\n--- {title} ---")
    failures = 0
    for label, payload, expected in cases:
        # A branch-dependent DENY is only expected while that submodule sits on an
        # environment branch; on a working branch the correct answer is PASS.
        if hook == BRANCH_GUARD and expected == "DENY" and "force-push" not in label:
            sub = BE if "backend" in label or payload.get("cwd") == BE else FE
            branch = current_branch(sub)
            if branch not in {"develop", "tst", "ppr", "main"}:
                print(f"  skip  {label:52} ({os.path.basename(sub)} esta em '{branch}')")
                continue
        got = call(hook, payload)
        ok = got == expected
        failures += 0 if ok else 1
        print(f"  {'ok   ' if ok else 'FALHA'} {label:52} esperado={expected} obtido={got}")
    return failures


def main() -> int:
    had_lock = os.path.exists(LOCK)
    failures = run_group("guard-protected-branch", BRANCH_GUARD, BRANCH_CASES, with_lock=False)
    failures += run_group("guard-test-surface (lock held)", SURFACE_GUARD, SURFACE_CASES, with_lock=True)

    if os.path.exists(LOCK) and not had_lock:
        os.remove(LOCK)

    print()
    if failures:
        print(f"{failures} CASO(S) A FALHAR")
        return 1
    print(f"TODOS OS {len(BRANCH_CASES) + len(SURFACE_CASES)} CASOS PASSAM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
