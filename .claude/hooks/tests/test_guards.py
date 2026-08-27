#!/usr/bin/env python3
"""Regression tests for the harness guards — one case per code-review finding.

Run: python3 .claude/hooks/tests/test_guards.py

Each case is a real hook payload piped into the real hook, asserting DENY or PASS. The
numbered cases are bypasses an independent review found in the first implementation; they
exist so those specific holes cannot reopen silently.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

REAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def sandbox() -> str:
    """A throwaway root the hooks agree on, so this suite never touches a live session.

    Every case here writes a real ticket state file and a real fix-loop lock, and the
    lock is what freezes the test surface. Run against the primary checkout while a
    session is working and you freeze its tests, clobber its lock and append to its
    log. So: a temp tree whose `.claude/state` is its own, with `.claude/hooks`,
    `backend` and `frontend` symlinked to the real ones — the guards `realpath` both
    sides of every path comparison, so the matching still works and git still reads
    the real repositories.
    """
    if os.environ.get("CLAUDE_HARNESS_ROOT"):
        return os.environ["CLAUDE_HARNESS_ROOT"]
    root = tempfile.mkdtemp(prefix="dadosgov-guards-")
    os.makedirs(os.path.join(root, ".claude", "state"))
    os.symlink(os.path.join(REAL_ROOT, ".claude", "hooks"), os.path.join(root, ".claude", "hooks"))
    for sub in ("backend", "frontend"):
        os.symlink(os.path.join(REAL_ROOT, sub), os.path.join(root, sub))
    os.environ["CLAUDE_HARNESS_ROOT"] = root  # inherited by every hook we spawn
    return root


ROOT = sandbox()
HOOKS = os.path.join(ROOT, ".claude", "hooks")
LOCK = os.path.join(ROOT, ".claude", "state", "fix-loop.lock")
BRANCH_GUARD = "guard-protected-branch.py"
SURFACE_GUARD = "guard-test-surface.py"
TICKET_GUARD = "guard-ticket-workflow.py"
TICKET_KEY = "LEDG-9999"
TICKET_STATE = os.path.join(ROOT, ".claude", "state", f"ticket-{TICKET_KEY}.json")


def call(hook: str, payload: dict) -> str:
    p = subprocess.run(
        ["python3", os.path.join(HOOKS, hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return "DENY" if p.stdout.strip() else "PASS"


def current_branch(path: str) -> str:
    return subprocess.run(
        ["git", "-C", path, "branch", "--show-current"], capture_output=True, text=True
    ).stdout.strip()


def bash(cmd: str, cwd: str = ROOT) -> dict:
    return {"tool_name": "Bash", "cwd": cwd, "tool_input": {"command": cmd}}


def edit(path: str, cwd: str = ROOT) -> dict:
    return {"tool_name": "Edit", "cwd": cwd, "tool_input": {"file_path": path}}


BE, FE = os.path.join(ROOT, "backend"), os.path.join(ROOT, "frontend")

BRANCH_CASES = [
    # The target used to be guessed from the command text alone, so the most natural form of
    # all slipped through: `cd backend` in one call, `git commit` in the next.
    ("#8a  bare git commit with cwd=backend", bash("git commit -am x", BE), "DENY"),
    ("#8b  (cd backend && git commit)", bash("(cd backend && git commit -m x)"), "DENY"),
    ("#8c  git -C backend -c user.email=x commit", bash("git -C backend -c user.email=x commit -m y"), "DENY"),
    ("#8d  git add -A && git commit, cwd=backend", bash("git add -A && git commit -m x", BE), "DENY"),
    ("     git commit in the monorepo (allowed by choice)", bash("git commit -m x", ROOT), "PASS"),
    ("     git status in backend", bash("git status", BE), "PASS"),
    ("     force-push", bash("git push --force"), "DENY"),
    ("     force-push, wrapped", bash("bash -lc 'git push -f'"), "DENY"),
    # Found while writing this file: the guard denied a heredoc that merely mentions the
    # pattern, i.e. this test file itself.
    ("     heredoc that only mentions force-push is data", bash("cat > t.py <<'EOF'\ngit push --force\nEOF"), "PASS"),
]

SURFACE_CASES = [
    ("#6   sed -i on a .test.ts mid-command", bash("sed -i s/a/b/ src/lib/foo.test.ts && npx vitest run", FE), "DENY"),
    ("#6b  mv of a .test.ts", bash("mv src/lib/foo.test.ts src/lib/foo.test.ts.bak", FE), "DENY"),
    ("#7   sed -i on a submodule-relative path", bash("sed -i 's/assert x/assert True/' udata/tests/test_utils.py", BE), "DENY"),
    ("#5   Edit on vitest.config.ts", edit(os.path.join(FE, "vitest.config.ts")), "DENY"),
    ("#5b  Edit on pyproject.toml", edit(os.path.join(BE, "pyproject.toml")), "DENY"),
    ("#5c  Edit on conftest.py", edit(os.path.join(BE, "conftest.py")), "DENY"),
    ("#12  pytest <test> | tee /tmp/log is read-only", bash("uv run pytest udata/tests/test_x.py 2>&1 | tee /tmp/log", BE), "PASS"),
    ("#12b vitest <test> > /tmp/out is read-only", bash("npx vitest run src/x.test.ts > /tmp/out", FE), "PASS"),
    ("#12c grep in a test > /tmp/o is read-only", bash("grep -n assert udata/tests/test_x.py > /tmp/o", BE), "PASS"),
    ("     Edit on source", edit(os.path.join(FE, "src/components/X.tsx")), "PASS"),
    ("     running the suite", bash("npx vitest run", FE), "PASS"),
    ("     redirect INTO a test file is a write", bash("echo x > src/lib/foo.test.ts", FE), "DENY"),
]


def ticket_state(**overrides) -> dict:
    """A minimal but complete ticket state; each case overrides just what it exercises."""
    state = {
        "ticket": TICKET_KEY, "title": "guard regression", "source": "jira",
        "phase": "approved", "paused": False, "repos": ["backend"],
        "deploy_order": None, "branch": {}, "plan_digest": "sha256:deadbeef",
        "plan_delegated_to_fable": True, "precedents": [], "points": [],
        "criteria": [{"id": 1, "text": "criterio", "status": "met", "evidence": "test"}],
        "verified": {}, "review": {"ran": True, "accepted": [], "rejected": []},
        "pr": {}, "overrides": [],
    }
    state.update(overrides)
    return state


def state_path(key: str) -> str:
    return os.path.join(ROOT, ".claude", "state", f"ticket-{key}.json")


def write_ticket(state: dict) -> None:
    path = state_path(state["ticket"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(state, fh)


def backend_branch() -> str:
    return current_branch(BE)


# Each case carries its own state, because what is being tested IS the state->decision map.
def TICKET_CASES() -> list:
    on_branch = ticket_state(branch={"backend": backend_branch()})
    good_msg = 'git commit -m "fix(admin): widen the producer scope" -m "Refs: LEDG-9999"'
    return [
        # 1. the approval gate: no source before the plan is approved
        ("#T1  Edit em backend/ com plano por aprovar", ticket_state(phase="planned"),
         edit(os.path.join(BE, "udata/core/dataset/api.py")), "DENY"),
        ("#T2  Edit em backend/ com plano aprovado", ticket_state(phase="approved"),
         edit(os.path.join(BE, "udata/core/dataset/api.py")), "PASS"),
        ("#T3  ticket pausado desliga o gate", ticket_state(phase="planned", paused=True),
         edit(os.path.join(BE, "udata/core/dataset/api.py")), "PASS"),
        # A park is not a pause: it stops one session, it does not unlock the repos.
        ("#T19 ticket estacionado mantem o lock",
         ticket_state(phase="planned", parked={"reason_code": "no-criteria",
                                               "question": "o que e 'feito'?"}),
         edit(os.path.join(BE, "udata/core/dataset/api.py")), "DENY"),
        # the harness itself must never be frozen by a ticket
        ("#T4  Edit em .claude/ nunca e bloqueado", ticket_state(phase="planned"),
         edit(os.path.join(REAL_ROOT, ".claude/hooks/x.py")), "PASS"),
        # 2. branch shape
        ("#T5  branch bem formada", ticket_state(),
         bash("git checkout -b bugfix/ledg-9999-producer-scope", BE), "PASS"),
        ("#T6  branch sem o prefixo ledg-", ticket_state(),
         bash("git checkout -b bugfix/2296-producer-scope", BE), "DENY"),
        ("#T7  branch de outro ticket", ticket_state(),
         bash("git checkout -b bugfix/ledg-1111-outro", BE), "DENY"),
        ("#T8  branch antes do plano aprovado", ticket_state(phase="planned"),
         bash("git checkout -b bugfix/ledg-9999-producer-scope", BE), "DENY"),
        # 3. commit messages, checked at the cheap moment
        ("#T9  commit sem trailer Refs:", ticket_state(),
         bash('git commit -m "fix(admin): widen the producer scope"', BE), "DENY"),
        ("#T10 commit nao-Conventional", ticket_state(),
         bash('git commit -m "arranjar o scope" -m "Refs: LEDG-9999"', BE), "DENY"),
        ("#T11 commit com Co-Authored-By", ticket_state(),
         bash(good_msg + ' -m "Co-Authored-By: alguem <a@b.c>"', BE), "DENY"),
        # the narrow attribution regex must not reject a commit that merely names .claude/
        ("#T12 commit que menciona .claude/ passa", ticket_state(),
         bash('git commit -m "chore(admin): read .claude/hooks config" -m "Refs: LEDG-9999"', BE),
         "PASS"),
        ("#T13 commit correto", ticket_state(), bash(good_msg, BE), "PASS"),
        ("#T14 commit fora do ticket (frontend nao listado)", ticket_state(),
         bash('git commit -m "chore: x"', ROOT), "PASS"),
        # 4. the push gate
        ("#T15 push sem verify", on_branch, bash("git push -u origin HEAD", BE), "DENY"),
        ("#T16 push numa branch nao registada", ticket_state(),
         bash("git push -u origin HEAD", BE), "PASS"),
        ("#T17 push com override armado",
         ticket_state(branch={"backend": backend_branch()},
                      overrides=[{"gate": "push", "reason": "ensaio", "consumed": False}]),
         bash("git push -u origin HEAD", BE), "PASS"),
        # `git stash push` is not a push: it moves nothing anywhere and is how you park a
        # file to prove a test goes red without it. The gate used to match any "push" after
        # "git" and refused it with the whole push checklist, mid-verification.
        ("#T26 stash push nao e um push", on_branch,
         bash("git stash push -q udata/harvest/api.py", BE), "PASS"),
    ]


def run_ticket_group() -> int:
    print("\n--- guard-ticket-workflow (estado por caso) ---")
    failures = 0
    for label, state, payload, expected in TICKET_CASES():
        write_ticket(state)
        got = call(TICKET_GUARD, payload)
        ok = got == expected
        failures += 0 if ok else 1
        print(f"  {'ok   ' if ok else 'FALHA'} {label:52} esperado={expected} obtido={got}")
    if os.path.exists(TICKET_STATE):
        os.remove(TICKET_STATE)
    # and it must be completely inert once no ticket is active
    got = call(TICKET_GUARD, edit(os.path.join(BE, "udata/core/dataset/api.py")))
    ok = got == "PASS"
    failures += 0 if ok else 1
    print(f"  {'ok   ' if ok else 'FALHA'} {'#T18 inerte sem ticket ativo':52} "
          f"esperado=PASS obtido={got}")
    return failures


# Two tickets at once. The old guard imposed every active state on every write, so one
# ticket waiting for its plan locked both submodules for all the others -- which is exactly
# why parallel sessions were impossible. Ownership is per repo and per checkout now.
def PARALLEL_CASES() -> list:
    waiting = ticket_state(ticket="LEDG-9997", phase="planned", repos=["backend"])
    working = ticket_state(ticket="LEDG-9996", phase="approved", repos=["frontend"])
    worktree = os.path.join(ROOT, ".claude", "worktrees", "ledg-9997")
    moved = ticket_state(
        ticket="LEDG-9997", phase="planned", repos=["backend"], workdir=worktree
    )
    return [
        ("#T20 outro repo nao e bloqueado por um plano pendente", [waiting, working],
         edit(os.path.join(FE, "src/components/X.tsx")), "PASS"),
        ("#T21 o repo do ticket pendente continua bloqueado", [waiting, working],
         edit(os.path.join(BE, "udata/core/dataset/api.py")), "DENY"),
        ("#T22 a arvore do ticket e a que ele bloqueia", [moved],
         edit(os.path.join(worktree, "backend/udata/core/dataset/api.py")), "DENY"),
        ("#T23 o checkout principal fica livre quando o ticket saiu", [moved],
         edit(os.path.join(BE, "udata/core/dataset/api.py")), "PASS"),
        ("#T24 commit aceita o Refs do ticket que detem a arvore", [waiting, working],
         bash('git commit -m "fix(x): y" -m "Refs: LEDG-9996"', FE), "PASS"),
        ("#T25 commit com o Refs do ticket do outro repo", [waiting, working],
         bash('git commit -m "fix(x): y" -m "Refs: LEDG-9997"', FE), "DENY"),
    ]


def run_parallel_group() -> int:
    print("\n--- guard-ticket-workflow (dois tickets ao mesmo tempo) ---")
    failures = 0
    for label, states, payload, expected in PARALLEL_CASES():
        for state in states:
            write_ticket(state)
        got = call(TICKET_GUARD, payload)
        ok = got == expected
        failures += 0 if ok else 1
        print(f"  {'ok   ' if ok else 'FALHA'} {label:52} esperado={expected} obtido={got}")
        for state in states:
            if os.path.exists(state_path(state["ticket"])):
                os.remove(state_path(state["ticket"]))
    return failures


# --- plan-audit: the deterministic half of a Phase 4 review -------------------
# Three false positives an audit of a real plan (LEDG-2328) produced, each of which made
# the correct plan unapprovable. They are regression cases now, because the fix loosens a
# gate and a loosened gate has to stay exactly as loose as intended.
PLAN_HEAD = "## Plano — LEDG-9999\n\n**Repo(s):** backend\n\n"
PLAN_TAIL = (
    "- **Prova:** `test:udata/tests/test_discussions.py::test_x`\n"
    "- **Commit:** `fix(discussions): align the notification field type`\n"
)
NOTIF = "backend/udata/core/discussions/notifications.py"
TESTS = "backend/udata/tests/test_notifications_integrity.py"


def plan(ficheiros: str, extra: str = "") -> str:
    return (
        PLAN_HEAD
        + "### Ponto 1 — resumo\n"
        + f"- **Ficheiros:** {ficheiros}\n"
        + extra
        + PLAN_TAIL
    )


def PLAN_AUDIT_CASES() -> list:
    justified = (
        f"- **Superfície de teste:** `{TESTS}` — remover o marcador xfail(strict=True) cuja "
        "causa este ponto corrige; nenhuma asserção é alterada.\n"
    )
    return [
        ("test surface, undeclared", plan(f"`{TESTS}`"), "FAIL", "superficie de teste"),
        ("test surface, declared + justified", plan(f"`{TESTS}`", justified), "PASS", None),
        (
            "test surface, declaration without a reason",
            plan(f"`{TESTS}`", f"- **Superfície de teste:** `{TESTS}` — n/a\n"),
            "FAIL",
            "nao traz justificacao",
        ),
        ("symbol that exists", plan(f"`{NOTIF}` (`DiscussionStatus`)"), "PASS", None),
        (
            "qualified symbol resolves by component",
            plan(f"`{NOTIF}` (`DiscussionNotificationDetails.message_id`)"),
            "PASS",
            None,
        ),
        (
            "new symbol marked with +",
            plan(f"`{NOTIF}` (`+zzz_symbol_that_never_exists`)"),
            "PASS",
            None,
        ),
        (
            "+ on a symbol that already exists",
            plan(f"`{NOTIF}` (`+DiscussionStatus`)"),
            "FAIL",
            "ja existe no ficheiro",
        ),
        (
            "symbol that does not exist and is not marked new",
            plan(f"`{NOTIF}` (`zzz_symbol_that_never_exists`)"),
            "FAIL",
            "nao encontrei",
        ),
    ]


def run_plan_audit_group() -> int:
    key = "LEDG-9998"
    write_ticket(ticket_state(ticket=key))
    print("\n--- ticket-state.py plan-audit ---")
    failures = 0
    for label, plan_text, expected, needle in PLAN_AUDIT_CASES():
        proc = subprocess.run(
            ["python3", os.path.join(HOOKS, "ticket-state.py"), "plan-audit", key,
             "--repos", "backend"],
            input=plan_text, capture_output=True, text=True,
        )
        out = proc.stdout + proc.stderr
        got = "PASS" if proc.returncode == 0 else "FAIL"
        ok = got == expected and (needle is None or needle in out)
        failures += 0 if ok else 1
        detail = "" if ok or needle is None or needle in out else f" (falta {needle!r})"
        print(f"  {'ok   ' if ok else 'FALHA'} {label:52} esperado={expected} obtido={got}{detail}")
    os.remove(state_path(key))
    return failures


def run_state_race_group() -> int:
    """A long command must not throw away what was written while it ran.

    `verify` holds its state across a ten-minute suite, and the workflow says to record the
    review and resolve the criteria during that time. It used to write the whole document at
    the end, silently reverting both.
    """
    import importlib.util

    # ticket-state.py imports its siblings by bare name, the way it does when run as a
    # script from its own directory.
    if HOOKS not in sys.path:
        sys.path.insert(0, HOOKS)

    spec = importlib.util.spec_from_file_location(
        "ticket_state", os.path.join(HOOKS, "ticket-state.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    print("\n--- ticket-state.py escrita concorrente ---")
    key = "LEDG-9997"
    write_ticket(ticket_state(ticket=key, review={"ran": False, "accepted": [], "rejected": []}))

    held = mod.load(key)                      # what a long command loaded at its start
    concurrent = mod.load(key)                # what another call writes while it runs
    concurrent["review"] = {"ran": True, "accepted": ["algo"], "rejected": []}
    concurrent["criteria"][0]["status"] = "met"
    mod.save(concurrent)

    held["verified"] = {"backend": {"head": "a" * 40}}
    mod.save_keys(held, "verified")

    after = mod.load(key)
    failures = 0
    for label, got, expected in (
        ("a review escrita no meio sobrevive", after["review"]["ran"], True),
        ("o criterio resolvido no meio sobrevive", after["criteria"][0]["status"], "met"),
        ("o verde do comando longo e gravado", after["verified"]["backend"]["head"], "a" * 40),
    ):
        ok = got == expected
        failures += 0 if ok else 1
        print(f"  {'ok   ' if ok else 'FALHA'} {label:52} esperado={expected} obtido={got}")
    os.remove(state_path(key))
    return failures


def run_group(title: str, hook: str, cases: list, with_lock: bool) -> int:
    if with_lock:
        os.makedirs(os.path.dirname(LOCK), exist_ok=True)
        with open(LOCK, "w") as fh:
            json.dump({"repo": "frontend", "attempts": 0}, fh)
    elif os.path.exists(LOCK):
        os.remove(LOCK)

    print(f"\n--- {title} ---")
    failures = 0
    for label, payload, expected in cases:
        # A branch-dependent DENY is only expected while that submodule sits on an
        # environment branch; on a working branch the correct answer is PASS.
        if hook == BRANCH_GUARD and expected == "DENY" and "force-push" not in label:
            sub = BE if "backend" in label or payload.get("cwd") == BE else FE
            branch = current_branch(sub)
            if branch not in {"develop", "tst", "ppr", "main"}:
                print(f"  skip  {label:52} ({os.path.basename(sub)} esta em '{branch}')")
                continue
        got = call(hook, payload)
        ok = got == expected
        failures += 0 if ok else 1
        print(f"  {'ok   ' if ok else 'FALHA'} {label:52} esperado={expected} obtido={got}")
    return failures


def main() -> int:
    print(f"root da corrida: {ROOT}")
    had_lock = os.path.exists(LOCK)
    failures = run_group("guard-protected-branch", BRANCH_GUARD, BRANCH_CASES, with_lock=False)
    failures += run_group("guard-test-surface (lock held)", SURFACE_GUARD, SURFACE_CASES, with_lock=True)
    failures += run_ticket_group()
    failures += run_parallel_group()
    failures += run_plan_audit_group()
    failures += run_state_race_group()

    if os.path.exists(LOCK) and not had_lock:
        os.remove(LOCK)

    print()
    if failures:
        print(f"{failures} CASO(S) A FALHAR")
        return 1
    total = (
        len(BRANCH_CASES) + len(SURFACE_CASES) + len(TICKET_CASES())
        + len(PARALLEL_CASES()) + len(PLAN_AUDIT_CASES()) + 3 + 1
    )
    print(f"TODOS OS {total} CASOS PASSAM")
    return 0


def cleanup(root: str) -> None:
    """Only ever remove a tree this run created, never one handed in by the caller."""
    if root.startswith(tempfile.gettempdir()) and os.path.basename(root).startswith(
        "dadosgov-guards-"
    ):
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    try:
        code = main()
    finally:
        cleanup(ROOT)
    sys.exit(code)
