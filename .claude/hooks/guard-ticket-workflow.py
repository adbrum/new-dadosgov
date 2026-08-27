#!/usr/bin/env python3
"""PreToolUse guard for the /ticket workflow.

Reads .claude/state/ticket-*.json (written only by ticket-state.py) and turns the skill's
"Never …" rules into denials instead of requests:

  * no writes into backend/ or frontend/ before the plan is approved — this is what makes
    "Phase 4 is an approval gate" real, and what gives `replan` teeth;
  * a working branch must be <type>/ledg-<n>-<kebab> and carry the active ticket's number;
  * a commit message must be Conventional, carry `Refs: LEDG-<n>`, and no AI attribution;
  * `git push` on a ticket branch is refused until lint+tests ran green over the code at
    HEAD (a later commit that touches only the CHANGELOG or docs does not invalidate that
    green -- it cannot change a test outcome, and the CHANGELOG is itself required before
    the push), the CHANGELOG gained an entry (and only gained), every acceptance criterion
    is resolved, every commit message in the range is clean, and the phase 7.5 review was
    recorded.

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
import tempfile
from datetime import datetime, timezone

from harness_patterns import (  # local: sits beside this hook
    ATTRIBUTION,
    CONVENTIONAL,
)
from harness_patterns import range_base as patterns_range_base
from harness_patterns import source_drift
from harness_root import harness_root

ROOT = harness_root()
STATE_DIR = os.path.join(ROOT, ".claude", "state")
LOG = os.path.join(STATE_DIR, "ticket.log")
SUBMODULES = ("backend", "frontend")

BRANCH_RE = re.compile(r"^(feature|bugfix|hotfix|chore|release)/ledg-(\d+)-[a-z0-9][a-z0-9-]*$")
# Deliberately narrow: a bare "claude" or "anthropic" would reject a legitimate commit that
# mentions .claude/ or the claude-mem plugin. What is banned is the attribution itself.

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
        if state.get("paused"):
            continue
        # A state carries the root it was started in. Normally that is this one, since the
        # state directory lives under it -- but a shared or symlinked state directory must
        # not let one checkout's tickets police another's files.
        root = state.get("root")
        if root and os.path.realpath(root) != os.path.realpath(ROOT):
            continue
        states.append(state)
    return states


def save(state: dict) -> None:
    """Atomic for the same reason as in ticket-state.py: this guard is also a writer
    (it marks a push override consumed), and a torn file reads as "no active ticket"."""
    final = os.path.join(STATE_DIR, f"ticket-{state['ticket']}.json")
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


def resolve(path: str, base: str):
    candidate = path if os.path.isabs(path) else os.path.join(base, path)
    try:
        return os.path.realpath(candidate)
    except Exception:
        return None


def repo_dir(state: dict, repo: str) -> str:
    """Where this ticket's copy of `repo` is: its worktree when it has one, else the checkout."""
    workdir = state.get("workdir")
    return os.path.realpath(
        os.path.join(workdir, repo) if workdir else os.path.join(ROOT, repo)
    )


def claimed_repos(state: dict) -> list:
    """Which submodules this ticket speaks for.

    An empty `repos` means Phase 3 has not run yet, and an undecided ticket speaks for
    both -- the conservative reading, and the one that keeps the Phase 4 gate shut before
    anyone knows where the code will land. Once `claim`/`plan-approved` records the repos,
    the ticket stops policing the one it does not touch, which is what lets a second
    session work the other repo at the same time.
    """
    return [r for r in (state.get("repos") or SUBMODULES) if r in SUBMODULES]


def trees(states: list) -> list:
    """(repo, path, owners) for every checkout any active ticket could be working in.

    The primary checkout is always listed, so a repo nobody claimed is still recognised
    as that repo -- it simply has no owner, and a gate with no owner has nothing to say.
    """
    seen = {}
    for state in states:
        for repo in claimed_repos(state):
            seen.setdefault((repo, repo_dir(state, repo)), []).append(state)
    for repo in SUBMODULES:
        seen.setdefault((repo, os.path.realpath(os.path.join(ROOT, repo))), [])
    return [(repo, path, owners) for (repo, path), owners in seen.items()]


def inside(path, tree: str) -> bool:
    return bool(path) and (path == tree or path.startswith(tree + os.sep))


def tree_of_path(path, states: list):
    """The (repo, path, owners) tuple containing this file, longest match first.

    Longest first because a worktree may sit under the primary checkout: without it,
    `<primary>/backend` would swallow a path inside `.claude/worktrees/…/backend`.
    """
    for repo, tree, owners in sorted(trees(states), key=lambda t: -len(t[1])):
        if inside(path, tree):
            return repo, tree, owners
    return None, None, []


def tree_of_command(cmd: str, cwd: str, states: list):
    """Same, for a Bash command: the target comes from cwd, `git -C` and `cd` alike."""
    candidates = {resolve(cwd, ROOT)}
    for match in DASH_C.findall(cmd):
        candidates.add(resolve(match, cwd))
    for match in CD_ANY.findall(cmd):
        candidates.add(resolve(match, cwd))
    for repo, tree, owners in sorted(trees(states), key=lambda t: -len(t[1])):
        if any(inside(c, tree) for c in candidates):
            return repo, tree, owners
    return None, None, []


def unapproved(states: list) -> list:
    return [s for s in states if s.get("phase") in ("started", "planned")]


def range_base(sub_path: str):
    """The environment branch this work was cut from — the closest one, not always develop."""
    return patterns_range_base(sh, sub_path)


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
        # Not every commit can change a test outcome. The CHANGELOG entry is *required*
        # before the push, so pinning the green to the exact sha charged a full suite for
        # writing it — every ticket, and again for every doc-only fix from the review. Ask
        # what actually changed instead, and only deny on source.
        drift = source_drift(sh, sub_path, verified["head"], head)
        if drift is None:
            problems.append(
                f"o ultimo verde foi em {verified['head'][:12]}, o HEAD e {head[:12]} e nao "
                "consegui ler o diff entre os dois — sem isso nao distingo um commit de "
                f"CHANGELOG de um commit de codigo. Corre: ticket-state.py verify {key} {repo}"
            )
        elif drift:
            listed = ", ".join(drift[:5]) + (f" (+{len(drift) - 5})" if len(drift) > 5 else "")
            problems.append(
                f"o verde foi em {verified['head'][:12]} e desde entao mudou codigo: {listed}. "
                f"Corre outra vez: ticket-state.py verify {key} {repo}"
            )
    if verified and verified.get("scope") == "narrow":
        problems.append(
            "o ultimo verde foi de uma corrida NARROW (caminhos dados a mao). Antes do push "
            f"corre o ambito do diff: ticket-state.py verify {key} {repo} --impacted"
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

    if tool in ("Edit", "Write", "NotebookEdit"):
        raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        path = resolve(raw, cwd) if raw else None
        if not path:
            return
        sub, _, owners = tree_of_path(path, states)
        if not sub:
            return
        # Only the tickets that own THIS tree of THIS repo have a say. That is the whole
        # difference between one session at a time and several: a ticket still waiting for
        # its plan used to lock both submodules for every other ticket too.
        blocking = unapproved(owners)
        if not blocking:
            return
        keys = ", ".join(s["ticket"] for s in blocking)
        first = blocking[0]["ticket"]
        deny(
            f"Escrita em {sub}/ bloqueada: o plano de {keys} ainda nao foi aprovado. "
            "A Fase 4 e um gate — nada de codigo antes do ok do utilizador.\n\n"
            "Depois da aprovacao: python3 .claude/hooks/ticket-state.py plan-approved "
            f"{first} --repos <repo> --point '…' <<'PLAN' … PLAN\n"
            f"Para trabalho fora do ticket: ticket-state.py pause {first}"
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

    repo, sub_path, owners = tree_of_command(cmd, cwd, states)
    if not repo:
        return
    if not owners:
        return  # a checkout no active ticket claims: nothing here to enforce

    match = NEW_BRANCH.search(cmd)
    if match:
        name = match.group(1)
        parsed = BRANCH_RE.match(name)
        expected = {s["ticket"].split("-")[1] for s in owners}
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
        if unapproved(owners):
            deny(
                "Branch de trabalho antes do plano aprovado — a Fase 5 vem depois do gate da "
                "Fase 4. Aprova o plano primeiro (ticket-state.py plan-approved)."
            )
        return

    if GIT_PUSH.search(cmd):
        rc, branch = sh(["git", "branch", "--show-current"], sub_path)
        branch = branch.strip()
        for state in owners:
            if state.get("branch", {}).get(repo) == branch and branch:
                check_push(state, repo, sub_path)
        return

    if GIT_COMMIT.search(cmd):
        messages = ["".join(groups) for groups in MSG_FLAG.findall(cmd)]
        if not messages:
            return  # -F or editor: the push gate re-checks every message deterministically
        full = "\n\n".join(messages)
        first = full.splitlines()[0] if full.splitlines() else ""
        keys = {s["ticket"] for s in owners}
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
