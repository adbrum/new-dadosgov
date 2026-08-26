#!/usr/bin/env python3
"""PreToolUse guard for the /ticket workflow.

Reads .claude/state/ticket-*.json (written only by ticket-state.py) and turns the skill's
"Never …" rules into denials instead of requests:

  * no writes into backend/ or frontend/ before the plan is approved — this is what makes
    "Phase 4 is an approval gate" real, and what gives `replan` teeth;
  * a working branch must be <type>/ledg-<n>-<kebab> and carry the active ticket's number;
  * a commit message must be Conventional, carry `Refs: LEDG-<n>`, and no AI attribution;
  * `git push` on a ticket branch is refused until lint+tests ran green on THIS HEAD, the
    CHANGELOG gained an entry (and only gained), every acceptance criterion is resolved,
    every commit message in the range is clean, and the phase 7.5 review was recorded.

Inert when no active ticket state exists, so ordinary work outside /ticket is untouched.
`ticket-state.py pause <KEY>` makes it inert on purpose.

Deliberate asymmetry with guard-test-surface.py, which fails closed: there is no lock being
defended here. Absence of readable state means absence of the workflow, so an unreadable
payload allows. The compensating control is that every override and transition is logged in
.claude/state/ticket.log, which outlives the session.

The escape hatch (`ticket-state.py override push <KEY> --reason …`) exists because a gate
with no exit is a gate people route around — and the route around this one would be
deleting the state file, which is cheaper and leaves no trace. The override is cheaper
still, and it writes a log line.

Exits 0 always; prints a deny decision when one applies.
"""

import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STATE_DIR = os.path.join(ROOT, ".claude", "state")
LOG = os.path.join(STATE_DIR, "ticket.log")
SUBMODULES = ("backend", "frontend")
ENV_BRANCHES = ("develop", "tst", "ppr", "main")

BRANCH_RE = re.compile(r"^(feature|bugfix|hotfix|chore|release)/ledg-(\d+)-[a-z0-9][a-z0-9-]*$")
CONVENTIONAL = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?: \S"
)
# Deliberately narrow: a bare "claude" or "anthropic" would reject a legitimate commit that
# mentions .claude/ or the claude-mem plugin. What is banned is the attribution itself.
ATTRIBUTION = re.compile(r"(?i)co-authored-by\s*:|generated with [^\n]{0,30}claude|\U0001F916")

NEW_BRANCH = re.compile(r"\bgit\b[^|;&]*\b(?:checkout\s+-b|switch\s+(?:-c|--create))\s+(\S+)")
GIT_COMMIT = re.compile(r"\bgit\b[^|;&]*\bcommit\b")
GIT_PUSH = re.compile(r"\bgit\b[^|;&]*\bpush\b")
MSG_FLAG = re.compile(r"(?:-m|--message)[= ]\s*(?:\"([^\"]*)\"|'([^']*)')", re.S)
DASH_C = re.compile(r"\bgit\s+(?:[^|;&]*?\s)?-C\s+(\S+)")
CD_ANY = re.compile(r"(?:^|[;&|(]\s*)cd\s+([^\s&;|)]+)")


def deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def log(line: str) -> None:
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(LOG, "a") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()} {line}\n")
    except Exception:
        pass


def sh(cmd, cwd, timeout=30):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout
    except Exception:
        return 1, ""


def active_states() -> list:
    states = []
    for f in sorted(glob.glob(os.path.join(STATE_DIR, "ticket-*.json"))):
        if f.endswith(".done"):
            continue
        try:
            with open(f) as fh:
                state = json.load(fh)
        except Exception:
            continue  # unreadable state cannot be defended deterministically
        if not state.get("paused"):
            states.append(state)
    return states


def save(state: dict) -> None:
    with open(os.path.join(STATE_DIR, f"ticket-{state['ticket']}.json"), "w") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)


def resolve(path: str, base: str):
    candidate = path if os.path.isabs(path) else os.path.join(base, path)
    try:
        return os.path.realpath(candidate)
    except Exception:
        return None


def repo_of(cmd: str, cwd: str):
    """Which submodule the command acts on, from every source available."""
    candidates = {resolve(cwd, ROOT)}
    for match in DASH_C.findall(cmd):
        candidates.add(resolve(match, cwd))
    for match in CD_ANY.findall(cmd):
        candidates.add(resolve(match, cwd))
    for sub in SUBMODULES:
        sub_path = os.path.realpath(os.path.join(ROOT, sub))
        for candidate in candidates:
            if candidate and (candidate == sub_path or candidate.startswith(sub_path + os.sep)):
                return sub
    return None


def range_base(sub_path: str):
    """The environment branch this work was cut from — the closest one, not always develop."""
    best, best_len = None, None
    for env in ENV_BRANCHES:
        rc, base = sh(["git", "merge-base", "HEAD", f"origin/{env}"], sub_path)
        base = base.strip()
        if rc != 0 or not base:
            continue
        rc, count = sh(["git", "rev-list", "--count", f"{base}..HEAD"], sub_path)
        if rc != 0 or not count.strip().isdigit():
            continue
        n = int(count.strip())
        if best_len is None or n < best_len:
            best, best_len = base, n
    return best


def check_commit_messages(sub_path: str, base: str, ticket: str) -> list:
    problems = []
    rc, raw = sh(["git", "log", "--format=%H%x00%P%x00%B%x01", f"{base}..HEAD"], sub_path, 60)
    if rc != 0:
        return ["nao consegui ler as mensagens de commit do range — nao emito veredicto vazio"]
    number = ticket.split("-")[1]
    for entry in raw.split("\x01"):
        if entry.count("\x00") < 2:
            continue
        sha, parents, body = entry.split("\x00", 2)
        sha = sha.strip()
        lines = [ln for ln in body.strip().splitlines()]
        first = lines[0] if lines else ""
        # Merge commits (2+ parents) are generated by git and by GitHub, and Conventional
        # Commits does not describe them: every merge on develop reads "Merge pull request
        # #N from ..." or "Merge remote-tracking branch ... into ...". Holding a merge to
        # the shape rule would make the convention unsatisfiable rather than enforced, so
        # the form checks skip them. The attribution ban does not: that applies to every
        # commit, however it was produced.
        is_merge = len(parents.split()) > 1
        if not is_merge:
            if not CONVENTIONAL.match(first):
                problems.append(f"commit {sha[:10]} nao e Conventional Commits: {first!r}")
            if f"Refs: LEDG-{number}" not in body:
                problems.append(f"commit {sha[:10]} sem o trailer 'Refs: LEDG-{number}'")
        if ATTRIBUTION.search(body):
            problems.append(f"commit {sha[:10]} contem atribuicao de IA — proibida neste projeto")
    return problems


def check_changelog(sub_path: str, base: str) -> list:
    problems = []
    rc, names = sh(["git", "diff", "--name-only", f"{base}..HEAD"], sub_path, 60)
    if rc != 0:
        return ["nao consegui comparar com a base — nao emito veredicto vazio"]
    if not any(n.strip().endswith("CHANGELOG.md") for n in names.splitlines()):
        return [
            "CHANGELOG.md sem entrada nesta branch — e obrigatorio nos dois repos (Fase 6). "
            "Entrada no topo de `## Unreleased`: resumo a bold + sub-bullets com o porque/como"
        ]
    rc, cdiff = sh(["git", "diff", f"{base}..HEAD", "--", "CHANGELOG.md"], sub_path, 60)
    if rc != 0:
        return ["nao consegui ler o diff do CHANGELOG — nao emito veredicto vazio"]
    for line in cdiff.splitlines():
        if line.startswith("-") and not line.startswith("---") and line[1:].strip():
            problems.append(
                "o diff do CHANGELOG remove ou edita linhas existentes — entradas ja promovidas "
                "nunca se editam: e o que faz a mesma linha divergir entre branches de ambiente "
                "e transforma um merge automatico num conflito"
            )
            break
    for line in cdiff.splitlines():
        if line.startswith("+") and not line.startswith("+++") and re.search(r"LEDG-\d+|#\d+", line):
            problems.append(
                "a entrada do CHANGELOG referencia um id Jira ou de PR — a convencao proibe-o "
                "(o merge commit ja regista o PR)"
            )
            break
    return problems


def check_push(state: dict, repo: str, sub_path: str) -> None:
    key = state["ticket"]

    for override in state.get("overrides", []):
        if override.get("gate") == "push" and not override.get("consumed"):
            override["consumed"] = True
            try:
                save(state)
            except Exception:
                pass
            log(f"PUSH-OVERRIDE-CONSUMED {key} repo={repo} reason={override.get('reason')!r}")
            return

    problems = []

    rc, head = sh(["git", "rev-parse", "HEAD"], sub_path)
    head = head.strip()
    verified = state.get("verified", {}).get(repo)
    if not verified:
        problems.append(
            f"lint+testes nunca correram por este gate. Corre: "
            f"python3 .claude/hooks/ticket-state.py verify {key} {repo}"
        )
    elif verified.get("head") != head:
        problems.append(
            f"o ultimo verde foi em {verified['head'][:12]} e o HEAD e {head[:12]} — houve "
            f"commits desde entao. Corre outra vez: ticket-state.py verify {key} {repo}"
        )
    elif verified.get("scope") == "narrow":
        problems.append(
            "o ultimo verde foi de uma corrida NARROW. Antes do push corre a suite completa: "
            f"ticket-state.py verify {key} {repo} (sem caminhos)"
        )

    base = range_base(sub_path)
    if not base:
        problems.append(
            "nao consegui determinar a base do range (fetch em falta?) — sem ela nao verifico "
            "CHANGELOG nem mensagens de commit, e nao passo um gate por omissao"
        )
    else:
        problems += check_changelog(sub_path, base)
        problems += check_commit_messages(sub_path, base, key)

    pending = [c for c in state.get("criteria", []) if c.get("status") == "pending"]
    if pending:
        listed = "; ".join(f"#{c['id']} {c['text'][:60]}" for c in pending)
        problems.append(
            f"criterios de aceitacao por resolver: {listed}. Resolve cada um "
            "(met | unmet | waived, com evidencia) — um 'unmet' honesto passa, um 'pending' nao"
        )

    if not state.get("review", {}).get("ran"):
        problems.append(
            "a review da Fase 7.5 nunca foi registada — corre /code-review sobre o diff e "
            f"regista: ticket-state.py review {key} [--accepted … | --rejected '… :: …' | --none]"
        )

    if problems:
        deny(
            f"Push bloqueado pelo gate do ticket {key} ({repo}/):\n- "
            + "\n- ".join(problems)
            + "\n\nEscape de uso unico, que fica registado: python3 .claude/hooks/"
            f"ticket-state.py override push {key} --reason '<porque>'"
        )


def main() -> None:
    states = active_states()
    if not states:
        return

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # no lock semantics here: unreadable payload allows

    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})
    cwd = payload.get("cwd") or ROOT
    unapproved = [s for s in states if s.get("phase") in ("started", "planned")]

    if tool in ("Edit", "Write", "NotebookEdit"):
        if not unapproved:
            return
        raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        path = resolve(raw, cwd) if raw else None
        if not path:
            return
        for sub in SUBMODULES:
            sub_path = os.path.realpath(os.path.join(ROOT, sub))
            if path == sub_path or path.startswith(sub_path + os.sep):
                keys = ", ".join(s["ticket"] for s in unapproved)
                deny(
                    f"Escrita em {sub}/ bloqueada: o plano de {keys} ainda nao foi aprovado. "
                    "A Fase 4 e um gate — nada de codigo antes do ok do utilizador.\n\n"
                    "Depois da aprovacao: python3 .claude/hooks/ticket-state.py plan-approved "
                    f"{unapproved[0]['ticket']} --repos <repo> --point '…' <<'PLAN' … PLAN\n"
                    f"Para trabalho fora do ticket: ticket-state.py pause {unapproved[0]['ticket']}"
                )
        return

    if tool != "Bash":
        return

    cmd = tool_input.get("command", "")
    if not cmd:
        return
    # Heredoc text is data, not execution: a script that merely mentions `git push` must not
    # be mistaken for doing it. Same rationale as guard-protected-branch.py.
    heredoc = re.search(r"<<-?\s*'?\"?[A-Za-z_][A-Za-z0-9_]*", cmd)
    if heredoc:
        cmd = cmd[: heredoc.start()]
        if not cmd.strip():
            return

    repo = repo_of(cmd, cwd)
    if not repo:
        return
    sub_path = os.path.realpath(os.path.join(ROOT, repo))

    match = NEW_BRANCH.search(cmd)
    if match:
        name = match.group(1)
        parsed = BRANCH_RE.match(name)
        expected = {s["ticket"].split("-")[1] for s in states}
        if not parsed:
            deny(
                f"Nome de branch invalido: {name!r}.\nFormato: "
                "<feature|bugfix|hotfix|chore|release>/ledg-<n>-<kebab-em-ingles> — por exemplo "
                "bugfix/ledg-2296-harvester-producer-admin-scope."
            )
        if parsed.group(2) not in expected:
            deny(
                f"A branch {name!r} refere LEDG-{parsed.group(2)}, mas o(s) ticket(s) ativo(s) "
                f"sao: {', '.join('LEDG-' + n for n in sorted(expected))}."
            )
        if unapproved:
            deny(
                "Branch de trabalho antes do plano aprovado — a Fase 5 vem depois do gate da "
                "Fase 4. Aprova o plano primeiro (ticket-state.py plan-approved)."
            )
        return

    if GIT_PUSH.search(cmd):
        rc, branch = sh(["git", "branch", "--show-current"], sub_path)
        branch = branch.strip()
        for state in states:
            if state.get("branch", {}).get(repo) == branch and branch:
                check_push(state, repo, sub_path)
        return

    if GIT_COMMIT.search(cmd):
        messages = ["".join(groups) for groups in MSG_FLAG.findall(cmd)]
        if not messages:
            return  # -F or editor: the push gate re-checks every message deterministically
        full = "\n\n".join(messages)
        first = full.splitlines()[0] if full.splitlines() else ""
        keys = {s["ticket"] for s in states if repo in (s.get("repos") or [repo])}
        problems = []
        if not CONVENTIONAL.match(first):
            problems.append(f"a primeira linha nao e Conventional Commits: {first!r}")
        if keys and not any(f"Refs: {k}" in full for k in keys):
            problems.append("falta o trailer 'Refs: " + " | ".join(sorted(keys)) + "'")
        if ATTRIBUTION.search(full):
            problems.append(
                "contem atribuicao de IA (Co-Authored-By / Generated with … Claude) — proibida "
                "em qualquer historico git deste projeto"
            )
        if problems:
            deny(
                "Mensagem de commit rejeitada:\n- "
                + "\n- ".join(problems)
                + "\n\nFormato: '<type>(<scope>): <imperative>' + linha em branco + "
                "'Refs: LEDG-<n>'. Corrigir agora custa menos do que um amend depois do gate "
                "de push."
            )


if __name__ == "__main__":
    main()
