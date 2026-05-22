"""Seed admin users via the udata CLI.

Runs `udata user create --admin` for each email below, with a shared password.
If the user already exists, falls back to `udata user set-admin` to promote it.

Usage (from repo root):
    # Backend a correr no host (default):
    python scripts/seed_admin_users.py

    # Backend a correr em Docker (`udata-backend-app`):
    python scripts/seed_admin_users.py --docker
"""

import argparse
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
PASSWORD = "***"
DOCKER_SERVICE = "app"

EMAILS = [
    "vitor.almeida@lbc-digital.com",
    "sergio.carvalho@lbc-digital.com",
    "kelman.santos@lbc-global.com",
    "maryelem.silva@lbc-global.com",
    "jonathan.almeida@lbc-digital.com",
    "marcos.ramos@lbc-digital.com",
    "valentim.pinto@lbc-global.com",
    "camila.manique@lbc-global.com",
    "erica.gameiro@lbc-global.com",
    "miguel.peneda@lbc-global.com",
    "laura.pereira@lbc-digital.com",
    "pedro.lima@lbc-digital.com",
    "joao.barradas@lbc-digital.com",
    "matheus.teixeira@lbc-digital.com",
    "ana.carvalho@babelgroup.com",
    "ines.correia@babelgroup.com",
    "joao.conceicao@babelgroup.com",
    "dados.abertos.l12@babelgroup.com",
    "joao.curado@ext.babelgroup.com",
]


def names_from_email(email: str) -> tuple[str, str]:
    local = email.split("@", 1)[0]
    parts = [p for p in local.replace("_", ".").split(".") if p]
    if not parts:
        return email, email
    first = parts[0].capitalize()
    last = " ".join(p.capitalize() for p in parts[1:]) or first
    return first, last


def run_udata(args: list[str], *, docker: bool) -> subprocess.CompletedProcess:
    if docker:
        cmd = [
            "docker", "compose", "exec", "-T", DOCKER_SERVICE,
            "uv", "run", "udata", *args,
        ]
    else:
        cmd = ["uv", "run", "udata", *args]
    return subprocess.run(
        cmd,
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )


def create_admin(email: str, *, docker: bool) -> str:
    first, last = names_from_email(email)
    create = run_udata(
        [
            "user", "create",
            "--first-name", first,
            "--last-name", last,
            "--email", email,
            "--password", PASSWORD,
            # user com role normal, omitir o --admin
            "--admin",
        ],
        docker=docker,
    )
    if create.returncode == 0:
        return "created"

    output = (create.stdout + create.stderr).lower()
    if "already" in output or "exist" in output or "duplicate" in output:
        promote = run_udata(["user", "set-admin", email], docker=docker)
        if promote.returncode == 0:
            return "promoted"
        sys.stderr.write(promote.stdout + promote.stderr)
        return "failed"

    sys.stderr.write(create.stdout + create.stderr)
    return "failed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Executa udata dentro do container `udata-backend-app` via docker compose.",
    )
    opts = parser.parse_args()

    if not BACKEND_DIR.exists():
        print(f"Backend directory not found: {BACKEND_DIR}", file=sys.stderr)
        return 1

    target = "docker" if opts.docker else "host"
    print(f"Seeding {len(EMAILS)} admin users against {target}...")

    failures: list[str] = []
    for email in EMAILS:
        status = create_admin(email, docker=opts.docker)
        marker = {"created": "+", "promoted": "*", "failed": "!"}[status]
        print(f"  [{marker}] {email} ({status})")
        if status == "failed":
            failures.append(email)

    print()
    print(f"Done. {len(EMAILS) - len(failures)}/{len(EMAILS)} OK.")
    if failures:
        print("Failed:")
        for email in failures:
            print(f"  - {email}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
