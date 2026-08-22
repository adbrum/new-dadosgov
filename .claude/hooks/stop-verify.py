#!/usr/bin/env python3
"""Stop: before the turn ends, state what is uncommitted and what still needs verifying.

Deliberately cheap and non-blocking — it does NOT run the test suites (pytest on udata
takes minutes). It reports which suite is owed for the files actually touched, so the
verification step is never silently skipped.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SUITES = {
    "backend": ("*.py", "cd backend && uv run pytest <caminho-do-teste>"),
    "frontend": ("*.ts/.tsx", "cd frontend && npm run lint && npm test"),
}


def sh(cmd: list[str], cwd: str) -> str:
    try:
        return subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=15
        ).stdout.strip()
    except Exception:
        return ""


def main() -> None:
    notes = []
    for sub in ("backend", "frontend"):
        path = os.path.join(ROOT, sub)
        if not os.path.isdir(path):
            continue
        changed = [
            line[3:] for line in sh(["git", "status", "--porcelain"], path).splitlines() if line.strip()
        ]
        if not changed:
            continue
        exts = (".py",) if sub == "backend" else (".ts", ".tsx", ".js", ".jsx")
        code_files = [f for f in changed if f.endswith(exts)]
        if not code_files:
            continue
        branch = sh(["git", "branch", "--show-current"], path)
        notes.append(
            f"{sub}/ (branch '{branch}'): {len(code_files)} ficheiro(s) de codigo alterado(s) "
            f"e nao commitado(s) -> falta correr `{SUITES[sub][1]}`"
        )

    lock = os.path.join(ROOT, ".claude", "state", "fix-loop.lock")
    if os.path.exists(lock):
        notes.append(
            "um fix-loop continua ATIVO: a superficie de teste fica congelada para a proxima "
            "sessao -> `python3 .claude/hooks/fix-loop-state.py end`"
        )

    if notes:
        json.dump({"systemMessage": "Verificacao em falta:\n- " + "\n- ".join(notes)}, sys.stdout)


if __name__ == "__main__":
    main()
