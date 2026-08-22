#!/usr/bin/env python3
"""State machine for a guarded fix loop.

The guarantees live here as code rather than prose. A loop asked to turn a suite green can
always weaken the suite instead; these subcommands are what make that impossible to do
unnoticed.

  start   measure the baseline BEFORE any source change — the suite must actually be red,
          and the test/skip counts and commit are recorded — then take the lock that freezes
          the test surface (see guard-test-surface.py).
  verify  re-measure and enforce, consuming one of a bounded number of attempts:
            0. the suite exits 0  (the authority is the runner's exit code, never a regex)
            1. no test file or runner config touched since the baseline commit (asked of git)
            2. no weakening marker introduced in test or config files
            3. the collected-test count did not drop
            4. the skipped-test count did not rise
  end     release the lock (also logs the release, since releasing is itself a way out).
  status  print the current state.

Exit code 0 means the check passed, 1 means it failed, 2 means misuse. A failed verify is a
legitimate final answer — the attempt cap exists so that insisting is not an option.

Design limit, stated because it matters: this process can release its own lock. It makes
cheating visible and effortful, not impossible. The authority that cannot be reached from
here is CI — see .github/workflows/tests.yml in the frontend repo.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STATE_DIR = os.path.join(ROOT, ".claude", "state")
LOCK = os.path.join(STATE_DIR, "fix-loop.lock")
LOG = os.path.join(STATE_DIR, "fix-loop.log")
MAX_ATTEMPTS = 2

REPOS = {
    "frontend": {
        "dir": os.path.join(ROOT, "frontend"),
        "run": ["npx", "vitest", "run"],
        "count": None,  # taken from the run output's "Tests ... (N)" line
    },
    "backend": {
        "dir": os.path.join(ROOT, "backend"),
        "run": ["uv", "run", "pytest", "-q"],
        "count": ["uv", "run", "pytest", "--collect-only", "-q"],
    },
}

# Files whose content decides what is tested or asserted. Freezing the test files alone is
# not enough: narrowing the runner's include/addopts removes failures just as effectively.
FROZEN = re.compile(
    r"("
    r"/tests?/|/__tests__/|(^|/)test_[^/]*\.py|(^|/)conftest\.py"
    r"|\.spec\.(ts|tsx|js)|\.test\.(ts|tsx|js|py)"
    r"|(^|/)vitest\.config\.[cm]?ts|(^|/)playwright\.config\.[cm]?ts|(^|/)jest\.config"
    r"|(^|/)pyproject\.toml|(^|/)pytest\.ini|(^|/)setup\.cfg|(^|/)tox\.ini|(^|/)coverage\.rc"
    r"|(^|/)factories\.py"
    r")"
)

# Only applied to the frozen surface above, so ordinary source using MongoEngine's
# .skip(offset) for pagination is not mistaken for a disabled test.
WEAKENING = [
    (re.compile(r"^\+.*\.(skip|only|todo)\s*\("), "adicionou .skip/.only/.todo"),
    (re.compile(r"^\+.*@pytest\.mark\.(skip|skipif|xfail)"), "adicionou skip/skipif/xfail"),
    (re.compile(r"^\+.*\b(pytest\.skip|pytest\.xfail)\b"), "adicionou pytest.skip/xfail"),
    (re.compile(r"^\+.*(--ignore|--deselect|-k\s)"), "estreitou a selecao do runner"),
]


def sh(cmd, cwd, timeout=1800):
    """Run a command. Returns (returncode, output). 124 = timeout, 127 = missing binary."""
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
    try:
        with open(LOCK) as fh:
            return json.load(fh)
    except Exception as exc:
        print(f"AVISO: lock ilegivel ({exc}).", file=sys.stderr)
        return {"repo": "?", "corrupt": True}


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(LOCK, "w") as fh:
        json.dump(state, fh, indent=2)


def log(line: str) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(LOG, "a") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat()} {line}\n")


def measure(repo: str, scope: list[str]):
    """Run the suite. Returns (code, total, skipped, out).

    `code` is the authority: 0 means the runner itself says everything passed. total/skipped
    are best-effort and only ever used for the "did not shrink" comparisons.
    """
    cfg = REPOS[repo]
    code, out = sh(cfg["run"] + scope, cfg["dir"])

    skipped = None
    total = None

    if repo == "frontend":
        line = re.search(r"Tests\s+(.*?)\((\d+)\)", out)
        if line:
            total = int(line.group(2))
            sk = re.search(r"(\d+) skipped", line.group(1))
            skipped = int(sk.group(1)) if sk else 0
    else:
        sk = re.search(r"(\d+) skipped", out)
        skipped = int(sk.group(1)) if sk else 0
        ccode, cout = sh(cfg["count"] + scope, cfg["dir"])
        if ccode in (0, 5):
            m = re.search(r"(\d+)(?:/\d+)? tests? collected", cout)
            if m:
                total = int(m.group(1))

    return code, total, skipped, out


def cmd_start(args):
    if load_state():
        print("Ja existe um fix-loop ativo. Termina-o primeiro: fix-loop-state.py end", file=sys.stderr)
        return 2

    repo = args.repo
    cfg = REPOS[repo]
    scope = args.scope or []

    rc, head = sh(["git", "rev-parse", "HEAD"], cfg["dir"], timeout=30)
    head = head.strip()
    if rc != 0 or not re.fullmatch(r"[0-9a-f]{40}", head):
        print(f"Nao consegui resolver o HEAD de {repo}: {head!r}. Abortado.", file=sys.stderr)
        return 2

    print(f"A medir a baseline de {repo} (pode demorar)...")
    code, total, skipped, out = measure(repo, scope)

    if code == 0:
        print(
            "\nA SUITE ESTA VERDE. Um fix-loop sem falha inicial nao tem nada para provar:\n"
            "qualquer alteracao ficaria 'verde' sem demonstrar que corrigiu algo. Escreve\n"
            "primeiro o teste que reproduz o problema (fora do loop, onde os testes ainda\n"
            "podem ser editados) e so depois arranca.",
            file=sys.stderr,
        )
        return 1
    if code in (124, 127):
        print(
            f"\nA suite nao correu (codigo {code}: {out.strip()[:200]}). Sem uma medicao real\n"
            "nao ha baseline, e sem baseline o loop nao pode provar nada. Corrige a execucao\n"
            "dos testes primeiro.",
            file=sys.stderr,
        )
        return 2

    state = {
        "repo": repo,
        "scope": scope,
        "baseline_commit": head,
        "baseline_exit_code": code,
        "baseline_total": total,
        "baseline_skipped": skipped,
        "attempts": 0,
        "max_attempts": MAX_ATTEMPTS,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    save_state(state)
    log(f"START repo={repo} commit={head[:12]} exit={code} total={total} skipped={skipped}")

    print(f"\nBaseline registada e superficie de teste CONGELADA (lock: {LOCK}).")
    print(f"  commit ............ {head[:12]}")
    print(f"  exit code da suite  {code}  (vermelha, como tem de ser)")
    print(f"  testes recolhidos . {total if total is not None else 'indeterminado'}")
    print(f"  skipped ........... {skipped if skipped is not None else 'indeterminado'}")
    print(f"\n  tentativas: {MAX_ATTEMPTS} (cada `verify` consome uma)")
    print("  Corrige APENAS codigo-fonte. Depois: fix-loop-state.py verify")
    return 0


def cmd_verify(args):
    state = load_state()
    if not state:
        print("Nenhum fix-loop ativo.", file=sys.stderr)
        return 2
    if state.get("corrupt"):
        print("Lock corrompido. Termina o loop (`end`) e recomeca.", file=sys.stderr)
        return 2

    if state["attempts"] >= state["max_attempts"]:
        print(
            f"Limite de {state['max_attempts']} tentativas esgotado. PARA aqui: escreve o "
            "diagnostico do que tentaste, o que a falha diz e a tua hipotese, e devolve a "
            "decisao ao utilizador. Insistir e como o loop degenera.",
            file=sys.stderr,
        )
        return 1

    state["attempts"] += 1
    save_state(state)

    repo = state["repo"]
    cfg = REPOS[repo]
    base = state["baseline_commit"]
    problems = []

    # 1. the frozen surface must be untouched — asked of git, so it also catches writes made
    #    outside the Edit/Write/Bash paths the hook can see. A git failure here must abort the
    #    verdict, never pass vacuously.
    rc_names, changed = sh(["git", "diff", "--name-only", base], cfg["dir"], timeout=60)
    rc_untracked, untracked = sh(
        ["git", "ls-files", "--others", "--exclude-standard"], cfg["dir"], timeout=60
    )
    rc_diff, diff = sh(["git", "diff", base], cfg["dir"], timeout=120)
    if rc_names != 0 or rc_untracked != 0 or rc_diff != 0:
        print(
            f"\nABORTADO: o git falhou ao comparar com a baseline {base[:12]} "
            f"(codigos {rc_names}/{rc_untracked}/{rc_diff}). Sem essa comparacao as verificacoes "
            "1 e 2 passariam vazias, portanto nao emito veredicto.",
            file=sys.stderr,
        )
        return 2

    touched = [f for f in (changed + "\n" + untracked).splitlines() if f.strip()]
    frozen_touched = [f for f in touched if FROZEN.search(f)]
    if frozen_touched:
        problems.append(
            "Superficie congelada alterada (o fix tem de estar no codigo-fonte): "
            + ", ".join(frozen_touched)
        )

    # 2. weakening markers, looked for ONLY inside the frozen surface
    rc_fdiff, frozen_diff = sh(
        ["git", "diff", base, "--"] + (frozen_touched or ["."]), cfg["dir"], timeout=120
    )
    if rc_fdiff == 0 and frozen_touched:
        for line in frozen_diff.splitlines():
            for pattern, label in WEAKENING:
                if pattern.search(line):
                    problems.append(f"Marca de enfraquecimento ({label}): {line.strip()[:120]}")

    print(f"A re-medir {repo}...")
    code, total, skipped, out = measure(repo, state["scope"])

    # 0. the runner's exit code is the authority
    if code != 0:
        detail = {124: "timeout", 127: "runner nao encontrado"}.get(code, f"codigo {code}")
        problems.append(f"A suite NAO esta verde ({detail}). Ultimas linhas:\n    " + "\n    ".join(out.strip().splitlines()[-8:]))

    # 3 / 4. the suite must not have shrunk, nor gained skips
    base_total, base_skipped = state.get("baseline_total"), state.get("baseline_skipped")
    if base_total is not None and total is not None and total < base_total:
        problems.append(f"Testes recolhidos desceram: {base_total} -> {total}.")
    if base_total is not None and total is None:
        problems.append("Nao consegui contar os testes agora, mas havia contagem na baseline.")
    if base_skipped is not None and skipped is not None and skipped > base_skipped:
        problems.append(f"Testes skipped aumentaram: {base_skipped} -> {skipped}.")

    ok = not problems
    print("\n" + "=" * 66)
    print("VERDICTO DO FIX-LOOP:", "APROVADO" if ok else "REPROVADO")
    print("=" * 66)
    print(f"  repo .............. {repo}")
    print(f"  tentativa ......... {state['attempts']}/{state['max_attempts']}")
    print(f"  exit code ......... {state['baseline_exit_code']} -> {code}")
    print(f"  testes ............ {base_total} -> {total}")
    print(f"  skipped ........... {base_skipped} -> {skipped}")
    for p in problems:
        print(f"  PROBLEMA: {p}")
    log(f"VERIFY repo={repo} attempt={state['attempts']} ok={ok} exit={code} total={total}")
    if ok:
        print("\n  Provado: a suite que estava vermelha esta verde, sem tocar em testes nem na")
        print("  configuracao do runner, sem marcas de enfraquecimento, sem perder testes e")
        print("  sem novos skips.")
        print("  NAO provado: que o fix ao codigo-fonte seja bom. Um retorno hardcoded satisfaz")
        print("  um teste correto tao bem como o fix certo — isso e o que a review do PR apanha.")
        print("\n  Termina o loop com: fix-loop-state.py end")
    return 0 if ok else 1


def cmd_end(args):
    if not os.path.exists(LOCK):
        print("Nenhum fix-loop ativo.")
        return 0
    state = load_state() or {}
    try:
        os.remove(LOCK)
    except OSError as exc:
        print(f"Nao consegui remover o lock: {exc}", file=sys.stderr)
        return 2
    log(f"END repo={state.get('repo')} attempts={state.get('attempts')}")
    print(f"Fix-loop terminado ({state.get('repo')}). Superficie de teste destravada.")
    print(f"Registo em {LOG} — libertar o lock e, em si, uma saida, por isso fica anotado.")
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

    p_start = sub.add_parser("start", help="measure the baseline and freeze the test surface")
    p_start.add_argument("repo", choices=sorted(REPOS))
    p_start.add_argument("scope", nargs="*", help="optional test paths to narrow the run")
    p_start.set_defaults(func=cmd_start)

    for name, fn, helptext in (
        ("verify", cmd_verify, "enforce the guarantees, consuming one attempt"),
        ("end", cmd_end, "release the lock"),
        ("status", cmd_status, "print the current state"),
    ):
        sp = sub.add_parser(name, help=helptext)
        sp.set_defaults(func=fn)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
