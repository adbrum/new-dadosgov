# dados.gov.pt - Portal de Dados Abertos

Monorepo com backend (Python/Flask) e frontend (Next.js). Ambos são trabalhados em conjunto — ao criar/alterar uma feature no frontend, garantir que o backend suporta a API necessária, e vice-versa.

## Arquitetura Geral

```
dadosgov/
├── backend/          # API REST (udata - Flask + MongoDB)
│   ├── udata/        # Código principal
│   └── CLAUDE.md     # Regras específicas do backend
├── frontend/         # Interface web (Next.js + React)
│   ├── src/          # Código principal
│   └── CLAUDE.md     # Regras específicas do frontend
```

## Fluxo Frontend ↔ Backend

### Contrato API

- **Base URL**: `/api/1` (v1) e `/api/2` (v2) — definido em `backend/udata/api/__init__.py`
- **Frontend consome**: via `frontend/src/services/api.ts` (fetch functions)
- **Tipos TS**: `frontend/src/types/api.ts` — devem espelhar os modelos do backend
- **Paginação**: `{ data: T[], page, page_size, total, next_page, previous_page }`

### Ao criar uma feature nova:

1. **Definir o contrato** — que endpoints são necessários e que dados trafegam
2. **Backend**: criar/alterar modelo (`models.py`), API endpoint (`api.py`), formulário (`forms.py`), permissões (`permissions.py`)
3. **Frontend**: criar tipo TS (`types/api.ts`), função de fetch (`services/api.ts`), componente(s), página
4. **Garantir consistência** — nomes de campos no JSON da API devem ser iguais nos tipos TS

### Mapeamento de entidades (Backend → Frontend)

| Backend (udata/core/)     | API endpoint            | Frontend type  | Frontend page          |
| ------------------------- | ----------------------- | -------------- | ---------------------- |
| `dataset/models.py`       | `/api/1/datasets/`      | `Dataset`      | `pages/datasets/`      |
| `organization/models.py`  | `/api/1/organizations/` | `Organization` | `pages/organizations/` |
| `reuse/models.py`         | `/api/1/reuses/`        | `Reuse`        | `pages/reuses/`        |
| `dataservices/models.py`  | `/api/1/dataservices/`  | —              | `pages/admin/`         |
| `discussions/models.py`   | `/api/1/discussions/`   | —              | —                      |
| `topic/models.py`         | `/api/2/topics/`        | —              | `pages/themes/`        |
| `post/models.py`          | `/api/1/posts/`         | —              | —                      |
| `user/models.py`          | `/api/1/users/`         | —              | —                      |
| `contact_point/models.py` | `/api/1/contacts/`      | —              | —                      |
| `spatial/models.py`       | `/api/1/spatial/`       | —              | —                      |

> Células com `—` indicam que o tipo/página ainda não foi implementado no frontend.

### Padrão de cada módulo backend

```
udata/core/<module>/
├── models.py        # MongoEngine documents
├── api.py           # Flask-RestX endpoints (v1)
├── apiv2.py         # Endpoints v2 (quando existem)
├── api_fields.py    # Serialização dos campos da API
├── forms.py         # Validação de input (WTForms)
├── permissions.py   # Controlo de acesso
├── factories.py     # Fixtures para testes
├── tasks.py         # Tarefas Celery assíncronas
├── signals.py       # Eventos/hooks
├── search.py        # Integração Elasticsearch
└── tests/           # Testes do módulo
```

### Padrão de cada feature frontend

```
src/
├── app/pages/<feature>/
│   └── page.tsx             # Rota (server ou client component)
├── components/<feature>/
│   ├── <Feature>Client.tsx  # Componente principal com estado ('use client')
│   ├── <Feature>Filters.tsx # Filtros (se aplicável)
│   └── <Feature>Card.tsx    # Card de listagem
├── services/api.ts          # Adicionar fetch function
└── types/api.ts             # Adicionar interface TS
```

## Comandos Rápidos

| Ação                  | Backend                                                           | Frontend                                  |
| --------------------- | ----------------------------------------------------------------- | ----------------------------------------- |
| Instalar dependências | `cd backend && uv sync --extra dev --extra test`                  | `cd frontend && npm install`              |
| Servidor dev          | `cd backend && inv serve` (porta 7000)                            | `cd frontend && npm run dev` (porta 3000) |
| Testes                | `cd backend && uv run pytest`                                     | `cd frontend && npm run lint`             |
| Lint/Format           | `cd backend && uv run ruff check --fix . && uv run ruff format .` | `cd frontend && npm run lint`             |
| Worker Celery         | `cd backend && inv work`                                          | —                                         |
| Migrações BD          | `cd backend && udata db migrate`                                  | —                                         |
| Build produção        | —                                                                 | `cd frontend && npm run build`            |

## Performance

When building or optimizing pages, apply these cross-cutting practices (especially for public-facing, high-traffic pages):

- **Aggregated endpoints** — When a page needs data from multiple sources, create a single backend endpoint that returns everything the page needs in one response (e.g., `/api/1/site/home/`). Avoid forcing the frontend to call multiple endpoints and assemble data.
- **Lightweight serialization** — Aggregated endpoints should use manual dict serialization including only the fields the frontend actually needs, reducing payload size significantly.
- **Server-side rendering** — Use Next.js async Server Components to fetch data at request time instead of client-side `useEffect`. Move interactive logic to a child `*Client.tsx` component that receives data as props.
- **ISR caching (frontend)** — Use `next: { revalidate: N }` on `fetch()` calls instead of `cache: "no-store"` for data that doesn't need to be real-time (homepage: 60s, posts: 120s, site metadata: 300s).
- **Server-side caching (backend)** — Use `@cache.cached(timeout=N, key_prefix="...")` from Flask-Caching on aggregated endpoints.
- **Query limiting** — Always limit querysets with `[:N]` slicing on the backend when only a fixed number of results is needed.

## Regras Gerais

- **Antes de corrigir um bug, procurar precedentes**: `git log --all --grep=<keyword>`, `git log --all -- <file>`, `grep -r` por padrões/símbolos relacionados (e.g. `Isolated*`, `Safe*` wrappers), e leitura de PRs/commits anteriores. Se já existe fix funcional, replicar o padrão. Se for possível melhorar, sugerir explicitamente antes de divergir.
- **Idioma do código**: inglês (variáveis, funções, comentários, commits)
- **Commits**: seguir [Conventional Commits 1.0.0](#convenções-de-branches-e-commits), mensagens em inglês, referenciar issues com `(fix #XXX)`. **Nunca incluir `Co-Authored-By` ou qualquer atribuição de IA nos commits.**
- **Branches**: seguir [Conventional Branch](#convenções-de-branches-e-commits) (`<type>/<descrição-em-kebab-case>`).
- **Ao alterar a API**: atualizar sempre tanto o backend (endpoint + serialização) como o frontend (tipo TS + fetch function)
- **Novos endpoints**: registar em `backend/udata/api/__init__.py` → `init_app()`
- **Novos tipos TS**: adicionar em `frontend/src/types/api.ts`
- **Novas fetch functions**: adicionar em `frontend/src/services/api.ts`
- **Testes**: backend obriga pytest; frontend usa ESLint para validação estática

## Convenções de Branches e Commits

Todos os contribuidores deste projeto **devem** seguir estas convenções. Padrões de referência:
[Conventional Branch](https://conventionalbranch.org/) e [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

### Branches — Conventional Branch

Formato: `<type>/<descrição>`

- **Descrição** em `kebab-case`, apenas minúsculas, alfanuméricos e hífens (sem espaços, `_`, maiúsculas ou caracteres especiais).
- Opcionalmente incluir o número da issue/ticket: `feature/issue-123-public-search-ratelimit`.

| Prefixo      | Uso                                                        |
| ------------ | ---------------------------------------------------------- |
| `main`       | Branch principal de produção (não usar prefixo).           |
| `feature/`   | Nova funcionalidade.                                       |
| `bugfix/`    | Correção de bug.                                           |
| `hotfix/`    | Correção urgente (normalmente sobre produção).             |
| `release/`   | Preparação de uma release.                                 |
| `chore/`     | Tarefas sem impacto em código de produção (deps, config).  |

Exemplos: `feature/aggregated-home-endpoint`, `bugfix/csrf-session-overwrite`, `chore/bump-backend-submodule`, `hotfix/download-ratelimit`.

### Commits — Conventional Commits 1.0.0

Formato:

```
<type>[scope opcional][!]: <descrição>

[corpo opcional]

[rodapé(s) opcional(is)]
```

- **type** (obrigatório): `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- **scope** (opcional): área afetada, e.g. `feat(dataset):`, `fix(api):`, `chore(frontend):`.
- **descrição**: imperativo, minúsculas, em inglês, sem ponto final.
- **`feat`** → bump _MINOR_; **`fix`** → bump _PATCH_.
- **Breaking changes**: `!` após o type/scope (e.g. `feat(api)!:`) e/ou rodapé `BREAKING CHANGE: <descrição>`.
- Referenciar issues no rodapé ou na descrição: `(fix #XXX)`.

Exemplos:

```
feat(search): add user_or_ip rate-limit to public GET endpoints
fix(auth): mint CSRF server-side on authenticated POSTs (fix #42)
chore: bump backend submodule for public download rate-limit fix
refactor(home): move data fetch to async Server Component
```
