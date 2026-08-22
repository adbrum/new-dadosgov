#!/usr/bin/env python3
"""State machine for a guarded fix loop.

The point of this file is that the loop's guarantees are code, not prose. A loop asked
to turn a suite green can always weaken the suite instead; these subcommands make that
mechanically impossible to do unnoticed:

  start   capture the baseline BEFORE any source change — which tests fail, how many
          tests exist, and the exact commit — then take the lock that freezes the
          test surface (see guard-test-surface.py).
  attempt claim one of a bounded number of attempts; refuses past the cap.
  verify  re-measure and enforce, in this order:
            1. no test file was touched since the baseline commit (git, not patterns)
            2. no weakening markers were introduced (skip/only/xfail, deleted asserts)
            3. the test count did not drop
            4. every baseline failure now passes
            5. no new failure appeared
  end     release the lock.
  status  print the current state.

Exit code 0 means the check passed, 1 means it failed, 2 means misuse. verify prints a
verdict block meant to be pasted into a report — a failed verify is a legitimate final
answer, not something to retry around.
"""

import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STATE_DIR = os.path.join(ROOT, ".claude", "state")
LOCK = os.path.join(STATE_DIR, "fix-loop.lock")
MAX_ATTEMPTS = 2

REPOS = {
    "frontend": {
        "dir": os.path.join(ROOT, "frontend"),
        "run": ["npx", "vitest", "run"],
    },
    "backend": {
        "dir": os.path.join(ROOT, "backend"),
        "run": ["uv", "run", "pytest", "-q"],
    },
}

TEST_PATH = re.compile(
    r"(/tests?/|/__tests__/|(^|/)test_[^/]*\.py$|\.spec\.(ts|tsx|js)$|\.test\.(ts|tsx|js|py)$)"
)
WEAKENING = [
    (re.compile(r"^\+.*\.(skip|only)\s*\("), "adicionou .skip/.only"),
    (re.compile(r"^\+.*@pytest\.mark\.(skip|xfail)"), "adicionou skip/xfail no pytest"),
    (re.compile(r"^\+.*\b(xfail|pytest\.skip)\b"), "adicionou xfail/pytest.skip"),
    (re.compile(r"^\+.*it\.todo\b"), "converteu um teste em it.todo"),
]


def sh(cmd, cwd, timeout=900):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return 124, "<timeout>"
    except FileNotFoundError:
        return 127, "<comando nao encontrado>"


def load_state():
    if not os.path.exists(LOCK):
        return None
    with open(LOCK) as fh:
        return json.load(fh)


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(LOCK, "w") as fh:
        json.dump(state, fh, indent=2)


def measure(repo: str, scope: list[str]):
    """Run the suite and return (failures, total_tests, raw_output)."""
    cfg = REPOS[repo]
    code, out = sh(cfg["run"] + scope, cfg["dir"])

    failures = []
    total = None

    if repo == "frontend":
        m = re.search(r"Tests\s+(?:(\d+) failed \| )?(\d+) passed(?: \| (\d+) skipped)?\s+\((\d+)\)", out)
        if m:
            total = int(m.group(4))
        failures = sorted(set(re.findall(r"(?:FAIL|×)\s+(\S+\.(?:test|spec)\.[a-z]+)\s*>\s*(.+?)\s*$", out, re.M)))
        failures = [f"{f[0]} :: {f[1]}" for f in failures]
    else:
        m = re.search(r"(\d+) (?:passed|failed)", out)
        collected = re.search(r"(\d+) tests? collected", out)
        if collected:
            total = int(collected.group(1))
        failures = sorted(set(re.findall(r"^(FAILED|ERROR)\s+(\S+)", out, re.M)))
        failures = [f[1] for f in failures]

    return failures, total, out, code


def cmd_start(args):
    if load_state():
        print("Ja existe um fix-loop ativo. Termina-o primeiro: fix-loop-state.py end", file=sys.stderr)
        return 2
    repo = args.repo
    cfg = REPOS[repo]
    scope = args.scope or []

    code, head = sh(["git", "rev-parse", "HEAD"], cfg["dir"])
    head = head.strip()

    print(f"A medir a baseline de {repo} (pode demorar)...")
    failures, total, out, _ = measure(repo, scope)

    if not failures:
        print(
            "\nNENHUM teste falha na baseline.\n"
            "Um fix-loop sem falha inicial nao tem nada para provar: qualquer alteracao ficaria\n"
            "'verde' sem demonstrar que corrigiu algo. Escreve primeiro o teste que reproduz o\n"
            "problema (fora do loop, onde os testes ainda podem ser editados), e so depois arranca.",
            file=sys.stderr,
        )
        return 1

    state = {
        "repo": repo,
        "scope": scope,
        "baseline_commit": head,
        "baseline_failures": failures,
        "baseline_total": total,
        "attempts": 0,
        "max_attempts": MAX_ATTEMPTS,
    }
    save_state(state)
    print(f"\nBaseline registada e superficie de teste CONGELADA (lock: {LOCK}).")
    print(f"  commit .......... {head[:12]}")
    print(f"  testes totais ... {total}")
    print(f"  a falhar ({len(failures)}):")
    for f in failures:
        print(f"    - {f}")
    print(f"\n  tentativas permitidas: {MAX_ATTEMPTS}")
    print("  Corrige APENAS codigo-fonte. Depois: fix-loop-state.py verify")
    return 0


def cmd_attempt(args):
    state = load_state()
    if not state:
        print("Nenhum fix-loop ativo.", file=sys.stderr)
        return 2
    if state["attempts"] >= state["max_attempts"]:
        print(
            f"Limite de {state['max_attempts']} tentativas esgotado. PARA aqui: escreve o "
            "diagnostico do que tentaste e porque falhou, e devolve a decisao ao utilizador. "
            "Insistir e como o loop degenera.",
            file=sys.stderr,
        )
        return 1
    state["attempts"] += 1
    save_state(state)
    print(f"Tentativa {state['attempts']}/{state['max_attempts']}.")
    return 0


def cmd_verify(args):
    state = load_state()
    if not state:
        print("Nenhum fix-loop ativo.", file=sys.stderr)
        return 2

    repo = state["repo"]
    cfg = REPOS[repo]
    problems = []

    # 1. the test surface must be untouched since the baseline commit — asked of git,
    #    not inferred from patterns, so it also catches writes made outside Edit/Write.
    _, changed = sh(["git", "diff", "--name-only", state["baseline_commit"]], cfg["dir"])
    _, untracked = sh(["git", "ls-files", "--others", "--exclude-standard"], cfg["dir"])
    touched = [f for f in (changed + "\n" + untracked).splitlines() if f.strip()]
    test_touched = [f for f in touched if TEST_PATH.search(f)]
    if test_touched:
        problems.append(
            "Ficheiros de teste alterados durante o loop (o fix tem de estar no codigo-fonte): "
            + ", ".join(test_touched)
        )

    # 2. weakening markers introduced anywhere in the diff
    _, diff = sh(["git", "diff", state["baseline_commit"]], cfg["dir"])
    for line in diff.splitlines():
        for pattern, label in WEAKENING:
            if pattern.search(line):
                problems.append(f"Marca de enfraquecimento no diff ({label}): {line.strip()[:120]}")

    print(f"A re-medir {repo}...")
    failures, total, out, _ = measure(repo, state["scope"])

    # 3. the number of tests must not drop
    base_total = state.get("baseline_total")
    if base_total and total is not None and total < base_total:
        problems.append(
            f"O numero de testes desceu: {base_total} -> {total}. Testes removidos contam como "
            "enfraquecimento mesmo com a suite verde."
        )

    # 4. every baseline failure must now pass
    still_failing = [f for f in state["baseline_failures"] if f in failures]

    # 5. no new failure
    new_failures = [f for f in failures if f not in state["baseline_failures"]]
    if new_failures:
        problems.append("Falhas NOVAS introduzidas: " + ", ".join(new_failures[:5]))

    ok = not problems and not still_failing
    print("\n" + "=" * 64)
    print("VERDICTO DO FIX-LOOP:", "APROVADO" if ok else "REPROVADO")
    print("=" * 64)
    print(f"  repo ................. {repo}")
    print(f"  tentativas ........... {state['attempts']}/{state['max_attempts']}")
    print(f"  testes ............... {base_total} -> {total}")
    print(f"  falhas da baseline ... {len(state['baseline_failures'])}")
    print(f"  ainda a falhar ....... {len(still_failing)}")
    for f in still_failing:
        print(f"      - {f}")
    for p in problems:
        print(f"  PROBLEMA: {p}")
    if ok:
        print("\n  Provado: as falhas registadas antes da alteracao passam agora, sem testes")
        print("  tocados, sem marcas de enfraquecimento e sem regressoes.")
        print("  A review do PR continua a ser necessaria: isto prova que o teste nao foi")
        print("  adulterado, nao que o fix ao codigo-fonte seja bom.")
        print("\n  Termina o loop com: fix-loop-state.py end")
    return 0 if ok else 1


def cmd_end(args):
    if not os.path.exists(LOCK):
        print("Nenhum fix-loop ativo.")
        return 0
    state = load_state()
    os.remove(LOCK)
    print(f"Fix-loop terminado ({state.get('repo')}). Superficie de teste destravada.")
    return 0


def cmd_status(args):
    state = load_state()
    if not state:
        print("Nenhum fix-loop ativo. A superficie de teste esta editavel normalmente.")
        return 0
    print(json.dumps(state, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_start = sub.add_parser("start", help="capture the baseline and freeze the test surface")
    p_start.add_argument("repo", choices=sorted(REPOS))
    p_start.add_argument("scope", nargs="*", help="optional test paths to narrow the run")
    p_start.set_defaults(func=cmd_start)

    for name, fn, helptext in (
        ("attempt", cmd_attempt, "claim one bounded attempt"),
        ("verify", cmd_verify, "enforce the guarantees and print a verdict"),
        ("end", cmd_end, "release the lock"),
        ("status", cmd_status, "print the current state"),
    ):
        sp = sub.add_parser(name, help=helptext)
        sp.set_defaults(func=fn)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
