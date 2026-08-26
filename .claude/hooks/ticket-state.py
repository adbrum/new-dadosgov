#!/usr/bin/env python3
"""State machine for the /ticket (jira-ticket-workflow) loop.

The workflow's promises live here as recorded state instead of conversation memory: which
phase we are in, which plan was approved (by digest), which point maps to which commit,
which acceptance criteria exist and how each was resolved, and the exact HEAD the suites
last ran green on. `guard-ticket-workflow.py` reads this file to turn the skill's "Never …"
rules into denials; this script is the only writer.

The problem it solves: a cleared or compacted session used to lose the whole loop. The
state file is what makes `/ticket LEDG-<n>` resume at the right point instead of re-reading
the ticket, re-planning, and re-implementing work that already has commits.

Design limit, stated because it matters (same as fix-loop-state.py): this process can flip
its own flags. The mechanism makes skipping a step visible and effortful — every transition
is logged with a timestamp — not impossible. The authority that cannot be faked from here
is `verify`, whose verdict is the runners' exit codes on the current HEAD, and after that
the CI job and the human reviewer.

Exit codes: 0 the step passed, 1 it failed, 2 misuse.
"""

import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from harness_patterns import CONVENTIONAL, FROZEN_PATH  # local: sits beside this hook
from harness_root import FILE_ROOT, candidates, harness_root

ROOT = harness_root()
STATE_DIR = os.path.join(ROOT, ".claude", "state")
LOG = os.path.join(STATE_DIR, "ticket.log")
KEY_RE = re.compile(r"^LEDG-\d+$")

# Why a ticket stopped, from a closed set: five parked tickets are only triageable if the
# reason is a value you can group by, not a paragraph. Add a code here before using it.
REASON_CODES = (
    "no-criteria",  # the ticket never said what "done" means
    "ambiguous-repo",  # the evidence does not say which submodule this lands in
    "two-repo-order",  # both repos, and the deploy order is not derivable
    "plan-audit-reprovado",  # the plan failed its audit twice
    "fixloop-reprovado",  # /fix-loop ended REPROVADO, so the diagnosis is the answer
    "review-finding",  # a review finding that cannot be fixed inside this ticket
    "gh-unavailable",  # no authenticated gh, so the PR cannot be opened here
    "attribution-deadlock",  # a commit in range carries AI attribution: the push gate is shut
    "blocked-prerequisite",  # the blocked point is what the remaining points depend on
    "other",  # anything else -- the question and the diagnosis carry the weight
)

SUITES = {
    "backend": {
        "dir": os.path.join(ROOT, "backend"),
        "lint": [
            ["uv", "run", "ruff", "check", "."],
            ["uv", "run", "ruff", "format", "--check", "."],
        ],
        # -n 2 --dist loadscope, the same shape CI runs: minutes instead of twenty.
        # loadscope keeps a class or module on one worker and each worker gets its own Mongo
        # database, but the split is NOT reliable here: udata/tests/apiv2/test_topics.py and
        # the rate-limit families fail under xdist on origin/develop too, and pass serially.
        # So a red xdist run is a question, not a verdict -- `serial` re-runs exactly the
        # tests that failed, and only what fails twice counts. Deliberately not
        # `inv test --ci`, whose i18nc pre-task compiles translations into .mo files that
        # are not git-ignored -- that would dirty the very working tree this gate inspects.
        "test": ["uv", "run", "pytest", "-n", "2", "--dist", "loadscope"],
        "serial": ["uv", "run", "pytest", "-p", "no:randomly"],
        # Two pytest runs in backend/ share the Mongo test databases and fake regressions
        # for each other. Never start a second one.
        "exclusive": "pytest",
    },
    "frontend": {
        "dir": os.path.join(ROOT, "frontend"),
        "lint": [["npm", "run", "lint"], ["npx", "tsc", "--noEmit"]],
        "test": ["npx", "vitest", "run"],
        "exclusive": None,
    },
}


def path_for(key: str) -> str:
    return os.path.join(STATE_DIR, f"ticket-{key}.json")


def log(line: str) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(LOG, "a") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat()} {line}\n")


def load(key: str):
    try:
        with open(path_for(key)) as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except Exception as exc:
        print(f"Estado de {key} ilegivel ({exc}).", file=sys.stderr)
        sys.exit(2)


def save(state: dict) -> None:
    """Write the whole file atomically -- a torn read disables that ticket's gates.

    The reader (`guard-ticket-workflow.py`) treats unparseable state as "skip this
    ticket", which is the right call for a guard that must not crash a tool call but
    means a half-written file silently unlocks the repos. With several sessions
    writing their own tickets this stopped being hypothetical, so: temp file in the
    same directory, then os.replace, which is atomic on the same filesystem.
    """
    os.makedirs(STATE_DIR, exist_ok=True)
    final = path_for(state["ticket"])
    fd, tmp = tempfile.mkstemp(dir=STATE_DIR, prefix=".ticket-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, final)
    except Exception:
        os.unlink(tmp)
        raise


def save_keys(state: dict, *keys: str) -> dict:
    """Write only `keys` back, onto whatever is on disk now.

    save() writes the whole document, which is fine for a command that loads, mutates and
    exits. `verify` is not that: it holds its state across a ten-minute suite, and the
    workflow explicitly says to record the review and resolve the criteria while that runs.
    Writing the whole document at the end therefore threw away everything written in
    between. Re-read, copy across only what this command owns, save that.
    """
    fresh = load(state["ticket"]) or state
    for key in keys:
        fresh[key] = state[key]
    save(fresh)
    return fresh


def require(key: str) -> dict:
    state = load(key)
    if not state:
        print(
            f"Nao existe estado para {key}. Corre primeiro: "
            f"python3 .claude/hooks/ticket-state.py start {key}",
            file=sys.stderr,
        )
        sys.exit(2)
    return state


def sh(cmd, cwd, timeout=1800, env=None):
    """Run a command. Returns (returncode, output). 124 = timeout, 127 = missing binary."""
    try:
        merged = {**os.environ, **env} if env else None
        p = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=merged
        )
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return 124, "<timeout>"
    except FileNotFoundError:
        return 127, "<comando nao encontrado>"


def repo_dir(state: dict, repo: str) -> str:
    """Where this ticket's copy of `repo` lives.

    A ticket worked in a per-ticket git worktree records that path once, in `workdir`;
    everything that touches the repo -- the suites, the lint hook, the guards -- reads
    it from here instead of assuming the primary checkout. No worktree, no change.
    """
    workdir = (state or {}).get("workdir")
    return os.path.join(workdir, repo) if workdir else SUITES[repo]["dir"]


def summary_line(state: dict) -> str:
    done = sum(1 for p in state["points"] if p["status"] == "done")
    resolved = sum(1 for c in state["criteria"] if c["status"] != "pending")
    branches = ", ".join(f"{r}:{b}" for r, b in state.get("branch", {}).items()) or "-"
    parked = state.get("parked")
    return (
        f"{state['ticket']} fase={state['phase']}"
        f"{' PAUSADO' if state.get('paused') else ''}"
        f"{' ESTACIONADO:' + parked['reason_code'] if parked else ''} "
        f"pontos={done}/{len(state['points'])} "
        f"criterios={resolved}/{len(state['criteria'])} branch={branches}"
    )


def cmd_start(args):
    if not KEY_RE.match(args.key):
        print(f"Chave invalida: {args.key!r} (esperado LEDG-<n>).", file=sys.stderr)
        return 2
    existing = load(args.key)
    if existing:
        print(f"Ja existe estado para {args.key} — isto e uma RETOMA, nao um recomeco.")
        print(f"  {summary_line(existing)}")
        print("\nO ficheiro prevalece sobre a memoria da conversa. Nao voltes a ler o ticket")
        print("nem a planear o que ja esta aqui; continua na fase registada.\n")
        print(json.dumps(existing, indent=2, ensure_ascii=False))
        return 0
    state = {
        "ticket": args.key,
        "title": args.title or "",
        "source": args.source,
        "phase": "started",
        "paused": False,
        "repos": [],
        "workdir": None,
        "root": ROOT,
        "deploy_order": None,
        "branch": {},
        "plan_digest": None,
        "plan_delegated_to_fable": False,
        "precedents": [],
        "points": [],
        "criteria": [],
        "verified": {},
        "review": {"ran": False, "accepted": [], "rejected": []},
        "pr": {},
        "overrides": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    save(state)
    log(f"START {args.key} source={args.source}")
    print(f"Estado criado: {path_for(args.key)} (fase: started).")
    print("A partir de agora as escritas em backend/ e frontend/ estao BLOQUEADAS ate")
    print("`plan-approved` — o plano aprovado pelo utilizador e o que desbloqueia o codigo.")
    return 0


def cmd_criteria(args):
    state = require(args.key)
    if args.add:
        for text in args.add:
            state["criteria"].append(
                {
                    "id": len(state["criteria"]) + 1,
                    "text": text,
                    "status": "pending",
                    "evidence": None,
                }
            )
        log(f"CRITERIA {args.key} +{len(args.add)}")
    if args.set is not None:
        if not args.status:
            print("--set exige --status (met|unmet|waived|pending).", file=sys.stderr)
            return 2
        for c in state["criteria"]:
            if c["id"] == args.set:
                if args.status in ("unmet", "waived") and not args.evidence:
                    print(
                        "Um criterio 'unmet' ou 'waived' exige --evidence com a razao — e isso "
                        "que o distingue de um criterio silenciosamente abandonado.",
                        file=sys.stderr,
                    )
                    return 2
                c["status"] = args.status
                c["evidence"] = args.evidence
                log(f"CRITERIA {args.key} #{args.set} -> {args.status}")
                break
        else:
            print(f"Criterio #{args.set} nao existe.", file=sys.stderr)
            return 2
    save(state)
    if not state["criteria"]:
        print("Sem criterios registados.")
    for c in state["criteria"]:
        evidence = f" — {c['evidence']}" if c["evidence"] else ""
        print(f"  [{c['status']:^7}] #{c['id']} {c['text']}{evidence}")
    return 0


def cmd_plan_delegated(args):
    """Record that the plan was written by a Fable subagent (phase 4's model split).

    Self-reported, like every other transition here: the value is that not reporting it
    makes `plan-approved` refuse and demand an explicit, logged `--planned-on opus`.
    """
    state = require(args.key)
    state["plan_delegated_to_fable"] = args.model == "fable"
    if state["phase"] == "started":
        state["phase"] = "planned"
    save(state)
    log(f"PLAN-DELEGATED {args.key} model={args.model}")
    print(f"Delegacao do plano registada (modelo: {args.model}).")
    return 0


def cmd_plan_approved(args):
    state = require(args.key)
    plan_text = "" if sys.stdin.isatty() else sys.stdin.read()
    if len(plan_text.strip()) < 40:
        print(
            "Passa o texto do plano aprovado no stdin (heredoc). O digest e o que permite "
            "detetar deriva depois — sem ele, 'o plano aprovado' e so memoria.",
            file=sys.stderr,
        )
        return 2
    if not state["criteria"] and not args.no_criteria_confirmed:
        print(
            "Zero criterios de aceitacao registados. Ou o ticket nao os tem — e nesse caso "
            "confirma com o utilizador o que significa 'done' e regista a resposta com "
            "`criteria --add` — ou repete com --no-criteria-confirmed depois dessa conversa.",
            file=sys.stderr,
        )
        return 1
    audit = state.get("plan_audit") or {}
    if audit.get("verdict") != "pass" or audit.get("digest") != digest_of(plan_text):
        why = (
            "nunca foi auditado" if not audit
            else "reprovou a auditoria" if audit.get("verdict") != "pass"
            else "mudou desde a auditoria (o digest nao coincide)"
        )
        print(
            f"O plano {why}. Corre primeiro:\n"
            f"  python3 .claude/hooks/ticket-state.py plan-audit {args.key} "
            f"--repos {args.repos} <<'PLAN' … PLAN\n"
            "A auditoria e deterministica: caminhos e simbolos que existem, cada ponto com "
            "prova e um commit que o gate da Fase 6 aceita, e a superficie de teste so "
            "quando declarada e justificada.",
            file=sys.stderr,
        )
        return 1
    if not state["plan_delegated_to_fable"] and not args.planned_on:
        print(
            "O plano nao passou por um subagente Fable (flag nao registada). Se o utilizador "
            "aprovou planear no Opus, repete com --planned-on opus --reason '<quem autorizou>'. "
            "O desvio fica registado, nao escondido.",
            file=sys.stderr,
        )
        return 1
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    clashes = collisions(args.key, repos, state.get("workdir"))
    if clashes:
        print(
            "Outro ticket esta a trabalhar a mesma arvore: "
            + ", ".join(f"{t} em {r}/" for t, r in clashes)
            + f". Da a {args.key} a sua propria arvore antes de aprovar o plano "
            "(ticket-worktree.py create).",
            file=sys.stderr,
        )
        return 1
    unknown = [r for r in repos if r not in SUITES]
    if unknown:
        print(f"Repos desconhecidos: {unknown} (esperado backend|frontend).", file=sys.stderr)
        return 2
    state["phase"] = "approved"
    state["repos"] = repos
    state["deploy_order"] = args.deploy_order
    state["plan_digest"] = digest_of(plan_text)
    state["points"] = [
        {
            "n": i + 1,
            "summary": s.strip(),
            "status": "pending",
            "commit": None,
            "proof": None,
            "blocked_reason": None,
        }
        for i, s in enumerate(args.point or [])
    ]
    if args.planned_on:
        state["overrides"].append(
            {
                "gate": "model-split",
                "reason": args.reason or "",
                "consumed": True,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
    save(state)
    log(
        f"APPROVED {args.key} repos={repos} points={len(state['points'])} "
        f"digest={state['plan_digest']} planned_on={args.planned_on or 'fable'}"
    )
    print(f"Plano aprovado registado ({state['plan_digest']}).")
    print("Escritas desbloqueadas em: " + ", ".join(repos))
    return 0


def cmd_replan(args):
    state = require(args.key)
    state["phase"] = "planned"
    state["plan_digest"] = None
    save(state)
    log(f"REPLAN {args.key} reason={args.reason!r}")
    print(
        "Plano invalidado — as escritas voltam a estar bloqueadas ate novo `plan-approved`.\n"
        "Apresenta o plano revisto ao utilizador: derivar em silencio deixou de ser possivel."
    )
    return 0


def cmd_branch(args):
    state = require(args.key)
    state["branch"][args.repo] = args.name
    save(state)
    log(f"BRANCH {args.key} {args.repo}={args.name}")
    print(f"Branch registada: {args.repo} -> {args.name}")
    return 0


def cmd_point(args):
    state = require(args.key)
    points = {p["n"]: p for p in state["points"]}
    if args.n not in points:
        print(
            f"Ponto {args.n} nao existe no plano aprovado ({len(points)} pontos). "
            "Se o plano mudou, usa `replan` e faz aprovar o plano revisto.",
            file=sys.stderr,
        )
        return 2
    point = points[args.n]
    if args.action == "done":
        if not args.commit:
            print("--commit obrigatorio: um ponto so conta como feito com o commit real.", file=sys.stderr)
            return 2
        repo = args.repo or (state["repos"][0] if len(state["repos"]) == 1 else None)
        if not repo:
            print("Ticket com dois repos: indica --repo.", file=sys.stderr)
            return 2
        rc, out = sh(["git", "cat-file", "-t", args.commit], SUITES[repo]["dir"], 30)
        if rc != 0 or out.strip() != "commit":
            print(
                f"O sha {args.commit!r} nao e um commit em {repo}/ — nao registo o ponto como "
                "feito com uma referencia que o git nao reconhece.",
                file=sys.stderr,
            )
            return 1
        rc, full = sh(["git", "rev-parse", args.commit], SUITES[repo]["dir"], 30)
        point.update(status="done", commit=full.strip() or args.commit, proof=args.proof)
    else:
        if not args.reason:
            print(
                "--reason obrigatorio: um ponto bloqueado sem razao registada e um ponto perdido.",
                file=sys.stderr,
            )
            return 2
        point.update(status="blocked", blocked_reason=args.reason)
    if state["phase"] in ("approved", "verified"):
        state["phase"] = "implementing"
    save(state)
    log(f"POINT {args.key} n={args.n} {args.action} commit={args.commit}")
    done = sum(1 for p in state["points"] if p["status"] == "done")
    print(f"Ponto {args.n}: {args.action}. Progresso: {done}/{len(state['points'])}.")
    return 0


SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}


def is_shell_wrapper(line: str) -> bool:
    """True for a `pgrep -af` hit that is a shell running a -c script, not the run itself.

    `pgrep -f` matches anywhere in the command line, so anything whose script text merely
    mentions the pattern looks like a running suite: this guard's own wait loops, an editor
    task, a grep. A real run always owns a process whose executable is the runner
    (`uv run pytest`, `.venv/bin/python .venv/bin/pytest`), so dropping shell wrappers can
    never hide one -- it only stops the guard from tripping over descriptions of itself.
    """
    parts = line.split()
    if len(parts) < 3:
        return False
    return os.path.basename(parts[1]) in SHELLS and "-c" in parts[2:4]


SUITE_CLAIM_MINUTES = 30


MONGO_PREFIX_VAR = "UDATA_TEST_MONGO_PREFIX"
MONGO_PREFIX_BASE = "mongodb://localhost:27017/udata_test"


def suite_isolation(state: dict, repo: str, workdir: str):
    """(env, claim_suffix) so two checkouts of `repo` can run their suites at once.

    The backend suite truncates every collection between tests, so two runs sharing a test
    database wipe each other's fixtures. A ticket working in its own tree gets its own
    database names, and only then is it safe to stop serialising.

    The safety hinges on the tree actually honouring the variable: a worktree cut before
    that change landed would silently share `udata-test` while this code believed the runs
    were isolated -- worse than serialising. So it is checked, not assumed.
    """
    if repo != "backend" or not state.get("workdir"):
        return {}, ""
    plugin = os.path.join(workdir, "udata", "tests", "plugin.py")
    try:
        with open(plugin) as fh:
            honours = MONGO_PREFIX_VAR in fh.read()
    except OSError:
        honours = False
    if not honours:
        return {}, ""
    slug = re.sub(r"[^a-z0-9]+", "", state["ticket"].lower())
    return {MONGO_PREFIX_VAR: f"{MONGO_PREFIX_BASE}_{slug}"}, f"-{slug}"


def claim_path(repo: str, suffix: str = "") -> str:
    return os.path.join(STATE_DIR, f"{repo}-suite{suffix}.claim")


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False
    return True


def take_suite_claim(repo: str, key: str, suffix: str = ""):
    """Serialise the suites that cannot share a machine. Returns None, or why not.

    Deliberately a claim and not a lock. `verify` runs inside a tool call with a timeout,
    and when that call is killed the process group goes with it -- an flock would release
    mid-pytest, letting a second run into the same Mongo databases, which is the exact
    destruction being prevented. A claim file outlives the kill and is judged instead by
    whether its pid is still alive, so a dead holder never blocks anyone.

    And it refuses rather than waits: a blocked session should end its turn and come back,
    not sit for four minutes holding a session open doing nothing.
    """
    path = claim_path(repo, suffix)
    try:
        with open(path) as fh:
            held = json.load(fh)
    except Exception:
        held = None
    if held:
        age = (
            datetime.now(timezone.utc) - datetime.fromisoformat(held["at"])
        ).total_seconds() / 60
        if held.get("pid") and pid_alive(held["pid"]) and age < SUITE_CLAIM_MINUTES:
            wait = max(1, int(SUITE_CLAIM_MINUTES - age))
            return (
                f"A suite de {repo} esta reservada por {held.get('ticket')} "
                f"(pid {held['pid']}, ha {int(age)} min).\n\n"
                f"Duas corridas em {repo}/ partilham as mesmas BD Mongo de teste e fabricam "
                "regressoes uma a outra. Nao esperes nesta chamada: termina o turno e volta a "
                f"correr o verify dentro de ~{min(wait, 5)} min."
            )
        if held.get("pid") and not pid_alive(held["pid"]):
            print(
                f"(reserva de {held.get('ticket')} abandonada — pid {held['pid']} ja morreu, a assumir)"
            )
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(
            {
                "ticket": key,
                "repo": repo,
                "pid": os.getpid(),
                "at": datetime.now(timezone.utc).isoformat(),
            },
            fh,
        )
    return None


def release_suite_claim(repo: str, suffix: str = "") -> None:
    try:
        with open(claim_path(repo, suffix)) as fh:
            if json.load(fh).get("pid") != os.getpid():
                return  # someone else's claim: never remove it
    except Exception:
        return
    try:
        os.remove(claim_path(repo, suffix))
    except OSError:
        pass


NODE_ID = re.compile(r"^(?:FAILED|ERROR)\s+(\S+::\S+)", re.MULTILINE)
# Re-running more than this serially costs more than the xdist run it is checking; past it
# the honest answer is "red, go look".
RECHECK_CAP = 400


def failing_nodes(output: str) -> list:
    """The node ids pytest listed in its short summary, de-duplicated, order kept."""
    seen, nodes = set(), []
    for node in NODE_ID.findall(output):
        if node not in seen:
            seen.add(node)
            nodes.append(node)
    return nodes


def cmd_verify(args):
    state = require(args.key)
    cfg = SUITES[args.repo]
    workdir = repo_dir(state, args.repo)
    if not os.path.isdir(workdir):
        print(
            f"A arvore deste ticket para {args.repo} nao existe: {workdir}. "
            "Corre `ticket-worktree.py create` ou limpa o `workdir` do estado.",
            file=sys.stderr,
        )
        return 2

    env, suffix = suite_isolation(state, args.repo, workdir)
    if env:
        print(f"BD de teste isolada: {env[MONGO_PREFIX_VAR]}_gw<n>")

    exclusive = cfg.get("exclusive")
    if exclusive:
        refusal = take_suite_claim(args.repo, args.key, suffix)
        if refusal:
            print(refusal, file=sys.stderr)
            return 2
        # Belt and braces, and only where it still makes sense: with its own databases this
        # run cannot be harmed by another one, so a pytest elsewhere is no longer a reason
        # to refuse. Sharing the default names, it is the only thing that sees a run started
        # outside this gate.
        rc, out = sh(["pgrep", "-af", exclusive], ROOT, 15) if not env else (1, "")
        running = [
            ln for ln in out.splitlines() if ln.strip() and not is_shell_wrapper(ln)
        ]
        if rc == 0 and running:
            release_suite_claim(args.repo, suffix)
            print(
                f"Ja ha uma corrida de {exclusive} em curso fora deste gate:\n  "
                + "\n  ".join(running[:5])
                + "\n\nDuas corridas em backend/ partilham as mesmas BD Mongo de teste e "
                "fabricam regressoes uma a outra. Espera que termine em vez de arrancar outra.",
                file=sys.stderr,
            )
            return 2

    rc, head = sh(["git", "rev-parse", "HEAD"], workdir, 30)
    head = head.strip()
    if rc != 0 or not re.fullmatch(r"[0-9a-f]{40}", head):
        print("Nao consegui resolver o HEAD — sem HEAD nao ha nada a que ligar o verde.", file=sys.stderr)
        return 2

    try:
        return run_suites(args, state, cfg, workdir, head, env)
    finally:
        if exclusive:
            release_suite_claim(args.repo, suffix)


def run_suites(args, state, cfg, workdir, head, env=None):
    problems = []
    for lint_cmd in cfg["lint"]:
        print(f"$ {' '.join(lint_cmd)}")
        code, out = sh(lint_cmd, workdir, 900, env)
        if code != 0:
            tail = "\n    ".join(out.strip().splitlines()[-10:])
            problems.append(f"$ {' '.join(lint_cmd)} -> {code}\n    {tail}")

    test_cmd = cfg["test"] + (args.scope or [])
    print(f"$ {' '.join(test_cmd)}")
    code, out = sh(test_cmd, workdir, env=env)
    quarantined = []
    if code != 0:
        detail = {124: "timeout", 127: "runner nao encontrado"}.get(code, f"exit {code}")
        nodes = failing_nodes(out) if cfg.get("serial") and code not in (124, 127) else []
        if nodes and len(nodes) <= RECHECK_CAP:
            # A red parallel run is a question. Ask it again, one worker, same tests: what
            # fails twice is the diff's problem, what passes was the split's.
            recheck = cfg["serial"] + nodes
            print(f"$ {' '.join(cfg['serial'])} <{len(nodes)} testes que falharam>")
            rc2, out2 = sh(recheck, workdir, env=env)
            still = failing_nodes(out2)
            if rc2 == 0 and not still:
                quarantined = nodes
                print(
                    f"  {len(nodes)} teste(s) falharam com -n 2 e passam em serie — "
                    "artefacto do split, nao do diff."
                )
            else:
                tail = "\n    ".join(out2.strip().splitlines()[-15:])
                problems.append(
                    f"suite -> {len(still) or 'exit ' + str(rc2)} falha(m) tambem em serie"
                    f"\n    {tail}"
                )
        else:
            if nodes:
                print(f"  {len(nodes)} falhas e demasiado para reconfirmar em serie.")
            tail = "\n    ".join(out.strip().splitlines()[-15:])
            problems.append(f"suite -> {detail}\n    {tail}")

    ok = not problems
    if ok:
        state["verified"][args.repo] = {
            "head": head,
            "scope": "narrow" if args.scope else "full",
            "at": datetime.now(timezone.utc).isoformat(),
            "xdist_only_failures": quarantined,
        }
        if state["phase"] == "implementing":
            state["phase"] = "verified"
        save_keys(state, "verified", "phase")
    log(
        f"VERIFY {args.key} repo={args.repo} head={head[:12]} ok={ok} "
        f"scope={'narrow' if args.scope else 'full'}"
    )
    print("\n" + "=" * 66)
    print("VERDICTO:", "VERDE" if ok else "VERMELHO", f"({args.repo} @ {head[:12]})")
    print("=" * 66)
    for p in problems:
        print(f"  PROBLEMA: {p}")
    if ok:
        print(f"  Registado. O gate de push aceita este HEAD ({head[:12]}) — e so este:")
        print("  qualquer commit novo invalida o verde e obriga a correr `verify` outra vez.")
    else:
        print(
            "\n  O gate de push vai recusar ate isto correr verde neste HEAD. Se a falha "
            "resistir\n  a uma tentativa honesta, passa para /fix-loop em vez de insistir aqui."
        )
    return 0 if ok else 1


def cmd_review(args):
    state = require(args.key)
    if not (args.accepted or args.rejected or args.none):
        print(
            "Indica o que a review deu: --accepted '<o que corrigiste>', "
            "--rejected '<achado> :: <razao da rejeicao>', ou --none se nao houve achados.",
            file=sys.stderr,
        )
        return 2
    rejected = []
    for item in args.rejected or []:
        if "::" not in item:
            print("Formato: --rejected '<achado> :: <razao da rejeicao>'.", file=sys.stderr)
            return 2
        finding, reason = item.split("::", 1)
        if not reason.strip():
            print("Um achado rejeitado sem razao escrita e um achado ignorado.", file=sys.stderr)
            return 2
        rejected.append({"finding": finding.strip(), "reason": reason.strip()})
    state["review"] = {"ran": True, "accepted": args.accepted or [], "rejected": rejected}
    save(state)
    log(f"REVIEW {args.key} accepted={len(args.accepted or [])} rejected={len(rejected)}")
    print(f"Review registada: {len(args.accepted or [])} aceite(s), {len(rejected)} rejeitado(s).")
    return 0


def cmd_pr(args):
    state = require(args.key)
    state["pr"][args.repo] = args.url
    state["phase"] = "pr"
    save(state)
    log(f"PR {args.key} {args.repo}={args.url}")
    print(f"PR registado: {args.repo} -> {args.url}")
    return 0


def cmd_pr_body(args):
    state = require(args.key)
    print(f"Refs: {state['ticket']}")
    if state["criteria"]:
        print("\n### Acceptance criteria")
        for c in state["criteria"]:
            mark = "x" if c["status"] == "met" else " "
            suffix = "" if c["status"] == "met" else f" — **{c['status']}**: {c['evidence']}"
            print(f"- [{mark}] {c['text']}{suffix}")
    if state["points"]:
        print("\n### Points → commits")
        for p in state["points"]:
            sha = (p["commit"] or "")[:12] or "blocked"
            line = f"- {p['n']}. {p['summary']} — `{sha}`"
            if p["status"] == "blocked":
                line += f" (blocked: {p['blocked_reason']})"
            if p.get("proof"):
                line += f" — proof: {p['proof']}"
            print(line)
    review = state.get("review", {})
    if review.get("ran") and (review.get("accepted") or review.get("rejected")):
        print("\n### Independent review")
        for f in review.get("accepted", []):
            print(f"- fixed: {f}")
        for f in review.get("rejected", []):
            print(f"- rejected: {f['finding']} — {f['reason']}")
    if state.get("deploy_order"):
        print(f"\n### Deploy order\n{state['deploy_order']}")
    return 0


def cmd_override(args):
    state = require(args.key)
    if not args.reason or len(args.reason.strip()) < 15:
        print(
            "--reason obrigatorio e substantivo: um bypass sem justificacao registada e o gate "
            "a ser contornado, nao usado.",
            file=sys.stderr,
        )
        return 2
    state["overrides"].append(
        {
            "gate": args.gate,
            "reason": args.reason.strip(),
            "consumed": False,
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save(state)
    log(f"OVERRIDE-ARMED {args.key} gate={args.gate} reason={args.reason.strip()!r}")
    print(f"Override de '{args.gate}' armado (uso unico), registado em {LOG}.")
    print("Diz ao utilizador que o usaste e porque — e isso que o distingue de contornar o gate.")
    return 0


def cmd_pause(args):
    state = require(args.key)
    state["paused"] = args.action == "pause"
    save(state)
    log(f"{'PAUSE' if state['paused'] else 'RESUME'} {args.key}")
    print(
        "Pausado — os guards ficam inertes para trabalho fora do ticket."
        if state["paused"]
        else "Retomado — guards ativos."
    )
    return 0


def cmd_status(args):
    key = getattr(args, "key", None)
    files = [path_for(key)] if key else sorted(glob.glob(os.path.join(STATE_DIR, "ticket-*.json")))
    found = False
    for f in files:
        try:
            with open(f) as fh:
                state = json.load(fh)
        except FileNotFoundError:
            continue
        except Exception as exc:
            print(f"{os.path.basename(f)}: ilegivel ({exc})", file=sys.stderr)
            continue
        found = True
        if key:
            print(summary_line(state) + "\n")
            print(json.dumps(state, indent=2, ensure_ascii=False))
        else:
            print("  " + summary_line(state))
    if not found:
        print("Nenhum ticket em curso." if not key else f"Sem estado para {key}.")
    return 0


def cmd_end(args):
    state = require(args.key)
    pending = [c for c in state["criteria"] if c["status"] == "pending"]
    if pending and not args.abandon:
        print(
            f"{len(pending)} criterio(s) ainda 'pending'. Resolve cada um (met/unmet/waived com "
            "evidencia) ou termina com --abandon, que fica registado como abandono.",
            file=sys.stderr,
        )
        return 1
    os.rename(path_for(args.key), path_for(args.key) + ".done")
    log(f"END {args.key} abandon={bool(args.abandon)}")
    print(f"Ticket {args.key} fechado (arquivado em ticket-{args.key}.json.done).")
    print("Os guards do ticket voltam a estar inertes.")
    return 0


def other_active(key: str) -> list:
    """Every other ticket still in flight in this root."""
    out = []
    for f in sorted(glob.glob(os.path.join(STATE_DIR, "ticket-*.json"))):
        try:
            with open(f) as fh:
                st = json.load(fh)
        except Exception:
            continue
        if st.get("ticket") != key and not st.get("paused"):
            out.append(st)
    return out


def collisions(key: str, repos: list, workdir) -> list:
    """Tickets already working the same repo in the same tree.

    Same repo in a *different* tree is exactly what the worktrees are for, so it is not a
    collision -- what cannot be shared is one checkout, because it can only be on one
    branch, and one Mongo test database.
    """
    mine = {repo: os.path.realpath(os.path.join(workdir, repo)) if workdir else SUITES[repo]["dir"]
            for repo in repos}
    clashes = []
    for st in other_active(key):
        for repo in st.get("repos") or []:
            if repo in mine and os.path.realpath(repo_dir(st, repo)) == os.path.realpath(mine[repo]):
                clashes.append((st["ticket"], repo))
    return clashes


BACKTICKED = re.compile(r"`([^`\n]+)`")
POINT_HEADING = re.compile(r"^#{2,4}\s*Ponto\s+(\d+)", re.MULTILINE)
FICHEIROS = re.compile(r"^\s*[-*]\s*\*\*Ficheiros?:\*\*(.*)$", re.MULTILINE)
FIELD = "**{}:**"
# A path has a separator or a short extension. `Model.field` is a symbol, not a file:
# a bare `[/.]` read every dotted symbol as a missing file and reported it as one.
PATHISH = re.compile(r"/|\.[A-Za-z0-9]{1,5}$")
TEST_SURFACE = re.compile(r"^\s*[-*]?\s*\*\*Superf[ií]cie de teste:\*\*(.*)$", re.MULTILINE)


def digest_of(plan_text: str) -> str:
    return "sha256:" + hashlib.sha256(plan_text.encode()).hexdigest()[:16]


def plan_paths(plan_text: str) -> list:
    """Every backticked token in a `**Ficheiros:**` line that looks like a path, with the
    symbols named in parentheses after it."""
    found = []
    for line in FICHEIROS.findall(plan_text):
        current = None
        for token in BACKTICKED.findall(line):
            token = token.strip()
            if PATHISH.search(token) and not token.endswith(("()", ")")):
                current = token
                found.append((token, []))
            elif found and current:
                found[-1][1].append(token.strip("()"))
    return found


def declared_test_surface(plan_text: str) -> dict:
    """Test paths the plan says it will touch, mapped to the justification it gives.

    Editing a test so a point passes is the degenerate solution this audit exists to catch,
    and it stays a problem. But two legitimate reasons to name a test file survive that
    rule: removing an `xfail(strict=True)` marker whose cause the same commit fixes -- which
    this project requires, because a strict XPASS is red -- and adding coverage that does not
    exist yet. Neither is allowed to pass unremarked: the plan has to name the file and say
    why on its own line, so whoever approves the plan reads the exception.
    """
    declared = {}
    for line in TEST_SURFACE.findall(plan_text):
        reason = BACKTICKED.sub(" ", line).strip(" -\u2014:,\t")
        for token in BACKTICKED.findall(line):
            token = token.strip()
            if PATHISH.search(token):
                # Two points may both touch one test file for different reasons; keep both,
                # so the note the approver reads does not silently lose one of them.
                prior = declared.get(token)
                if prior and reason and reason not in prior:
                    declared[token] = f"{prior} | {reason}"
                else:
                    declared[token] = prior or reason
    return declared


def audit_plan(plan_text: str, repos: list, state: dict) -> tuple:
    """The half of a plan review a script can settle. Returns (problems, notes).

    Not a replacement for reading the plan -- a judgement call about whether the approach
    is right stays a judgement call. But "names a file that does not exist", "a point with
    no proof", "a commit line that the commit gate will reject at Phase 6" and "edits the
    test surface" are all decidable here, and catching them before a human reads the plan
    is the difference between one round-trip and three.
    """
    problems, notes = [], []
    declared = declared_test_surface(plan_text)

    points = POINT_HEADING.split(plan_text)
    if len(points) < 3:
        problems.append("nenhum bloco '### Ponto N' — o plano nao esta na forma que a Fase 6 segue")
    for number, body in zip(points[1::2], points[2::2]):
        for field in ("Prova", "Commit"):
            marker = FIELD.format(field)
            if marker not in body:
                problems.append(f"ponto {number}: falta {marker}")
                continue
            value = body.split(marker, 1)[1].splitlines()[0].strip(" `")
            if not value:
                problems.append(f"ponto {number}: {marker} esta vazio")
            elif field == "Commit" and not CONVENTIONAL.match(value):
                problems.append(
                    f"ponto {number}: a linha de Commit nao passa o gate do Fase 6: {value!r}"
                )

    for path, symbols in plan_paths(plan_text):
        repo = path.split("/", 1)[0] if "/" in path else None
        if repo in SUITES:
            rel = path.split("/", 1)[1]
        else:
            repo, rel = (repos[0] if len(repos) == 1 else None), path
        if repo is None:
            notes.append(f"{path}: nao consegui dizer a que repo pertence")
            continue
        if repo not in repos:
            problems.append(f"{path} esta em {repo}/, que nao e um dos repos deste ticket ({', '.join(repos)})")
            continue
        if FROZEN_PATH.search(rel):
            reason = declared.get(path) or declared.get(rel)
            if not reason:
                problems.append(
                    f"{path} e superficie de teste — um plano nao altera testes nem a "
                    "configuracao do runner para satisfazer um ponto. Se a alteracao e remover "
                    "um marcador xfail cuja causa este plano corrige, ou acrescentar cobertura "
                    "que nao existe, declara-o numa linha propria: "
                    f"`**Superficie de teste:** `{path}` — <justificacao>`"
                )
            elif len(reason) < 15:
                problems.append(
                    f"{path}: a declaracao de superficie de teste nao traz justificacao"
                )
            else:
                notes.append(f"{path}: superficie de teste declarada — {reason}")
            continue
        tree = repo_dir(state, repo)
        full = os.path.join(tree, rel)
        if os.path.exists(full):
            blob = open(full, errors="ignore").read()
            for symbol in symbols:
                bare = symbol.strip().rstrip("()")
                # `+name` says the point ADDS this symbol to an existing file. Without it a
                # plan could never describe an addition, and the check inverts usefully: a
                # symbol claimed as new that already exists is a plan working from a stale
                # reading of the tree.
                adds = bare.startswith("+")
                bare = bare.lstrip("+").strip()
                if not bare:
                    continue
                # A qualified name (`Class.field`) never appears verbatim in the source, so
                # resolve it by its components -- otherwise the most precise way to name a
                # symbol was the one the audit rejected.
                parts = [bare] if "." not in bare else bare.split(".")
                present = all(
                    sh(["git", "grep", "-q", "--", part, "--", rel], tree, 30)[0] == 0
                    or part in blob
                    for part in parts
                )
                if adds and present:
                    problems.append(
                        f"{path}: `{bare}` esta marcado como novo (`+`) mas ja existe no ficheiro"
                    )
                elif not adds and not present:
                    problems.append(
                        f"{path}: nao encontrei `{symbol}` no ficheiro "
                        f"(se e para acrescentar, escreve-o `+{bare}`)"
                    )
        elif os.path.isdir(os.path.dirname(full)):
            notes.append(f"{path}: ainda nao existe (ficheiro novo)")
        else:
            problems.append(f"{path}: nem o ficheiro nem a pasta {os.path.dirname(rel)}/ existem")

    return problems, notes


def cmd_plan_audit(args):
    state = require(args.key)
    plan_text = "" if sys.stdin.isatty() else sys.stdin.read()
    if len(plan_text.strip()) < 40:
        print("Passa o texto do plano no stdin (heredoc).", file=sys.stderr)
        return 2
    repos = [r.strip() for r in args.repos.split(",") if r.strip()] or (state.get("repos") or [])
    unknown = [r for r in repos if r not in SUITES]
    if unknown or not repos:
        print(f"--repos invalido: {args.repos!r} (esperado backend|frontend).", file=sys.stderr)
        return 2

    problems, notes = audit_plan(plan_text, repos, state)
    verdict = "pass" if not problems else "fail"
    state["plan_audit"] = {
        "digest": digest_of(plan_text),
        "verdict": verdict,
        "problems": problems,
        "notes": notes,
        "repos": repos,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    save(state)
    log(f"PLAN-AUDIT {args.key} verdict={verdict} problems={len(problems)}")

    print(f"Auditoria do plano de {args.key}: {'APROVADO' if verdict == 'pass' else 'REPROVADO'}")
    for note in notes:
        print(f"  nota .... {note}")
    for problem in problems:
        print(f"  PROBLEMA  {problem}")
    if verdict == "pass":
        print("\nA parte verificavel esta consistente. O julgamento — abordagem certa,")
        print("precedente replicado, ambito — continua a ser lido por quem aprova.")
        return 0
    print("\nCorrige o plano e volta a auditar. Sem `pass` neste digest, plan-approved recusa.")
    return 1


def cmd_claim(args):
    """Say which repos this ticket touches, as soon as Phase 3 knows.

    Two things follow from it. The guard stops locking the submodule this ticket does not
    touch, so another session can work that one at the same time -- before this, one ticket
    waiting for its plan froze both repos for everybody. And a second ticket aiming at the
    same checkout is refused here, with the command that gives it its own.
    """
    state = require(args.key)
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    unknown = [r for r in repos if r not in SUITES]
    if unknown:
        print(f"Repos desconhecidos: {', '.join(unknown)} (esperado backend|frontend).", file=sys.stderr)
        return 2
    workdir = os.path.abspath(args.workdir) if args.workdir else state.get("workdir")
    if workdir and not os.path.isdir(workdir):
        print(f"A arvore {workdir} nao existe.", file=sys.stderr)
        return 2
    clashes = collisions(args.key, repos, workdir)
    if clashes:
        print(
            "Ja ha outro ticket a trabalhar a mesma arvore:\n  "
            + "\n  ".join(f"{t} em {r}/" for t, r in clashes)
            + "\n\nUm checkout so pode estar numa branch, e as duas suites de backend partilham "
            "a mesma BD de teste. Da a este ticket a sua propria arvore:\n  "
            f"python3 .claude/hooks/ticket-worktree.py create {args.key} "
            f"--repos {','.join(repos)}",
            file=sys.stderr,
        )
        return 1
    state["repos"] = repos
    if workdir:
        state["workdir"] = workdir
    save(state)
    log(f"CLAIM {args.key} repos={','.join(repos)} workdir={workdir or '-'}")
    print(f"{args.key} reclama {', '.join(repos)}" + (f" em {workdir}" if workdir else " no checkout principal") + ".")
    print("O outro submodulo deixa de estar bloqueado por este ticket.")
    return 0


def cmd_park(args):
    """Stop this ticket with the decision it is waiting on written down.

    Deliberately not a phase, and deliberately not `pause`. `pause` makes the guards
    inert, which is the opposite of what is wanted here: a ticket that stopped before
    its plan was approved must keep the repos locked while it waits. So the phase is
    left exactly where it was and this is recorded alongside it -- the gates keep
    behaving as they did, and every reader learns to say "parked".

    What gets recorded is what a resume needs and what a human needs to answer the
    question: the reason as a groupable code, the question itself, the diagnosis, and
    the state of the work at the moment it stopped.
    """
    state = require(args.key)
    diagnosis = "" if sys.stdin.isatty() else sys.stdin.read().strip()
    if len(diagnosis) < 40:
        print(
            "Passa o diagnostico no stdin (heredoc): o que foi tentado, o que se sabe, e "
            "porque e que a decisao nao e tua. Um park sem diagnostico e uma sessao "
            "abandonada com outro nome.",
            file=sys.stderr,
        )
        return 2
    git_status = {}
    for repo in state.get("repos") or list(SUITES):
        workdir = repo_dir(state, repo)
        if os.path.isdir(workdir):
            _, out = sh(["git", "status", "--porcelain"], workdir, 30)
            git_status[repo] = out.strip()
    state["parked"] = {
        "reason_code": args.reason_code,
        "question": args.question,
        "diagnosis": diagnosis,
        "phase": state["phase"],
        "branch": dict(state.get("branch") or {}),
        "workdir": state.get("workdir"),
        "plan_digest": state.get("plan_digest"),
        "points_done": [
            {"n": pt["n"], "commit": pt.get("commit")}
            for pt in state["points"]
            if pt["status"] == "done"
        ],
        "git_status": git_status,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    save(state)
    log(f"PARK {args.key} code={args.reason_code} phase={state['phase']}")
    print(f"{args.key} ESTACIONADO em fase={state['phase']} ({args.reason_code}).")
    print(f"Decisao em divida: {args.question}")
    print("Os gates continuam como estavam — um park nao desbloqueia nada.")
    print(f"Retoma com /ticket {args.key} depois da resposta, ou `unpark {args.key}`.")
    return 0


def cmd_unpark(args):
    state = require(args.key)
    parked = state.pop("parked", None)
    if not parked:
        print(f"{args.key} nao esta estacionado.", file=sys.stderr)
        return 1
    save(state)
    log(f"UNPARK {args.key} code={parked['reason_code']}")
    print(f"{args.key} retomado (estava estacionado por {parked['reason_code']}).")
    print(f"A pergunta era: {parked['question']}")
    return 0


def cmd_doctor(args):
    """Which tree the hooks and this CLI each think they are guarding.

    The failure this catches is the silent one: when the hook processes resolve one
    root and the CLI another, the guards read an empty state directory and behave
    exactly as they would with no ticket in flight. Nothing errors; the gates simply
    stop existing. So print every candidate and say plainly when they disagree.
    """
    chosen = harness_root()
    print("Raiz do harness")
    for var, value in candidates():
        if value is None:
            mark, note = "  ", "nao definido"
        elif not os.path.isdir(os.path.join(value, ".claude", "hooks")):
            mark, note = "!!", "definido mas NAO tem .claude/hooks — ignorado"
        else:
            mark, note = ("->" if os.path.abspath(value) == chosen else "  "), "ok"
        print(f"  {mark} {var:22} {value or '-'}   ({note})")
    print(f"\n  escolhida:      {chosen}")
    print(f"  estado:         {STATE_DIR}  ({'existe' if os.path.isdir(STATE_DIR) else 'ainda nao existe'})")
    for repo, cfg in SUITES.items():
        print(f"  {repo + ':':15} {cfg['dir']}  ({'existe' if os.path.isdir(cfg['dir']) else 'AUSENTE'})")

    problems = []
    for var, value in candidates()[:-1]:
        if value and not os.path.isdir(os.path.join(value, ".claude", "hooks")):
            problems.append(f"{var} aponta para {value}, que nao e um checkout do harness")
    if chosen != FILE_ROOT:
        problems.append(
            f"a raiz escolhida ({chosen}) nao e a do ficheiro ({FILE_ROOT}) — os hooks e a CLI "
            "so concordam enquanto ambos virem a mesma variavel de ambiente"
        )
    active = sorted(glob.glob(os.path.join(STATE_DIR, "ticket-*.json")))
    print(f"\n  tickets ativos: {len(active)}")
    for f in active:
        print(f"    {os.path.basename(f)}")
    if problems:
        print("\nA CORRIGIR:")
        for line in problems:
            print(f"  - {line}")
        return 1
    print("\nTudo a apontar para o mesmo sitio.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("start", help="create the ticket state (or print it, if it exists)")
    p.add_argument("key")
    p.add_argument("--title", default="")
    p.add_argument("--source", default="jira", choices=["jira", "fallback-doc", "user-dictated"])
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("criteria", help="add (phase 1) or resolve (phase 7) acceptance criteria")
    p.add_argument("key")
    p.add_argument("--add", action="append")
    p.add_argument("--set", type=int)
    p.add_argument("--status", choices=["met", "unmet", "waived", "pending"])
    p.add_argument("--evidence")
    p.set_defaults(func=cmd_criteria)

    p = sub.add_parser("plan-delegated", help="record which model wrote the plan (phase 4)")
    p.add_argument("key")
    p.add_argument("--model", default="fable", choices=["fable", "opus"])
    p.set_defaults(func=cmd_plan_delegated)

    p = sub.add_parser("plan-approved", help="record the user-approved plan; unlocks the repos")
    p.add_argument("key")
    p.add_argument("--repos", required=True, help="comma-separated: backend,frontend")
    p.add_argument("--point", action="append", help="one per implementation point, in order")
    p.add_argument("--deploy-order")
    p.add_argument("--no-criteria-confirmed", action="store_true")
    p.add_argument("--planned-on", choices=["opus", "fable"])
    p.add_argument("--reason")
    p.set_defaults(func=cmd_plan_approved)

    p = sub.add_parser("replan", help="invalidate the plan; re-locks the repos")
    p.add_argument("key")
    p.add_argument("--reason", default="")
    p.set_defaults(func=cmd_replan)

    p = sub.add_parser("branch", help="record the working branch")
    p.add_argument("key")
    p.add_argument("repo", choices=sorted(SUITES))
    p.add_argument("name")
    p.set_defaults(func=cmd_branch)

    p = sub.add_parser("point", help="map a plan point to its commit, or mark it blocked")
    p.add_argument("key")
    p.add_argument("action", choices=["done", "blocked"])
    p.add_argument("n", type=int)
    p.add_argument("--commit")
    p.add_argument("--proof")
    p.add_argument("--reason")
    p.add_argument("--repo", choices=sorted(SUITES))
    p.set_defaults(func=cmd_point)

    p = sub.add_parser("verify", help="run lint+tests and record the HEAD they ran green on")
    p.add_argument("key")
    p.add_argument("repo", choices=sorted(SUITES))
    p.add_argument("scope", nargs="*", help="optional test paths to narrow the run")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("review", help="record the phase 7.5 review outcome")
    p.add_argument("key")
    p.add_argument("--accepted", action="append")
    p.add_argument("--rejected", action="append", help="'<finding> :: <reason>'")
    p.add_argument("--none", action="store_true")
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("pr", help="record the PR url")
    p.add_argument("key")
    p.add_argument("repo", choices=sorted(SUITES))
    p.add_argument("url")
    p.set_defaults(func=cmd_pr)

    p = sub.add_parser("pr-body", help="emit the structured part of the PR body from state")
    p.add_argument("key")
    p.set_defaults(func=cmd_pr_body)

    p = sub.add_parser("override", help="arm a one-shot, logged bypass of a gate")
    p.add_argument("gate", choices=["push"])
    p.add_argument("key")
    p.add_argument("--reason")
    p.set_defaults(func=cmd_override)

    for name in ("pause", "resume"):
        p = sub.add_parser(name, help=f"{name} the guards for this ticket")
        p.add_argument("key")
        p.set_defaults(func=cmd_pause, action=name)

    p = sub.add_parser("status", help="print one ticket, or a summary of all active ones")
    p.add_argument("key", nargs="?")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("plan-audit", help="check the verifiable half of a plan, deterministically")
    p.add_argument("key")
    p.add_argument("--repos", default="", help="backend | frontend | backend,frontend")
    p.set_defaults(func=cmd_plan_audit)

    p = sub.add_parser("claim", help="declare which repos (and which tree) this ticket touches")
    p.add_argument("key")
    p.add_argument("--repos", required=True, help="backend | frontend | backend,frontend")
    p.add_argument("--workdir", help="the per-ticket worktree, when it has one")
    p.set_defaults(func=cmd_claim)

    p = sub.add_parser("park", help="stop this ticket with the decision it awaits written down")
    p.add_argument("key")
    p.add_argument("--reason-code", required=True, choices=REASON_CODES)
    p.add_argument("--question", required=True, help="the decision owed, with its options")
    p.set_defaults(func=cmd_park)

    p = sub.add_parser("unpark", help="clear the park after the decision is made")
    p.add_argument("key")
    p.set_defaults(func=cmd_unpark)

    p = sub.add_parser("doctor", help="check that hooks and CLI agree on the harness root")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("end", help="archive the ticket state")
    p.add_argument("key")
    p.add_argument("--abandon", action="store_true")
    p.set_defaults(func=cmd_end)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
