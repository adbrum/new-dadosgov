#!/usr/bin/env python3
"""PreToolUse/Bash guard for the dadosgov promotion flow.

Blocks two classes of git command:
  1. force-push anywhere (the flow promotes via PRs, never by rewriting history);
  2. any git write op targeting backend/ or frontend/ while that submodule sits on a
     long-lived environment branch (develop | tst | ppr | main).

Reads the hook payload on stdin, prints a deny decision on stdout, exits 0 always so a
parsing failure never blocks legitimate work.
"""

import json
import os
import re
import subprocess
import sys

PROTECTED = {"develop", "tst", "ppr", "main"}
SUBMODULES = ("backend", "frontend")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

WRITE_OP = re.compile(
    r"git(?:\s+-C\s+\S+)?\s+(commit|push|merge|rebase|cherry-pick|reset\s+--hard)"
)
FORCE_PUSH = re.compile(r"git[^|;&]*push[^|;&]*(--force(?!-with-lease)\b|--force-with-lease|\s-f\b)")
DASH_C = re.compile(r"git\s+-C\s+(\S+)")
LEADING_CD = re.compile(r"^\s*cd\s+([^\s&;|]+)")


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


def current_branch(path: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", path, "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except Exception:
        return ""


def main() -> None:
    try:
        cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    except Exception:
        return
    if not cmd:
        return

    if FORCE_PUSH.search(cmd):
        deny(
            "Force-push bloqueado (hook guard-protected-branch). O fluxo dadosgov promove "
            "develop -> tst -> ppr -> main por PR; reescrever historico partilhado quebra as "
            "branches de ambiente e as promocoes pendentes."
        )

    if not WRITE_OP.search(cmd):
        return

    m = DASH_C.search(cmd) or LEADING_CD.match(cmd)
    target = m.group(1) if m else "."
    abs_target = target if os.path.isabs(target) else os.path.join(ROOT, target)
    abs_target = os.path.realpath(abs_target)

    for sub in SUBMODULES:
        if abs_target != os.path.realpath(os.path.join(ROOT, sub)):
            continue
        branch = current_branch(abs_target)
        if branch in PROTECTED:
            deny(
                f"O submodulo {sub}/ esta na branch de ambiente '{branch}'. Nunca commitar, "
                "push ou merge diretamente em develop|tst|ppr|main. Cria uma branch de trabalho "
                "a partir de develop (feature/ | bugfix/ | chore/ | hotfix/) e promove por PR."
            )


if __name__ == "__main__":
    main()
