#!/usr/bin/env python3
"""PreToolUse/Bash guard for the dadosgov promotion flow.

Blocks two classes of git command:
  1. force-push anywhere (the flow promotes via PRs, never by rewriting history);
  2. any git write op targeting backend/ or frontend/ while that submodule sits on a
     long-lived environment branch (develop | tst | ppr | main).

The target repo is resolved from every source available, because an earlier version only
read the command text and so missed the most natural form of all: `cd backend` in one Bash
call (the working directory persists between calls) followed by a bare `git commit`. The
payload's `cwd` does track that shell, so it is now the default.

The monorepo itself is deliberately out of scope: this project commits submodule-pointer and
tooling changes straight onto its own main by choice.

Reads the hook payload on stdin, prints a deny decision on stdout, exits 0 always so a
parsing failure never blocks legitimate work.
"""

import json
import os
import re
import subprocess
import sys

from harness_root import harness_root  # local: sits beside this hook

PROTECTED = {"develop", "tst", "ppr", "main"}
SUBMODULES = ("backend", "frontend")
ROOT = harness_root()

# Tolerates any flags between `git` and the verb: `git -C x -c user.email=y commit`.
WRITE_OP = re.compile(
    r"\bgit\b[^|;&]*?\b(commit|push|merge|rebase|cherry-pick)\b|\bgit\b[^|;&]*?\breset\b[^|;&]*--hard"
)
FORCE_PUSH = re.compile(r"\bgit\b[^|;&]*\bpush\b[^|;&]*(--force\b|--force-with-lease\b|\s-f\b)")
DASH_C = re.compile(r"\bgit\s+(?:[^|;&]*?\s)?-C\s+(\S+)")
# Also matches inside a subshell: `(cd backend && git commit …)`.
CD_ANY = re.compile(r"(?:^|[;&|(]\s*)cd\s+([^\s&;|)]+)")


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


def run(args: list[str], cwd: str | None = None) -> str:
    try:
        return subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:
        return ""


def resolve(path: str, base: str) -> str | None:
    candidate = path if os.path.isabs(path) else os.path.join(base, path)
    try:
        return os.path.realpath(candidate)
    except Exception:
        return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    cmd = payload.get("tool_input", {}).get("command", "")
    cwd = payload.get("cwd") or ROOT
    if not cmd:
        return

    # Text inside a heredoc is data, not execution: writing a script or a test *about*
    # `git push --force` must not be mistaken for doing it. Found by this guard denying the
    # very file that tests it.
    heredoc = re.search(r"<<-?\s*'?\"?[A-Za-z_][A-Za-z0-9_]*", cmd)
    if heredoc:
        cmd = cmd[: heredoc.start()]
        if not cmd.strip():
            return

    if FORCE_PUSH.search(cmd):
        deny(
            "Force-push bloqueado (hook guard-protected-branch). O fluxo dadosgov promove "
            "develop -> tst -> ppr -> main por PR; reescrever historico partilhado quebra as "
            "branches de ambiente e as promocoes pendentes."
        )

    if not WRITE_OP.search(cmd):
        return

    # Every place the command could be acting on, not just the first one found.
    candidates = {resolve(cwd, ROOT)}
    for match in DASH_C.findall(cmd):
        candidates.add(resolve(match, cwd))
    for match in CD_ANY.findall(cmd):
        candidates.add(resolve(match, cwd))

    # A path inside a submodule counts as that submodule (git would walk up to it anyway).
    for sub in SUBMODULES:
        sub_path = os.path.realpath(os.path.join(ROOT, sub))
        for candidate in candidates:
            if not candidate:
                continue
            if candidate != sub_path and not candidate.startswith(sub_path + os.sep):
                continue
            branch = run(["git", "-C", sub_path, "branch", "--show-current"])
            if branch in PROTECTED:
                deny(
                    f"O submodulo {sub}/ esta na branch de ambiente '{branch}'. Nunca commitar, "
                    "push ou merge diretamente em develop|tst|ppr|main. Cria uma branch de "
                    "trabalho a partir de develop (feature/ | bugfix/ | chore/ | hotfix/) e "
                    "promove por PR.\n\n"
                    f"(alvo detetado a partir de: cwd={cwd})"
                )


if __name__ == "__main__":
    main()
