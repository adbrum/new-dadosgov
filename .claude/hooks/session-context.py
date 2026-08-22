#!/usr/bin/env python3
"""SessionStart: inject the real git state of both submodules into context.

The monorepo aggregates two independent repos with their own environment branches, so
"which branch am I on, and in which repo" is the single most common wrong assumption.
This states it up front instead of letting the model infer it.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPOS = {"backend": "amagovpt/udata-pt", "frontend": "amagovpt/dadosgov-fe"}
PROTECTED = {"develop", "tst", "ppr", "main"}


def sh(cmd: list[str], cwd: str, timeout: int = 15) -> str:
    try:
        return subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        ).stdout.strip()
    except Exception:
        return ""


def main() -> None:
    lines = ["Estado git do monorepo dadosgov (hook session-context):"]
    for sub, repo in REPOS.items():
        path = os.path.join(ROOT, sub)
        if not os.path.isdir(path):
            continue
        branch = sh(["git", "branch", "--show-current"], path) or "(detached)"
        dirty = sh(["git", "status", "--porcelain"], path)
        n = len([x for x in dirty.splitlines() if x.strip()])
        flag = "  <- branch de ambiente: NAO commitar aqui" if branch in PROTECTED else ""
        lines.append(f"- {sub}/ ({repo}): branch '{branch}', {n} ficheiro(s) modificado(s){flag}")
        prs = sh(
            [
                "gh", "pr", "list", "--repo", repo, "--state", "open",
                "--limit", "10", "--json", "number,title,baseRefName,headRefName",
            ],
            path,
            timeout=25,
        )
        try:
            for pr in json.loads(prs or "[]"):
                lines.append(
                    f"    PR #{pr['number']} {pr['headRefName']} -> {pr['baseRefName']}: {pr['title']}"
                )
        except Exception:
            pass

    lines.append(
        "Fluxo: branch a partir de develop -> PR para develop -> tst -> ppr -> main, "
        "so no(s) repo(s) efetivamente alterado(s)."
    )
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "\n".join(lines),
            },
            "suppressOutput": True,
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
