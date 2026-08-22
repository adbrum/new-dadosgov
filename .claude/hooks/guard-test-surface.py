#!/usr/bin/env python3
"""PreToolUse guard: freeze the test surface while a fix loop is running.

A loop told to "make the tests pass" has a degenerate solution: change the tests.
This removes the ability rather than asking for restraint — while
.claude/state/fix-loop.lock exists, no write may land on a test file.

Inert when there is no lock, so normal work (where editing tests is expected) is
untouched. Covers both write paths:
  * Edit / Write     -> the tool's file_path
  * Bash             -> a command that both names a test path and looks like a write

Exits 0 always; prints a deny decision when it applies.
"""

import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOCK = os.path.join(ROOT, ".claude", "state", "fix-loop.lock")

# Test surfaces of both submodules.
TEST_PATTERNS = [
    re.compile(r"backend/udata/.*/tests?/"),
    re.compile(r"backend/.*/test_[^/]*\.py"),
    re.compile(r"backend/udata/tests/"),
    re.compile(r"frontend/src/.*/__tests__/"),
    re.compile(r"frontend/tests/"),
    re.compile(r"[^/]*\.spec\.(ts|tsx|js)$"),
    re.compile(r"[^/]*\.test\.(ts|tsx|js|py)$"),
]

# Bash verbs that can mutate a file. `python3 -` / heredocs are included because
# that is how files get rewritten in this project.
WRITE_INDICATORS = re.compile(
    r"(\bsed\b[^|;&]*-i|\btee\b|>\s*\S|>>\s*\S|\brm\b|\bmv\b|\bcp\b|\btruncate\b"
    r"|\bpython3?\b[^|;&]*<<|\bgit\s+(checkout|restore|rm|apply)\b|\bpatch\b)"
)


def deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def is_test_path(text: str) -> str | None:
    normalized = text.replace(ROOT + os.sep, "").replace("\\", "/")
    for pattern in TEST_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return match.group(0)
    return None


def main() -> None:
    if not os.path.exists(LOCK):
        return

    try:
        payload = json.load(sys.stdin)
    except Exception:
        # Fail closed: while a loop holds the lock, an unreadable payload must not
        # become a silent way past the freeze.
        deny(
            "Payload do hook ilegivel e um fix-loop esta ativo, portanto a escrita e negada por "
            "precaucao. Termina o loop se isto for um falso positivo: "
            "python3 .claude/hooks/fix-loop-state.py end"
        )
        return

    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    try:
        with open(LOCK) as fh:
            state = json.load(fh)
    except Exception:
        state = {}
    scope = state.get("repo", "?")

    reason_tail = (
        f"\n\nUm fix-loop esta ativo (repo: {scope}). Os ficheiros de teste estao congelados: "
        "o loop tem de corrigir codigo-fonte, nunca a expectativa. Se o teste e que esta errado, "
        "PARA e reporta ao utilizador com a justificacao — essa decisao nao e do loop. "
        "Para terminar o loop: python3 .claude/hooks/fix-loop-state.py end"
    )

    if tool in ("Edit", "Write", "NotebookEdit"):
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        hit = is_test_path(path)
        if hit:
            deny(f"Escrita bloqueada em '{path}' (superficie de teste: {hit})." + reason_tail)
        return

    if tool == "Bash":
        command = tool_input.get("command", "")
        hit = is_test_path(command)
        if hit and WRITE_INDICATORS.search(command):
            deny(
                f"Comando bloqueado: nomeia a superficie de teste ({hit}) e contem uma operacao "
                "de escrita." + reason_tail
            )


if __name__ == "__main__":
    main()
