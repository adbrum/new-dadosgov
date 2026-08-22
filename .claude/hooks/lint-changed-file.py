#!/usr/bin/env python3
"""PostToolUse/Write|Edit: lint and format the file that was just written.

backend/*.py   -> uv run ruff check --fix + ruff format   (~0.5s)
frontend/*.ts(x)|*.js(x) -> npx eslint --fix              (~3s)

Anything else is ignored. Remaining problems are fed back to the model as
additionalContext so they get fixed in the same turn instead of surfacing in CI.
Always exits 0 — a broken linter must not block the edit.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


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

    backend = os.path.realpath(os.path.join(ROOT, "backend"))
    frontend = os.path.realpath(os.path.join(ROOT, "frontend"))

    if path.startswith(backend + os.sep) and path.endswith(".py"):
        rel = os.path.relpath(path, backend)
        for cmd in (
            ["uv", "run", "ruff", "check", "--fix", rel],
            ["uv", "run", "ruff", "format", rel],
        ):
            code, out = run(cmd, backend)
            if code != 0 and out:
                problems.append(f"$ {' '.join(cmd)}\n{out}")

    elif path.startswith(frontend + os.sep) and path.endswith(
        (".ts", ".tsx", ".js", ".jsx", ".mjs")
    ):
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
