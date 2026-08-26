#!/usr/bin/env python3
"""PostToolUse/Write|Edit: lint and format the file that was just written.

backend/*.py   -> uv run ruff check --fix + ruff format   (~0.5s)
frontend/*.ts(x)|*.js(x) -> npx eslint --fix              (~3s)

Anything else is ignored. Remaining problems are fed back to the model as
additionalContext so they get fixed in the same turn instead of surfacing in CI.
Always exits 0 — a broken linter must not block the edit.
"""

import glob
import json
import os
import subprocess
import sys

from harness_root import harness_root  # local: sits beside this hook

ROOT = harness_root()


def emit(context: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": context,
            }
        },
        sys.stdout,
    )


def run(cmd: list[str], cwd: str) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 0, ""
    except FileNotFoundError:
        return 0, ""


def tree_for(path: str, repo: str):
    """The checkout of `repo` that holds this file: a ticket's worktree, or the primary one.

    Without this the hook simply did not fire for a file inside a per-ticket worktree --
    no lint, no feedback, and silence looks exactly like "nothing to report".
    """
    trees = [os.path.realpath(os.path.join(ROOT, repo))]
    for state_file in glob.glob(os.path.join(ROOT, ".claude", "state", "ticket-*.json")):
        try:
            with open(state_file) as fh:
                workdir = json.load(fh).get("workdir")
        except Exception:
            continue
        if workdir:
            trees.append(os.path.realpath(os.path.join(workdir, repo)))
    # longest first: a worktree may live under the primary checkout
    for tree in sorted(set(trees), key=len, reverse=True):
        if path.startswith(tree + os.sep):
            return tree
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    path = payload.get("tool_input", {}).get("file_path") or payload.get(
        "tool_response", {}
    ).get("filePath")
    if not path:
        return
    path = os.path.realpath(path)
    if not os.path.isfile(path):
        return

    problems: list[str] = []

    backend = tree_for(path, "backend")
    frontend = tree_for(path, "frontend")

    if backend and path.endswith(".py"):
        rel = os.path.relpath(path, backend)
        for cmd in (
            ["uv", "run", "ruff", "check", "--fix", rel],
            ["uv", "run", "ruff", "format", rel],
        ):
            code, out = run(cmd, backend)
            if code != 0 and out:
                problems.append(f"$ {' '.join(cmd)}\n{out}")

    elif frontend and path.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs")):
        rel = os.path.relpath(path, frontend)
        code, out = run(["npx", "eslint", "--fix", rel], frontend)
        if code != 0 and out:
            problems.append(f"$ npx eslint --fix {rel}\n{out}")

    if problems:
        emit(
            "Lint automatico (hook lint-changed-file) deixou problemas nao corrigiveis "
            "automaticamente. Corrige-os agora, antes de continuar:\n\n"
            + "\n\n".join(problems)
        )


if __name__ == "__main__":
    main()
