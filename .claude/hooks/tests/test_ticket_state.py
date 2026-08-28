#!/usr/bin/env python3
"""Regression tests for concurrent writes to one ticket's state file.

Run: python3 .claude/hooks/tests/test_ticket_state.py

The bug these exist for: `verify` read the state at process start, ran a suite for minutes,
then wrote its whole in-memory snapshot back. The skill recommends starting the two repos'
verifies in the background, so each wrote a snapshot taken before the other had finished
and the second write dropped the first one's recorded green -- both printed VERDE, and
`status` then said "sem verde registado" for a repo that had just passed.

So the cases here are about the write, not the suites: `run_suites` is driven directly with
a `sleep` standing in for pytest, which is what gives the two writers a window wide enough
for the race to be deterministic rather than a once-in-a-while flake.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

REAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HOOKS = os.path.join(REAL_ROOT, ".claude", "hooks")
STATE = os.path.join(HOOKS, "ticket-state.py")
KEY = "LEDG-9980"

# One writer, driven straight into run_suites: the function that clobbered. `sleep` stands
# in for the suite so both writers are still inside it when the other one starts.
WRITER = r'''
import argparse, importlib.util, os, sys
sys.path.insert(0, os.environ["HOOKS"])
spec = importlib.util.spec_from_file_location("ts", os.path.join(os.environ["HOOKS"], "ticket-state.py"))
ts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts)

repo, secs = sys.argv[1], sys.argv[2]
args = argparse.Namespace(key=os.environ["KEY"], repo=repo)
plan = {
    "mode": "impacted", "base": None, "changed": [], "lint_cmds": [],
    "lint_paths": None, "test_cmd": ["sleep", secs], "impacted_files": [f"{repo}/x"],
    "full_reason": None, "notes": [],
}
state = ts.require(args.key)
head = repo[0] * 40
sys.exit(ts.run_suites(args, state, plan, os.environ["ROOT"], head))
'''


def build_root() -> str:
    root = tempfile.mkdtemp(prefix="dadosgov-tstate-")
    os.makedirs(os.path.join(root, ".claude", "state"))
    os.symlink(HOOKS, os.path.join(root, ".claude", "hooks"))
    # `point` refuses a sha git does not recognise, so the repos have to be the real ones;
    # nothing here writes to them (state lives in the sandbox's own .claude/state).
    for repo in ("backend", "frontend"):
        os.symlink(os.path.join(REAL_ROOT, repo), os.path.join(root, repo))
    return root


def run(root: str, *args):
    env = {**os.environ, "CLAUDE_HARNESS_ROOT": root}
    p = subprocess.run(
        ["python3", STATE, *args], capture_output=True, text=True, cwd=root, env=env
    )
    return p.returncode, p.stdout + p.stderr


def writer(root: str, repo: str, secs: str):
    env = {**os.environ, "CLAUDE_HARNESS_ROOT": root, "HOOKS": HOOKS, "ROOT": root, "KEY": KEY}
    return subprocess.Popen(
        ["python3", "-c", WRITER, repo, secs],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=root, env=env,
    )


def state_of(root: str) -> dict:
    with open(os.path.join(root, ".claude", "state", f"ticket-{KEY}.json")) as fh:
        return json.load(fh)


def check(label: str, got, want) -> int:
    ok = got == want
    print(f"  {'ok  ' if ok else 'FALHA'} {label}" + ("" if ok else f"  (obtido {got!r}, esperado {want!r})"))
    return 0 if ok else 1


def case_parallel_verify_keeps_both_greens(root: str) -> int:
    """Dois verifies em paralelo (backend e frontend) registam ambos o verde."""
    run(root, "start", KEY, "--title", "concorrencia")
    run(root, "claim", KEY, "--repos", "backend,frontend")
    a, b = writer(root, "backend", "2"), writer(root, "frontend", "1")
    outs = [a.communicate()[0], b.communicate()[0]]
    failures = check("ambos os processos sairam 0", [a.returncode, b.returncode], [0, 0])
    failures += check("ambos imprimiram VERDE", [o.count("VERDICTO: VERDE") for o in outs], [1, 1])
    verified = state_of(root)["verified"]
    failures += check("verified tem os dois repos", sorted(verified), ["backend", "frontend"])
    failures += check("head do backend intacto", verified.get("backend", {}).get("head"), "b" * 40)
    failures += check("head do frontend intacto", verified.get("frontend", {}).get("head"), "f" * 40)
    return failures


def case_verify_does_not_revive_an_ended_ticket(root: str) -> int:
    """Um `end` a meio da suite: o verify avisa e nao ressuscita o ficheiro."""
    run(root, "start", KEY, "--title", "fechado a meio")
    run(root, "claim", KEY, "--repos", "backend")
    run(root, "criteria", KEY, "--add", "criterio")
    run(root, "criteria", KEY, "--resolve", "1", "--status", "waived", "--evidence", "teste")
    proc = writer(root, "backend", "2")
    rc, out = run(root, "end", KEY, "--abandon")
    seen = proc.communicate()[0]
    path = os.path.join(root, ".claude", "state", f"ticket-{KEY}.json")
    failures = check("o estado continua arquivado", os.path.exists(path), False)
    failures += check("o verify avisou que nao registou", "NAO ficou registado" in seen, True)
    failures += check("o .lock nao ficou para tras", os.path.exists(path + ".lock"), False)
    return failures


def case_concurrent_point_writes_survive(root: str) -> int:
    """Quatro `point` simultaneos: nenhum apaga o commit do outro."""
    shas = subprocess.run(
        ["git", "-C", os.path.join(REAL_ROOT, "backend"), "log", "-4", "--format=%H", "develop"],
        capture_output=True, text=True,
    ).stdout.split()
    if len(shas) < 4:
        print("  ok   (sem 4 commits em backend/develop para usar — caso ignorado)")
        return 0
    run(root, "start", KEY, "--title", "pontos")
    # The points are written straight into the state, as in test_guards: what is under test
    # is the state->write map, and `plan-approved` would drag in the digest, the audit and
    # the criteria gates without making the race any more real.
    path = os.path.join(root, ".claude", "state", f"ticket-{KEY}.json")
    with open(path) as fh:
        state = json.load(fh)
    state["repos"] = ["backend"]
    state["phase"] = "approved"
    state["points"] = [
        {"n": n, "summary": f"ponto {n}", "status": "pending", "commit": None,
         "proof": None, "blocked_reason": None}
        for n in (1, 2, 3, 4)
    ]
    with open(path, "w") as fh:
        json.dump(state, fh)
    env = {**os.environ, "CLAUDE_HARNESS_ROOT": root}
    procs = [
        subprocess.Popen(
            ["python3", STATE, "point", KEY, "done", str(n), "--commit", shas[n - 1],
             "--repo", "backend", "--proof", f"test:x{n}"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=root, env=env,
        )
        for n in (1, 2, 3, 4)
    ]
    outs = [pr.communicate()[0] for pr in procs]
    failures = check("os 4 processos sairam 0", [pr.returncode for pr in procs], [0, 0, 0, 0])
    if failures:
        print("".join(outs))
        return failures
    points = {p["n"]: p.get("commit") for p in state_of(root)["points"]}
    return check(
        "os 4 commits sobreviveram",
        [points.get(n) for n in (1, 2, 3, 4)],
        [shas[n - 1] for n in (1, 2, 3, 4)],
    )


CASES = [
    case_parallel_verify_keeps_both_greens,
    case_verify_does_not_revive_an_ended_ticket,
    case_concurrent_point_writes_survive,
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
    print(f"{failures} VERIFICACAO(OES) A FALHAR" if failures else "TODAS AS VERIFICACOES PASSAM")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
