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
- **Frontend consome**: via `frontend/src/service/api/<domain>/index.ts` (fetch functions por domínio); helpers partilhados (`authFetch`, base URLs por ambiente) em `src/service/utils/API.ts`
- **Tipos TS**: `frontend/src/service/types/<domain>/` (barrel `index.ts` por domínio) — devem espelhar os modelos do backend
- **Paginação**: `{ data: T[], page, page_size, total, next_page, previous_page }`

### Ao criar uma feature nova:

1. **Definir o contrato** — que endpoints são necessários e que dados trafegam
2. **Backend**: criar/alterar modelo (`models.py`), API endpoint (`api.py`), formulário (`forms.py`), permissões (`permissions.py`)
3. **Frontend**: criar tipo TS (`src/service/types/<domain>/`), função de fetch (`src/service/api/<domain>/index.ts`), componente(s), página
4. **Garantir consistência** — nomes de campos no JSON da API devem ser iguais nos tipos TS

### Mapeamento de entidades (Backend → Frontend)

| Backend (udata/core/)     | API endpoint            | Frontend type  | Frontend page (rota)      |
| ------------------------- | ----------------------- | -------------- | ------------------------- |
| `dataset/models.py`       | `/api/1/datasets/`      | `Dataset`      | `(pages)/datasets/`       |
| `organization/models.py`  | `/api/1/organizations/` | `Organization` | `(pages)/organizations/`  |
| `reuse/models.py`         | `/api/1/reuses/`        | `Reuse`        | `(pages)/reuses/`         |
| `dataservices/models.py`  | `/api/1/dataservices/`  | —              | `(admin)/admin/`          |
| `discussions/models.py`   | `/api/1/discussions/`   | —              | —                         |
| `topic/models.py`         | `/api/2/topics/`        | —              | `(pages)/themes/`         |
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
├── app/[locale]/(pages)/<feature>/   # route group — sem segmento /pages na URL
│   └── page.tsx             # Rota (server ou client component)
├── components/<feature>/
│   ├── <Feature>Client.tsx  # Componente principal com estado ('use client')
│   ├── <Feature>Filters.tsx # Filtros (se aplicável)
│   └── <Feature>Card.tsx    # Card de listagem
├── service/api/<domain>/index.ts    # Adicionar fetch function
└── service/types/<domain>/index.ts  # Adicionar interface TS
```

## Comandos Rápidos

| Ação                  | Backend                                                           | Frontend                                  |
| --------------------- | ----------------------------------------------------------------- | ----------------------------------------- |
| Instalar dependências | `cd backend && uv sync --extra dev --extra test`                  | `cd frontend && npm install`              |
| Servidor dev          | `cd backend && inv serve` (porta 7000)                            | `cd frontend && npm run dev` (porta 3000) |
| Testes                | `cd backend && uv run pytest`                                     | `cd frontend && npm run lint`             |
| Lint/Format           | `cd backend && uv run ruff check --fix . && uv run ruff format .` | `cd frontend && npm run lint`             |
| Worker Celery         | `cd backend && inv work`                                          | —                                         |
| Migrações BD          | `cd backend && udata db upgrade`                                  | —                                         |
| Build produção        | —                                                                 | `cd frontend && npm run build`            |

## Performance

When building or optimizing pages, apply these cross-cutting practices (especially for public-facing, high-traffic pages):

- **Aggregated endpoints** — When a page needs data from multiple sources, create a single backend endpoint that returns everything the page needs in one response (e.g., `/api/1/site/home/`). Avoid forcing the frontend to call multiple endpoints and assemble data.
- **Lightweight serialization** — Aggregated endpoints should use manual dict serialization including only the fields the frontend actually needs, reducing payload size significantly.
- **Server-side rendering** — Use Next.js async Server Components to fetch data at request time instead of client-side `useEffect`. Move interactive logic to a child `*Client.tsx` component that receives data as props.
- **ISR caching (frontend)** — Use `next: { revalidate: N }` on `fetch()` calls instead of `cache: "no-store"` for data that doesn't need to be real-time (homepage: 60s, posts: 120s, site metadata: 300s).
- **Server-side caching (backend)** — Use `@cache.cached(timeout=N, key_prefix="...")` from Flask-Caching on aggregated endpoints.
- **Query limiting** — Always limit querysets with `[:N]` slicing on the backend when only a fixed number of results is needed.

## Repositórios Git & Fluxo de Promoção

O monorepo agrega **dois repositórios git independentes** (submódulos), cada um com o seu próprio fluxo:

| Submódulo   | Repositório GitHub                  |
| ----------- | ----------------------------------- |
| `backend/`  | `github.com/amagovpt/udata-pt`      |
| `frontend/` | `github.com/amagovpt/dadosgov-fe`   |

Cada repo tem branches de ambiente de longa duração — `develop`, `tst`, `ppr`, `main` — e promove alterações por PRs, um ambiente de cada vez:

1. Criar branch **a partir de `develop`** (nomenclatura Conventional Branch: `feature/...`, `fix/...`).
2. Quando pronto, abrir PR de volta **para `develop`**; integrar e testar aí.
3. Depois PR **para `tst`**; testar em tst.
4. Depois PR **para `ppr`**; testar em ppr.
5. Depois PR **para `main`** (produção).

- A base de cada PR é sempre o **ambiente seguinte**, não sempre `main`.
- **Fazer o fluxo só no(s) repo(s) efetivamente alterado(s)** — uma alteração só de backend passa por este fluxo apenas em `udata-pt`; o frontend fica intocado, e vice-versa.
- **Abrir PRs** — verificar primeiro com `gh auth status`. Se o GitHub CLI estiver autenticado: `gh pr create --repo amagovpt/<repo> --base <ambiente> --head <branch>`, e acompanhar o CI com `gh pr checks` / `gh run watch`. Caso contrário, abrir pelo URL de comparação `https://github.com/amagovpt/<repo>/compare/<base>...<head>?expand=1`. Não assumir nenhum dos casos: o `gh` está instalado em algumas máquinas da equipa e não noutras.
- A mesma regra condicional está a ser aplicada aos `CLAUDE.md` dos submódulos: PRs [udata-pt#222](https://github.com/amagovpt/udata-pt/pull/222) e [dadosgov-fe#580](https://github.com/amagovpt/dadosgov-fe/pull/580), ambos para `develop`. Até serem integrados, esses ficheiros continuam a afirmar que o `gh` não existe.

## Versionamento & Releases

Cada submódulo é versionado por **tags**, uma por promoção para `main`, e cada tag tem a sua release no GitHub com as notas tiradas da secção correspondente do `CHANGELOG.md`. Os esquemas são diferentes de propósito:

| Repo | Esquema | Exemplo | Porquê |
| --- | --- | --- | --- |
| `backend/` (`udata-pt`) | `vX.Y.Z.N` | `v16.0.0.12` | É um fork de [udata](https://github.com/opendatateam/udata). `X.Y.Z` é a versão upstream em que assenta; `N` é a revisão portuguesa, reiniciada a cada sync. O upstream só publica três segmentos, por isso um quarto nunca colide. |
| `frontend/` (`dadosgov-fe`) | `vX.Y.Z` | `v1.4.15` | É inteiramente nosso, não tem upstream. SemVer simples: `feat!` → MAJOR, `feat` → MINOR, o resto → PATCH. |

- **Não procurar correspondência entre os números dos dois repos** — são independentes. A única relação honesta entre uma versão de backend e uma de frontend é a **data** da tag.
- A versão upstream do backend confirma-se por ancestralidade, nunca a ler o `pyproject.toml`: `git merge-base --is-ancestor refs/tags/upstream/vX.Y.Z origin/main`. O remote `upstream` deve ter `tagOpt = --no-tags`, para que um fetch não importe as tags dos franceses para o namespace principal.
- Ferramentas que listem versões devem ler **tags de git**, não releases do GitHub: funcionam offline, sem token e sem API. As releases são a camada de texto. O `run_servers.py` faz isso na opção **4 — arrancar numa versão específica**, que lista as tags publicadas de cada submódulo com a data do *commit* (não a da criação da tag: no frontend as duas primeiras foram criadas no mesmo dia para commits com semanas de diferença), marca a versão do outro repositório mais próxima no tempo, e avisa antes de correr um backend anterior ao mais recente, porque as migrações de MongoDB não revertem.
- **Depois de cada deploy**, confirmar que o ambiente serve mesmo a versão que foi publicada: `./scripts/check_deployed_version.sh https://dados.gov.pt [versão]`. O número que a API devolve vem da metadata do pacote **instalado**, não do `pyproject.toml` — código publicado sem o pacote ser reinstalado continua a responder com a versão anterior, e o rodapé do portal repete-a a quem lá entra. Foi assim que o rodapé anunciou uma versão errada durante meses.
- Detalhe por repo em `backend/CLAUDE.md` e `frontend/CLAUDE.md`, secção **Versioning & Releases**.

## Ambiente de cada máquina

O `run_servers.py` é o mesmo em todas as máquinas — local, tst, ppr e produção — e precisa de saber qual é a desta. Essa informação vive num ficheiro **por máquina**, fora do git:

```bash
cp .dadosgov-env.example .dadosgov-env   # e escrever lá: develop, tst, ppr ou main
```

As opções 1 e 2 publicam **a branch desse ambiente**: se um submódulo estiver noutra branch, param e oferecem a mudança; em *detached HEAD*, param, porque sem branch não há o que publicar. Publicar na mesma é possível — escrevendo `forçar` por extenso e confirmando a seguir — porque numa máquina de desenvolvimento é legítimo querer correr a própria branch. Num servidor não é, e aí o correcto é apagar ou corrigir o `.dadosgov-env`, não forçar a cada arranque; é por isso que esta saída se escreve e as outras duas são uma tecla. Antes de construir, mostram sempre o que vai subir — ambiente, branch, commit, data e assunto — e pedem confirmação.

O ambiente é uma propriedade da máquina, não uma escolha de quem corre o script: um servidor de tst é de tst em todos os arranques, e perguntá-lo a cada corrida transformaria uma constante numa decisão. Para correr uma versão arbitrária existe a opção 4.

**Sem o ficheiro** — o caso normal numa máquina de desenvolvimento — usa-se a branch em checkout, mostrada e confirmada. Não se assume `develop`: em local trabalha-se em branches de feature, e assumir uma branch de ambiente ou impedia o arranque ou tirava a pessoa de cima do seu trabalho.

## Regras Gerais

- **Antes de corrigir um bug, procurar precedentes**: `git log --all --grep=<keyword>`, `git log --all -- <file>`, `grep -r` por padrões/símbolos relacionados (e.g. `Isolated*`, `Safe*` wrappers), e leitura de PRs/commits anteriores. Se já existe fix funcional, replicar o padrão. Se for possível melhorar, sugerir explicitamente antes de divergir.
- **Idioma do código**: inglês (variáveis, funções, comentários, commits)
- **Commits**: mensagens descritivas em inglês, referenciar issues com `(fix #XXX)`. **Nunca incluir `Co-Authored-By` ou qualquer atribuição de IA nos commits.**
- **Branches e commits** seguem [Conventional Branch](https://conventionalbranch.org/) / [Conventional Commits](https://www.conventionalcommits.org/) em **qualquer** dos repos (incluindo o do monorepo) — ver `backend/CLAUDE.md` ou `frontend/CLAUDE.md` para a tabela completa de prefixos e tipos.
- **Tickets Jira**: projeto **`LEDG`** ("L11 - Evol&Man.dados.gov") no site `ticapp.atlassian.net`, cloudId `0d1d9259-29f0-46ff-bb50-522a373f8daf`, acedido pelo MCP Atlassian. Ao criar um ticket, **assiná-lo no utilizador logado ao Jira** — `reporter` *e* `assignee` com o accountId vindo de `atlassianUserInfo` + `lookupJiraAccountId`, nunca a identidade por omissão da ligação MCP — e inseri-lo **sempre no sprint aberto** (não perguntar): id lido na altura da criação com `sprint in openSprints()`, campo `customfield_10020` (board `352`). Indicar o key criado e o sprint em que ficou. Para trabalhar um ticket de ponta a ponta usar `/ticket LEDG-XXXX` (skill `jira-ticket-workflow`).
- **Ao alterar a API**: atualizar sempre tanto o backend (endpoint + serialização) como o frontend (tipo TS + fetch function)
- **Novos endpoints**: registar em `backend/udata/api/__init__.py` → `init_app()`
- **Novos tipos TS**: adicionar em `frontend/src/service/types/<domain>/`
- **Novas fetch functions**: adicionar em `frontend/src/service/api/<domain>/index.ts`
- **Testes**: backend obriga pytest; frontend usa ESLint para validação estática
