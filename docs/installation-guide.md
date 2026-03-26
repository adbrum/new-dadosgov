# Guia de Instalacao - dados.gov.pt

Guia passo a passo para replicar a instalacao completa do sistema dados.gov.pt (frontend + backend) num novo ambiente de desenvolvimento.

---

## Pre-requisitos

Antes de comecar, garantir que as seguintes ferramentas estao instaladas:

| Ferramenta | Versao minima | Verificacao |
|---|---|---|
| Git | 2.x | `git --version` |
| Docker | 24.x | `docker --version` |
| Docker Compose | 2.x | `docker compose version` |
| Node.js | 22.x | `node --version` |
| npm | 10.x | `npm --version` |
| Python | 3.12.x | `python3 --version` |
| uv | 0.4+ | `uv --version` |
| MongoDB | 6.x/7.x | `mongod --version` |
| Redis | 7.x | `redis-server --version` |

> **Nota:** MongoDB e Redis podem correr localmente ou via Docker. A seccao 5 cobre ambas as opcoes.

---

## 1. Clonar o repositorio principal (monorepo)

O projeto usa Git submodules para backend e frontend.

```bash
# 1.1 Clonar o monorepo com submodulos
git clone --recurse-submodules git@github.com:adbrum/new-dadosgov.git

# 1.2 Entrar no diretorio do projeto
cd new-dadosgov

# 1.3 Se ja tiver clonado sem --recurse-submodules, inicializar manualmente
git submodule update --init --recursive
```

### Estrutura resultante

```
new-dadosgov/
├── backend/          # git@github.com:amagovpt/udata-pt.git
├── frontend/         # git@github.com:adbrum/udata_agora.git
├── docs/
├── .env              # GitHub PAT (para acesso a pacotes privados)
├── .gitmodules
├── CLAUDE.md
└── README.md
```

---

## 2. Configurar o ficheiro `.env` da raiz

Este ficheiro contem o GitHub Personal Access Token necessario para aceder a pacotes privados.

```bash
# 2.1 Criar o ficheiro .env na raiz (se nao existir)
cat > .env << 'EOF'
GITHUB_PAT=<YOUR_GITHUB_PERSONAL_ACCESS_TOKEN>
EOF
```

> **Seguranca:** Nunca commitar este ficheiro. Ja esta no `.gitignore`.

---

## 3. Configurar o backend

### 3.1 Criar o ficheiro `backend/.env`

```bash
cp backend/.env.example backend/.env 2>/dev/null || true
```

Se nao existir `.env.example`, criar manualmente com o seguinte conteudo (ajustar os valores):

```bash
cat > backend/.env << 'EOF'
# Configuracoes Basicas
DEBUG=True
SITE_ID=local
SERVER_NAME=localhost:7000
SITE_URL=http://localhost:7000
PREFERRED_URL_SCHEME=http
CDATA_BASE_URL=http://localhost:3000

# Cookies de Sessao
SESSION_COOKIE_SECURE=False

# Seguranca e Monitorizacao
SENTRY_DSN=
SENTRY_ENVIRONMENT=local

# IP Services (ajustar se MongoDB/Redis nao correm em localhost)
SERVER_MONGO=localhost
SERVER_REDIS=localhost
SERVER_ELASTICSEARCH=localhost

# Uploads de Ficheiros
FS_ROOT=/opt/udata/fs

# Validacao de URLs (apenas para dev)
URLS_ALLOW_LOCAL=True
URLS_ALLOW_PRIVATE=True
URLS_ADDITIONAL_TLDS=local

# Tabular Preview
TABULAR_API_URL=http://localhost:8005
TABULAR_EXPLORE_URL=http://localhost:7000

# Metricas
METRICS_API=http://localhost:8006/api

# Hydra (Analise de Eventos)
RESOURCES_ANALYSER_URI=http://localhost:8000
RESOURCES_ANALYSER_API_KEY=<YOUR_ANALYSER_API_KEY>

# Autenticacao SAML
SECURITY_SAML_ENTITY_ID="www.dados.gov.pt"
SECURITY_SAML_ENTITY_NAME="AMA - Dados Abertos (Dados Gov)"
SECURITY_SAML_KEY_FILE="udata/auth/saml/credentials/private.pem"
SECURITY_SAML_CERT_FILE="udata/auth/saml/credentials/AMA.pem"
SECURITY_SAML_IDP_METADATA="udata/auth/saml/credentials/metadata.xml"
SECURITY_SAML_FAAALEVEL=3
SECURITY_SAML_FA_URL="https://preprod.autenticacao.gov.pt/fa/"

# Configuracoes de E-mail
MAIL_SERVER=localhost
MAIL_DEFAULT_SENDER=noreply@localhost
MAIL_DEFAULT_RECEIVER=admin@localhost
MAIL_PORT=1025
MAIL_USE_TLS=False
MAIL_USE_SSL=False

# reCAPTCHA
RECAPTCHA_PUBLIC_KEY=<YOUR_RECAPTCHA_PUBLIC_KEY>
RECAPTCHA_PRIVATE_KEY=<YOUR_RECAPTCHA_PRIVATE_KEY>

# Tags
TAG_MIN_LENGTH=0
TAG_MAX_LENGTH=250

# Exportacao & Modo de Leitura
EXPORT_CSV_DATASET_ID=
READ_ONLY_MODE=False

# Piwik (Matomo) & Metricas
PIWIK_ID_FRONT=5
PIWIK_ID_API=5
PIWIK_ID=5
PIWIK_SCHEME=http
PIWIK_URL=
PIWIK_AUTH=
EOF
```

### 3.2 Verificar o ficheiro `backend/udata.cfg`

O `udata.cfg` ja esta incluido no repositorio e le as variaveis do `.env` automaticamente via `python-dotenv`. Nao precisa de alteracoes a menos que seja necessario personalizar plugins ou harvester backends.

```bash
# Verificar que o ficheiro existe
ls -la backend/udata.cfg
```

### 3.3 Copiar credenciais SAML

Os ficheiros de credenciais SAML sao necessarios para a autenticacao via Autenticacao.gov.

```bash
# 3.3.1 Verificar que o diretorio de credenciais existe
ls -la backend/udata/auth/saml/credentials/
```

O diretorio deve conter:

| Ficheiro | Descricao |
|---|---|
| `private.pem` | Chave privada do Service Provider (RSA 4096) |
| `AMA.pem` | Certificado publico do Service Provider |
| `metadata.xml` | Metadados XML do Identity Provider (Autenticacao.gov) |

> **Importante:** Estes ficheiros sao sensiveis e nao devem ser commitados. Se nao existirem no repositorio, obter junto da equipa ou gerar novos:
>
> ```bash
> # Gerar par de chaves (apenas se necessario para ambiente de desenvolvimento)
> openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
>   -keyout backend/udata/auth/saml/credentials/private.pem \
>   -out backend/udata/auth/saml/credentials/AMA.pem \
>   -subj "/CN=dados.gov-DEV"
> ```
>
> O `metadata.xml` do IdP deve ser obtido a partir do portal de pre-producao da Autenticacao.gov.

### 3.4 Criar o `docker-compose.override.yml`

Este ficheiro permite que os containers Docker se liguem ao MongoDB e Redis que correm na maquina host.

```bash
cp backend/docker-compose.override.yml.example backend/docker-compose.override.yml
```

Conteudo esperado:

```yaml
services:
  app:
    environment:
      SERVER_MONGO: host.docker.internal
      SERVER_REDIS: host.docker.internal
  worker:
    environment:
      SERVER_MONGO: host.docker.internal
      SERVER_REDIS: host.docker.internal
  beat:
    environment:
      SERVER_MONGO: host.docker.internal
      SERVER_REDIS: host.docker.internal
```

### 3.5 Criar o diretorio de uploads

```bash
# Criar o diretorio configurado em FS_ROOT
mkdir -p /opt/udata/fs
# Ou usar um caminho local
mkdir -p ~/udata-fs
```

> Atualizar `FS_ROOT` no `backend/.env` se usar um caminho diferente de `/opt/udata/fs`.

---

## 4. Configurar o frontend

### 4.1 Criar o ficheiro `frontend/.env.local`

```bash
cp frontend/.env.example frontend/.env.local
```

Conteudo esperado:

```env
# Backend API
NEXT_PUBLIC_API_BASE=/api/1
NEXT_PUBLIC_API_V2_BASE=/api/2
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

---

## 5. Instalar servicos de infraestrutura (MongoDB + Redis)

### Opcao A: MongoDB e Redis nativos (recomendado para dev local)

```bash
# 5A.1 Instalar e iniciar MongoDB
sudo systemctl start mongod
# Verificar
mongosh --eval "db.runCommand({ ping: 1 })"

# 5A.2 Instalar e iniciar Redis
sudo systemctl start redis-server
# Verificar
redis-cli ping  # Deve retornar PONG
```

### Opcao B: MongoDB e Redis via Docker

```bash
# 5B.1 Criar um docker-compose para infraestrutura na raiz
cat > docker-compose.infra.yml << 'EOF'
services:
  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongodb-data:/data/db
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

volumes:
  mongodb-data:
EOF

# 5B.2 Iniciar os servicos
docker compose -f docker-compose.infra.yml up -d
```

> **Nota:** Se usar Docker para MongoDB/Redis, atualizar `SERVER_MONGO` e `SERVER_REDIS` no `backend/.env` para `localhost` (os containers expoe as portas no host).

---

## 6. Instalar dependencias

### 6.1 Backend (Python)

```bash
cd backend

# Instalar dependencias com uv
uv sync --extra dev --extra test

# Voltar a raiz
cd ..
```

### 6.2 Frontend (Node.js)

```bash
cd frontend

# Instalar dependencias
npm install

# Voltar a raiz
cd ..
```

---

## 7. Inicializar a base de dados

```bash
cd backend

# 7.1 Inicializar o udata (cria colecoes e dados iniciais)
uv run udata init

# 7.2 Executar migracoes pendentes
uv run udata db upgrade

cd ..
```

---

## 8. Levantar o sistema

### Opcao A: Desenvolvimento local (sem Docker)

```bash
# Terminal 1 - Backend API (porta 7000)
cd backend && inv serve

# Terminal 2 - Celery Worker
cd backend && inv work

# Terminal 3 - Celery Beat (scheduler)
cd backend && inv beat

# Terminal 4 - Frontend (porta 3000)
cd frontend && npm run dev
```

### Opcao B: Com Docker Compose

```bash
# 8B.1 Backend (build + start)
cd backend
docker compose up -d --build

# 8B.2 Frontend (build + start)
cd ../frontend
docker compose up -d --build
```

---

## 9. Verificar a instalacao

### 9.1 Backend API

```bash
# Verificar que a API responde
curl -s http://localhost:7000/api/1/ | head -c 200

# Verificar endpoint de datasets
curl -s http://localhost:7000/api/1/datasets/ | python3 -m json.tool | head -20
```

### 9.2 Frontend

```bash
# Abrir no browser
open http://localhost:3000  # macOS
xdg-open http://localhost:3000  # Linux
```

### 9.3 Servicos de infraestrutura

```bash
# MongoDB
mongosh --eval "db.runCommand({ ping: 1 })"

# Redis
redis-cli ping

# Docker containers (se aplicavel)
docker compose ps
```

---

## 10. Comandos uteis pos-instalacao

| Acao | Comando |
|---|---|
| Ver logs do backend (Docker) | `cd backend && docker compose logs -f app` |
| Ver logs do worker (Docker) | `cd backend && docker compose logs -f worker` |
| Parar tudo (Docker) | `docker compose down` |
| Reconstruir containers | `docker compose up -d --build` |
| Correr testes backend | `cd backend && docker compose -f docker-compose.test.yml up -d && uv run pytest` |
| Lint backend | `cd backend && uv run ruff check --fix . && uv run ruff format .` |
| Lint frontend | `cd frontend && npm run lint` |
| Build producao frontend | `cd frontend && npm run build` |
| Inicializar Elasticsearch | `cd backend && uv run udata search init` |

---

## Resumo dos ficheiros de configuracao

| # | Ficheiro | Tipo | Acao |
|---|---|---|---|
| 1 | `.env` (raiz) | GitHub PAT | Criar manualmente |
| 2 | `backend/.env` | Variaveis de ambiente do backend | Criar a partir do template |
| 3 | `backend/udata.cfg` | Configuracao Flask | Ja incluido no repo |
| 4 | `backend/docker-compose.override.yml` | Override Docker local | Copiar do `.example` |
| 5 | `backend/udata/auth/saml/credentials/private.pem` | Chave privada SAML | Obter da equipa ou gerar |
| 6 | `backend/udata/auth/saml/credentials/AMA.pem` | Certificado SAML | Obter da equipa ou gerar |
| 7 | `backend/udata/auth/saml/credentials/metadata.xml` | Metadados IdP | Obter da Autenticacao.gov |
| 8 | `frontend/.env.local` | Variaveis de ambiente do frontend | Copiar do `.env.example` |

---

## Portas utilizadas

| Servico | Porta | Descricao |
|---|---|---|
| Frontend (Next.js) | 3000 | Interface web |
| Backend API (Flask) | 7000 | API REST |
| MongoDB | 27017 | Base de dados |
| Redis | 6379 | Cache + message broker |
| Elasticsearch | 9200 | Motor de pesquisa (opcional) |
| Mailpit SMTP | 1025 | Servidor de email local (dev) |
| Mailpit UI | 8025 | Interface web do Mailpit |

---

## Resolucao de problemas

### Erro: `ECONNREFUSED` ao ligar ao MongoDB/Redis

- Verificar que MongoDB e Redis estao a correr
- Se usar Docker, verificar que `host.docker.internal` resolve corretamente
- Em Linux (sem Docker Desktop), pode ser necessario adicionar `--add-host=host.docker.internal:host-gateway` ou usar o `extra_hosts` no docker-compose

### Erro: `xmlsec1` not found

O backend precisa da biblioteca `xmlsec1` para SAML:

```bash
# Ubuntu/Debian
sudo apt-get install xmlsec1 libxmlsec1-dev libxmlsec1-openssl

# macOS
brew install libxmlsec1
```

### Erro CSRF com cookies de sessao

Garantir que `SESSION_COOKIE_SECURE=False` no `backend/.env` quando usar HTTP em desenvolvimento local.

### Frontend nao consegue ligar ao backend

Verificar que `BACKEND_URL=http://localhost:7000` esta definido no `frontend/.env.local` e que o backend esta a correr na porta 7000.
