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


def backend_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=BE, capture_output=True, text=True
    ).stdout.strip()


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
            plan(f"`{NOTIF}` (`+purge_orphan_discussion_notifications`)"),
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
            plan(f"`{NOTIF}` (`purge_orphan_discussion_notifications`)"),
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


def load_module(name: str, filename: str):
    """Import a hyphenated hook as a module, so its pure functions can be tested directly."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, os.path.join(HOOKS, filename))
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, HOOKS)
    spec.loader.exec_module(module)
    return module


SCOPE_CASES = 18


def _with_env(module, key: str, value: str):
    """Read module.pytest_workers() with one environment variable set."""
    before = os.environ.get(key)
    os.environ[key] = value
    try:
        return module.pytest_workers()
    finally:
        if before is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = before


def run_scope_group() -> int:
    """The two decisions that made /ticket slow: what invalidates a green, and what to run.

    Both are pure enough to test directly, and both are load-bearing: a green that survives
    too much authorises a push over untested code, and a resolver that selects too little
    proves nothing while looking green.
    """
    print("\n--- ambito do verde e do impacted ---")
    failures = 0
    patterns = load_module("harness_patterns", "harness_patterns.py")
    ts = load_module("ticket_state", "ticket-state.py")

    def check(label: str, got, expected) -> None:
        nonlocal failures
        ok = got == expected
        failures += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FALHA'} {label}" + ("" if ok else f"  (got={got!r})"))

    # A throwaway repo, so the "what changed between these two commits" plumbing is exercised
    # for real instead of mocked.
    tmp = tempfile.mkdtemp(prefix="dadosgov-scope-")
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp, capture_output=True, text=True, check=False)
    git("init", "-q")
    git("config", "user.email", "t@t.t")
    git("config", "user.name", "t")
    open(os.path.join(tmp, "foo.py"), "w").write("x = 1\n")
    git("add", "-A"); git("commit", "-qm", "c1")
    c1 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp, capture_output=True, text=True).stdout.strip()
    open(os.path.join(tmp, "CHANGELOG.md"), "w").write("- entry\n")
    open(os.path.join(tmp, "docs"), "w").close()
    os.remove(os.path.join(tmp, "docs"))
    git("add", "-A"); git("commit", "-qm", "c2")
    c2 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp, capture_output=True, text=True).stdout.strip()
    open(os.path.join(tmp, "foo.py"), "w").write("x = 2\n")
    git("add", "-A"); git("commit", "-qm", "c3")
    c3 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp, capture_output=True, text=True).stdout.strip()

    def run(cmd, cwd):
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    check("um commit so de CHANGELOG nao invalida o verde",
          patterns.source_drift(run, tmp, c1, c2), [])
    check("um commit de codigo invalida o verde",
          patterns.source_drift(run, tmp, c2, c3), ["foo.py"])
    check("um sha ilegivel nao vale como 'nada mudou'",
          patterns.source_drift(run, tmp, "0" * 40, c3), None)
    check(".github/workflows nao e inerte (decide o que o CI corre)",
          patterns.non_inert([".github/workflows/tests.yml"]), [".github/workflows/tests.yml"])
    shutil.rmtree(tmp, ignore_errors=True)

    # The resolver, against the real backend tree.
    wide, reason = ts.impacted_backend(["udata/api/limits.py"], BE)
    check("infra partilhada escala para a suite completa", (wide, bool(reason)), (set(), True))
    _, reason = ts.impacted_backend(["udata/templates/mail/confirm.html"], BE)
    check("ficheiro nao-Python sem mapeamento escala para completa", bool(reason), True)
    _, reason = ts.impacted_backend([], BE)
    check("diff vazio nunca e um verde", bool(reason), True)
    tests, reason = ts.impacted_backend(["udata/core/dataset/api.py"], BE)
    check("um modulo do core resolve os seus testes",
          (reason, "udata/tests/dataset" in tests), (None, True))
    tests, reason = ts.impacted_backend(["udata/tests/dataset/test_proxy_download.py"], BE)
    check("um teste alterado corre-se a si mesmo",
          (reason, tests), (None, {"udata/tests/dataset/test_proxy_download.py"}))
    # The gate is only worth reading if a local red means what CI will say, so the runner
    # shape and the settings CI uses are asserted, not assumed.
    # Not CI's worker count (4 against CI's 2, measured stable x3 where -n 8 is not), but
    # everything else is CI's, and the divergence has to stay overridable and bounded.
    check("a suite corre com xdist e loadscope",
          ts.SUITES["backend"]["test"][-4:-2] + ts.SUITES["backend"]["test"][-1:],
          ["-n", "4", "loadscope"])
    check("DADOSGOV_PYTEST_WORKERS manda",
          _with_env(ts, "DADOSGOV_PYTEST_WORKERS", "2"), "2")
    check("um valor absurdo cai na omissao",
          _with_env(ts, "DADOSGOV_PYTEST_WORKERS", "banana"), "4")
    check("a suite completa corre o pacote, como o CI",
          ts.SUITES["backend"]["target_all"], ["udata"])
    # The positional belongs to the full run only. With it baked into the runner, a scoped
    # run appended its paths to the whole package and quietly ran everything -- reported as
    # `impacted`, which is worse than being slow.
    check("o pacote nao esta no runner, senao um ambito corre tudo",
          "udata" in ts.SUITES["backend"]["test"], False)
    check("udata.cfg fica de fora, como no CI",
          ts.suite_isolation({"ticket": "LEDG-9999"}, "backend", BE)[0].get("UDATA_SETTINGS"),
          ts.SETTINGS_NONE)

    # And the same rules as the push gate sees them. The gate denies this sandbox for the
    # CHANGELOG (the real checkout sits on develop with no branch commits), so what is
    # asserted here is the *reason*: whether the recorded green was accepted or not.
    def deny_reason(verified: dict) -> str:
        write_ticket(ticket_state(branch={"backend": backend_branch()}, verified=verified))
        payload = {"tool_name": "Bash",
                   "tool_input": {"command": "git push -u origin HEAD"}, "cwd": BE}
        out = subprocess.run(
            ["python3", os.path.join(HOOKS, TICKET_GUARD)],
            input=json.dumps(payload), capture_output=True, text=True,
        ).stdout
        if not out.strip():
            return ""
        return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]

    head = backend_head()
    reason = deny_reason({"backend": {"head": head, "scope": "impacted",
                                      "files": ["udata/tests/dataset"]}})
    check("um verde impacted neste HEAD nao e motivo de recusa",
          "verify" in reason.lower() or "narrow" in reason.lower(), False)
    reason = deny_reason({"backend": {"head": head, "scope": "narrow"}})
    check("um verde narrow continua a ser recusado", "NARROW" in reason, True)

    rc, prev = run(["git", "rev-parse", "HEAD~1"], BE)
    drift = patterns.source_drift(run, BE, prev.strip(), head) if rc == 0 else None
    reason = deny_reason({"backend": {"head": prev.strip(), "scope": "impacted"}})
    if drift:
        check("codigo commitado depois do verde invalida-o", "mudou codigo" in reason, True)
    else:
        check("commit inerte depois do verde nao o invalida", "mudou codigo" in reason, False)
    return failures


def main() -> int:
    print(f"root da corrida: {ROOT}")
    had_lock = os.path.exists(LOCK)
    failures = run_group("guard-protected-branch", BRANCH_GUARD, BRANCH_CASES, with_lock=False)
    failures += run_group("guard-test-surface (lock held)", SURFACE_GUARD, SURFACE_CASES, with_lock=True)
    failures += run_ticket_group()
    failures += run_parallel_group()
    failures += run_plan_audit_group()
    failures += run_scope_group()

    if os.path.exists(LOCK) and not had_lock:
        os.remove(LOCK)

    print()
    if failures:
        print(f"{failures} CASO(S) A FALHAR")
        return 1
    total = (
        len(BRANCH_CASES) + len(SURFACE_CASES) + len(TICKET_CASES())
        + len(PARALLEL_CASES()) + len(PLAN_AUDIT_CASES()) + 1 + SCOPE_CASES
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
