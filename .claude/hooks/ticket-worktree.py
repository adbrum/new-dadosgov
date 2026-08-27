#!/usr/bin/env python3
"""Per-ticket git worktrees, so several /ticket sessions can run at once.

One checkout can only be on one branch, so two tickets touching the same repo need two
checkouts. What this deliberately does *not* do is create a second project: the session
keeps running from the monorepo root, and the worktree is recorded as a path in the
ticket's state (`workdir`). Everything that touches the repo -- the suites, the lint hook,
the guards -- reads it from there.

The alternative, giving each worktree its own `.claude/`, looks tidier and is a trap: the
hooks resolve their root from the invocation string, so the hook processes and the CLI
calls would each answer differently, and a guard pointed at the wrong state directory does
not fail -- it finds no ticket and behaves exactly as if there were nothing to enforce.

Nor is it a worktree of the monorepo: that yields empty `backend/` and `frontend/`
directories, because submodules are not checked out by `git worktree add`. The worktrees
are per submodule, which is where the real repositories are.

Exit codes: 0 done, 1 refused, 2 misuse.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from harness_root import harness_root

ROOT = harness_root()
WORKTREES = os.path.join(ROOT, ".claude", "worktrees")
STATE = os.path.join(ROOT, ".claude", "hooks", "ticket-state.py")
MARKER = ".ticket-worktree.json"
KEY_RE = re.compile(r"^LEDG-\d+$")
REPOS = ("backend", "frontend")
BASE = "origin/develop"

# Untracked local files the suites need and a fresh worktree will not have. Symlinked, not
# copied: they are gitignored, they change rarely, and a copy silently goes stale -- the
# backend SAML tests and the password policy both read .env, and without it they do not
# fail, they quietly test something else.
LOCAL_FILES = {
    "backend": [".env", "docker-compose.override.yml"],
    "frontend": [".env"],
}
INSTALL = {
    "backend": ["uv", "sync", "--extra", "dev", "--extra", "test"],
    "frontend": ["npm", "ci"],
}


def sh(cmd, cwd=None, timeout=1800):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "<timeout>"
    except FileNotFoundError:
        return 127, "<comando nao encontrado>"


def slug(key: str) -> str:
    return key.lower()


def path_for(key: str) -> str:
    return os.path.join(WORKTREES, slug(key))


def read_marker(path: str):
    try:
        with open(os.path.join(path, MARKER)) as fh:
            return json.load(fh)
    except Exception:
        return None


def registered(key: str):
    path = path_for(key)
    return read_marker(path) if os.path.isdir(path) else None


def cmd_create(args):
    if not KEY_RE.match(args.key):
        print(f"Chave invalida: {args.key!r} (esperado LEDG-<n>).", file=sys.stderr)
        return 2
    existing = registered(args.key)
    if existing:
        print(f"{args.key} ja tem arvore em {path_for(args.key)}:")
        print(json.dumps(existing, indent=2, ensure_ascii=False))
        print("\nUsa-a, ou remove-a com `ticket-worktree.py remove`.")
        return 0

    repos = [r.strip() for r in (args.repos or "").split(",") if r.strip()]
    unknown = [r for r in repos if r not in REPOS]
    if unknown or not repos:
        print(f"--repos invalido: {args.repos!r} (esperado backend|frontend).", file=sys.stderr)
        return 2

    target = path_for(args.key)
    os.makedirs(target, exist_ok=True)
    created = []
    for repo in repos:
        source = os.path.join(ROOT, repo)
        rc, out = sh(["git", "fetch", "origin"], source, 600)
        if rc != 0:
            print(f"git fetch em {repo}/ falhou: {out}", file=sys.stderr)
            return 1
        dest = os.path.join(target, repo)
        # Detached on the base branch: the working branch is created by Phase 5, inside the
        # worktree, where the guard checks its name. And `checkout develop` would fail here
        # anyway -- worktrees share the ref namespace, so develop is already checked out.
        rc, out = sh(["git", "worktree", "add", "--detach", dest, args.base], source, 600)
        print(f"$ git -C {repo} worktree add --detach … {args.base}\n{out}")
        if rc != 0:
            return 1
        created.append((repo, dest))

        for name in LOCAL_FILES[repo]:
            origin = os.path.join(source, name)
            if os.path.exists(origin) and not os.path.exists(os.path.join(dest, name)):
                os.symlink(origin, os.path.join(dest, name))
                print(f"  ligado {repo}/{name} -> {origin}")

    with open(os.path.join(target, MARKER), "w") as fh:
        json.dump(
            {
                "ticket": args.key,
                "repos": repos,
                "root": ROOT,
                "base": args.base,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            fh,
            indent=2,
        )

    # The state file is the authority on which tree belongs to which ticket, and `claim` is
    # what refuses two tickets in one checkout -- so go through it rather than writing the
    # field here. It is also what stops this ticket locking the repo it does not touch.
    rc, out = sh(
        ["python3", STATE, "claim", args.key, "--repos", ",".join(repos), "--workdir", target],
        ROOT,
        120,
    )
    print(out)
    if rc != 0:
        print(
            "\nA arvore ficou criada, mas o estado do ticket nao a registou. Corrige o que "
            "`claim` diz e repete apenas essa linha.",
            file=sys.stderr,
        )

    if not args.no_install:
        for repo, dest in created:
            print(f"\n$ {' '.join(INSTALL[repo])}   (em {repo}/, pode demorar)")
            code, out = sh(INSTALL[repo], dest, 1800)
            tail = "\n  ".join(out.splitlines()[-6:])
            print(f"  -> {'ok' if code == 0 else f'codigo {code}'}\n  {tail}")
            if code != 0:
                print(
                    f"  Instalacao de {repo}/ falhou. A arvore existe; corre a instalacao a mao "
                    "antes de correr as suites — um .venv ou node_modules em falta faz o verify "
                    "falhar por razoes que nao sao do ticket.",
                    file=sys.stderr,
                )

    print(f"\nArvore de {args.key}: {target}")
    print("Arranca a sessao deste ticket com:")
    print(f"  cd {ROOT} && claude \"/ticket {args.key}\"")
    print("A sessao corre da raiz do monorepo — a arvore e um caminho no estado do ticket,")
    print("nao um segundo projeto. `ticket-state.py doctor` mostra tudo resolvido.")
    return 0


def dirty_or_unpushed(path: str) -> list:
    problems = []
    rc, out = sh(["git", "status", "--porcelain"], path, 60)
    if rc == 0 and out:
        problems.append(f"{len(out.splitlines())} ficheiro(s) nao commitado(s)")
    rc, out = sh(["git", "log", "--oneline", f"{BASE}..HEAD"], path, 60)
    if rc == 0 and out:
        rc2, remote = sh(["git", "log", "--oneline", "@{u}..HEAD"], path, 60)
        if rc2 != 0 or remote:
            problems.append(f"{len(out.splitlines())} commit(s) que podem nao estar no origin")
    return problems


def cmd_remove(args):
    marker = registered(args.key)
    target = path_for(args.key)
    if not marker:
        print(f"{args.key} nao tem arvore registada em {target}.", file=sys.stderr)
        return 1
    problems = {}
    for repo in marker["repos"]:
        dest = os.path.join(target, repo)
        if os.path.isdir(dest):
            found = dirty_or_unpushed(dest)
            if found:
                problems[repo] = found
    if problems and not args.force:
        print(f"Nao removo a arvore de {args.key} — ha trabalho que se perderia:")
        for repo, found in problems.items():
            print(f"  {repo}/: " + "; ".join(found))
        print("\nCommita e empurra primeiro, ou repete com --force se for para descartar.")
        return 1
    for repo in marker["repos"]:
        dest = os.path.join(target, repo)
        cmd = ["git", "worktree", "remove", dest] + (["--force"] if args.force else [])
        rc, out = sh(cmd, os.path.join(ROOT, repo), 300)
        print(f"$ git -C {repo} worktree remove {'--force ' if args.force else ''}{dest}\n{out or 'ok'}")
    shutil.rmtree(target, ignore_errors=True)
    for repo in marker["repos"]:
        sh(["git", "worktree", "prune"], os.path.join(ROOT, repo), 60)
    print(f"Arvore de {args.key} removida.")
    print(f"O estado do ticket mantem o workdir — limpa-o com `ticket-state.py claim {args.key} "
          f"--repos {','.join(marker['repos'])}` se voltar a trabalhar no checkout principal.")
    return 0


def cmd_list(args):
    if not os.path.isdir(WORKTREES):
        print("Nenhuma arvore de ticket criada.")
        return 0
    found = False
    for name in sorted(os.listdir(WORKTREES)):
        marker = read_marker(os.path.join(WORKTREES, name))
        if not marker:
            continue
        found = True
        print(f"{marker['ticket']}  {os.path.join(WORKTREES, name)}")
        for repo in marker["repos"]:
            dest = os.path.join(WORKTREES, name, repo)
            _, branch = sh(["git", "branch", "--show-current"], dest, 30)
            _, dirty = sh(["git", "status", "--porcelain"], dest, 30)
            n = len([x for x in dirty.splitlines() if x.strip()])
            print(f"    {repo:9} {branch or '(detached)':45} {n} ficheiro(s) alterado(s)")
    if not found:
        print("Nenhuma arvore de ticket criada.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("create", help="give a ticket its own checkout of the repos it touches")
    p.add_argument("key")
    p.add_argument("--repos", help="backend | frontend | backend,frontend")
    p.add_argument("--base", default=BASE, help=f"branch to start from (default {BASE})")
    p.add_argument("--no-install", action="store_true", help="skip uv sync / npm ci")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("remove", help="remove a ticket's checkout once its work is pushed")
    p.add_argument("key")
    p.add_argument("--force", action="store_true", help="discard uncommitted or unpushed work")
    p.set_defaults(func=cmd_remove)

    p = sub.add_parser("list", help="every ticket checkout, its branch and whether it is dirty")
    p.set_defaults(func=cmd_list)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
