# Testes End-to-End (Playwright) — dados.gov.pt

> Como correr a suite Playwright (`frontend/tests/e2e/`) e ver o relatório, tanto contra a base de dados de desenvolvimento como contra a base de dados de testes descartável.

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Estrutura da suite](#2-estrutura-da-suite)
3. [Executar a suite normal](#3-executar-a-suite-normal-dev-db)
4. [Executar com base de dados descartável](#4-executar-com-base-de-dados-descartável)
5. [Ver o relatório no browser](#5-ver-o-relatório-no-browser)
6. [Variáveis de ambiente](#6-variáveis-de-ambiente)
7. [Modo UI / debug interactivo](#7-modo-ui--debug-interactivo)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Pré-requisitos

Antes de correr a suite garante que o ambiente local está pronto:

| Componente | Necessário | Comando para validar |
|---|---|---|
| **Node.js + dependências do frontend** | sim | `cd frontend && npm install` |
| **Python/uv + dependências do backend** | sim | `cd backend && uv sync --extra dev --extra test` |
| **MongoDB local em `27017`** | só para a suite normal | `docker ps \| grep udata-mongodb` |
| **Frontend dev em `:3000`** | só para a suite normal | `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000` (200) |
| **Backend dev em `:7000`** | só para a suite normal | `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:7000/api/1/site/` (200) |
| **Docker** | só para a DB descartável | `docker --version` |
| **Test admin/editor** | sim, ambos os modos | `cd backend && uv run udata user create --email e2e-admin@dados.gov.pt --first-name E2E --last-name Admin --password 'E2eAdmin2026!' --admin` (idem editor) |
| **Browsers Playwright** | sim | `cd frontend && npx playwright install chromium` |

> O test admin e editor são partilhados entre os dois modos. As fixtures (org/dataset/reuse) são geradas automaticamente pelo `globalSetup` em cada modo.

---

## 2. Estrutura da suite

```
frontend/
├── playwright.config.ts                    # 5 projects definidos abaixo
├── tests/
│   ├── auth.setup.ts                       # login admin+editor → grava admin.json/editor.json
│   ├── auth.setup.disposable.ts            # mesmo, mas contra o backend de teste
│   ├── global-setup.ts                     # pre-warm + seed (e boot da stack disposable se aplicável)
│   ├── global-teardown.ts                  # cleanup (fixtures dev DB + stack disposable)
│   ├── helpers/
│   │   ├── auth.ts                         # performLogin (UI)
│   │   ├── fixtures.ts                     # loadFixtures() — IDs da dev DB
│   │   └── disposable-fixtures.ts          # constantes da DB de teste
│   ├── e2e/
│   │   ├── frontend-public/                # 20 specs públicos (anónimo)
│   │   └── backoffice/
│   │       ├── *.spec.ts                   # 17 specs admin (não-destrutivos)
│   │       └── disposable/                 # specs destrutivos (CRUD real)
│   ├── .auth/                              # storage states (gitignored)
│   └── .fixtures/                          # IDs MongoDB seeded (gitignored)
```

### Projects no `playwright.config.ts`

| Project | testDir | Pré-requisitos | Quando usar |
|---|---|---|---|
| `frontend-public` | `tests/e2e/frontend-public` | dev frontend `:3000` | suite anónima pública |
| `auth-setup` | `auth.setup.ts` | dev frontend + backend | corre 1× e grava cookies |
| `backoffice` | `tests/e2e/backoffice` (excl. `disposable/`) | depende de `auth-setup` | admin pages não-destrutivas |
| `auth-setup-disposable` | `auth.setup.disposable.ts` | stack disposable arrancada | login no backend de teste |
| `backoffice-disposable` | `tests/e2e/backoffice/disposable` | depende de `auth-setup-disposable` | CRUD destrutivo (delete/edit) |
| `metrics` | `metrics-*.spec.ts` | dev frontend | suite específica de métricas |

---

## 3. Executar a suite normal (dev DB)

Usa o frontend (`:3000`) e o backend (`:7000`) com a tua base de dados de desenvolvimento. **Não corre testes destrutivos** — esses ficam `test.skip` para evitar perda de dados.

### Pré-condições

```bash
# 1. Frontend dev a correr (terminal A)
cd frontend && npm run dev

# 2. Backend dev a correr (terminal B)
cd backend && inv serve
```

### Comandos

```bash
cd frontend

# Suite pública anónima (20 specs, ~187 testes)
npx playwright test --project=frontend-public

# Suite backoffice (17 specs, ~134 testes; depende do auth-setup)
npx playwright test --project=auth-setup --project=backoffice

# Tudo junto: público + backoffice
npx playwright test --project=auth-setup --project=frontend-public --project=backoffice

# Um único spec
npx playwright test tests/e2e/frontend-public/01-homepage.spec.ts --project=frontend-public

# Filtrar por nome
npx playwright test -g "HP-01" --project=frontend-public
```

### Resultados típicos

| Suite | Passed | Skipped | Failed | Tempo |
|---|---|---|---|---|
| Pública | ~158 | ~28 | 0 | ~4 min |
| Backoffice | ~78 | ~57 | 0 | ~4 min |

> Skipped no backoffice = testes que precisam de fixtures destrutivas (criar/apagar). Para os correr, ver a próxima secção.

---

## 4. Executar com base de dados descartável

Usado para **testes destrutivos** (criar dataset, apagar reuse, mudar role de utilizador, etc.). Tudo o que mexer em dados reais corre numa **stack isolada**:

| Componente | Porta | Local |
|---|---|---|
| MongoDB de teste | `27019` | container `udata-mongodb-test` (tmpfs — wiped a cada arranque) |
| Redis de teste | `6380` | container `udata-redis-test` (tmpfs) |
| Backend de teste | `7001` | `uv run flask --app udata.wsgi_test:app run --host 127.0.0.1 --port 7001` |
| Frontend de teste | `3001` | `next dev -p 3001` (`NEXT_DIST_DIR=.next-test`, `BACKEND_URL=http://127.0.0.1:7001`) |

A stack arranca e desliga automaticamente a partir do `globalSetup` quando o filtro de project inclui `*-disposable` ou quando `PLAYWRIGHT_USE_DISPOSABLE=1` está definido.

### Comando único (recomendado)

```bash
cd frontend

# Auto-arranca: docker → backend test → frontend test → corre testes → desliga tudo
npx playwright test --project=auth-setup-disposable --project=backoffice-disposable
```

### Lifecycle controlado manualmente (debug)

Útil para inspecionar a stack de teste sem fechar entre runs.

```bash
# 1. MongoDB + Redis isolados (tmpfs — apaga ao reiniciar)
cd backend && bash scripts/test_db.sh up

# 2. Migra schema, cria admin/editor (bcrypt) + org/dataset/reuse
cd backend && UDATA_SETTINGS=$(pwd)/udata.test.cfg uv run python scripts/init_test_db.py

# 3. Backend de teste em :7001
cd backend && bash scripts/start_test_backend.sh --bg

# 4. Frontend de teste em :3001 (deixar a correr noutro terminal)
cd frontend && BACKEND_URL=http://127.0.0.1:7001 NEXT_DIST_DIR=.next-test npm run dev -- -p 3001

# 5. Correr os testes sem desligar a stack no fim
cd frontend && PLAYWRIGHT_USE_DISPOSABLE=1 PLAYWRIGHT_KEEP_FIXTURES=1 \
  npx playwright test --project=auth-setup-disposable --project=backoffice-disposable

# 6. Cleanup quando acabares
cd frontend && pkill -f "next dev -p 3001"
cd backend && bash scripts/start_test_backend.sh stop
cd backend && bash scripts/test_db.sh down
```

> A flag `-v` no `docker compose down` apaga o tmpfs do MongoDB. Da próxima vez que correres `test_db.sh up` voltas a ter uma DB vazia.

---

## 5. Ver o relatório no browser

O Playwright tem um reporter HTML interactivo (timeline, traces, screenshots, videos, error context).

### Configuração do reporter

Editar `frontend/playwright.config.ts` para garantir que o reporter HTML é gerado:

```ts
reporter: [
  ["list"],
  ["json", { outputFile: "test-results/e2e-results.json" }],
  ["html", { open: "never", outputFolder: "playwright-report" }],
],
```

### Comandos

```bash
cd frontend

# Após correr os testes:
npx playwright show-report

# Abrir relatório de um folder específico:
npx playwright show-report path/to/playwright-report

# Forçar HTML reporter numa corrida ad-hoc (sem alterar a config):
npx playwright test --project=frontend-public --reporter=html
npx playwright show-report
```

O comando abre o browser default em `http://localhost:9323` com:
- **Tabs** filtráveis (passed / failed / flaky / skipped)
- **Trace viewer** (timeline + DOM snapshot por step) — clica em "View trace" no teste falhado
- **Screenshots** automáticos em failures (`screenshot: "only-on-failure"`)
- **Network log** com requests/responses
- **Console output** capturado durante o teste

### Modos alternativos

```bash
# JSON (consumido por CI):
cat test-results/e2e-results.json | jq '.stats'

# Trace de um teste específico:
npx playwright show-trace test-results/<spec>/trace.zip
```

---

## 6. Variáveis de ambiente

Todas opcionais. Default = comportamento normal.

| Variável | Efeito |
|---|---|
| `PLAYWRIGHT_USE_DISPOSABLE=1` | Força arranque da stack disposable mesmo sem filtro de project |
| `PLAYWRIGHT_SKIP_WARMUP=1` | Pula pre-compilation Next.js (mais rápido em dev local quente) |
| `PLAYWRIGHT_SKIP_SEED=1` | Não cria nem apaga fixtures na dev DB |
| `PLAYWRIGHT_KEEP_FIXTURES=1` | Deixa a stack disposable a correr no fim (debug) |
| `TEST_ADMIN_EMAIL` / `TEST_ADMIN_PASSWORD` | Credenciais admin (defaults `e2e-admin@dados.gov.pt` / `E2eAdmin2026!`) |
| `TEST_EDITOR_EMAIL` / `TEST_EDITOR_PASSWORD` | Credenciais editor (defaults `e2e-editor@dados.gov.pt` / `E2eEditor2026!`) |
| `TEST_BACKEND_URL` | URL alternativa para o backend de teste (default `http://127.0.0.1:7001`) |
| `BACKEND_URL` | Lido pelo `next.config.ts` ao arrancar o frontend (default `http://127.0.0.1:7000`) |
| `NEXT_DIST_DIR` | Pasta de build do Next.js — usar `.next-test` em paralelo com o `.next` da dev |

### Combinações úteis

```bash
# Run rápido: pre-warm já feito, sem mexer na DB
PLAYWRIGHT_SKIP_WARMUP=1 PLAYWRIGHT_SKIP_SEED=1 npx playwright test --project=frontend-public

# Debug disposable: stack fica de pé no fim
PLAYWRIGHT_KEEP_FIXTURES=1 npx playwright test --project=backoffice-disposable
```

---

## 7. Modo UI / debug interactivo

```bash
cd frontend

# Modo UI: timeline, watch mode, locator picker, re-correr só o que mudou
npx playwright test --ui

# Modo UI restrito a um project:
npx playwright test --ui --project=frontend-public
npx playwright test --ui --project=auth-setup --project=backoffice

# Modo headed (browser visível), sem o UI controller:
npx playwright test --headed --project=frontend-public

# Debug interactivo de um teste específico, com inspector
npx playwright test tests/e2e/frontend-public/01-homepage.spec.ts -g "HP-01" --debug
```

Para o disposable em modo UI, arranca a stack manualmente (`scripts/test_db.sh up` + `start_test_backend.sh --bg` + `npm run dev -- -p 3001`) e depois corre `npx playwright test --ui --project=auth-setup-disposable --project=backoffice-disposable` com `PLAYWRIGHT_KEEP_FIXTURES=1`.

---

## 8. Troubleshooting

### "address already in use" no docker compose

Mesmo depois de `down -v`, o Docker proxy pode reter a porta:

```bash
docker network prune -f
docker rm -f udata-mongodb-test udata-redis-test
bash scripts/test_db.sh up
```

Se persistir, mudar a porta em `docker-compose.test.yml` (já usámos 27018→27019 por causa disto).

### "Unable to acquire lock at .next/dev/lock"

Tentaste arrancar 2× o frontend na mesma pasta. Solução: define `NEXT_DIST_DIR=.next-test` na 2ª instance:

```bash
NEXT_DIST_DIR=.next-test npm run dev -- -p 3001
```

### Login falha com "E-mail ou senha/código inválido"

O password hash não corresponde. O `init_test_db.py` usa `flask_security.utils.hash_password` (bcrypt). Se criaste o user com outro hash, apaga e recria:

```bash
cd backend
UDATA_SETTINGS=$(pwd)/udata.test.cfg uv run python -c "
from udata.app import create_app
from udata.core.user.models import User
app = create_app()
with app.app_context():
    User.objects(email='e2e-admin@dados.gov.pt').delete()
"
UDATA_SETTINGS=$(pwd)/udata.test.cfg uv run python scripts/init_test_db.py
```

### Specs falham com "element(s) not found" mas o DOM tem o elemento

Geralmente é Suspense / hidratação tardia em Next.js dev. Aumenta o `waitForTimeout`, troca `getByRole("heading")` por `page.locator("h3", { hasText: ... })` (que apanha headings escondidos em accordions), ou substitui `networkidle` por `waitForURL(/regex/)` para navegações client-side.

### Tests destrutivos partem fixtures (DS-D2 etc.)

Por design — o seed re-cria tudo na próxima `init_test_db.py`. Se um teste falhar a meio e deixar lixo, basta:

```bash
bash scripts/test_db.sh reset    # = down -v + up
uv run python scripts/init_test_db.py
```

---

## Referências

- `frontend/playwright.config.ts` — configuração dos projects
- `frontend/tests/global-setup.ts` — orquestração de boot
- `frontend/tests/global-teardown.ts` — cleanup
- `backend/docker-compose.test.yml` — stack Docker isolada
- `backend/udata.test.cfg` — config do backend de teste
- `backend/scripts/test_db.sh` — wrapper para Docker compose
- `backend/scripts/start_test_backend.sh` — boot do backend de teste
- `backend/scripts/init_test_db.py` — seeding determinístico
