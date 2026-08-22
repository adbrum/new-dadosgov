#!/usr/bin/env python3
"""PreToolUse guard: freeze the test surface while a fix loop is running.

A loop told to "make the tests pass" has a degenerate solution: change the tests. This
removes the ability rather than asking for restraint — while .claude/state/fix-loop.lock
exists, no write may land on a test file or on the runner configuration that decides what
gets tested.

Inert when there is no lock, so ordinary work (where editing tests is expected) is untouched.

Covers both write paths:
  * Edit / Write / NotebookEdit -> the tool's file_path
  * Bash                        -> a command that names the frozen surface AND writes to it

Paths are matched without requiring a repo prefix or an end anchor, because a Bash command
mentions paths mid-string and may be issued from inside a submodule.

Exits 0 always; prints a deny decision when it applies. Fails closed on an unreadable payload
while the lock is held.
"""

import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOCK = os.path.join(ROOT, ".claude", "state", "fix-loop.lock")

# Kept deliberately in step with FROZEN in fix-loop-state.py: the write-time guard and the
# verify-time git check must agree on what "the test surface" means.
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

# Verbs that mutate a file in place. Redirections are handled separately, because
# `pytest tests/x.py > /tmp/log` writes to /tmp, not to the test.
MUTATORS = re.compile(
    r"(\bsed\b[^|;&]*-i|\btee\b\s+(?!/tmp/|/dev/null)|\brm\b|\bmv\b|\bcp\b|\btruncate\b"
    r"|\bpython3?\b[^|;&]*<<|\bcat\b[^|;&]*<<|\bgit\s+(checkout|restore|rm|apply|stash)\b"
    r"|\bpatch\b|\bdd\b)"
)
# A redirect only matters when its target is itself inside the frozen surface.
REDIRECT_TARGET = re.compile(r">>?\s*([^\s;|&]+)")


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


def frozen_hit(text: str) -> str | None:
    normalized = text.replace(ROOT + os.sep, "").replace("\\", "/")
    match = FROZEN.search(normalized)
    return match.group(0).strip("\"' \t") if match else None


def bash_writes_to_frozen(command: str) -> str | None:
    """Return the offending fragment when the command writes to the frozen surface."""
    for target in REDIRECT_TARGET.findall(command):
        hit = frozen_hit(target)
        if hit:
            return f"redireciona para {target}"
    if MUTATORS.search(command):
        hit = frozen_hit(command)
        if hit:
            return f"operacao de escrita sobre {hit}"
    return None


def main() -> None:
    if not os.path.exists(LOCK):
        return

    try:
        payload = json.load(sys.stdin)
    except Exception:
        # Fail closed: while a loop holds the lock, an unreadable payload must not become a
        # silent way past the freeze.
        deny(
            "Payload do hook ilegivel e um fix-loop esta ativo, portanto a escrita e negada por "
            "precaucao. Se for falso positivo, termina o loop: "
            "python3 .claude/hooks/fix-loop-state.py end"
        )
        return

    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    state = {}
    try:
        with open(LOCK) as fh:
            state = json.load(fh)
    except Exception:
        pass

    tail = (
        f"\n\nUm fix-loop esta ativo (repo: {state.get('repo', '?')}). Ficheiros de teste E "
        "configuracao do runner estao congelados: o loop corrige codigo-fonte, nunca a "
        "expectativa nem o que e selecionado para correr. Se o teste e que esta errado, PARA e "
        "reporta ao utilizador com a justificacao — essa decisao nao e do loop. "
        "Correr os testes e ler ficheiros continua permitido."
    )

    if tool in ("Edit", "Write", "NotebookEdit"):
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        hit = frozen_hit(path)
        if hit:
            deny(f"Escrita bloqueada em '{path}' (superficie congelada: {hit})." + tail)
        return

    if tool == "Bash":
        command = tool_input.get("command", "")
        offence = bash_writes_to_frozen(command)
        if offence:
            deny(f"Comando bloqueado: {offence}." + tail)


if __name__ == "__main__":
    main()
