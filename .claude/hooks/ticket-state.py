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
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STATE_DIR = os.path.join(ROOT, ".claude", "state")
LOG = os.path.join(STATE_DIR, "ticket.log")
KEY_RE = re.compile(r"^LEDG-\d+$")

SUITES = {
    "backend": {
        "dir": os.path.join(ROOT, "backend"),
        "lint": [
            ["uv", "run", "ruff", "check", "."],
            ["uv", "run", "ruff", "format", "--check", "."],
        ],
        "test": ["uv", "run", "pytest"],
        # Two pytest processes in backend/ share the Mongo test databases on 27018 and
        # fake regressions for each other. Never start a second one.
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
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(path_for(state["ticket"]), "w") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)


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


def sh(cmd, cwd, timeout=1800):
    """Run a command. Returns (returncode, output). 124 = timeout, 127 = missing binary."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return 124, "<timeout>"
    except FileNotFoundError:
        return 127, "<comando nao encontrado>"


def summary_line(state: dict) -> str:
    done = sum(1 for p in state["points"] if p["status"] == "done")
    resolved = sum(1 for c in state["criteria"] if c["status"] != "pending")
    branches = ", ".join(f"{r}:{b}" for r, b in state.get("branch", {}).items()) or "-"
    return (
        f"{state['ticket']} fase={state['phase']}"
        f"{' PAUSADO' if state.get('paused') else ''} "
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
    if not state["plan_delegated_to_fable"] and not args.planned_on:
        print(
            "O plano nao passou por um subagente Fable (flag nao registada). Se o utilizador "
            "aprovou planear no Opus, repete com --planned-on opus --reason '<quem autorizou>'. "
            "O desvio fica registado, nao escondido.",
            file=sys.stderr,
        )
        return 1
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    unknown = [r for r in repos if r not in SUITES]
    if unknown:
        print(f"Repos desconhecidos: {unknown} (esperado backend|frontend).", file=sys.stderr)
        return 2
    state["phase"] = "approved"
    state["repos"] = repos
    state["deploy_order"] = args.deploy_order
    state["plan_digest"] = "sha256:" + hashlib.sha256(plan_text.encode()).hexdigest()[:16]
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


def cmd_verify(args):
    state = require(args.key)
    cfg = SUITES[args.repo]

    exclusive = cfg.get("exclusive")
    if exclusive:
        rc, out = sh(["pgrep", "-af", exclusive], ROOT, 15)
        running = [ln for ln in out.splitlines() if ln.strip()]
        if rc == 0 and running:
            print(
                f"Ja ha uma corrida de {exclusive} em curso:\n  "
                + "\n  ".join(running[:5])
                + "\n\nDuas corridas em backend/ partilham as BD Mongo de teste na porta 27018 e "
                "fabricam regressoes uma a outra. Espera que termine em vez de arrancar outra.",
                file=sys.stderr,
            )
            return 2

    rc, head = sh(["git", "rev-parse", "HEAD"], cfg["dir"], 30)
    head = head.strip()
    if rc != 0 or not re.fullmatch(r"[0-9a-f]{40}", head):
        print("Nao consegui resolver o HEAD — sem HEAD nao ha nada a que ligar o verde.", file=sys.stderr)
        return 2

    problems = []
    for lint_cmd in cfg["lint"]:
        print(f"$ {' '.join(lint_cmd)}")
        code, out = sh(lint_cmd, cfg["dir"], 900)
        if code != 0:
            tail = "\n    ".join(out.strip().splitlines()[-10:])
            problems.append(f"$ {' '.join(lint_cmd)} -> {code}\n    {tail}")

    test_cmd = cfg["test"] + (args.scope or [])
    print(f"$ {' '.join(test_cmd)}")
    code, out = sh(test_cmd, cfg["dir"])
    if code != 0:
        detail = {124: "timeout", 127: "runner nao encontrado"}.get(code, f"exit {code}")
        tail = "\n    ".join(out.strip().splitlines()[-15:])
        problems.append(f"suite -> {detail}\n    {tail}")

    ok = not problems
    if ok:
        state["verified"][args.repo] = {
            "head": head,
            "scope": "narrow" if args.scope else "full",
            "at": datetime.now(timezone.utc).isoformat(),
        }
        if state["phase"] == "implementing":
            state["phase"] = "verified"
        save(state)
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

    p = sub.add_parser("end", help="archive the ticket state")
    p.add_argument("key")
    p.add_argument("--abandon", action="store_true")
    p.set_defaults(func=cmd_end)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
