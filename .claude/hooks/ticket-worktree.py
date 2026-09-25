#!/usr/bin/env python3
"""Cleanup of the per-ticket git worktrees that earlier /ticket sessions created.

The /ticket flow no longer creates worktrees: every ticket works the primary checkout of
each submodule, one ticket per checkout at a time (`ticket-state.py claim` refuses a second
one; pause the other ticket instead). What is left here is `list`, `remove` and `gc`, for
trees that still exist on disk. A tree was a path in the ticket's state (`workdir`), which
is why removing one also releases that field.

Both `remove` and `gc` refuse to discard work: a tree with uncommitted changes, or with
commits that are on no origin ref, is kept and reported.

Exit codes: 0 done, 1 refused, 2 misuse.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

from harness_root import harness_root

ROOT = harness_root()
WORKTREES = os.path.join(ROOT, ".claude", "worktrees")
STATE_DIR = os.path.join(ROOT, ".claude", "state")
STATE = os.path.join(ROOT, ".claude", "hooks", "ticket-state.py")
MARKER = ".ticket-worktree.json"
REPOS = ("backend", "frontend")


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


def dirty_or_unpushed(path: str) -> list:
    """What would be lost by deleting this checkout, in words, or an empty list.

    "Unpushed" is asked as "is this commit on any origin ref", not as "is it ahead of its
    upstream". The upstream question answers wrongly exactly when a tree becomes safe to
    delete: the PR merged and the remote branch was deleted, so `@{u}` no longer resolves
    and the old check read that as unpushed work forever -- which is one of the reasons
    the trees piled up. Reachable from `origin/*` means the commits survive the deletion.
    """
    problems = []
    rc, out = sh(["git", "status", "--porcelain"], path, 60)
    if rc == 0 and out:
        problems.append(f"{len(out.splitlines())} ficheiro(s) nao commitado(s)")
    rc, out = sh(["git", "log", "--oneline", "HEAD", "--not", "--remotes=origin"], path, 120)
    if rc != 0:
        problems.append("nao consegui confirmar que os commits estao no origin")
    elif out:
        problems.append(f"{len(out.splitlines())} commit(s) que nao estao em nenhuma ref do origin")
    return problems


def tree_repos(target: str, marker) -> list:
    """The repos a tree holds — from its marker, or from the directories if it has none."""
    if marker and marker.get("repos"):
        return [r for r in marker["repos"] if r in REPOS]
    return [r for r in REPOS if os.path.isdir(os.path.join(target, r))]


def key_of(name: str, marker) -> str:
    return (marker or {}).get("ticket") or name.upper()


def is_active(key: str) -> bool:
    """A ticket is in flight while its live state file exists (`end` renames it `.done`)."""
    return os.path.exists(os.path.join(STATE_DIR, f"ticket-{key}.json"))


def size_mb(path: str):
    rc, out = sh(["du", "-sm", path], None, 120)
    try:
        return int(out.split()[0]) if rc == 0 else None
    except (ValueError, IndexError):
        return None


def drop_tree(target: str, repos: list, force: bool, clean: bool) -> None:
    """Unregister every checkout and delete the directory.

    `git worktree remove` also refuses over ignored build output — `.venv/`, `node_modules/`
    — which is precisely what every one of these trees contains. So when the caller has
    already established there is nothing to lose (`clean`), the retry with `--force` is not
    a bypass of the safety check, it is what carries out its verdict.
    """
    for repo in repos:
        dest = os.path.join(target, repo)
        source = os.path.join(ROOT, repo)
        if not os.path.isdir(dest):
            continue
        cmd = ["git", "worktree", "remove", dest] + (["--force"] if force else [])
        rc, out = sh(cmd, source, 300)
        if rc != 0 and (force or clean):
            rc, out = sh(["git", "worktree", "remove", "--force", dest], source, 300)
        print(f"  {repo}: {'removido' if rc == 0 else 'git recusou — apago a pasta: ' + out}")
    shutil.rmtree(target, ignore_errors=True)
    for repo in repos:
        sh(["git", "worktree", "prune"], os.path.join(ROOT, repo), 60)


def release_workdir(key: str, repos: list) -> None:
    """Tell the state file the tree is gone, so the ticket points back at the main checkout.

    Only ticket-state.py writes ticket state, hence the subprocess rather than a json.dump
    from here. A ticket already archived by `end` has nothing to release.
    """
    if not is_active(key):
        return
    rc, out = sh(
        ["python3", STATE, "claim", key, "--repos", ",".join(repos), "--no-workdir"], ROOT, 120
    )
    if rc != 0:
        print(
            f"  o estado de {key} ainda aponta para a arvore removida; corrige com\n"
            f"    python3 .claude/hooks/ticket-state.py claim {key} "
            f"--repos {','.join(repos)} --no-workdir\n  ({out})",
            file=sys.stderr,
        )


def cmd_remove(args):
    marker = registered(args.key)
    target = path_for(args.key)
    if not marker and not os.path.isdir(target):
        print(f"{args.key} nao tem arvore registada em {target}.", file=sys.stderr)
        return 1
    repos = tree_repos(target, marker)
    problems = {}
    for repo in repos:
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
    freed = size_mb(target)
    print(f"A remover a arvore de {args.key} ({target}):")
    drop_tree(target, repos, args.force, clean=not problems)
    release_workdir(args.key, repos)
    print(f"Arvore de {args.key} removida" + (f" — {freed} MB libertados." if freed else "."))
    return 0


def cmd_gc(args):
    """Sweep the trees whose tickets are over — the accumulation this exists to stop.

    A session that is cleared, killed or simply ends before Phase 10 leaves its tree on
    disk with nothing pointing at it. Nobody notices one; six of them are six gigabytes.
    Two things are never swept: a ticket still in flight (its state file is live) and a
    tree holding work that is not on any origin ref.
    """
    if not os.path.isdir(WORKTREES):
        print("Nenhuma arvore de ticket criada.")
        return 0
    names = sorted(n for n in os.listdir(WORKTREES) if os.path.isdir(os.path.join(WORKTREES, n)))
    if not names:
        print("Nenhuma arvore de ticket criada.")
        return 0

    removed, kept, freed = [], [], 0
    for name in names:
        target = os.path.join(WORKTREES, name)
        marker = read_marker(target)
        key = key_of(name, marker)
        repos = tree_repos(target, marker)
        if is_active(key) and not args.include_active:
            kept.append((key, "ticket em curso — fecha-o com `ticket-state.py end` primeiro"))
            continue
        problems = []
        for repo in repos:
            dest = os.path.join(target, repo)
            if os.path.isdir(dest):
                problems += [f"{repo}/: {x}" for x in dirty_or_unpushed(dest)]
        if problems and not args.force:
            kept.append((key, "; ".join(problems)))
            continue
        mb = size_mb(target) or 0
        if args.dry_run:
            removed.append((key, mb))
            continue
        print(f"A remover {key} ({target}):")
        drop_tree(target, repos, args.force, clean=not problems)
        release_workdir(key, repos)
        removed.append((key, mb))
        freed += mb

    verb = "A remover" if not args.dry_run else "Removeria"
    if removed:
        print(f"\n{verb} {len(removed)} arvore(s):")
        for key, mb in removed:
            print(f"  {key:12} {mb or '?'} MB")
    if kept:
        print(f"\nMantidas {len(kept)}:")
        for key, why in kept:
            print(f"  {key:12} {why}")
    if args.dry_run:
        total = sum(mb for _, mb in removed)
        print(f"\n(--dry-run: nada foi apagado; libertaria ~{total} MB. Repete sem --dry-run.)")
    elif removed:
        print(f"\n{freed} MB libertados.")
    else:
        print("\nNada a limpar.")
    for repo in REPOS:
        sh(["git", "worktree", "prune"], os.path.join(ROOT, repo), 60)
    return 0


def cmd_list(args):
    if not os.path.isdir(WORKTREES):
        print("Nenhuma arvore de ticket criada.")
        return 0
    found = reclaimable = 0
    for name in sorted(os.listdir(WORKTREES)):
        target = os.path.join(WORKTREES, name)
        if not os.path.isdir(target):
            continue
        marker = read_marker(target)
        key = key_of(name, marker)
        found += 1
        active = is_active(key)
        if not active:
            reclaimable += 1
        print(f"{key}  {target}  [{'ticket em curso' if active else 'ticket fechado'}]"
              + ("" if marker else "  (sem marcador)"))
        for repo in tree_repos(target, marker):
            dest = os.path.join(target, repo)
            _, branch = sh(["git", "branch", "--show-current"], dest, 30)
            problems = dirty_or_unpushed(dest)
            print(f"    {repo:9} {branch or '(detached)':45} "
                  + ("; ".join(problems) if problems else "limpa e empurrada"))
    if not found:
        print("Nenhuma arvore de ticket criada.")
    elif reclaimable:
        print(f"\n{reclaimable} arvore(s) de tickets ja fechados. Limpa com "
              "`ticket-worktree.py gc` (nao toca em trabalho por empurrar).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("remove", help="remove a ticket's checkout once its work is pushed")
    p.add_argument("key")
    p.add_argument("--force", action="store_true", help="discard uncommitted or unpushed work")
    p.set_defaults(func=cmd_remove)

    p = sub.add_parser("gc", help="remove every tree whose ticket is closed and whose work is pushed")
    p.add_argument("--dry-run", action="store_true", help="say what it would remove, remove nothing")
    p.add_argument("--force", action="store_true", help="also discard uncommitted or unpushed work")
    p.add_argument(
        "--include-active",
        action="store_true",
        help="also sweep tickets still in flight (their state points back at the main checkout)",
    )
    p.set_defaults(func=cmd_gc)

    p = sub.add_parser("list", help="every ticket checkout, its branch and whether it is dirty")
    p.set_defaults(func=cmd_list)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
