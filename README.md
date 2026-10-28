# dados.gov.pt (new-dadosgov)

Monorepo for the Portuguese National Open Data Portal, [dados.gov.pt](https://dados.gov.pt). It brings together the REST API and the web interface, which are developed together: a new frontend feature needs the matching backend API, and vice versa.

| Part | Stack | Source repository |
|---|---|---|
| `backend/` | Python, Flask, MongoDB, Celery, Elasticsearch (a fork of [udata](https://github.com/opendatateam/udata)) | amagovpt/udata-pt |
| `frontend/` | Next.js, React, TypeScript | amagovpt/dadosgov-fe |

`backend/` and `frontend/` are Git submodules, so clone with submodules:

```bash
git clone --recurse-submodules https://github.com/adbrum/new-dadosgov.git
```

## Repository layout

| Path | Purpose |
|---|---|
| `backend/` | REST API (v1 at `/api/1`, v2 at `/api/2`) |
| `frontend/` | Web interface |
| `docs/` | Installation guides, runbooks, workflows and analysis documents |
| `scripts/` | Helper scripts, such as `check_deployed_version.sh` |
| `run_servers.py` | Interactive launcher for the whole stack |
| `.circleci/` | CI configuration |

## Quick commands

| Action | Backend | Frontend |
|---|---|---|
| Install dependencies | `cd backend && uv sync --extra dev --extra test` | `cd frontend && npm install` |
| Development server | `cd backend && inv serve` (port 7000) | `cd frontend && npm run dev` (port 3000) |
| Tests | `cd backend && uv run pytest` | `cd frontend && npm run lint` |
| Lint and format | `uv run ruff check --fix . && uv run ruff format .` | `npm run lint` |
| Celery worker | `cd backend && inv work` | - |
| Database migrations | `cd backend && udata db upgrade` | - |
| Production build | - | `cd frontend && npm run build` |

## Running the stack

`run_servers.py` starts the stack and is the same on every machine (local, tst, ppr and production). Each machine declares its environment in an untracked file:

```bash
cp .dadosgov-env.example .dadosgov-env   # then set: develop, tst, ppr or main
```

Without that file, the branch currently checked out is used, shown and confirmed before anything is built. After a deploy, confirm which version is served with `./scripts/check_deployed_version.sh https://dados.gov.pt`.

## Development workflow

- Both parts have long-lived environment branches (`develop`, `tst`, `ppr`, `main`). Changes are promoted by pull request one environment at a time, and the base of each PR is the next environment.
- Branches follow Conventional Branch and commits follow Conventional Commits.
- When the API changes, update both sides: the backend endpoint and serialisation, and the frontend TypeScript type and fetch function.
- Each part is versioned by Git tags, one per promotion to `main`, with a GitHub release per tag.

More detail lives in `CLAUDE.md` and in the guides under `docs/` (for example `docs/INSTALLATION.md` and `docs/docker-setup.md`).

## Credits

The backend is based on [udata](https://github.com/opendatateam/udata), the open source platform maintained by data.gouv.fr, the French public agency in charge of Open Data.
