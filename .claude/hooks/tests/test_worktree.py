#!/usr/bin/env python3
"""Regression tests for the per-ticket worktree lifecycle.

Run: python3 .claude/hooks/tests/test_worktree.py

The bug these exist for: nothing ever removed a tree. `create` was called at Phase 3 and
that was the end of it -- `remove` existed but no phase invoked it, so every worked ticket
left a checkout with its own `.venv`/`node_modules` on disk, and they accumulated by the
gigabyte until somebody looked.

So the cases here are about the *end* of the lifecycle: that closing a ticket reclaims its
tree, that a sweep collects what dead sessions left behind, and -- the half that matters
more -- that neither of them can delete work. The trees are built from scratch (a bare
"origin" plus two clones), never from the real repositories.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

REAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HOOKS = os.path.join(REAL_ROOT, ".claude", "hooks")
WORKTREE = os.path.join(HOOKS, "ticket-worktree.py")
STATE = os.path.join(HOOKS, "ticket-state.py")
KEY = "LEDG-9990"


def git(cwd, *args, check=True):
    p = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} em {cwd}: {p.stdout}{p.stderr}")
    return p.stdout.strip()


def run(script, *args, root):
    """A hook, with the sandbox as its harness root — the same way the session runs them."""
    env = {**os.environ, "CLAUDE_HARNESS_ROOT": root}
    p = subprocess.run(
        ["python3", script, *args], capture_output=True, text=True, cwd=root, env=env
    )
    return p.returncode, p.stdout + p.stderr


def build_root() -> str:
    """A harness root with two throwaway repos where `backend/` and `frontend/` live.

    Real repositories, real remotes: the whole point of the guarded removal is what git
    answers about pushed commits, so a mock of git would test nothing.
    """
    root = tempfile.mkdtemp(prefix="dadosgov-worktree-")
    os.makedirs(os.path.join(root, ".claude", "state"))
    os.symlink(HOOKS, os.path.join(root, ".claude", "hooks"))
    for repo in ("backend", "frontend"):
        origin = os.path.join(root, "origins", repo + ".git")
        os.makedirs(origin)
        subprocess.run(["git", "init", "--bare", "-b", "develop", origin], capture_output=True)
        path = os.path.join(root, repo)
        subprocess.run(["git", "clone", origin, path], capture_output=True)
        git(path, "config", "user.email", "t@t")
        git(path, "config", "user.name", "t")
        open(os.path.join(path, "README.md"), "w").write("x\n")
        git(path, "add", "-A")
        git(path, "commit", "-m", "chore: seed")
        git(path, "push", "-u", "origin", "develop")
    return root


def start_ticket(root, key=KEY, repos="backend"):
    run(STATE, "start", key, "--title", "t", root=root)
    rc, out = run(WORKTREE, "create", key, "--repos", repos, "--base", "origin/develop",
                  "--no-install", root=root)
    assert rc == 0, out
    return os.path.join(root, ".claude", "worktrees", key.lower())


def state_of(root, key=KEY, done=False):
    path = os.path.join(root, ".claude", "state", f"ticket-{key}.json" + (".done" if done else ""))
    with open(path) as fh:
        return json.load(fh)


def check(label, condition, detail="") -> int:
    print(f"  {'ok   ' if condition else 'FALHA'} {label}" + (f"  — {detail}" if not condition and detail else ""))
    return 0 if condition else 1


# --- the cases ---------------------------------------------------------------


def case_end_reclaims(root) -> int:
    """Phase 10 closes the ticket, and the tree goes with it."""
    tree = start_ticket(root)
    failures = check("create deixa a arvore em disco", os.path.isdir(os.path.join(tree, "backend")))
    failures += check("create regista o workdir no estado", state_of(root)["workdir"] == tree)
    rc, out = run(STATE, "end", KEY, root=root)
    failures += check("end fecha o ticket", rc == 0, out)
    failures += check("end remove a arvore", not os.path.exists(tree), out)
    failures += check(
        "end desregista o worktree no repo",
        "worktrees" not in git(os.path.join(root, "backend"), "worktree", "list"),
    )
    return failures


def case_end_refuses_to_lose_work(root) -> int:
    """A tree with a commit that is on no origin ref survives `end`, with the reason said."""
    tree = start_ticket(root)
    be = os.path.join(tree, "backend")
    git(be, "checkout", "-b", "bugfix/ledg-9990-x")
    git(be, "config", "user.email", "t@t")
    git(be, "config", "user.name", "t")
    open(os.path.join(be, "novo.py"), "w").write("x\n")
    git(be, "add", "-A")
    git(be, "commit", "-m", "fix(x): nao empurrado")
    rc, out = run(STATE, "end", KEY, root=root)
    failures = check("o ticket fecha na mesma", os.path.exists(
        os.path.join(root, ".claude", "state", f"ticket-{KEY}.json.done")))
    failures += check("a arvore com commit por empurrar e mantida", os.path.isdir(be), out)
    failures += check("e diz porque", "nenhuma ref do origin" in out, out)
    # ...and once it is pushed, the sweep collects it.
    git(be, "push", "-u", "origin", "bugfix/ledg-9990-x")
    rc, out = run(WORKTREE, "gc", root=root)
    failures += check("gc leva a arvore depois do push", not os.path.exists(tree), out)
    return failures


def case_gc_spares_the_living(root) -> int:
    """The sweep is for closed tickets; one still in flight is not swept."""
    tree = start_ticket(root)
    rc, out = run(WORKTREE, "gc", root=root)
    failures = check("gc nao toca num ticket em curso", os.path.isdir(tree), out)
    failures += check("e explica que esta em curso", "ticket em curso" in out, out)
    rc, out = run(WORKTREE, "gc", "--dry-run", "--include-active", root=root)
    failures += check("--dry-run nao apaga nada", os.path.isdir(tree), out)
    failures += check("--dry-run diz o que levaria", KEY in out and "Removeria" in out, out)
    return failures


def case_gc_collects_orphans(root) -> int:
    """A tree whose state file never existed — a session killed before Phase 3 finished."""
    tree = start_ticket(root)
    os.remove(os.path.join(root, ".claude", "state", f"ticket-{KEY}.json"))
    rc, out = run(WORKTREE, "gc", root=root)
    failures = check("gc apanha a arvore orfa", not os.path.exists(tree), out)
    failures += check(
        "e o repo fica sem registos pendentes",
        "worktrees" not in git(os.path.join(root, "backend"), "worktree", "list"),
    )
    return failures


def case_dirty_tree_is_kept(root) -> int:
    """Uncommitted edits are work too: `remove` refuses, `--force` is the way past."""
    tree = start_ticket(root)
    be = os.path.join(tree, "backend")
    open(os.path.join(be, "README.md"), "a").write("editado\n")
    rc, out = run(WORKTREE, "remove", KEY, root=root)
    failures = check("remove recusa uma arvore suja", rc == 1 and os.path.isdir(be), out)
    failures += check("e conta os ficheiros", "nao commitado" in out, out)
    rc, out = run(WORKTREE, "remove", KEY, "--force", root=root)
    failures += check("--force remove-a", rc == 0 and not os.path.exists(tree), out)
    failures += check("e o estado deixa de apontar para ela", state_of(root)["workdir"] is None)
    return failures


def case_state_keeps_pointing_at_reality(root) -> int:
    """`claim --no-workdir` is how the tree stops being the ticket's working directory.

    It matters because everything that resolves a path — the suites, the lint hook, the
    guards — reads `workdir`. Left pointing at a deleted tree, `verify` fails on a missing
    directory instead of running.
    """
    tree = start_ticket(root)
    failures = check("workdir aponta para a arvore", state_of(root)["workdir"] == tree)
    rc, out = run(STATE, "claim", KEY, "--repos", "backend", "--no-workdir", root=root)
    failures += check("claim --no-workdir limpa-o", rc == 0 and state_of(root)["workdir"] is None, out)
    rc, out = run(STATE, "claim", KEY, "--repos", "backend", "--workdir", tree,
                  "--no-workdir", root=root)
    failures += check("--workdir com --no-workdir e recusado", rc == 2, out)
    return failures


CASES = [
    case_end_reclaims,
    case_end_refuses_to_lose_work,
    case_gc_spares_the_living,
    case_gc_collects_orphans,
    case_dirty_tree_is_kept,
    case_state_keeps_pointing_at_reality,
]


def main() -> int:
    failures = 0
    for case in CASES:
        print(f"\n--- {case.__name__} — {(case.__doc__ or '').splitlines()[0]}")
        root = build_root()
        try:
            failures += case(root)
        finally:
            shutil.rmtree(root, ignore_errors=True)
    print()
    print(f"{failures} CASO(S) A FALHAR" if failures else "TODOS OS CASOS PASSAM")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
