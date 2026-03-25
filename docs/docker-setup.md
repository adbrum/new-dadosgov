# Docker Setup - dados.gov.pt

Guide for running the dados.gov.pt platform (backend + frontend) with Docker.

## Architecture Overview

### Local Development (MongoDB/Redis on same machine)

```
┌─────────────────────────────────────────────────────────┐
│                    Host Machine                         │
│                                                         │
│  ┌──────────┐  ┌──────────┐                             │
│  │ MongoDB  │  │  Redis   │                             │
│  │ :27017   │  │  :6379   │                             │
│  └────▲─────┘  └────▲─────┘                             │
│       │              │                                  │
│       │   host.docker.internal                          │
│       │              │                                  │
│  ┌────┼──────────────┼──────────────────────────┐       │
│  │    │    Backend Docker Compose               │       │
│  │    │              │                          │       │
│  │  ┌─┴──────────────┴──┐  ┌──────────────────┐│       │
│  │  │   app (gunicorn)  │  │  worker (celery)  ││       │
│  │  │   :7000           │  │                   ││       │
│  │  └───────────────────┘  └──────────────────┘│       │
│  │  ┌───────────────────┐  ┌──────────────────┐│       │
│  │  │  beat (celery)    │  │  mailpit          ││       │
│  │  │                   │  │  SMTP :1025       ││       │
│  │  │                   │  │  UI   :8025       ││       │
│  │  └───────────────────┘  └──────────────────┘│       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │    Frontend Docker Compose                  │       │
│  │  ┌───────────────────┐                      │       │
│  │  │   app (next.js)   │──► host.docker       │       │
│  │  │   :3000           │   .internal:7000     │       │
│  │  └───────────────────┘                      │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  Browser → http://localhost:3000                        │
└─────────────────────────────────────────────────────────┘
```

### Remote Environments (DEV/TST/PRD — MongoDB/Redis on dedicated machines)

```
┌──────────────────────────────────┐    ┌──────────────────┐
│         App Server               │    │  Database Server  │
│                                  │    │                  │
│  ┌────────────────────────────┐  │    │  MongoDB :27017  │
│  │  Backend Docker Compose    │  │    │  Redis   :6379   │
│  │  app / worker / beat       │──┼───►│                  │
│  └────────────────────────────┘  │    │  (IPs defined    │
│                                  │    │   in .env)       │
│  ┌────────────────────────────┐  │    └──────────────────┘
│  │  Frontend Docker Compose   │  │
│  │  app (next.js) :3000       │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

## Prerequisites

- Docker and Docker Compose v2
- MongoDB (port 27017) — local or remote
- Redis (port 6379) — local or remote

## Quick Start

### 1. Backend

```bash
cd backend

# Copy and configure environment variables
cp .env.example .env   # Edit .env with your settings (see Configuration section)

# Build and start all services
docker compose up -d --build
```

This starts 4 services:

| Service   | Description                       | Port  |
|-----------|-----------------------------------|-------|
| `app`     | Flask API via gunicorn (4 workers)| 7000  |
| `worker`  | Celery worker (4 concurrency)     | -     |
| `beat`    | Celery beat scheduler             | -     |
| `mailpit` | Local SMTP server + web UI        | 1025 / 8025 |

### 2. Frontend

```bash
cd frontend

# Build and start
docker compose up -d --build
```

| Service | Description                 | Port |
|---------|-----------------------------|------|
| `app`   | Next.js standalone server   | 3000 |

### 3. Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:7000/api/1/
- **Mailpit UI** (captured emails): http://localhost:8025

## Configuration

### Backend Environment (.env)

The backend reads from `.env` file and `udata.cfg`. The `.env` file contains sensitive values; `udata.cfg` is the main Flask configuration that reads from `.env` via `os.getenv()`.

Key variables for Docker:

```bash
# Basic
DEBUG=True
SITE_ID=local
SERVER_NAME=localhost:7000
PREFERRED_URL_SCHEME=http

# Frontend URL (SAML redirects after login)
CDATA_BASE_URL=http://localhost:3000

# Session cookies
SESSION_COOKIE_SECURE=False

# Infrastructure — IPs of MongoDB and Redis servers (see "Infrastructure Connectivity" below)
SERVER_MONGO=localhost
SERVER_REDIS=localhost

# File storage
FS_ROOT=/home/user/udata-fs  # Adjust to your local path

# SAML / Autenticação.gov
SECURITY_SAML_ENTITY_ID=www.dados.gov.pt
SECURITY_SAML_ENTITY_NAME=AMA - Dados Abertos (Dados Gov)
SECURITY_SAML_KEY_FILE=udata/auth/saml/credentials/private.pem
SECURITY_SAML_CERT_FILE=udata/auth/saml/credentials/AMA.pem
SECURITY_SAML_IDP_METADATA=udata/auth/saml/credentials/metadata.xml
SECURITY_SAML_FAAALEVEL=3
SECURITY_SAML_FA_URL=https://autenticacao.gov.pt/fa/

# Email
MAIL_SERVER=mail.ama.pt
MAIL_DEFAULT_SENDER=noreply.dados.gov@arte.gov.pt
MAIL_PORT=25
```

> **Note:** In Docker, `SERVER_MONGO` and `SERVER_REDIS` may be overridden by `docker-compose.yml` depending on the environment (see "Infrastructure Connectivity" below). The mail is routed to the Mailpit container in local development.

### Infrastructure Connectivity (MongoDB, Redis, Elasticsearch)

The backend connects to MongoDB, Redis (and optionally Elasticsearch) via IPs defined in `.env` → read by `udata.cfg` via `os.getenv()`. The correct IP depends on the **deployment environment**:

| Environment | MongoDB / Redis location | How to configure |
|---|---|---|
| **Local dev (sem Docker)** | Same machine (`localhost`) | `.env`: `SERVER_MONGO=localhost` |
| **Local dev (Docker)** | Same machine, but in separate containers | `docker-compose.yml` overrides to `host.docker.internal` |
| **DEV server** | Dedicated machines | `.env`: `SERVER_MONGO=10.55.37.143`, `SERVER_REDIS=10.55.37.142` |
| **TST server** | Dedicated machines | `.env`: `SERVER_MONGO=10.55.37.40`, `SERVER_REDIS=10.55.37.41` |
| **PRD server** | Dedicated machines | `.env`: configured per environment |

**How it works:**

1. `.env` defines the base values (e.g., `SERVER_MONGO=localhost`)
2. `udata.cfg` reads them and builds connection URLs:
   ```python
   SERVER_MONGO = os.getenv('SERVER_MONGO')
   MONGODB_HOST = f'mongodb://{SERVER_MONGO}:27017/udata'
   ```
3. In Docker, `docker-compose.yml` can override these via the `environment:` block:
   ```yaml
   environment:
     SERVER_MONGO: host.docker.internal  # reach host's MongoDB from inside the container
     SERVER_REDIS: host.docker.internal
   ```
   Container environment variables take priority over `.env` values.

**For remote environments (DEV/TST/PRD):** remove the `SERVER_MONGO` and `SERVER_REDIS` overrides from `docker-compose.yml` so the values from `.env` are used directly with the real server IPs. Alternatively, set the correct IPs in the `docker-compose.yml` `environment:` block.

> **Elasticsearch** is currently disabled in `udata.cfg` (commented out). If re-enabled, follow the same pattern: set `SERVER_ELASTICSEARCH` in `.env` with the appropriate IP for each environment.

### Frontend Environment

The frontend uses build-time `ARG` values in the Dockerfile and runtime `environment` in `docker-compose.yml`.

| Variable | Build-time (ARG) | Runtime (env) | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE` | `/api/1` | `/api/1` | API v1 base path |
| `NEXT_PUBLIC_API_V2_BASE` | `/api/2` | `/api/2` | API v2 base path |
| `NEXT_PUBLIC_SAML_ENABLED` | `true` | `true` | Show CMD/eIDAS login button |
| `BACKEND_URL` | `http://host.docker.internal:7000` | `http://host.docker.internal:7000` | Backend URL for Next.js rewrites |

> **Important:** `BACKEND_URL` and `NEXT_PUBLIC_*` variables must be set at **build time** (as `ARG` in the Dockerfile) because Next.js bakes them into the standalone output. Setting them only at runtime via `docker-compose.yml` environment has no effect on rewrites or client-side code.

## Dockerfile Details

### Backend Dockerfile

```dockerfile
FROM python:3.12-slim
```

Key system dependencies:
- `build-essential`, `libxml2-dev`, `libxslt1-dev` — for lxml/mongoengine
- `libffi-dev`, `libssl-dev` — for cryptography
- `xmlsec1`, `libxmlsec1-dev`, `libxmlsec1-openssl` — **required for SAML authentication** (pysaml2 uses xmlsec1 to sign requests and validate signatures)
- `git` — for pip dependencies from git repos

Package management uses **uv** (not pip). The build uses two `uv sync` steps for layer caching:
1. `uv sync --no-dev --no-install-project` — install dependencies only
2. `uv sync --no-dev` — install the project itself

Default command: gunicorn with 4 workers, 2 threads, 120s timeout.

### Frontend Dockerfile

Multi-stage build with 3 stages:

1. **deps** — `npm ci` (dependency installation)
2. **builder** — `npm run build` (Next.js build with all ARGs available)
3. **runner** — Minimal production image with standalone output

Runs as non-root user `nextjs` (uid 1001).

## Docker Compose Details

### Backend (`backend/docker-compose.yml`)

```yaml
services:
  app:       # Flask API (gunicorn)
  worker:    # Celery async task worker
  beat:      # Celery periodic task scheduler
  mailpit:   # Local SMTP server for email testing
```

**Volumes:**
- `./udata.cfg:/app/udata.cfg:ro` — Flask configuration (read-only mount)
- `udata-fs:/udata/fs` — File uploads (shared between app and worker)
- `app-logs:/logs` — Application logs

**Networking:**
- In local dev, `docker-compose.yml` overrides `SERVER_MONGO` and `SERVER_REDIS` to `host.docker.internal` (resolves to the host machine where MongoDB and Redis run as separate containers or services)
- In remote environments (DEV/TST/PRD), remove those overrides or set the real server IPs so the containers connect directly to the dedicated database machines
- Mailpit container provides SMTP on port 1025 (UI on 8025)
- Worker runs with `C_FORCE_ROOT=true` (Celery requires this in Docker)

### Frontend (`frontend/docker-compose.yml`)

Single service that connects to the backend via `host.docker.internal:7000`.

## Common Operations

### View Logs

```bash
# Backend (all services)
docker compose -f backend/docker-compose.yml logs -f

# Backend (specific service)
docker compose -f backend/docker-compose.yml logs -f app
docker compose -f backend/docker-compose.yml logs -f worker

# Frontend
docker compose -f frontend/docker-compose.yml logs -f app

# Filter SAML-related logs
docker compose -f backend/docker-compose.yml logs app 2>&1 | grep -i "SAML"
```

### Rebuild After Code Changes

```bash
# Backend
docker compose -f backend/docker-compose.yml up -d --build app

# Frontend (always use --no-cache if changing ARGs or next.config.ts)
docker compose -f frontend/docker-compose.yml build --no-cache app
docker compose -f frontend/docker-compose.yml up -d app
```

### Run Database Migrations

```bash
docker compose -f backend/docker-compose.yml exec app uv run udata db upgrade
```

### Initialize Database

```bash
docker compose -f backend/docker-compose.yml exec app uv run udata init
```

### Run Tests

Tests require a separate MongoDB instance on port 27018:

```bash
cd backend
docker compose -f docker-compose.test.yml up -d   # Start test MongoDB
uv run pytest                                       # Run tests locally
docker compose -f docker-compose.test.yml down      # Stop test MongoDB
```

### Stop All Services

```bash
docker compose -f backend/docker-compose.yml down
docker compose -f frontend/docker-compose.yml down
```

### Check Service Status

```bash
docker compose -f backend/docker-compose.yml ps
docker compose -f frontend/docker-compose.yml ps
```

### Access Mailpit (Email Testing)

Open http://localhost:8025 to view all emails sent by the application (registration confirmations, password resets, migration codes, etc.).

## Troubleshooting

### `ECONNREFUSED 127.0.0.1:7000` in Frontend Logs

**Cause:** The frontend container cannot reach the backend. The `BACKEND_URL` was not set at build time, so the Next.js rewrites fell back to `127.0.0.1:7000` (which is the container itself, not the host).

**Fix:** Ensure `BACKEND_URL` is defined as an `ARG` in the frontend Dockerfile (it is by default). Rebuild with `--no-cache`:

```bash
docker compose -f frontend/docker-compose.yml build --no-cache app
docker compose -f frontend/docker-compose.yml up -d app
```

### `SigverError: Cannot find ['xmlsec1']` in Backend Logs

**Cause:** The `xmlsec1` binary is not installed in the backend Docker image. pysaml2 requires it for SAML request signing and response validation.

**Fix:** Ensure the backend Dockerfile includes `xmlsec1`, `libxmlsec1-dev`, and `libxmlsec1-openssl` in the `apt-get install` step. Rebuild:

```bash
docker compose -f backend/docker-compose.yml up -d --build app
```

### SAML Login Button Does Nothing

**Cause:** The `submitSamlForm()` function was silently catching errors without showing feedback.

**Diagnosis:**
1. Open browser DevTools (F12 → Console)
2. Click "Autenticar com CMD"
3. Check for error messages in the console and on the page

Common sub-causes:
- Backend not reachable (see `ECONNREFUSED` above)
- Backend returning 500 (see `xmlsec1` above)
- `NEXT_PUBLIC_SAML_ENABLED` not set to `true`

### MongoDB/Redis Connection Errors

**Cause:** The app container cannot reach MongoDB or Redis at the configured IP.

**Diagnosis:**
- **Local dev:** MongoDB/Redis run on the host machine — `docker-compose.yml` overrides the IPs to `host.docker.internal`
- **Remote environments:** MongoDB/Redis run on dedicated servers — IPs are defined in `.env` (e.g., `SERVER_MONGO=10.55.37.143`)

**Fix (local):** Ensure MongoDB and Redis are running on the host:

```bash
# Check if MongoDB is running
mongosh --eval "db.runCommand({ping: 1})"

# Check if Redis is running
redis-cli ping
```

**Fix (remote):** Verify the IPs in `.env` are correct and the servers are reachable from the app server:

```bash
# Test connectivity from inside the container
docker compose -f backend/docker-compose.yml exec app python -c "
import os; print(f'SERVER_MONGO={os.getenv(\"SERVER_MONGO\")}')
"
```

### Emails Not Being Sent

In Docker, emails are routed to Mailpit (not the real mail server). Check http://localhost:8025 for captured emails.

### Container Keeps Restarting

Check logs for the specific service:

```bash
docker compose -f backend/docker-compose.yml logs --tail=50 app
```

Common causes:
- Missing `.env` file
- Missing `udata.cfg` file
- MongoDB/Redis not accessible

## Port Summary

| Port  | Service               | Description                      |
|-------|-----------------------|----------------------------------|
| 3000  | Frontend (Next.js)    | Web interface                    |
| 7000  | Backend (gunicorn)    | REST API                         |
| 1025  | Mailpit (SMTP)        | Email capture (internal)         |
| 8025  | Mailpit (UI)          | Email viewer                     |
| 27017 | MongoDB (host)        | Database                         |
| 6379  | Redis (host)          | Cache / Celery broker            |
