#!/usr/bin/env python3
"""SessionStart: inject the real git state of both submodules into context.

The monorepo aggregates two independent repos with their own environment branches, so
"which branch am I on, and in which repo" is the single most common wrong assumption.
This states it up front instead of letting the model infer it.
"""

import glob
import json
import os
import subprocess
import sys

from harness_root import harness_root  # local: sits beside this hook

ROOT = harness_root()
REPOS = {"backend": "amagovpt/udata-pt", "frontend": "amagovpt/dadosgov-fe"}
PROTECTED = {"develop", "tst", "ppr", "main"}


def sh(cmd: list[str], cwd: str, timeout: int = 5) -> str:
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
            timeout=10,
        )
        try:
            for pr in json.loads(prs or "[]"):
                lines.append(
                    f"    PR #{pr['number']} {pr['headRefName']} -> {pr['baseRefName']}: {pr['title']}"
                )
        except Exception:
            pass

    # An in-flight ticket whose state file nobody reads is the restart-blind problem all
    # over again: the loop's memory exists, but the new session does not know to look.
    for path in sorted(glob.glob(os.path.join(ROOT, ".claude", "state", "ticket-*.json"))):
        try:
            with open(path) as fh:
                st = json.load(fh)
        except Exception:
            continue
        done = sum(1 for x in st.get("points", []) if x.get("status") == "done")
        resolved = sum(1 for c in st.get("criteria", []) if c.get("status") != "pending")
        branches = ", ".join(f"{r}:{b}" for r, b in (st.get("branch") or {}).items()) or "-"
        lines.append(
            f"- TICKET EM CURSO {st.get('ticket')}: fase={st.get('phase')}"
            f"{' (PAUSADO)' if st.get('paused') else ''}, pontos={done}/{len(st.get('points', []))}, "
            f"criterios={resolved}/{len(st.get('criteria', []))}, branch={branches}"
            f" -> retoma com /ticket {st.get('ticket')}; o ficheiro de estado prevalece sobre a"
            " memoria da conversa, e o git prevalece sobre o ficheiro."
        )

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
