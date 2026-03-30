# Guia de Instalação — dados.gov.pt

> Guia passo a passo para configurar o ambiente de desenvolvimento do portal dados.gov.pt num novo computador.

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Clonar o repositório](#2-clonar-o-repositório)
3. [Serviços externos (MongoDB + Redis)](#3-serviços-externos-mongodb--redis)
4. [Configurar o Backend](#4-configurar-o-backend)
5. [Configurar o Frontend](#5-configurar-o-frontend)
6. [Ficheiros que NÃO estão no Git](#6-ficheiros-que-não-estão-no-git)
7. [Iniciar os servidores](#7-iniciar-os-servidores)
8. [Verificar a instalação](#8-verificar-a-instalação)
9. [Modo Docker (alternativa)](#9-modo-docker-alternativa)
10. [Comandos úteis](#10-comandos-úteis)
11. [Resolução de problemas](#11-resolução-de-problemas)

---

## 1. Pré-requisitos

Instalar no sistema operativo **antes** de começar:

| Ferramenta | Versão | Instalação |
|---|---|---|
| **Python** | 3.11, 3.12 ou 3.13 | [python.org](https://www.python.org/downloads/) |
| **uv** | Última versão | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Node.js** | 22.x | [nodejs.org](https://nodejs.org/) ou `nvm install 22` |
| **npm** | Vem com Node.js | — |
| **Git** | Última versão | `sudo apt install git` |
| **MongoDB** | 6.x ou 7.x | Ver secção 3 |
| **Redis** | 7.x | Ver secção 3 |
| **Docker** (opcional) | Última versão | [docker.com](https://docs.docker.com/get-docker/) |

### Verificar versões

```bash
python3 --version   # >= 3.11
uv --version        # qualquer versão recente
node --version      # >= 22.0
npm --version       # >= 10.0
mongod --version    # >= 6.0
redis-server --version  # >= 7.0
```

---

## 2. Clonar o repositório

O projeto usa **git submodules** — o frontend e backend são repositórios separados.

```bash
# Clonar com submodules
git clone --recurse-submodules git@github.com:adbrum/new-dadosgov.git
cd new-dadosgov

# Se já clonaste sem submodules, inicializar:
git submodule init
git submodule update
```

### Estrutura do repositório

```
new-dadosgov/
├── backend/          # Submodule — API REST (Python/Flask/udata)
├── frontend/         # Submodule — Interface web (Next.js/React)
├── docs/             # Documentação
├── run_servers.py    # Script interativo para iniciar os servidores
└── CLAUDE.md         # Regras do projeto
```

### Ficheiros que precisam de ser copiados (NÃO estão no Git)

Após clonar, os seguintes ficheiros/diretórios **não existem no repositório** e precisam de ser criados ou copiados de um membro da equipa:

| Ficheiro | Caminho | Obrigatório | Como obter |
|---|---|---|---|
| `.env` | `backend/.env` | **Sim** | `cp backend/.env.example backend/.env` + pedir valores sensíveis à equipa |
| `.env.local` | `frontend/.env.local` | **Sim** | `cp frontend/.env.example frontend/.env.local` |
| `docker-compose.override.yml` | `backend/docker-compose.override.yml` | **Sim** (Docker) | `cp backend/docker-compose.override.yml.example backend/docker-compose.override.yml` |
| `udata-fs/` | `./udata-fs/` | **Sim** | `mkdir -p udata-fs` (diretório de uploads) |
| `private.pem` | `backend/udata/auth/saml/credentials/private.pem` | Apenas SAML | Pedir ao admin do projeto |
| `AMA.pem` | `backend/udata/auth/saml/credentials/AMA.pem` | Apenas SAML | Pedir ao admin do projeto |
| `metadata.xml` | `backend/udata/auth/saml/credentials/metadata.xml` | Apenas SAML | Pedir ao admin do projeto |

> Os passos de criação de cada ficheiro estão detalhados nas secções seguintes (4.2, 5.2, 3-B).

---

## 3. Serviços externos (MongoDB + Redis)

O projeto precisa de **MongoDB** (base de dados) e **Redis** (cache + fila de tarefas).

### Opção A: Instalar localmente

**MongoDB:**
```bash
# Ubuntu/Debian
sudo apt install -y gnupg curl
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update && sudo apt install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod
```

**Redis:**
```bash
sudo apt install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### Opção B: Via Docker (recomendado)

Já existe um template pronto no backend que configura o acesso ao MongoDB e Redis do host:

```bash
cd backend
cp docker-compose.override.yml.example docker-compose.override.yml
cd ..
```

Depois iniciar os containers de MongoDB e Redis:

```bash
docker run -d --name mongodb -p 27017:27017 mongo:7
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

> O `docker-compose.override.yml` é também necessário se usares o modo Docker (secção 9) — já está criado com este passo.

### Verificar que estão a funcionar

```bash
mongosh --eval "db.runCommand({ping:1})"    # { ok: 1 }
redis-cli ping                               # PONG
```

---

## 4. Configurar o Backend

```bash
cd backend
```

### 4.1. Instalar dependências Python

```bash
uv sync --extra dev --extra test
```

### 4.2. Criar o ficheiro `.env`

> **Este ficheiro NÃO está no Git** porque contém dados sensíveis (chaves API, credenciais SAML, passwords de serviços).

Já existe um template — basta copiar e preencher os valores sensíveis:

```bash
cp .env.example .env
```

O conteúdo do `.env.example` é:

```bash
# Configurações Básicas
DEBUG=True
SITE_ID=local
SERVER_NAME=localhost:7000
SITE_URL=http://localhost:7000
PREFERRED_URL_SCHEME=http
SESSION_COOKIE_SECURE=False

# URL do frontend Next.js
CDATA_BASE_URL=http://localhost:3000

# Serviços (ajustar se não forem localhost)
SERVER_MONGO=localhost
SERVER_REDIS=localhost

# Uploads de Ficheiros — ALTERAR PARA O TEU PATH ABSOLUTO
FS_ROOT=/home/SEU_USER/workspace/new-dadosgov/udata-fs

# Validação de URLs (apenas dev)
URLS_ALLOW_LOCAL=True
URLS_ALLOW_PRIVATE=True
URLS_ADDITIONAL_TLDS=local,tst,dev

# Segurança, Password policy, E-mail, reCAPTCHA, SAML, Tags
# ... campos com ***** — pedir os valores reais à equipa
```

> **Após copiar:**
> 1. Alterar `FS_ROOT` para o caminho absoluto do teu utilizador.
> 2. Pedir os valores dos campos marcados com `*****` a um membro da equipa (Sentry, passwords, email, reCAPTCHA, SAML, etc.).

### 4.3. Criar o diretório de uploads

```bash
mkdir -p ../udata-fs
```

### 4.4. Inicializar a base de dados

```bash
uv run udata init
uv run udata db upgrade
```

### 4.5. Criar um utilizador admin (opcional)

```bash
uv run udata user create --email admin@example.com --password "MinhaPassword123!" --first-name Admin --last-name User
uv run udata user set-admin admin@example.com
```

---

## 5. Configurar o Frontend

```bash
cd ../frontend
```

### 5.1. Instalar dependências Node.js

```bash
npm install
```

### 5.2. Criar o ficheiro `.env.local`

> **Este ficheiro NÃO está no Git** por consistência de ambientes (cada programador pode ter URLs diferentes).

Já existe um template — basta copiar:

```bash
cp .env.example .env.local
```

O conteúdo do `.env.example` (e portanto do teu `.env.local`) é:

```bash
# Backend API (URLs relativos — proxy via Next.js rewrite)
NEXT_PUBLIC_API_BASE=/api/1
NEXT_PUBLIC_API_V2_BASE=/api/2
# URL absoluto do backend (usado pelo proxy server-side)
BACKEND_URL=http://localhost:7000
NEXT_PUBLIC_FRONT_BASE=http://localhost:3000
NEXT_PUBLIC_BASE_URL=https://dados.gov.pt/
NEXT_PUBLIC_STATIC_URL=https://dados.gov.pt/static/
# Feature flags
NEXT_PUBLIC_READ_ONLY_MODE=false
NEXT_PUBLIC_REQUIRE_EMAIL_CONFIRMATION=true
NEXT_PUBLIC_SAML_ENABLED=true
# Analytics (opcional)
NEXT_PUBLIC_SENTRY_DSN=
NEXT_PUBLIC_MATOMO_HOST=
NEXT_PUBLIC_MATOMO_SITE_ID=1
```

> **Nota:** Para dev local, podes alterar `NEXT_PUBLIC_STATIC_URL` para `http://localhost:7000/static/` se quiseres servir assets do backend local.

---

## 6. Ficheiros que NÃO estão no Git

Estes ficheiros precisam de ser criados manualmente ou copiados de outro programador:

### Obrigatórios

| Ficheiro | Caminho | Descrição | Como obter |
|---|---|---|---|
| `.env` | `backend/.env` | Variáveis de ambiente do backend (dados sensíveis) | Pedir à equipa ou criar template (secção 4.2) |
| `.env.local` | `frontend/.env.local` | Variáveis de ambiente do frontend | `cp .env.example .env.local` |
| `udata-fs/` | `./udata-fs/` | Diretório de uploads | `mkdir -p udata-fs` |

### Opcionais (necessários para SAML / Autenticação.gov)

| Ficheiro | Caminho | Descrição | Como obter |
|---|---|---|---|
| `private.pem` | `backend/udata/auth/saml/credentials/private.pem` | Chave privada SP | Pedir ao admin do projeto |
| `AMA.pem` | `backend/udata/auth/saml/credentials/AMA.pem` | Certificado público SP | Pedir ao admin do projeto |
| `metadata.xml` | `backend/udata/auth/saml/credentials/metadata.xml` | Metadata do IdP | Pedir ao admin do projeto |

### Opcionais (Docker dev)

| Ficheiro | Caminho | Descrição | Como obter |
|---|---|---|---|
| `docker-compose.override.yml` | `backend/docker-compose.override.yml` | Override local para Docker | `cp docker-compose.override.yml.example docker-compose.override.yml` |

---

## 7. Iniciar os servidores

### Opção 1: Script interativo (recomendado)

Na raiz do projeto existe o `run_servers.py` que gere todos os modos de execução:

```bash
cd new-dadosgov
python run_servers.py
```

O script apresenta um menu com 6 opções:

| Opção | Modo | Descrição |
|---|---|---|
| **1** | Desenvolvimento (foreground) | Backend (`inv dev`) + Frontend (`npm run dev`) no terminal |
| **2** | Segundo plano (PM2) | Backend + Frontend em background via PM2 |
| **3** | Produção (foreground) | Frontend com `npm run build` + `npm run start` |
| **4** | Docker | Backend e frontend via Docker Compose (hot-reload) |
| **5** | Docker (rebuild) | Igual ao 4 mas reconstrói as imagens |
| **6** | Docker (produção) | Backend com gunicorn, sem hot-reload |

Para desenvolvimento normal, escolher a **opção 1**:
```
Backend:  http://localhost:7000
Frontend: http://localhost:3000
```

Parar com `Ctrl+C`.

### Opção 2: Manual em dois terminais

**Terminal 1 — Backend:**
```bash
cd backend
uv run inv dev    # Inicia Flask (7000) + Celery worker
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev       # Inicia Next.js (3000)
```

---

## 8. Verificar a instalação

| URL | O que deve aparecer |
|---|---|
| http://localhost:7000/api/1/ | Swagger da API (JSON) |
| http://localhost:3000 | Homepage do portal dados.gov |
| http://localhost:3000/pages/datasets | Listagem de datasets |
| http://localhost:3000/pages/admin | Backoffice (requer login) |

### Testar a API

```bash
curl http://localhost:7000/api/1/site/ | python -m json.tool
```

### Testar o login

1. Ir a http://localhost:3000
2. Clicar em "Iniciar sessão"
3. Usar as credenciais criadas na secção 4.5

---

## 9. Modo Docker (alternativa)

Se preferires correr tudo via Docker (não precisa de instalar Python/Node localmente):

### 9.1. Criar `docker-compose.override.yml` no backend

Já existe um template pronto — basta copiar:

```bash
cd backend
cp docker-compose.override.yml.example docker-compose.override.yml
```

Este ficheiro redireciona o MongoDB e Redis para o host da máquina (onde já os tens a correr via Docker ou localmente).

### 9.2. Iniciar via script

```bash
cd ..
python run_servers.py
# Escolher opção 4 (Docker) ou 5 (Docker rebuild)
```

### Portas em modo Docker

| Serviço | Porta |
|---|---|
| Backend API | 7000 |
| Frontend | 3000 |
| Mailpit (email dev) | 8025 |

---

## 10. Comandos úteis

### Backend

```bash
cd backend

# Servidor de desenvolvimento
uv run inv serve                      # Apenas API (sem worker)
uv run inv dev                        # API + Celery worker

# Base de dados
uv run udata init                     # Inicializar BD
uv run udata db upgrade               # Correr migrações

# Utilizadores
uv run udata user create              # Criar utilizador
uv run udata user set-admin EMAIL     # Dar permissões admin

# Testes
docker compose -f docker-compose.test.yml up -d   # MongoDB de teste
uv run pytest                                       # Correr testes
uv run pytest -x -v                                 # Parar no 1º erro

# Lint e formato
uv run ruff check --fix .
uv run ruff format .
```

### Frontend

```bash
cd frontend

# Desenvolvimento
npm run dev                # Servidor dev (porta 3000)
npm run build              # Build de produção
npm run start              # Servidor de produção

# Qualidade
npm run lint               # ESLint

# Testes E2E
npx playwright install     # Instalar browsers (1ª vez)
npx playwright test        # Correr testes
```

---

## 11. Resolução de problemas

### Erro: `PermissionError: [Errno 13] Permission denied: '/home/...'`

O `FS_ROOT` no `backend/.env` aponta para um diretório que não existe ou sem permissões.

```bash
# Verificar e criar
mkdir -p /caminho/para/udata-fs
```

### Erro: `MongoServerError: connect ECONNREFUSED`

MongoDB não está a correr.

```bash
sudo systemctl start mongod
# ou via Docker:
docker start mongodb
```

### Erro: `CORS blocked` no browser

O frontend está a tentar chamar a API diretamente. Verificar que:
- `NEXT_PUBLIC_API_BASE=/api/1` (relativo, NÃO `http://localhost:7000/api/1`)
- `BACKEND_URL=http://localhost:7000` (só para o server-side)

### Erro: `Module not found` no frontend

Falta uma dependência:

```bash
cd frontend && npm install
```

### Erro: `uv: command not found`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc   # ou ~/.zshrc
```

### Submodules vazios após clone

```bash
git submodule init
git submodule update
```

### Frontend mostra dados antigos / cache

```bash
# Limpar cache do Next.js
cd frontend
rm -rf .next
npm run dev
```

---

## Resumo rápido (TL;DR)

```bash
# 1. Clonar
git clone --recurse-submodules git@github.com:adbrum/new-dadosgov.git
cd new-dadosgov

# 2. Serviços
docker run -d --name mongodb -p 27017:27017 mongo:7
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 3. Backend
cd backend
uv sync --extra dev --extra test
# Copiar .env e preencher valores sensíveis (ver secção 4.2)
cp .env.example .env
mkdir -p ../udata-fs
uv run udata init && uv run udata db upgrade

# 4. Frontend
cd ../frontend
npm install
cp .env.example .env.local

# 5. Arrancar
cd ..
python run_servers.py   # Escolher opção 1
```
