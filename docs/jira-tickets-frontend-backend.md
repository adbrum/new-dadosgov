# Tickets - Frontend ↔ Backend Integration

> Generated: 2026-03-09
> Project: dados.gov.pt - Portal de Dados Abertos
> Scope: **Lógica de conexão** entre frontend (Next.js) e backend (udata/Flask) — tipos TypeScript, funções em `services/api.ts`, endpoints, payloads, e fluxo de dados. O layout/UI não faz parte destes tickets.

---

# PÁGINAS PÚBLICAS — Tickets

---

## TICKET-01: Authentication — Login (Conexão API) ✅

**Descrição**
Implementar a lógica de conexão do login: fluxo CSRF → POST login → session cookie, usando o route handler existente.

**Contexto Arquitetural**

- Backend usa Flask-Security com auth por sessão. Endpoint: `POST /login/` (HTML form, não JSON).
- Frontend já tem route handler em `src/app/login/route.ts` que faz proxy ao backend, traduz HTML→JSON, e reencaminha `Set-Cookie`.
- Next.js rewrites em `next.config.ts` fazem proxy de `/get-csrf` e `/logout/` para o backend.
- `LoginClient.tsx` tem UI mas não submete ao backend.
- Fluxo documentado em `docs/login-workflow.md`.

**O que deve ser feito**

1. **Funções em `services/api.ts`**:
   - `fetchCsrfToken()` → `GET /get-csrf` (extrair token do cookie `csrf_token`).
   - `login(email, password, csrfToken)` → `POST /login` (route handler do frontend, body: `email`, `password`, `csrf_token` como form-data).
   - `logout()` → `GET /logout/` (proxied pelo rewrite).
2. **Fluxo de dados**:
   - Chamar `fetchCsrfToken()` → obter token do cookie.
   - Chamar `login()` com form data → route handler faz proxy ao backend → backend retorna 302 (sucesso) ou 400 (erro) → route handler traduz para JSON `{ status, redirect?, error? }`.
   - Em sucesso: backend envia `Set-Cookie` com session → route handler reencaminha o header.
   - Em erro: retorna mensagem de erro do HTML (`help-block`).
   - `logout()`: backend limpa a sessão e retorna redirect.

**Critérios de Aceitação**

- [x] `fetchCsrfToken()` obtém o token do cookie.
- [x] `login()` envia os campos corretos e retorna resposta JSON.
- [x] Em sucesso, session cookie é definido pelo backend.
- [x] Em erro, a mensagem é retornada em formato utilizável.
- [x] `logout()` limpa a sessão.

---

## TICKET-02: Authentication — Registration (Conexão API) ✅✅

**Descrição**
Implementar a lógica de conexão do registo: route handler proxy e função de submit.

**Contexto Arquitetural**

- Backend: `POST /register` com campos `email`, `password`, `password_confirm`, `first_name`, `last_name`, `csrf_token`.
- `SECURITY_REGISTERABLE = True` está ativo.
- Confirmação de email pode ser necessária (`NEXT_PUBLIC_REQUIRE_EMAIL_CONFIRMATION`).
- `RegisterClient.tsx` tem form UI mas `handleSubmit` só faz `preventDefault()`.

**O que deve ser feito**

1. **Route handler** `src/app/register/route.ts`:
   - Proxy de `POST /register` ao backend (mesmo padrão do login route handler).
   - Traduzir resposta HTML para JSON `{ status, error?, redirect? }`.
   - Reencaminhar `Set-Cookie` headers.
2. **Funções em `services/api.ts`**:
   - `register(payload)` → `POST /register` (route handler do frontend).
   - Payload: `{ email, password, password_confirm, first_name, last_name, csrf_token }`.
3. **Fluxo de dados**:
   - Obter CSRF token (reutilizar `fetchCsrfToken()` do TICKET-01).
   - POST com form data → route handler traduz resposta.
   - Em sucesso: redirect para login ou página de confirmação.
   - Em erro: retorna erros de validação do backend.

**Critérios de Aceitação**

- [x] Route handler proxy funciona (mesmo padrão do login).
- [x] `register()` envia payload correto.
- [x] Erros de validação do backend são retornados em JSON.
- [x] CSRF token é incluído no pedido.
- [x] Resposta indica se confirmação de email é necessária.

---

## TICKET-03: Authentication — Current User State (Conexão API) ✅✅

**Descrição**
Implementar o tipo `User`, a função `fetchCurrentUser()`, e o contexto de autenticação que consome `GET /api/1/me/`.

**Contexto Arquitetural**

- Backend: `GET /api/1/me/` retorna o perfil do utilizador autenticado (ou 401).
- Proxy `/api/*` → backend já configurado em `next.config.ts`.
- Frontend não tem tipo User, nem função fetch, nem contexto de auth.

**O que deve ser feito**

1. **Tipo TS** em `types/api.ts`:
   - `User`: id, slug, email, first_name, last_name, avatar, avatar_thumbnail, roles[], organizations[] (ref), about, website, created_at, last_login, metrics, active.
2. **Funções em `services/api.ts`**:
   - `fetchCurrentUser()` → `GET /api/1/me/` (retorna `User | null`, trata 401 como null).
3. **Contexto** em `src/contexts/AuthContext.tsx`:
   - Chamar `fetchCurrentUser()` no mount.
   - Expor: `user: User | null`, `isAuthenticated: boolean`, `isLoading: boolean`, `refresh()`.
4. **Fluxo de dados**:
   - Na montagem do layout, `GET /api/1/me/` → se 200, user autenticado; se 401, user null.
   - O contexto é consumido pelo Header e por qualquer componente que precise saber se o utilizador está autenticado.

**Critérios de Aceitação**

- [ ] Tipo `User` definido em `types/api.ts` espelhando o backend.
- [ ] `fetchCurrentUser()` retorna user ou null (sem erro em 401).
- [ ] `AuthContext` disponível em toda a aplicação.
- [ ] `refresh()` permite re-fetch após login/logout.

---

## TICKET-04: Homepage — Dados Dinâmicos (Conexões API) ✅✅

**Descrição**
Implementar as funções de fetch e tipos necessários para a homepage consumir dados reais do backend, substituindo todo o conteúdo hardcoded (stats, datasets em destaque, storytelling/reuses, notícias) e ativando a pesquisa global do hero.

**Contexto Arquitetural**

- Homepage (`src/app/page.tsx`) tem tudo hardcoded: stats, datasets em destaque, storytelling (reuses), notícias.
- A barra de pesquisa global no hero (`InputSearchBar`) existe na UI mas não está ligada a nenhum endpoint.
- A secção "Utilizado diariamente por" usa logos estáticos — não requer API.
- Backend endpoints necessários:
  - `GET /api/1/site/` → stats do site (nb_datasets, nb_organizations, nb_reuses, nb_users).
  - `GET /api/1/datasets/?featured=true&page_size=3` → datasets em destaque.
  - `GET /api/1/reuses/?featured=true&page_size=3` → reuses em destaque (secção Storytelling).
  - `GET /api/1/posts/?page_size=3` → últimas notícias.
  - `GET /api/1/datasets/suggest/?q=<query>&size=<n>` → autocomplete para pesquisa global.
  - `GET /api/1/datasets/?q=<query>` → pesquisa full-text (resultado da pesquisa global).

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - `SiteInfo`: id, title, metrics `{ nb_datasets, nb_organizations, nb_reuses, nb_users }`.
   - `Post`: id, name, slug, headline, content, body_type, image, image_thumbnail, created_at, last_modified, tags[].
   - `GlobalSearchSuggestion`: title, slug, score (para autocomplete da pesquisa global).
2. **Funções em `services/api.ts`**:
   - `fetchSiteInfo()` → `GET /api/1/site/`
   - `fetchFeaturedDatasets(pageSize?)` → `GET /api/1/datasets/?featured=true&page_size=<n>`
   - `fetchFeaturedReuses(pageSize?)` → `GET /api/1/reuses/?featured=true&page_size=<n>`
   - `fetchPosts(page?, pageSize?)` → `GET /api/1/posts/?page=<n>&page_size=<n>`
   - `suggestGlobalSearch(query, size?)` → `GET /api/1/datasets/suggest/?q=<query>&size=<n>` (autocomplete para a barra de pesquisa do hero)
3. **Fluxo de dados**:
   - Homepage (`'use client'`) chama as funções de dados em `useEffect` (paralelo via `Promise.all`).
   - Stats section (Comunidade): usa `SiteInfo.metrics` para popular os 4 contadores (Conjuntos de Dados, Reutilizações, Organizações, Utilizadores).
   - Datasets em destaque: usa `fetchFeaturedDatasets(3)` para os 3 cards.
   - Storytelling (Reuses): usa `fetchFeaturedReuses(3)` para os 3 cards.
   - Últimas novidades: usa `fetchPosts(1, 3)` para os 3 cards de notícias.
   - Pesquisa global (hero): `InputSearchBar` chama `suggestGlobalSearch()` no `onChange` (debounced) para mostrar sugestões; no submit, redireciona para `/pages/datasets?q=<query>`.

**Critérios de Aceitação**

- [x] Tipos `SiteInfo`, `Post` e `GlobalSearchSuggestion` definidos.
- [x] `fetchSiteInfo()` retorna métricas do site.
- [x] `fetchFeaturedDatasets()` retorna datasets com featured=true.
- [x] `fetchFeaturedReuses()` retorna reuses com featured=true.
- [x] `fetchPosts()` retorna posts paginados.
- [x] `suggestGlobalSearch()` retorna sugestões de autocomplete.
- [x] Pesquisa global redireciona para a página de datasets com o parâmetro `q`.
- [x] Todas as funções tratam erros graciosamente (retornam dados vazios, não crasham).

---

## TICKET-05: Datasets — Search (Conexão API) ✅✅

**Descrição**
Estender `fetchDatasets()` para suportar pesquisa full-text e implementar a função de suggest/autocomplete.

**Contexto Arquitetural**

- `fetchDatasets()` existente aceita `page`, `pageSize`, `organization`, mas não `q`.
- Backend: `GET /api/1/datasets/?q=<query>` (full-text search v1).
- Backend: `GET /api/2/datasets/search/?q=<query>` (search v2, Elasticsearch).
- Backend: `GET /api/1/datasets/suggest/?q=<query>&size=<n>` (autocomplete, retorna `[{title, slug, score}]`).

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - `DatasetSuggestion`: title, slug, score (ou id, title, slug, image_url conforme resposta).
2. **Atualizar `fetchDatasets()`** em `services/api.ts`:
   - Aceitar parâmetro `q?: string`.
   - Se `q` fornecido, passar como query param: `GET /api/1/datasets/?q=<query>&page=<n>&page_size=<n>`.
3. **Nova função** em `services/api.ts`:
   - `suggestDatasets(query, size?)` → `GET /api/1/datasets/suggest/?q=<query>&size=<n>`

**Critérios de Aceitação**

- [x] `fetchDatasets()` aceita `q` e passa ao backend.
- [x] Resultados de pesquisa são paginados corretamente.
- [x] `suggestDatasets()` retorna sugestões para autocomplete.
- [x] Pesquisa vazia retorna todos os datasets.

---

## TICKET-06: Datasets — Filtros Avançados (Conexões API) ✅✅

**Descrição**
Implementar as funções de fetch para opções de filtros e estender `fetchDatasets()` para aceitar todos os parâmetros de filtro do backend.

**Contexto Arquitetural**

- `DatasetsFilters.tsx` tem 8 grupos de filtros, mas só organização é dinâmica.
- Backend suporta filtros: `tag`, `license`, `format`, `schema`, `geozone`, `granularity`, `organization`, `badge`, `featured`, `temporal_coverage`.
- Backend fornece endpoints de metadados para popular os filtros.

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - `License`: id, title, url, maintainer, flags[].
   - `Frequency`: id, label.
   - `Badge`: kind.
   - `Tag`: name (ou string simples).
2. **Funções em `services/api.ts`**:
   - `fetchLicenses()` → `GET /api/1/datasets/licenses/`
   - `fetchFrequencies()` → `GET /api/1/datasets/frequencies/`
   - `fetchSchemas()` → `GET /api/1/datasets/schemas/`
   - `fetchDatasetBadges()` → `GET /api/1/datasets/badges/`
   - `suggestFormats(query)` → `GET /api/1/datasets/suggest/formats/?q=<query>`
   - `suggestTags(query)` → `GET /api/1/tags/suggest/?q=<query>&size=10`
3. **Atualizar `fetchDatasets()`** em `services/api.ts`:
   - Aceitar objeto de filtros: `{ q?, tag?, license?, format?, schema?, geozone?, granularity?, organization?, badge?, featured?, sort? }`.
   - Construir query string com todos os filtros fornecidos.

**Critérios de Aceitação**

- [x] Funções de fetch para licenças, frequências, schemas, badges retornam dados do backend.
- [x] `suggestFormats()` e `suggestTags()` retornam sugestões.
- [x] `fetchDatasets()` aceita todos os filtros e os passa como query params.
- [x] Múltiplos filtros podem ser combinados numa só chamada.

---

## TICKET-07: Discussions (Conexões API) ✅✅

**Descrição**
Implementar tipos e funções para o CRUD de discussions associadas a datasets.

**Contexto Arquitetural**

- `DatasetTabs.tsx` tem tab "Discussions" com placeholder.
- Backend endpoints:
  - `GET /api/1/discussions/?for=<dataset_id>` → listar discussions de um dataset.
  - `POST /api/1/discussions/` → criar discussion (body: title, comment, subject `{class: "Dataset", id: <id>}`). Auth required.
  - `GET /api/1/discussions/<id>/` → detalhes de uma discussion.
  - `POST /api/1/discussions/<id>/messages/` → responder (body: comment). Auth required.
  - `POST /api/1/discussions/<id>/close/` → fechar discussion (body: comment). Auth required.
  - `DELETE /api/1/discussions/<id>/` → eliminar discussion. Auth required.

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - `Discussion`: id, title, subject (class + id), user, created, closed, closed_by, discussion[].
   - `DiscussionMessage`: content, posted_by, posted_on.
   - `DiscussionCreatePayload`: title, comment, subject `{ class: string, id: string }`.
2. **Funções em `services/api.ts`**:
   - `fetchDiscussions(subjectId, subjectClass?, page?)` → `GET /api/1/discussions/?for=<id>`
   - `createDiscussion(payload)` → `POST /api/1/discussions/`
   - `replyToDiscussion(discussionId, comment)` → `POST /api/1/discussions/<id>/messages/`
   - `closeDiscussion(discussionId, comment)` → `POST /api/1/discussions/<id>/close/`
   - `deleteDiscussion(discussionId)` → `DELETE /api/1/discussions/<id>/`

**Critérios de Aceitação**

- [x] Tipos `Discussion` e `DiscussionMessage` definidos.
- [x] `fetchDiscussions()` retorna lista de discussions para um dataset.
- [x] `createDiscussion()` envia o payload correto (title + comment + subject).
- [x] `replyToDiscussion()` adiciona mensagem a uma discussion existente.
- [x] `closeDiscussion()` fecha a discussion.
- [x] Erros de autenticação (401) são tratados.

---

## TICKET-08: Followers (Conexões API) ✅✅

**Descrição**
Implementar as funções de follow/unfollow genéricas para datasets, organizations, e reuses.

**Contexto Arquitetural**

- `DatasetDetailClient.tsx` tem toggle de favorito mas usa `useState` local — perde-se ao recarregar.
- Backend segue o mesmo padrão para as 3 entidades:
  - `GET /api/1/<entity>/<id>/followers/` → lista seguidores.
  - `POST /api/1/<entity>/<id>/followers/` → seguir. Auth required.
  - `DELETE /api/1/<entity>/<id>/followers/` → deixar de seguir. Auth required.
- Entidades: `datasets`, `organizations`, `reuses`.

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - `FollowersResponse`: `{ data: User[], total: number }` (ou conforme resposta).
2. **Funções em `services/api.ts`** (genéricas ou por entidade):
   - `followEntity(entityType, id)` → `POST /api/1/<entityType>/<id>/followers/`
   - `unfollowEntity(entityType, id)` → `DELETE /api/1/<entityType>/<id>/followers/`
   - `fetchFollowers(entityType, id)` → `GET /api/1/<entityType>/<id>/followers/`
   - Onde `entityType` é `'datasets' | 'organizations' | 'reuses'`.
   - Alternativamente, funções específicas: `followDataset(id)`, `unfollowDataset(id)`, `followOrganization(id)`, etc.

**Critérios de Aceitação**

- [x] Funções follow/unfollow funcionam para datasets, organizations e reuses.
- [x] `fetchFollowers()` retorna lista de seguidores.
- [x] POST retorna 201 em sucesso, DELETE retorna 200.
- [x] Erros de autenticação (401) são tratados.

---

## TICKET-09: Organization Detail (Conexões API) ✅✅

**Descrição**
Implementar a função de fetch e tipos para a página de detalhe de organização (que não existe ainda).

**Contexto Arquitetural**

- Listagem de organizações existe e usa `fetchOrganizations()`.
- ~~Não existe `fetchOrganization(slug)` para detalhe individual.~~ Implementado.
- Backend endpoints:
  - `GET /api/1/organizations/<org>/` → detalhes completos.
  - `GET /api/1/organizations/<org>/datasets/?page=<n>` → datasets da organização.
  - `GET /api/1/organizations/<org>/reuses/?page=<n>` → reuses da organização.
  - `GET /api/1/organizations/<org>/discussions/?page=<n>` → discussions.

**O que deve ser feito**

1. **Estender tipo** `Organization` em `types/api.ts`:
   - Adicionar: `description`, `url`, `business_number_id`, `members[]` (user + role), `badges[]`, `metrics` (datasets, followers, members, reuses, views), `created_at`, `last_modified`, `page`.
   - Criar `OrganizationMember`: user (ref User), role.
2. **Funções em `services/api.ts`**:
   - `fetchOrganization(slugOrId)` → `GET /api/1/organizations/<org>/`
   - `fetchOrgDatasets(org, page?, pageSize?)` → `GET /api/1/organizations/<org>/datasets/`
   - `fetchOrgReuses(org, page?, pageSize?)` → `GET /api/1/organizations/<org>/reuses/`
   - `fetchOrgDiscussions(org, page?, pageSize?)` → `GET /api/1/organizations/<org>/discussions/`

**Implementação realizada (branch: `ticket-09-organization-detail-api`)**

- Tipos criados em `src/types/api.ts`: `UserRef`, `OrganizationMember`, `Badge`, `OrganizationMetrics`, `Dataservice`, `DiscussionMessage`, `Discussion`. Tipo `Organization` estendido com todos os campos.
- Funções criadas em `src/services/api.ts`: `fetchOrganization()` (com 404→null), `fetchOrgDatasets()`, `fetchOrgDataservices()`, `fetchOrgReuses()`, `fetchOrgDiscussions()`.
- Página de detalhe (`src/app/pages/organizations/[slug]/page.tsx`) atualizada com `notFound()` para 404.
- `OrganizationDetailClient` corrigido:
  - `last_modified` real em vez de `new Date()`.
  - Sidebar métricas: "Visualizações" usa `metrics.views`, "Seguidores" usa `metrics.followers` (antes usava campos errados e label "Downloads").
  - Pill com valores computados a partir das métricas reais.
  - "desde" usa `organization.created_at` formatado (antes hardcoded "julho de 2022").
  - SVG `clip-rule` → `clipRule` (React DOM prop).
- `OrganizationTabs` refatorizado com 5 tabs alinhadas à referência data.gouv.fr:
  1. **Apresentação** — descrição da organização.
  2. **Conjuntos de dados** — datasets com cards (métricas: views, downloads, reuses, followers) e paginação.
  3. **API** — dataservices com formato, métricas e paginação.
  4. **Reutilizações** — reuses com cards e métricas.
  5. **Informações** — estatísticas (datasets, API, reuses, seguidores), membros (avatar, nome, role), informações técnicas (última atualização, ID, data criação, website, NIF).

**Critérios de Aceitação**

- [x] Tipo `Organization` estendido com todos os campos do backend.
- [x] `fetchOrganization()` retorna organização completa.
- [x] `fetchOrgDatasets()` e `fetchOrgReuses()` retornam listas paginadas.
- [x] 404 é tratado quando organização não existe.

---

## TICKET-10: Organizations — Search, Filtros e Página Completa (Conexão API) ✅✅

**Descrição**
Estender `fetchOrganizations()` para suportar pesquisa e filtros, e completar a página de Organizações com funcionalidades de pesquisa, ordenação, filtros por badge e métricas reais.

**Contexto Arquitetural**

- `fetchOrganizations()` atual aceita apenas `page` e `pageSize`.
- Backend: `GET /api/1/organizations/?q=<query>&badge=<badge>&sort=<sort>`.
- Backend: `GET /api/1/organizations/suggest/?q=<query>&size=<n>` (autocomplete).
- Backend: `GET /api/1/organizations/badges/` (badges disponíveis).
- Backend sorts disponíveis: `name`, `reuses`, `datasets`, `followers`, `views`, `created`, `last_modified`.

**O que foi feito**

1. **Tipos TS** em `types/api.ts`:
   - `OrganizationSuggestion`: id, name, slug, logo, score.
   - `OrgBadges`: mapa `{ [kind: string]: string }` (kind → label).
   - `OrganizationFilters`: interface com `q?`, `badge?`, `sort?`.
   - `SiteMetrics`: tipo extraído com `datasets`, `dataservices?`, `organizations`, `reuses`, `users`.
2. **Atualizar `fetchOrganizations()`** em `services/api.ts`:
   - Aceita: `{ q?, badge?, sort?, page?, pageSize? }` via `OrganizationFilters`.
3. **Novas funções** em `services/api.ts`:
   - `suggestOrganizations(query, size?)` → `GET /api/1/organizations/suggest/?q=<query>&size=<n>`
   - `fetchOrgBadges()` → `GET /api/1/organizations/badges/` (retorna `OrgBadges`)
4. **Pesquisa funcional** na página de Organizações:
   - Barra de pesquisa ligada ao parâmetro `q` da URL.
   - Pesquisa via Enter ou clique no ícone de pesquisa.
5. **Ordenação funcional** com Agora `InputSelect`:
   - Por relevância (default), Ordem alfabética (`name`), Mais recentes (`-last_modified`).
   - Componente `SortSelect` isolado com deferred mount para evitar erros de render do `InputSelect`.
6. **Filtros por badge** na sidebar:
   - Badges obtidos via `fetchOrgBadges()` com contagens por badge (fetched server-side em paralelo).
   - Cada badge é um item clicável com nome (PT) + Pill com contagem de resultados.
   - Mapa de tradução `BADGE_LABELS_PT` para garantir nomes em português.
   - Clicar ativa/desativa o filtro via parâmetro `badge` na URL.
7. **Métricas reais** nos cards de organização:
   - Visualizações, datasets, reutilizações e favoritos a partir de `org.metrics`.
   - Datas relativas reais ("Atualizado há X dias") via `date-fns`.
8. **Componente reutilizável `CategoryToggles`** (`src/components/CategoryToggles.tsx`):
   - 4 toggles: Reutilizações, Conjunto de dados, APIs, Organizações.
   - Cada toggle mostra o total real via `SiteMetrics` da API `/api/1/site/`.
   - Deteta automaticamente a página ativa via `usePathname()`.
   - Clicar no item ativo reseta os filtros (navega para o href base sem query params).
   - Clicar noutro item navega para a página correspondente.
   - Reutilizável em qualquer página de listagem.
9. **Paginação preserva filtros**:
   - Componente `Pagination` atualizado para manter `sort`, `q`, `badge` ao mudar de página.
10. **Server-side filters** (`initialFilters`):
    - Filtros passados do server component como props para evitar hydration mismatches.
    - Eliminado uso de `window.location.search` nos componentes client.

**Critérios de Aceitação**

- [x] `fetchOrganizations()` aceita `q`, `badge` e `sort` e os passa ao backend.
- [x] `suggestOrganizations()` retorna sugestões.
- [x] `fetchOrgBadges()` retorna mapa de badges.
- [x] Barra de pesquisa funcional na página de Organizações.
- [x] Ordenação funcional (relevância, alfabética, mais recentes).
- [x] Filtros por badge com contagens reais.
- [x] Métricas reais nos cards (views, datasets, reuses, followers).
- [x] Componente `CategoryToggles` reutilizável com totais reais.
- [x] Paginação preserva todos os filtros ativos.
- [x] Sem erros de hydration (filtros via server props).

---

## TICKET-11: Reuses — Search, Filtros e Detail (Conexões API) ✅✅

**Descrição**
Estender `fetchReuses()` para pesquisa/filtros e estender `fetchReuse()` para dados completos incluindo datasets associados.

**Contexto Arquitetural**

- `fetchReuses()` atual aceita apenas `page` e `pageSize`.
- `fetchReuse(rid)` existe mas pode não retornar todos os campos.
- Backend: `GET /api/1/reuses/?q=<query>&type=<type>&tag=<tag>&organization=<org>&sort=<sort>`.
- Backend: `GET /api/1/reuses/types/` (tipos de reuse disponíveis).
- Backend: `GET /api/1/reuses/suggest/?q=<query>&size=<n>`.
- Reuse detail inclui `datasets[]` (referências a datasets associados).

**O que foi feito**

1. ✅ **Tipos TS** em `types/api.ts`:
   - `ReuseType`: id, label.
   - `ReuseSuggestion`: id, title, slug, image_url, score.
   - `ReuseFilters`: q?, type?, tag?, organization?, sort?.
   - Estendido `Reuse` com: `datasets[]`, `dataservices[]`, `owner`, `badges[]`.
2. ✅ **Atualizado `fetchReuses()`** em `services/api.ts`:
   - Aceita: `{ q?, type?, tag?, organization?, sort?, page?, pageSize? }` via `ReuseFilters`.
3. ✅ **Novas funções** em `services/api.ts`:
   - `fetchReuseTypes()` → `GET /api/1/reuses/types/`
   - `suggestReuses(query, size?)` → `GET /api/1/reuses/suggest/?q=<query>&size=<n>`
   - `followReuse(id)` → `POST /api/1/reuses/<id>/followers/`
   - `unfollowReuse(id)` → `DELETE /api/1/reuses/<id>/followers/`
4. ✅ **Search bar na listing page** ligada à API (parâmetro `q` via URL search params).
5. ✅ **Sort dropdown** ligado à API (`-created`, `-views`, `-reuses`, `-followers`).
6. ✅ **Filtro por tipo** populado dinamicamente via `fetchReuseTypes()`.
7. ✅ **Botão "Limpar filtros"** quando existem filtros ativos.
8. ✅ **Detail page**: datasets associados agora dinâmicos via `reuse.datasets[]` (removidos os 5 hardcoded).
9. ✅ **Detail page**: descrição dinâmica via `reuse.description` (removido conteúdo hardcoded).
10. ✅ **Detail page**: métricas (views, dataset count), owner/organização dinâmicos.

**Critérios de Aceitação**

- [x] `fetchReuses()` aceita `q`, `type`, `tag`, `organization`.
- [x] `fetchReuseTypes()` retorna lista de tipos.
- [x] `suggestReuses()` retorna sugestões.
- [x] `fetchReuse()` retorna dados completos incluindo datasets associados.

**Branch:** `ticket-11-reuses-search-filters-detail` (frontend)

---

## TICKET-12: Topics/Themes — Dados Dinâmicos (Conexões API v2) 2ª fase ✅

**Descrição**
Implementar tipos e funções para consumir a API v2 de topics nas páginas públicas de themes.

**Contexto Arquitetural**

- Themes page tem conteúdo hardcoded, sem conexão a API.
- Backend (API v2):
  - `GET /api/2/topics/` → listar topics.
  - `GET /api/2/topics/<topic>/` → detalhes do topic.
  - `GET /api/2/topics/<topic>/elements/` → elementos (datasets/reuses associados).
- `NEXT_PUBLIC_API_V2_BASE` está configurado mas não é usado.

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - `Topic`: id, name, slug, description, tags[], featured, private, created_at, last_modified, datasets_count, reuses_count, owner, image, image_thumbnail.
   - `TopicElement`: id, type (`'dataset' | 'reuse'`), content (ref Dataset | Reuse), position.
2. **Funções em `services/api.ts`** (usando `NEXT_PUBLIC_API_V2_BASE`):
   - `fetchTopics(page?, pageSize?)` → `GET /api/2/topics/`
   - `fetchTopic(slugOrId)` → `GET /api/2/topics/<topic>/`
   - `fetchTopicElements(topicId, page?)` → `GET /api/2/topics/<topic>/elements/`
3. **Nota**: Estas funções são de leitura para as páginas públicas. O CRUD admin está no TICKET-33.

**Critérios de Aceitação**

- [x] Funções usam `NEXT_PUBLIC_API_V2_BASE` como base URL.
- [x] `fetchTopics()` retorna lista paginada.
- [x] `fetchTopic()` retorna detalhes completos.
- [x] `fetchTopicElements()` retorna datasets e reuses associados.
- [x] Tipos TS espelham a resposta da API v2.

---

## TICKET-13: User Profile (Conexões API) ✅

**Descrição**
Implementar as funções de fetch para perfis de utilizador: perfil público e dados do utilizador autenticado (datasets, reuses, organizações).

**Contexto Arquitetural**

- Não existe página de perfil no frontend.
- Backend endpoints:
  - `GET /api/1/me/` → perfil do utilizador autenticado (já coberto no TICKET-03).
  - `GET /api/1/me/datasets/?page=<n>` → datasets do utilizador.
  - `GET /api/1/me/reuses/?page=<n>` → reuses do utilizador.
  - `GET /api/1/me/org_datasets/?page=<n>` → datasets das organizações.
  - `GET /api/1/users/<user>/` → perfil público de qualquer utilizador.
  - `GET /api/1/users/<user>/datasets/` → datasets públicos de um utilizador (via query filter).

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - `UserPublic`: id, slug, first_name, last_name, avatar, avatar_thumbnail, about, website, metrics, organizations[].
   - (Reutilizar `User` do TICKET-03 para o utilizador autenticado.)
2. **Funções em `services/api.ts`**:
   - `fetchMyDatasets(page?, pageSize?)` → `GET /api/1/me/datasets/`
   - `fetchMyReuses(page?, pageSize?)` → `GET /api/1/me/reuses/`
   - `fetchMyOrgDatasets(page?, pageSize?)` → `GET /api/1/me/org_datasets/`
   - `fetchUserProfile(userId)` → `GET /api/1/users/<user>/`
3. **Nota**: Edit profile (PUT /me, avatar upload) está no TICKET-30 (admin).

**Critérios de Aceitação**

- [x] `fetchMyDatasets()` e `fetchMyReuses()` retornam listas paginadas.
- [x] `fetchMyOrgDatasets()` retorna datasets das organizações do utilizador.
- [x] `fetchUserProfile()` retorna perfil público de qualquer utilizador.
- [x] 404 é tratado para utilizadores inexistentes.

---

## TICKET-14: Dataset Create & Edit — `CANCELADO`

> **Nota**: A lógica de conexão para criação e edição de datasets está detalhada no TICKET-26 (Admin — Datasets CRUD). Este ticket é mantido como referência.

---

## TICKET-15: Reuse Create & Edit — `CANCELADO`

> **Nota**: A lógica de conexão para criação e edição de reuses está detalhada no TICKET-27 (Admin — Reuses CRUD). Este ticket é mantido como referência.

---

## TICKET-16: Dataservices — Wiring do Form Existente — `CANCELADO`

> **Nota**: A lógica de conexão para dataservices está detalhada no TICKET-28 (Admin — Dataservices CRUD). Este ticket é mantido como referência.

---

## TICKET-17: Posts/News — Leitura (Conexões API) ✅

**Descrição**
Implementar tipos e funções para consumir a API de posts nas páginas públicas de notícias, e integrar nas páginas de artigos existentes.

**Contexto Arquitetural**

- Backend endpoints:
  - `GET /api/1/posts/?page=<n>&page_size=<n>` → listar posts.
  - `GET /api/1/posts/<post>/` → detalhes de um post.

**O que foi feito**

1. **Tipo `Post` completo** em `types/api.ts` — todos os campos: id, name, slug, headline, content, body_type, kind, published, owner, image, image_thumbnail, credit_to, credit_url, created_at, last_modified, tags[].
2. **`fetchPosts(page?, pageSize?)`** em `services/api.ts` — lista paginada de posts.
3. **`fetchPost(slugOrId)`** em `services/api.ts` — post individual com tratamento de 404 (retorna `null`).
4. **`ArticleClient.tsx`** integrado com `fetchPosts()` — paginação real, loading state, empty state. Mock data removido.
5. **`ArticleDetail.tsx`** integrado com `fetchPost()` — conteúdo da API, sidebar com posts relacionados, tags, créditos. Mock data removido.
6. **Tratamento de 404** — página "Artigo não encontrado" com link para voltar à lista.
7. **Homepage** integrada com posts reais da API (chama `fetchPosts(1, 3)`).
8. **Nota**: O CRUD admin de posts está no TICKET-34. Aqui é só leitura pública.

**Critérios de Aceitação**

- [x] `fetchPosts()` retorna lista paginada.
- [x] Tipo `Post` definido com **todos** os campos (kind, published, owner, credit_to, credit_url).
- [x] `fetchPost(slugOrId)` retorna post completo.
- [x] `ArticleClient.tsx` consome `fetchPosts()` em vez de dados mock.
- [x] `ArticleDetail.tsx` consome `fetchPost()` em vez de dados mock.
- [x] 404 é tratado na página de detalhe.

---

## TICKET-18: Notifications (Conexão API) ✅

**Descrição**
Implementar tipo e função para consumir notificações do utilizador autenticado.

**Contexto Arquitetural**

- Backend: `GET /api/1/notifications/` → lista notificações do utilizador. Auth required (`@api.secure`).
- Modelo `Notification` em `udata/features/notifications/models.py` com 3 tipos de detalhes:
  - `DiscussionNotificationDetails`: discussion, status, message_id
  - `MembershipRequestNotificationDetails`: request_organization, request_user
  - `TransferRequestNotificationDetails`: transfer_owner, transfer_recipient, transfer_subject

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - `Notification`: id, created_at, last_modified, handled_at, user, details (union type).
   - `DiscussionNotificationDetails`: `{ discussion?: string, status?: string, message_id?: string }`
   - `MembershipRequestNotificationDetails`: `{ request_organization?: OrganizationRef, request_user?: UserRef }`
   - `TransferRequestNotificationDetails`: `{ transfer_owner?: object, transfer_recipient?: object, transfer_subject?: object }`
   - `NotificationDetails`: union dos 3 tipos acima.
2. **Funções em `services/api.ts`**:
   - `fetchNotifications(page?, pageSize?)` → `GET /api/1/notifications/`

**Critérios de Aceitação**

- [x] Tipo `Notification` definido (com campos corretos: id, created_at, handled_at, user, details).
- [x] Tipos de detalhes (Discussion, MembershipRequest, TransferRequest) definidos.
- [x] `fetchNotifications()` retorna lista paginada.
- [x] Auth required (401 se não autenticado).

---

## TICKET-19: Global Search — Suggest Multi-Entidade (Conexões API) ✅

**Descrição**
Implementar uma pesquisa global inspirada no projeto francês cdata (data.gouv.fr): dropdown de seleção de tipo ao digitar + página de resultados com sidebar de tipos/contagens e lista paginada.

**Contexto Arquitetural**

- Implementado como parte do TICKET-04 (Ponto 4), mas merece ticket próprio pela complexidade e por ser uma feature distinta da homepage.
- Inspiração direta no projeto [cdata](https://github.com/datagouv/cdata) — componentes `MenuSearch.vue` (dropdown) e `GlobalSearch` (página de resultados com sidebar).
- Backend endpoints utilizados:
  - `GET /api/1/datasets/?q=<query>&page=<n>&page_size=<n>` → pesquisa full-text de datasets.
  - `GET /api/1/organizations/?q=<query>&page=<n>&page_size=<n>` → pesquisa full-text de organizações.
  - `GET /api/1/reuses/?q=<query>&page=<n>&page_size=<n>` → pesquisa full-text de reutilizações.
- Frontend usa `'use client'` com `useSearchParams` (requer `Suspense` wrapper).
- Navegação por URL: `/pages/search?q=<query>&type=<datasets|reuses|organizations>&page=<n>`.

**O que foi feito**

1. **Funções em `services/api.ts`**:
   - `searchDatasets(query, page?, pageSize?)` → `GET /api/1/datasets/?q=<query>&page=<n>&page_size=<n>` — retorna `APIResponse<Dataset>`.
   - `searchOrganizations(query, page?, pageSize?)` → `GET /api/1/organizations/?q=<query>&page=<n>&page_size=<n>` — retorna `APIResponse<Organization>`.
   - `searchReuses(query, page?, pageSize?)` → `GET /api/1/reuses/?q=<query>&page=<n>&page_size=<n>` — retorna `APIResponse<Reuse>`.
2. **Componente `SearchDropdown`** (`src/components/search/SearchDropdown.tsx`):
   - Input de pesquisa reutilizável com dropdown de 3 opções ao digitar: "Pesquisar «X» nos/nas conjuntos de dados / reutilizações / organizações".
   - Navegação por teclado (ArrowUp/ArrowDown, Enter, Escape) e click-outside para fechar.
   - Navega para `/pages/search?q=<query>&type=<type>` ao selecionar uma opção.
   - Props: `id`, `darkMode`, `placeholder`, `label`, `hasVoiceActionButton`.
   - Usa `InputSearchBar` do agora-design-system internamente.
   - Integrado no hero da homepage (modo escuro) e no Header (modo claro).
3. **Componente `SearchClient`** (`src/components/search/SearchClient.tsx`):
   - Página de resultados com layout sidebar (inspirado no cdata GlobalSearch).
   - Sidebar esquerda: navegação por tipo (Conjuntos de Dados, Reutilizações, Organizações) com contagens totais.
   - Conteúdo direito: lista de resultados com paginação (PAGE_SIZE = 10).
   - Breadcrumb: Início > Pesquisa.
   - Título dinâmico por tipo ("Pesquisa avançada de conjuntos de dados", etc.).
   - Usa `SearchDropdown` para permitir nova pesquisa na própria página.
   - Fetch de totais em paralelo (`Promise.all`) + fetch de resultados do tab ativo.
   - Estado controlado por URL: `?q=<query>&type=<type>&page=<page>`.
4. **Página de rota** (`src/app/pages/search/page.tsx`):
   - Server component que renderiza `SearchClient` dentro de `Suspense` (necessário para `useSearchParams`).
5. **Integração na homepage** (`src/app/page.tsx`):
   - Substituído `InputSearchBar` + `useRouter` + estado `searchQuery` pelo componente `SearchDropdown`.
6. **Integração no Header** (`src/components/Header.tsx`):
   - Substituído `InputSearchBar` do header pelo `SearchDropdown` na `GeneralBar`.

**Ficheiros criados/alterados**

| Ficheiro                                   | Ação                                         |
| ------------------------------------------ | -------------------------------------------- |
| `src/components/search/SearchDropdown.tsx` | Criado                                       |
| `src/components/search/SearchClient.tsx`   | Criado                                       |
| `src/app/pages/search/page.tsx`            | Criado                                       |
| `src/services/api.ts`                      | Alterado — adicionadas 3 funções de pesquisa |
| `src/app/page.tsx`                         | Alterado — hero usa SearchDropdown           |
| `src/components/Header.tsx`                | Alterado — header usa SearchDropdown         |

**Critérios de Aceitação**

- [x] `searchDatasets()`, `searchOrganizations()`, `searchReuses()` retornam resultados paginados do backend.
- [x] Dropdown aparece ao digitar no campo de pesquisa com 3 opções de tipo.
- [x] Navegação por teclado funciona no dropdown (ArrowUp/Down, Enter, Escape).
- [x] Seleção de opção navega para `/pages/search?q=<query>&type=<type>`.
- [x] Página de resultados mostra sidebar com tipos e contagens.
- [x] Resultados são paginados (10 por página).
- [x] Pesquisa funciona a partir do hero da homepage e do header.
- [x] URL reflete o estado da pesquisa (query, tipo, página).
- [x] Click-outside fecha o dropdown.

---

## TICKET-20: Mini-Courses — Fonte de Dados (Conexão API) ❓

**Descrição**
Definir a estratégia de dados e implementar os tipos e funções para substituir os mini-courses hardcoded.

**Contexto Arquitetural**

- `MiniCoursesClient.tsx` tem array de cursos hardcoded.
- Backend **não tem** módulo de mini-courses. Opções:
  - Usar Posts API com `kind='course'`.
  - Criar módulo backend dedicado.
  - CMS externo.

**O que deve ser feito**

1. **Decisão de arquitetura**: definir a fonte de dados (posts com kind, módulo novo, ou CMS).
2. **Se Posts API** (opção mais simples):
   - Tipo TS: reutilizar `Post` com `kind: 'course'`.
   - Função: `fetchCourses(page?, pageSize?)` → `GET /api/1/posts/?kind=course&page=<n>&page_size=<n>`
   - Função: `fetchCourse(slug)` → `GET /api/1/posts/<slug>/`
3. **Se módulo backend novo**:
   - Criar tipo `MiniCourse`: id, title, slug, description, content, modules[], duration, level, tags[], image, created_at.
   - Criar funções CRUD correspondentes.
4. **Fluxo de dados**: as funções substituem o array hardcoded em `MiniCoursesClient.tsx`.

**Critérios de Aceitação**

- [ ] Estratégia de dados decidida e documentada.
- [ ] Tipo TS definido conforme a estratégia escolhida.
- [ ] Função de fetch implementada.
- [ ] Dados vêm da API, não de array hardcoded.

---

## TICKET-21: ~~Password Reset (Conexão API)~~ — `CANCELADO`

**Estado:** ❌ Cancelado — não aplicável.

**Motivo:** A autenticação do portal será exclusivamente via Chave Móvel Digital (CMD/SAML) e eIDAS. O login por email/password está a ser descontinuado, pelo que o fluxo de reset de password não será implementado. Os rewrites de `/reset/` foram também removidos do `next.config.ts`.

---

## TICKET-22: Spatial/Geographic (Conexões API) ✅

**Estado:** Concluído — PR #88 merged.

**Descrição**
Implementar tipos e funções para a API spatial: suggest de zonas, granularidades, e levels. Integrar nos filtros de datasets.

**Contexto Arquitetural**

- Filtros "Spatial Coverage" e "Spatial Granularity" **não existem ainda** em `DatasetsFilters.tsx` — precisam ser adicionados.
- `DatasetFilters.granularity` já existe como query param (string) em `types/api.ts` e é passado na `fetchDatasets()`.
- `DatasetFilters.geozone` já existe como query param em `types/api.ts`.
- Backend endpoints:
  - `GET /api/1/spatial/zones/suggest/?q=<query>&size=<n>` → suggest de zonas geográficas.
  - `GET /api/1/spatial/zones/<ids>/` → zonas como GeoJSON.
  - `GET /api/1/spatial/granularities/` → níveis de granularidade.
  - `GET /api/1/spatial/levels/` → níveis geográficos.

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - `SpatialZone`: id, name, code, level, uri.
   - `Granularity`: id, label.
   - `GeoLevel`: id, label.
2. **Funções em `services/api.ts`**:
   - `suggestSpatialZones(query, size?)` → `GET /api/1/spatial/zones/suggest/?q=<query>&size=<n>`
   - `fetchSpatialZones(ids)` → `GET /api/1/spatial/zones/<ids>/` (retorna GeoJSON).
   - `fetchGranularities()` → `GET /api/1/spatial/granularities/`
   - `fetchGeoLevels()` → `GET /api/1/spatial/levels/`
3. **Integração em `DatasetsFilters.tsx`**:
   - Adicionar filtro "Granularidade Espacial" usando `fetchGranularities()` (carregado no `useEffect` inicial, mesmo padrão de organizations/licenses/frequencies).
   - Adicionar filtro "Cobertura Espacial" usando `suggestSpatialZones()` como autocomplete (mesmo padrão de tags/formats com `suggest: true`).

**Critérios de Aceitação**

- [x] Tipos `SpatialZone`, `Granularity`, `GeoLevel` definidos — `src/types/api.ts`
- [x] `suggestSpatialZones()` retorna sugestões para autocomplete — `src/services/api.ts`
- [x] `fetchGranularities()` retorna lista de granularidades — `src/services/api.ts`
- [x] `fetchGeoLevels()` retorna lista de níveis — `src/services/api.ts`
- [x] Filtro "Granularidade Espacial" em `DatasetsFilters.tsx` com dados dinâmicos da API
- [x] Filtro "Cobertura Espacial" em `DatasetsFilters.tsx` com autocomplete via `suggestSpatialZones()`

---

## TICKET-23: Reports — Submissão (Conexão API) — ✅

**Descrição**
Implementar tipos e funções para submeter reports de conteúdo ao backend.

**Contexto Arquitetural**

- Backend endpoints:
  - `POST /api/1/reports/` → criar report (body: subject `{class, id}`, reason, message). Supports anonymous submissions.
  - `GET /api/1/reports/reasons/` → razões de report disponíveis (public).

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - `ReportCreatePayload`: subject `{ class: string, id: string }`, reason, message?.
   - `ReportReason`: value, label.
   - `Report`: full response type (id, by, subject, reason, message, reported_at, dismissed_at, etc.).
2. **Funções em `services/api.ts`**:
   - `fetchReportReasons()` → `GET /api/1/reports/reasons/`
   - `createReport(payload)` → `POST /api/1/reports/`
3. **Nota**: A gestão de reports (moderação) está no TICKET-36 (admin sysadmin).

**Critérios de Aceitação**

- [x] `fetchReportReasons()` retorna lista de razões. → `services/api.ts:fetchReportReasons()`
- [x] `createReport()` envia subject, reason e message. → `services/api.ts:createReport()`
- [x] Credentials included (cookies sent for authenticated users, anonymous also supported).
- [x] Erros de validação retornados em formato utilizável (error thrown with parsed message).

---

## TICKET-24: Organization Membership (Conexões API) ✅

**Descrição**
Implementar as funções de pedido de adesão a organizações e gestão de membros.

**Contexto Arquitetural**

- Backend endpoints:
  - `POST /api/1/organizations/<org>/membership/` → pedir adesão. Auth required.
  - `GET /api/1/organizations/<org>/membership/` → listar pedidos pendentes.
  - `POST /api/1/organizations/<org>/membership/<id>/accept/` → aceitar pedido.
  - `POST /api/1/organizations/<org>/membership/<id>/refuse/` → recusar pedido.
  - `POST /api/1/organizations/<org>/member/<user>/` → adicionar membro (body: role).
  - `PUT /api/1/organizations/<org>/member/<user>/` → atualizar role.
  - `DELETE /api/1/organizations/<org>/member/<user>/` → remover membro.
  - `GET /api/1/organizations/roles/` → roles disponíveis.

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - `MembershipRequest`: id, user (ref), status, created, comment?. ❌ Em falta.
   - `OrgMember`: user (ref User), role. ⚠️ Parcial — existe como `OrganizationMember` (com campo `since` extra). Considerar reutilizar.
   - `OrgRole`: id, label. ❌ Em falta.
2. **Funções em `services/api.ts`** — ❌ **Nenhuma implementada**:
   - `requestMembership(org)` → `POST /api/1/organizations/<org>/membership/`
   - `fetchMembershipRequests(org)` → `GET /api/1/organizations/<org>/membership/`
   - `acceptMembership(org, requestId)` → `POST /api/1/organizations/<org>/membership/<id>/accept/`
   - `refuseMembership(org, requestId)` → `POST /api/1/organizations/<org>/membership/<id>/refuse/`
   - `addMember(org, userId, role)` → `POST /api/1/organizations/<org>/member/<user>/`
   - `updateMemberRole(org, userId, role)` → `PUT /api/1/organizations/<org>/member/<user>/`
   - `removeMember(org, userId)` → `DELETE /api/1/organizations/<org>/member/<user>/`
   - `fetchOrgRoles()` → `GET /api/1/organizations/roles/`
3. **Nota**: Funções partilhadas com TICKET-29 (admin organizations). Definir uma vez e reutilizar.
4. **Estado atual**: Display read-only de membros já existe em `OrganizationTabs.tsx` (tab "Informações"). Backend totalmente implementado.

**Critérios de Aceitação**

- [x] Tipos `MembershipRequest`, `OrgRole` definidos. (`OrganizationMember` atualizado com campo `label`.)
- [x] Request membership funciona — `requestMembership(org, comment?)` em `services/api.ts`.
- [x] Accept/refuse request funciona — `acceptMembership(org, id)` e `refuseMembership(org, id, comment?)`.
- [x] Gestão de membros (add, update role, remove) funciona — `addMember()`, `updateMemberRole()`, `removeMember()`.
- [x] `fetchOrgRoles()` retorna roles disponíveis.

---

## TICKET-25: CSV/Data Export (Conexão API) ✅

**Descrição**
Implementar funções utilitárias para gerar URLs de export CSV dos endpoints do backend.

**Contexto Arquitetural**

- Backend endpoints de export (organização):
  - `GET /api/1/organizations/<org>/datasets.csv`
  - `GET /api/1/organizations/<org>/dataservices.csv`
  - `GET /api/1/organizations/<org>/discussions.csv`
  - `GET /api/1/organizations/<org>/datasets-resources.csv`
- Backend endpoints de export (site/global):
  - `GET /api/1/site/datasets.csv`
  - `GET /api/1/site/resources.csv`
  - `GET /api/1/site/organizations.csv`
  - `GET /api/1/site/reuses.csv`
  - `GET /api/1/site/dataservices.csv`
  - `GET /api/1/site/harvests.csv`
  - `GET /api/1/site/tags.csv`

**O que deve ser feito**

1. **Funções utilitárias** em `services/api.ts`:
   - `getOrgExportUrl(org, type)` → retorna URL completa `${API_BASE}/organizations/<org>/<type>.csv`.
     - `type`: `'datasets' | 'dataservices' | 'discussions' | 'datasets-resources'`.
   - `getSiteExportUrl(type)` → retorna URL completa `${API_BASE}/site/<type>.csv`.
     - `type`: `'datasets' | 'resources' | 'organizations' | 'reuses' | 'dataservices' | 'harvests' | 'tags'`.
2. **Nota**: Não é necessário fetch — o browser abre a URL diretamente para download.

**Critérios de Aceitação**

- [x] `getOrgExportUrl()` gera URL correta para exports de organização.
- [x] `getSiteExportUrl()` gera URL correta para exports globais.
- [x] URLs usam a base URL da API configurada.

---

## TICKET-37: Authentication — Login via Autenticação.gov / SAML (Conexão API) ✅✅

**Descrição**
Implementar o fluxo completo de autenticação via Autenticação.gov (Cartão de Cidadão) usando protocolo SAML 2.0, incluindo login, registo automático, migração de contas legado para CMD, e logout — tanto no backend (plugin SAML) como no frontend (redirect flow e callbacks).

**Contexto Arquitetural**

- Referência: projecto `udata-front-pt` já tem implementação completa em `udata_front/saml_plugin/`.
- Backend usa `pysaml2` (v7.4.2) para comunicação SAML com o IdP da Autenticação.gov.
- O plugin regista um Blueprint Flask com rotas `/saml/*`.
- Fluxo SP-initiated: o frontend redireciona para `/saml/login`, o backend gera o AuthnRequest e redireciona para o IdP, o IdP retorna o utilizador para `/saml/sso` (callback).
- Atributos SAML recebidos do IdP:
  - `http://interop.gov.pt/MDC/Cidadao/CorreioElectronico` → email (obrigatório)
  - `http://interop.gov.pt/MDC/Cidadao/NIC` → NIC (opcional, guardado em `user.extras['auth_nic']`)
  - `http://interop.gov.pt/MDC/Cidadao/NomeProprio` → first_name (opcional)
  - `http://interop.gov.pt/MDC/Cidadao/NomeApelido` → last_name (opcional)
- Se o utilizador já existe (por email ou NIC) e já tem NIC associado: faz login direto (`existing_saml`).
- Se o utilizador já existe mas é legado (tem password, sem NIC): é classificado como `migration_candidate` e redirecionado para o fluxo de migração.
- Se o utilizador não existe: cria conta automaticamente via SAML.
- **Fluxo de Migração de Conta Legado → CMD**:
  - Quando o IdP retorna um email que corresponde a um utilizador legado (com password, sem NIC), o backend guarda os dados SAML em `session["saml_migration_pending"]` e redireciona para `/pages/migrate-account`.
  - O frontend (`MigrateAccountClient.tsx`) apresenta os dados da conta legada encontrada e oferece ao utilizador a opção de vincular a conta CMD à conta existente.
  - Se o SAML não devolveu email, o utilizador pode pesquisar a conta legada via email/nome (`POST /saml/migration/search`).
  - Verificação: o utilizador confirma a migração por **código de verificação enviado por email** (`POST /saml/migration/send-code`) ou por **password antiga** (`POST /saml/migration/confirm`).
  - Após confirmação, o backend associa o NIC do CMD ao utilizador existente (`user.extras['auth_nic']`), remove a password legada, e faz login automático.
  - Alternativa: o utilizador pode saltar a migração (`POST /saml/migration/skip`) e criar uma conta nova a partir dos dados SAML.
  - Endpoint auxiliar: `GET /saml/migration/check` — verifica se o utilizador autenticado é legado e precisa de migração.
  - Endpoint auxiliar: `GET /saml/migration/pending` — retorna dados da migração pendente na sessão.
- Logout SAML: `/saml/logout` envia LogoutRequest ao IdP, callback em `/saml/sso_logout`.
- Sessão: flag `saml_login = True` indica que o login foi via SAML (usado para decidir o fluxo de logout).
- Suporte adicional para eIDAS (autenticação europeia cross-border) com rotas `/saml/eidas/*`.

**Critérios de Aceitação**

- [x] Plugin SAML registado no backend com rotas `/saml/login`, `/saml/sso`, `/saml/logout`, `/saml/sso_logout`.
- [x] Rotas eIDAS: `/saml/eidas/login`, `/saml/eidas/sso`, `/saml/eidas/logout`, `/saml/eidas/sso_logout`.
- [x] Configurações SAML (`SECURITY_SAML_*`) definidas em `udata.cfg` com valores adequados.
- [x] `GET /saml/login` gera AuthnRequest válido e redireciona para o IdP.
- [x] `POST /saml/sso` processa SAMLResponse, valida assinatura, e faz login ou cria conta.
- [x] Utilizador existente (por email/NIC) é autenticado automaticamente.
- [x] Utilizador novo é criado automaticamente.
- [x] NIC é guardado em `user.extras['auth_nic']` após criação.
- [x] Logout SAML (`/saml/logout`) envia LogoutRequest ao IdP e limpa sessão local.
- [x] Frontend tem botões CMD e eIDAS na página de login (visíveis quando `NEXT_PUBLIC_SAML_ENABLED=true`).
- [x] Rewrites no `next.config.ts` encaminham `/saml/*` para o backend.
- [x] Após login SAML bem-sucedido, `AuthContext` atualiza o estado do utilizador.
- [x] Proteção XXE ativa (via `defusedxml`).
- [x] Suporte a múltiplos IdP metadata files com fallback.
- [x] Frontend logout diferencia sessões SAML — redireciona para `/saml/logout` em vez de `/logout/` quando `saml_login` é `true`.
- [x] Utilizador legado (com password, sem NIC) é identificado como `migration_candidate` durante login SAML.
- [x] Backend redireciona `migration_candidate` para `/pages/migrate-account` com dados SAML em sessão.
- [x] Endpoints de migração implementados: `GET /saml/migration/check`, `GET /saml/migration/pending`, `POST /saml/migration/search`, `POST /saml/migration/send-code`, `POST /saml/migration/confirm`, `POST /saml/migration/skip`.
- [x] Frontend (`MigrateAccountClient.tsx`) apresenta dados da conta legada e permite vincular ao CMD.
- [x] Migração confirmável por código de verificação (email) ou password antiga.
- [x] Após migração, NIC é associado ao utilizador e password legada é removida.
- [x] Utilizador pode saltar migração e criar conta nova a partir dos dados SAML.
- [x] Registo direto removido — novos utilizadores são criados exclusivamente via SAML/CMD.

---

## TICKET-38: Repository Maintenance — Login Integration & Branch Cleanup ✅✅

**Descrição**
Sincronizar as branches divergentes de login (`login_tabs` da Ines e `login_final` do Adriano) na branch `main`, resolvendo conflitos, restaurando arquivos perdidos em resets e unificando a UI com a lógica de API.

**Contexto Arquitetural**

- Trabalho realizado em paralelo em múltiplas branches causou divergência no frontend.
- `login_tabs` continha o layout moderno com Tabs verticais e suporte a CMD/eIDAS na UI.
- `login_final` continha a lógica de API e proxying necessária para o funcionamento real do login.
- Inconsistências de checkout levaram à exclusão acidental de arquivos críticos: `src/app/login/route.ts`, `.env.example`, `src/config/env.ts` e `src/config/site.ts`.
- Foi necessário unificar o código para garantir que o formulário de login (UI) utilizasse as funções de API restauradas.

**O que deve ser feito**

1. **Consolidação de Branches**:
   - Identificar e restaurar o estado da branch `main` após resets acidentais.
   - Unificar o layout (`LoginClient.tsx`) da branch da Ines com as funções de conexão de API.
2. **Restauração de Arquivos Perdidos**:
   - Recuperar `src/app/login/route.ts` (API Proxy handler).
   - Recuperar `.env.example` e diretório `src/config/` (`env.ts` e `site.ts`).
3. **Integração de Código**:
   - Conectar o evento `onSubmit` do formulário de login às funções `fetchCsrfToken()` e `login()` do `services/api.ts`.
   - Garantir que rewrites no `next.config.ts` apontem corretamente para o backend (`BACKEND_URL`).
4. **Limpeza do Repositório**:
   - Remover branches locais e remotas obsoletas para evitar futuras divergências.

**Critérios de Aceitação**

- [ ] Todas as branches de login unificadas na `main`.
- [ ] Arquivos `.env.example`, `env.ts`, `site.ts` e `route.ts` restaurados e versionados.
- [ ] Formulário de login funcional (autentica via API e trata erros).
- [ ] Branches secundárias obsoletas removidas.

---

## TICKET-39: Global Search — Página de Pesquisa com Dropdown e Resultados (Frontend) ✅✅

**Descrição**
Implementar uma pesquisa global inspirada no projeto francês cdata (data.gouv.fr): dropdown de seleção de tipo ao digitar + página de resultados com sidebar de tipos/contagens e lista paginada.

**Contexto Arquitetural**

- Implementado como parte do TICKET-04 (Ponto 4), mas merece ticket próprio pela complexidade e por ser uma feature distinta da homepage.
- Inspiração direta no projeto [cdata](https://github.com/datagouv/cdata) — componentes `MenuSearch.vue` (dropdown) e `GlobalSearch` (página de resultados com sidebar).
- Backend endpoints utilizados:
  - `GET /api/1/datasets/?q=<query>&page=<n>&page_size=<n>` → pesquisa full-text de datasets.
  - `GET /api/1/organizations/?q=<query>&page=<n>&page_size=<n>` → pesquisa full-text de organizações.
  - `GET /api/1/reuses/?q=<query>&page=<n>&page_size=<n>` → pesquisa full-text de reutilizações.
- Frontend usa `'use client'` com `useSearchParams` (requer `Suspense` wrapper).
- Navegação por URL: `/pages/search?q=<query>&type=<datasets|reuses|organizations>&page=<n>`.

**O que foi feito**

1. **Funções em `services/api.ts`**:
   - `searchDatasets(query, page?, pageSize?)` → `GET /api/1/datasets/?q=<query>&page=<n>&page_size=<n>` — retorna `APIResponse<Dataset>`.
   - `searchOrganizations(query, page?, pageSize?)` → `GET /api/1/organizations/?q=<query>&page=<n>&page_size=<n>` — retorna `APIResponse<Organization>`.
   - `searchReuses(query, page?, pageSize?)` → `GET /api/1/reuses/?q=<query>&page=<n>&page_size=<n>` — retorna `APIResponse<Reuse>`.
2. **Componente `SearchDropdown`** (`src/components/search/SearchDropdown.tsx`):
   - Input de pesquisa reutilizável com dropdown de 3 opções ao digitar: "Pesquisar «X» nos/nas conjuntos de dados / reutilizações / organizações".
   - Navegação por teclado (ArrowUp/ArrowDown, Enter, Escape) e click-outside para fechar.
   - Navega para `/pages/search?q=<query>&type=<type>` ao selecionar uma opção.
   - Props: `id`, `darkMode`, `placeholder`, `label`, `hasVoiceActionButton`.
   - Usa `InputSearchBar` do agora-design-system internamente.
   - Integrado no hero da homepage (modo escuro) e no Header (modo claro).
3. **Componente `SearchClient`** (`src/components/search/SearchClient.tsx`):
   - Página de resultados com layout sidebar (inspirado no cdata GlobalSearch).
   - Sidebar esquerda: navegação por tipo (Conjuntos de Dados, Reutilizações, Organizações) com contagens totais.
   - Conteúdo direito: lista de resultados com paginação (PAGE_SIZE = 10).
   - Breadcrumb: Início > Pesquisa.
   - Título dinâmico por tipo ("Pesquisa avançada de conjuntos de dados", etc.).
   - Usa `SearchDropdown` para permitir nova pesquisa na própria página.
   - Fetch de totais em paralelo (`Promise.all`) + fetch de resultados do tab ativo.
   - Estado controlado por URL: `?q=<query>&type=<type>&page=<page>`.
4. **Página de rota** (`src/app/pages/search/page.tsx`):
   - Server component que renderiza `SearchClient` dentro de `Suspense` (necessário para `useSearchParams`).
5. **Integração na homepage** (`src/app/page.tsx`):
   - Substituído `InputSearchBar` + `useRouter` + estado `searchQuery` pelo componente `SearchDropdown`.
6. **Integração no Header** (`src/components/Header.tsx`):
   - Substituído `InputSearchBar` do header pelo `SearchDropdown` na `GeneralBar`.

**Ficheiros criados/alterados**

| Ficheiro                                   | Ação                                         |
| ------------------------------------------ | -------------------------------------------- |
| `src/components/search/SearchDropdown.tsx` | Criado                                       |
| `src/components/search/SearchClient.tsx`   | Criado                                       |
| `src/app/pages/search/page.tsx`            | Criado                                       |
| `src/services/api.ts`                      | Alterado — adicionadas 3 funções de pesquisa |
| `src/app/page.tsx`                         | Alterado — hero usa SearchDropdown           |
| `src/components/Header.tsx`                | Alterado — header usa SearchDropdown         |

**Critérios de Aceitação**

- [x] `searchDatasets()`, `searchOrganizations()`, `searchReuses()` retornam resultados paginados do backend.
- [x] Dropdown aparece ao digitar no campo de pesquisa com 3 opções de tipo.
- [x] Navegação por teclado funciona no dropdown (ArrowUp/Down, Enter, Escape).
- [x] Seleção de opção navega para `/pages/search?q=<query>&type=<type>`.
- [x] Página de resultados mostra sidebar com tipos e contagens.
- [x] Resultados são paginados (10 por página).
- [x] Pesquisa funciona a partir do hero da homepage e do header.
- [x] URL reflete o estado da pesquisa (query, tipo, página).
- [x] Click-outside fecha o dropdown.

**Status**: ✅ Concluído (branch `fix-homepage`, commit `c4e17fb`)

---

## TICKET-40: Dataset Detail Page — Fix Hardcoded Content & UI Bugs (Frontend) ✅✅

**Descrição**
Corrigir a página de detalhe de dataset que contém múltiplos blocos de conteúdo estático/hardcoded (incluindo texto copiado de um dataset francês), métricas falsas, links não funcionais, e tabs sem dados reais. Substituir todo o conteúdo estático por dados dinâmicos da API.

**Contexto Arquitetural**

- `DatasetDetailClient.tsx` foi criado com conteúdo placeholder que nunca foi substituído por dados reais da API.
- O objeto `Dataset` da API já contém campos suficientes para substituir quase todo o conteúdo hardcoded: `license`, `quality`, `metrics`, `description`, `private`, `archived`.
- `DatasetTabs.tsx` tem 3 tabs com placeholders (Reutilizações, Discussões, Recursos comunitários) — as funções de API para discussões já existem (TICKET-07).
- `DatasetsClient.tsx` (listagem) também tem uma métrica hardcoded.

**Problemas identificados**

### A. Conteúdo francês/placeholder que deve ser removido

1. **Secção "Observações preliminares"** (`DatasetDetailClient.tsx`, linhas 64-70):
   - Texto estático sobre "tendências demográficas e económicas" — não vem da API.
   - **Ação**: Remover completamente. A descrição do dataset já é renderizada acima.

2. **Secção "O que é DVF?"** (`DatasetDetailClient.tsx`, linhas 72-85):
   - Texto copiado de um dataset francês (DVF — Données de Valorisation Foncière), traduzido para português.
   - Referências a "Alsácia, Mosela e Mayotte", "Direção Geral das Finanças Públicas" francesa.
   - **Ação**: Remover completamente.

3. **Box "Está à procura do preço de venda de um imóvel ou terreno?"** (`DatasetDetailClient.tsx`, linhas 190-203):
   - Bloco promocional de uma aplicação francesa (DVF) que não existe no portal português.
   - **Ação**: Remover completamente.

### B. Dados hardcoded que devem vir da API

4. **Pill "Rascunho"** (`DatasetDetailClient.tsx`, linha 33):
   - Aparece sempre, independentemente do estado do dataset.
   - **Ação**: Mostrar condicionalmente: `dataset.private` → "Rascunho", `dataset.archived` → "Arquivado", caso contrário não mostrar.

5. **Licença hardcoded** (`DatasetDetailClient.tsx`, linha 124):
   - Texto fixo "Licença Aberta / Licença Aberta versão 2.0" com `href="#"`.
   - **Ação**: Usar `dataset.license` da API para o título e URL da licença.

6. **Métricas de variação hardcoded** (`DatasetDetailClient.tsx`, linhas 145-148, 163-166):
   - Valores fixos `+11.2 mil` e `+37.2 mil` e data "desde julho de 2022".
   - **Ação**: Remover os pills de variação (a API não fornece deltas). Manter apenas os valores reais de `dataset.metrics.views` e `dataset.metrics.downloads`.

7. **Qualidade dos metadados hardcoded a 100%** (`DatasetDetailClient.tsx`, linhas 175-179):
   - `ProgressBar value={100}` fixo.
   - **Ação**: Usar `dataset.quality` da API. Calcular a percentagem com base nos campos preenchidos (description, tags, license, resources, temporal_coverage, frequency, spatial).

8. **"Metadados: 35%" na listagem** (`DatasetsClient.tsx`, linha 188):
   - Todos os cards de dataset mostram 35% fixo.
   - **Ação**: Calcular individualmente por dataset usando `dataset.quality` ou remover se não disponível.

### C. Links não funcionais (href="#")

9. **4 links com `href="#"`** (`DatasetDetailClient.tsx`, linhas 81, 123, 183, 198):
   - "Leia mais" → remover (faz parte do conteúdo francês a eliminar).
   - Licença → usar URL da licença da API.
   - "Saiba mais sobre este indicador" → linkar a documentação real ou remover.
   - "Consulte o aplicativo DVF" → remover (conteúdo francês).

### D. Tabs com placeholder

10. **Tab "Reutilizações e APIs"** (`DatasetTabs.tsx`, linhas 40-42):
    - Texto placeholder "Conteúdo das reutilizações e APIs."
    - **Ação**: Fetch reuses associados ao dataset via API (`fetchReuses` com filtro por dataset).

11. **Tab "Discussões"** (`DatasetTabs.tsx`, linhas 46-50):
    - Contagem hardcoded `(0)` e texto placeholder.
    - **Ação**: Usar `fetchDiscussions(dataset.id)` (já implementado no TICKET-07) para listar discussões e mostrar contagem real.

12. **Tab "Recursos comunitários"** (`DatasetTabs.tsx`, linhas 54-58):
    - Texto placeholder "Recursos da comunidade."
    - **Ação**: Fetch community resources via API.

### E. Favorito não persistido

13. **Estado de favorito local** (`DatasetDetailClient.tsx`, linha 16):
    - `useState(false)` — nunca persiste nem verifica na API.
    - **Ação**: Usar `followDataset()`/`unfollowDataset()` do TICKET-08 para persistir. Verificar estado inicial com `fetchFollowers()` ou endpoint de check.

**O que deve ser feito**

1. **Remover conteúdo francês/placeholder**: Eliminar secções "Observações preliminares", "O que é DVF?", e box DVF (pontos A.1, A.2, A.3).
2. **Corrigir estado de publicação**: Mostrar Pill "Rascunho"/"Arquivado" condicionalmente com base em `dataset.private`/`dataset.archived` (ponto B.4).
3. **Usar licença da API**: Substituir texto e link fixo pela licença real do dataset (ponto B.5).
4. **Corrigir métricas**: Remover deltas falsos, usar apenas valores reais da API; calcular qualidade dos metadados dinamicamente (pontos B.6, B.7, B.8).
5. **Remover links mortos**: Eliminar `href="#"` — usar URLs reais ou remover (ponto C.9).
6. **Popular tabs com dados reais**: Implementar fetch de discussões (já existe), reutilizações e recursos comunitários nos tabs (pontos D.10, D.11, D.12).
7. **Persistir favoritos**: Ligar botão de favoritos às funções follow/unfollow da API (ponto E.13).

**Ficheiros a alterar**

| Ficheiro                                          | Alterações                                              |
| ------------------------------------------------- | ------------------------------------------------------- |
| `src/components/datasets/DatasetDetailClient.tsx` | Remover conteúdo estático, usar dados da API            |
| `src/components/datasets/DatasetTabs.tsx`         | Popular tabs com dados reais                            |
| `src/components/datasets/DatasetsClient.tsx`      | Corrigir métrica hardcoded nos cards                    |
| `src/types/api.ts`                                | Adicionar/verificar tipo `DatasetQuality` se necessário |
| `src/services/api.ts`                             | Adicionar funções em falta (community resources, etc.)  |

**Critérios de Aceitação**

- [ ] Nenhum conteúdo francês ou placeholder estático visível na página.
- [ ] Pill de estado ("Rascunho"/"Arquivado") aparece condicionalmente.
- [ ] Licença exibida vem de `dataset.license`.
- [ ] Métricas (views, downloads) mostram valores reais sem deltas inventados.
- [ ] Qualidade dos metadados calculada dinamicamente.
- [ ] Tab "Discussões" carrega discussões reais via API.
- [ ] Tab "Reutilizações" carrega reutilizações associadas ao dataset.
- [ ] Nenhum link `href="#"` restante na página.
- [ ] Botão favoritos persiste estado via API.
- [ ] "Metadados: 35%" na listagem corrigido ou removido.

## TICKET-41: Legacy Account Migration to CMD/eIDAS ✅✅

**Descrição**
Migrar utilizadores legados (email/password) para CMD (Chave Móvel Digital) ou eIDAS como único método de autenticação, sem perda de dados. Inclui wizard de migração, bloqueio de login legado, remoção da página de registo, e criação automática de conta via SAML.

**Contexto Arquitetural**

- Depende de TICKET-37 (autenticação SAML já implementada).
- Abordagem MERGE: manter o utilizador existente, adicionar NIC a `extras`, anular `password` → todos os `ReferenceField` (datasets, orgs, reuses, discussions, follows) mantêm-se válidos.
- Plano detalhado em `docs/ticket-37-legacy-account-migration-cmd.md`.

**Fluxos implementados**

- **Fluxo A — Migração via CMD/eIDAS**: utilizador autentica-se via SAML → backend deteta conta legada (password + sem NIC) → redirect para wizard de migração → confirmação visual → verificação por código ou password → merge.
- **Fluxo B — Bloqueio de login legado**: utilizador legado faz login por email/password → route handler verifica migração pendente → faz logout → mostra aviso de migração obrigatória com botões CMD e eIDAS.
- **Criação de conta**: CMD/eIDAS → SAML → backend não encontra utilizador → cria automaticamente. Sem página de registo separada.

**O que foi feito**

### Backend (`udata/auth/saml/saml_plugin/saml_govpt.py`)

1. **`_find_or_create_saml_user()`** — retorna tuple `(user, status)`: `"existing_saml"`, `"migration_candidate"`, `"new"`, `"error"`.
2. **`idp_initiated()` + `idp_eidas_initiated()`** — detetam candidatos a migração e redirecionam para wizard.
3. **Helpers**: `_handle_migration_redirect()`, `_mask_email()`, `_send_migration_code()`, `_find_legacy_user()`.
4. **Endpoints de migração** (`/saml/migration/*`):
   - `GET /check` — verifica se utilizador autenticado precisa de migração.
   - `GET /pending` — estado da migração (email mascarado, nome, apelido).
   - `POST /search` — procura conta legada por email ou nome.
   - `POST /send-code` — gera e envia código de 6 dígitos (10 min expiração, máx 5 tentativas, máx 3 envios).
   - `POST /confirm` — verifica código ou password, faz merge (`password = None`, adiciona NIC), login.
   - `POST /skip` — cria conta nova sem migrar.

### Frontend

5. **Wizard de migração** (`MigrateAccountClient.tsx`):
   - Step 1: Deteção → Step 2: Pesquisa manual (se sem email) → Step 3: Confirmação visual (nome + email mascarado) → Step 4: Escolha de método → Step 5: Verificação (código ou password) → Step 6: Sucesso.
6. **Bloqueio de login legado** (`login/route.ts`): após login, chama `/saml/migration/check`; se legado, faz logout e devolve 403.
7. **LoginClient.tsx**: tabs CMD/eIDAS com "conta criada automaticamente"; tab legada com aviso de migração e botões "Migrar com CMD" / "Migrar com eIDAS".
8. **Remoção da página de registo**: `RegisterClient.tsx`, `LoginRegisterClient.tsx`, `register/route.ts` removidos; `/pages/register` e `/pages/loginregister` → redirect para `/pages/login`; `register()` removida de `api.ts`; Header atualizado.
9. **Rewrites**: `/saml/migration/:path*` → backend.
10. **Funções API**: `fetchMigrationPending()`, `searchMigrationAccount()`, `sendMigrationCode()`, `confirmMigration()`, `skipMigration()`.

**Ficheiros criados**

| Ficheiro                                                 | Descrição                     |
| -------------------------------------------------------- | ----------------------------- |
| `frontend/src/app/pages/migrate-account/page.tsx`        | Rota da página de migração    |
| `frontend/src/components/login/MigrateAccountClient.tsx` | Wizard de migração multi-step |

**Ficheiros removidos**

| Ficheiro                                                | Motivo                               |
| ------------------------------------------------------- | ------------------------------------ |
| `frontend/src/components/login/RegisterClient.tsx`      | Registo por email/password eliminado |
| `frontend/src/components/login/LoginRegisterClient.tsx` | Duplicado — redirecionado para login |
| `frontend/src/app/register/route.ts`                    | Proxy de registo desnecessário       |

**Ficheiros modificados**

| Ficheiro                                            | Alterações                                                                                                             |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `backend/udata/auth/saml/saml_plugin/saml_govpt.py` | `_find_or_create_saml_user()` → tuple; redirect migração em ambos os callbacks; endpoints `/saml/migration/*`; helpers |
| `frontend/next.config.ts`                           | Rewrite `/saml/migration/:path*`                                                                                       |
| `frontend/src/app/login/route.ts`                   | Interceção login legado: `/saml/migration/check` → logout → 403                                                        |
| `frontend/src/services/api.ts`                      | 5 funções de migração; `register()` removida                                                                           |
| `frontend/src/components/login/LoginClient.tsx`     | Mensagem "criar conta automaticamente"; estado `migrationRequired` com aviso e botões CMD/eIDAS                        |
| `frontend/src/components/Header.tsx`                | `/pages/loginregister` → `/pages/login`                                                                                |
| `frontend/src/app/pages/register/page.tsx`          | Redirect para `/pages/login`                                                                                           |
| `frontend/src/app/pages/loginregister/page.tsx`     | Redirect para `/pages/login`                                                                                           |

**Dependências**

- Depende de: TICKET-37 (SAML/CMD/eIDAS), TICKET-01 (login básico), TICKET-03 (AuthContext).

**Critérios de Aceitação**

- [x] Utilizador legado (password + sem NIC) detetado como candidato a migração ao autenticar via CMD/eIDAS.
- [x] Wizard de migração com confirmação visual (nome + email mascarado) e verificação por código ou password.
- [x] Código de verificação: 6 dígitos, expiração 10 min, máx 5 tentativas, máx 3 envios.
- [x] Após migração: `extras.auth_nic` definido, `password = None`, dados (datasets, orgs, reuses) mantidos.
- [x] Login legado bloqueado para utilizadores não migrados — aviso com botões CMD e eIDAS.
- [x] Após migração: login por email/password falha permanentemente.
- [x] Re-login via CMD/eIDAS funciona diretamente sem wizard.
- [x] Fallback sem email: pesquisa manual por email ou nome → mesmo fluxo.
- [x] Página de registo eliminada — `/pages/register` e `/pages/loginregister` redirecionam para `/pages/login`.
- [x] Tabs CMD e eIDAS informam que conta é criada automaticamente.
- [x] Utilizador novo criado automaticamente ao autenticar via CMD/eIDAS sem conta existente.
- [x] Endpoints de migração: `/saml/migration/check`, `/pending`, `/search`, `/send-code`, `/confirm`, `/skip`.
- [x] Rewrite `/saml/migration/:path*` configurado no `next.config.ts`.
- [x] `npm run lint` sem novos erros.

---

# BACKOFFICE / ADMIN — Tickets

> Based on the original project [datagouv/cdata](https://github.com/datagouv/cdata/tree/main/pages/admin) (Vue.js/Nuxt), adapted for our React/Next.js stack.
> Focus: **lógica de conexão** — tipos TypeScript, funções fetch/mutate em `services/api.ts`, endpoints backend, e fluxo de dados. O layout/UI não faz parte destes tickets.

---

## TICKET-26: Admin — Datasets CRUD (Conexões API) ✅

**Descrição**
Implementar toda a camada de conexão (tipos TS + funções API) necessária para as páginas admin de datasets: listagem pessoal, criação, edição, eliminação, e gestão de resources.

**Contexto Arquitetural**

- Ref. original: `pages/admin/me/datasets.vue`, `pages/admin/datasets/new.vue`, `pages/admin/datasets/[id].vue`, `pages/admin/datasets/structured.vue`.
- O fluxo de criação no original é um wizard de 4 steps: (1) tipo de publicação, (2) metadados, (3) upload de resources, (4) publicação (toggle private→public).
- O fluxo de edição tem 4 tabs: Metadata, Resources, Discussions, Activities.
- Backend endpoints necessários:
  - `GET /api/1/me/datasets/` — datasets do utilizador autenticado.
  - `GET /api/1/me/org_datasets/` — datasets das organizações do utilizador.
  - `POST /api/1/datasets/` — criar dataset (body: title, description, tags, license, frequency, temporal_coverage, spatial, organization, private).
  - `PUT /api/1/datasets/<id>/` — atualizar dataset.
  - `DELETE /api/1/datasets/<id>/` — eliminar dataset.
  - `GET /api/2/datasets/<id>/` — detalhes do dataset (v2, inclui extras e quality score).
  - `POST /api/1/datasets/<id>/resources/` — criar resource (body: title, type, url, filetype, format, description).
  - `POST /api/1/datasets/<id>/upload/` — upload de ficheiro (multipart/form-data).
  - `PUT /api/1/datasets/<id>/resources/<rid>/` — atualizar resource.
  - `DELETE /api/1/datasets/<id>/resources/<rid>/` — eliminar resource.
  - `PUT /api/1/datasets/<id>/resources/` — reordenar resources (body: array de resource IDs).
  - `POST /api/1/datasets/<id>/featured/` — marcar como destaque (admin).
  - `DELETE /api/1/datasets/<id>/featured/` — remover destaque (admin).
  - `GET /api/1/activity/?related_to=<id>&sort=-created_at` — log de atividade.
  - Endpoints auxiliares para dropdowns:
    - `GET /api/1/datasets/licenses/` — lista de licenças.
    - `GET /api/1/datasets/frequencies/` — frequências de atualização.
    - `GET /api/1/datasets/schemas/` — schemas disponíveis.
    - `GET /api/1/datasets/resource_types/` — tipos de resource.
    - `GET /api/1/datasets/extensions/` — extensões de ficheiro permitidas.

**O que foi feito**

1. **Tipos TS** em `types/api.ts`:
   - `Dataset` estendido com: `acronym`, `private`, `featured`, `archived`, `frequency`, `frequency_date`, `temporal_coverage`, `spatial`, `quality`, `badges[]`, `owner`, `uri`, `permissions`, `description_short`, `schema`, `harvest`, `extras`, `community_resources`, `deleted`, `last_update`.
   - `Resource` estendido com: `description`, `filetype`, `mime`, `checksum`, `last_modified`, `schema`, `extras`, `preview_url`, `latest`.
   - Payloads criados: `DatasetCreatePayload`, `DatasetUpdatePayload`, `ResourceCreatePayload`, `ResourceUpdatePayload`.
   - Tipos auxiliares: `SchemaRef`, `TemporalCoverage`, `SpatialCoverage`, `Checksum`, `DatasetPermissions`, `ResourceType`, `Activity`.
   - `License`, `Frequency`, `Badge`, `DatasetBadges` — já existiam.
2. **Funções em `services/api.ts`**:
   - Leitura: `fetchMyDatasets()` (flat array → APIResponse wrapper, filtra datasets pessoais), `fetchMyOrgDatasets()`, `fetchLicenses()`, `fetchFrequencies()`, `fetchSchemas()`, `fetchDatasetBadges()`, `fetchResourceTypes()`, `fetchActivity()`.
   - Mutações: `createDataset()`, `updateDataset()`, `deleteDataset()`, `uploadResource()` (multipart), `createResource()`, `updateResource()`, `deleteResource()`, `reorderResources()`, `toggleDatasetFeatured()`.
   - Erros de validação do backend retornados como objetos estruturados.
3. **Wizard de criação** (`DatasetsAdminClient.tsx`) integrado com API:
   - Step 2: POST `createDataset()` com `private: true` + metadados → dataset pessoal (owner = current user, sem organization).
   - Step 3: Upload ficheiros via `uploadResource()` (multipart/form-data).
   - Step 4: "Publicar" → `updateDataset(private: false)`; "Salvar rascunho" → redirige para listagem.
   - Dropdowns de licenças e frequências carregados da API.
   - Loading states e erros de validação exibidos.
4. **Página de edição** (`app/pages/admin/me/datasets/edit/page.tsx` + `DatasetsEditClient.tsx`):
   - 4 tabs via Agora `Tabs` component: Metadados, Ficheiros, Discussões, Atividades.
   - Tab Metadados: edição de título, acrónimo, descrição, licença, frequência, cobertura temporal + botão eliminar.
   - Tab Ficheiros: listagem de resources com upload e delete.
   - Tab Atividades: lazy-load de `fetchActivity()`.
   - Erros de validação do backend exibidos.
5. **Listagem admin** (`DatasetsClient.tsx` + `SystemDatasetsClient.tsx`):
   - Mock data removido, dados reais da API.
   - Pesquisa client-side por título, acrónimo e slug.
   - Filtro por estado: Público, Rascunho, Arquivo, Excluído.
   - Ordenação controlada por: título (string), criado em (date), última modificação (date), ficheiros (numeric).
   - Paginação client-side com `onPageChange` / `onPageSizeChange`.
   - `DatasetsClient` filtra apenas datasets pessoais (`owner` presente, `organization` ausente).
   - `SystemDatasetsClient` mostra todos os datasets do sistema.

**Critérios de Aceitação**

- [x] `fetchMyDatasets()` retorna a lista paginada do utilizador.
- [x] Funções auxiliares (licenses, frequencies, schemas) retornam dados corretos.
- [x] Todos os tipos TS estão definidos e espelham os campos do backend (Dataset extensions, payloads, Schema, Activity).
- [x] Todas as funções fetch/mutate estão em `services/api.ts` e funcionam.
- [x] `createDataset()` envia o payload correto e retorna o dataset criado.
- [x] Upload de ficheiros funciona com `multipart/form-data`.
- [x] `updateDataset()` e `deleteDataset()` funcionam.
- [x] Resource CRUD (create, update, delete, reorder) funciona.
- [x] Listagem admin usa dados reais da API (mock data removido).
- [x] Wizard de criação integrado com API (POST dataset → upload resources → publicar).
- [x] Página de edição de dataset implementada e funcional.
- [x] Erros de validação do backend são retornados em formato utilizável pelo frontend.

---

## TICKET-27: Admin — Reuses CRUD (Conexões API) ✅✅

**Descrição**
Implementar a camada de conexão para as páginas admin de reuses: listagem pessoal, criação, edição, eliminação, e gestão de datasets/dataservices associados.

**Contexto Arquitetural**

- Ref. original: `pages/admin/me/reuses.vue`, `pages/admin/reuses/new.vue`, `pages/admin/reuses/[id].vue`.
- Criação no original é um wizard de 3 steps: (1) descrever reuse, (2) associar datasets/dataservices, (3) publicar.
- Backend endpoints necessários:
  - `GET /api/1/me/reuses/` — reuses do utilizador.
  - `POST /api/1/reuses/` — criar reuse (body: title, description, url, type, topic, tags, organization, private).
  - `PUT /api/1/reuses/<id>/` — atualizar reuse.
  - `DELETE /api/1/reuses/<id>/` — eliminar reuse.
  - `POST /api/1/reuses/<id>/image/` — upload de imagem (multipart/form-data).
  - `POST /api/1/reuses/<id>/datasets/` — associar dataset.
  - `POST /api/1/reuses/<id>/dataservices/` — associar dataservice.
  - `GET /api/1/reuses/types/` — tipos de reuse disponíveis.
  - `GET /api/1/reuses/topics/` — tópicos de reuse.
  - `POST /api/1/reuses/<id>/featured/` — marcar como destaque.
  - `DELETE /api/1/reuses/<id>/featured/` — remover destaque.

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - Estender `Reuse` com: `private`, `featured`, `archived`, `topic`, `owner`, `datasets[]`, `dataservices[]`.
   - Criar `ReuseCreatePayload`, `ReuseUpdatePayload`.
   - Criar `ReuseType`, `ReuseTopic` types.
2. **Funções em `services/api.ts`**:
   - `fetchMyReuses(page?, pageSize?)` → `GET /api/1/me/reuses/`
   - `createReuse(payload)` → `POST /api/1/reuses/`
   - `updateReuse(id, payload)` → `PUT /api/1/reuses/<id>/`
   - `deleteReuse(id)` → `DELETE /api/1/reuses/<id>/`
   - `uploadReuseImage(id, file)` → `POST /api/1/reuses/<id>/image/` (multipart)
   - `linkDatasetToReuse(reuseId, datasetId)` → `POST /api/1/reuses/<id>/datasets/`
   - `linkDataserviceToReuse(reuseId, dataserviceId)` → `POST /api/1/reuses/<id>/dataservices/`
   - `fetchReuseTypes()` → `GET /api/1/reuses/types/`
   - `fetchReuseTopics()` → `GET /api/1/reuses/topics/`
3. **Fluxo de criação**:
   - Step 1: POST reuse com `private: true` → backend retorna reuse com `id`.
   - Step 1.5: POST image (se fornecida).
   - Step 2: POST datasets e dataservices associados.
   - Step 3: PUT reuse com `private: false` para publicar.

**Critérios de Aceitação**

- [x] Tipos TS espelham os campos do backend.
- [x] `fetchMyReuses()` retorna lista paginada.
- [x] `createReuse()` + `uploadReuseImage()` + `linkDatasetToReuse()` funcionam em sequência.
- [x] `updateReuse()` e `deleteReuse()` funcionam.
- [x] Tipos e tópicos de reuse são carregados do backend.
- [x] Erros de validação são retornados em formato utilizável.

---

## TICKET-28: Admin — Dataservices CRUD (Conexões API) ✅✅

**Descrição**
Implementar a camada de conexão para dataservices: listagem, criação (wiring do form existente `ApiRegistrationClient.tsx`), edição e eliminação.

**Contexto Arquitetural**

- Ref. original: `pages/admin/me/dataservices.vue`, `pages/admin/dataservices/new.vue`, `pages/admin/dataservices/[id].vue`.
- O frontend já tem `ApiRegistrationClient.tsx` com UI completa mas sem submissão ao backend.
- Backend endpoints necessários:
  - `GET /api/1/dataservices/` — listar (filtros: owner, organization).
  - `POST /api/1/dataservices/` — criar (body: title, description, base_api_url, endpoint_description_url, authorization_request_url, rate_limiting, availability, organization, access_type).
  - `GET /api/1/dataservices/<id>/` — detalhes.
  - `PUT /api/1/dataservices/<id>/` — atualizar.
  - `DELETE /api/1/dataservices/<id>/` — eliminar.
  - `GET /api/1/dataservices/<id>/followers/` — seguidores.
  - `POST /api/1/dataservices/<id>/followers/` — seguir.
  - `DELETE /api/1/dataservices/<id>/followers/` — deixar de seguir.

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - Criar `Dataservice`: id, title, description, base_api_url, endpoint_description_url, authorization_request_url, rate_limiting, availability, access_type, organization, created_at, last_modified, metrics, archived.
   - Criar `DataserviceCreatePayload`, `DataserviceUpdatePayload`.
2. **Funções em `services/api.ts`**:
   - `fetchMyDataservices(page?, pageSize?)` → `GET /api/1/dataservices/?owner=me`
   - `fetchDataservice(id)` → `GET /api/1/dataservices/<id>/`
   - `createDataservice(payload)` → `POST /api/1/dataservices/`
   - `updateDataservice(id, payload)` → `PUT /api/1/dataservices/<id>/`
   - `deleteDataservice(id)` → `DELETE /api/1/dataservices/<id>/`
3. **Wiring do form existente**:
   - Mapear os campos do `ApiRegistrationClient.tsx` para `DataserviceCreatePayload`.
   - No submit, chamar `createDataservice()`.

**Critérios de Aceitação**

- [x] Tipo `Dataservice` definido em `types/api.ts`.
- [x] Todas as funções CRUD estão em `services/api.ts`.
- [x] O form existente (`ApiRegistrationClient.tsx`) submete ao backend.
- [x] Erros de validação são retornados e utilizáveis.

---

## TICKET-29: Admin — Organizations CRUD (Conexões API) ✅✅

**Descrição**
Implementar a camada de conexão para organizações no admin: criação, edição, eliminação, logo upload, e gestão de membros.

> **Nota:** As páginas de conteúdo da organização (`org/dataservices`, `org/reuses`, `org/harvesters`, `org/community-resources`, `org/profile`, `org/statistics`) estão cobertas pelo **TICKET-41**.

**Contexto Arquitetural**

- Ref. original: `pages/admin/organizations/new.vue`, `pages/admin/organizations/[oid].vue`.
- Criação no original é wizard de 3 steps: (1) criar ou juntar-se, (2) detalhes, (3) finalizar.
- Backend endpoints necessários:
  - `POST /api/1/organizations/` — criar (body: name, acronym, description, url, business_number_id).
  - `PUT /api/1/organizations/<org>/` — atualizar.
  - `DELETE /api/1/organizations/<org>/` — eliminar.
  - `POST /api/1/organizations/<org>/logo/` — upload logo (multipart/form-data).
  - `PUT /api/1/organizations/<org>/logo/` — atualizar crop do logo.
  - `GET /api/1/organizations/<org>/membership/` — pedidos de adesão pendentes.
  - `POST /api/1/organizations/<org>/membership/` — pedir adesão.
  - `POST /api/1/organizations/<org>/membership/<id>/accept/` — aceitar.
  - `POST /api/1/organizations/<org>/membership/<id>/refuse/` — recusar.
  - `POST /api/1/organizations/<org>/member/<user>/` — adicionar membro.
  - `PUT /api/1/organizations/<org>/member/<user>/` — atualizar role.
  - `DELETE /api/1/organizations/<org>/member/<user>/` — remover membro.
  - `GET /api/1/organizations/<org>/datasets/` — datasets da organização.
  - `GET /api/1/organizations/<org>/reuses/` — reuses da organização.
  - `GET /api/1/organizations/<org>/contacts/` — contact points.
  - `GET /api/1/organizations/roles/` — roles disponíveis.
  - `GET /api/1/organizations/suggest/?q=` — autocomplete de organizações.

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - Estender `Organization` com: `description`, `url`, `business_number_id`, `members[]`, `badges[]`, `metrics`, `created_at`.
   - Criar `OrganizationCreatePayload`, `OrganizationUpdatePayload`.
   - Criar `Member` (user, role), `MembershipRequest` (id, user, status, created).
   - Criar `OrgRole` type.
2. **Funções em `services/api.ts`**:
   - `createOrganization(payload)` → `POST /api/1/organizations/`
   - `updateOrganization(org, payload)` → `PUT /api/1/organizations/<org>/`
   - `deleteOrganization(org)` → `DELETE /api/1/organizations/<org>/`
   - `uploadOrgLogo(org, file)` → `POST /api/1/organizations/<org>/logo/`
   - `fetchMembershipRequests(org)` → `GET /api/1/organizations/<org>/membership/`
   - `requestMembership(org)` → `POST /api/1/organizations/<org>/membership/`
   - `acceptMembership(org, requestId)` → `POST /api/1/organizations/<org>/membership/<id>/accept/`
   - `refuseMembership(org, requestId)` → `POST /api/1/organizations/<org>/membership/<id>/refuse/`
   - `addMember(org, userId, role)` → `POST /api/1/organizations/<org>/member/<user>/`
   - `updateMemberRole(org, userId, role)` → `PUT /api/1/organizations/<org>/member/<user>/`
   - `removeMember(org, userId)` → `DELETE /api/1/organizations/<org>/member/<user>/`
   - `fetchOrgDatasets(org, page?)` → `GET /api/1/organizations/<org>/datasets/`
   - `fetchOrgReuses(org, page?)` → `GET /api/1/organizations/<org>/reuses/`
   - `fetchOrgRoles()` → `GET /api/1/organizations/roles/`
   - `suggestOrganizations(query)` → `GET /api/1/organizations/suggest/?q=`

**Critérios de Aceitação**

- [x] Tipos completos para Organization, Member, MembershipRequest.
- [x] CRUD de organização funciona (create, update, delete).
- [x] Upload de logo funciona com multipart.
- [x] Gestão de membros: add, update role, remove, accept/refuse request.
- [x] Autocomplete de organizações funciona.

---

## TICKET-30: Admin — User Profile & Metrics (Conexões API) ✅✅

**Descrição**
Implementar a camada de conexão para o perfil do utilizador autenticado: edição de perfil, upload de avatar, invitations de organizações, eliminação de conta, e métricas pessoais.

> **Nota:** A extensão do `AuthContext` com `roles[]` e `organizations[]` está coberta pelo **TICKET-43** (Permission Guards).

**Contexto Arquitetural**

- Ref. original: `pages/admin/me/profile.vue`, `pages/admin/me/metrics.vue`.
- Backend endpoints necessários:
  - `GET /api/1/me/` — perfil atual (já existe `fetchCurrentUser` do TICKET-03).
  - `PUT /api/1/me/` — atualizar perfil (body: first_name, last_name, about, website).
  - `POST /api/1/me/avatar/` — upload avatar (multipart/form-data).
  - `DELETE /api/1/me/` — eliminar conta.
  - `GET /api/1/me/org_invitations/` — convites de organizações pendentes.
  - `GET /api/1/me/metrics/` — métricas agregadas do utilizador.
  - `GET /api/1/activity/?owner=<userId>` — atividade do utilizador.

**O que foi feito**

1. **Tipos TS** em `types/api.ts`:
   - `UserPublic` estendido com `apikey: string | null`.
   - `UserMetrics` estendido com `downloads: number`.
   - Criado `UserUpdatePayload`: first_name, last_name, about, website (todos opcionais).
   - Criado `OrgInvitation`: id, organization, status (pending|accepted|refused), created.
2. **Funções em `services/api.ts`**:
   - `updateProfile(payload)` → `PUT /api/1/me/` — envia JSON, retorna `UserPublic`.
   - `uploadAvatar(file)` → `POST /api/1/me/avatar` — multipart/form-data, retorna `UserPublic`.
   - `deleteAccount()` → `DELETE /api/1/me/` — sem retorno (void).
   - `fetchOrgInvitations(page?, pageSize?)` → `GET /api/1/me/org_invitations/` — retorna `APIResponse<OrgInvitation>`.
   - `fetchMyMetrics()` → `GET /api/1/me/metrics/` — retorna `UserMetrics`.
   - `fetchUserActivity(userId?, page?, pageSize?)` → `GET /api/1/activity/?owner=<id>` — retorna `APIResponse<Activity>`.

**Critérios de Aceitação**

- [x] `updateProfile()` envia os campos corretos e retorna user atualizado.
- [x] `uploadAvatar()` funciona com multipart.
- [x] `deleteAccount()` funciona e retorna confirmação.
- [x] `fetchOrgInvitations()` retorna lista de convites.
- [x] `fetchMyMetrics()` retorna métricas agregadas.
- [x] Tipos TS espelham as respostas da API.

---

## TICKET-31: Admin — Community Resources CRUD (Conexões API) ✅✅

**Descrição**
Implementar a camada de conexão para community resources: listagem pessoal, criação, edição, eliminação.

**Contexto Arquitetural**

- Ref. original: `pages/admin/me/community-resources.vue`, `pages/admin/community-resources/new.vue`.
- Backend endpoints necessários:
  - `GET /api/1/datasets/community_resources/` — listar (filtros: owner, organization, dataset).
  - `POST /api/1/datasets/community_resources/` — criar (body: title, description, url, filetype, format, dataset).
  - `GET /api/1/datasets/community_resources/<id>/` — detalhes.
  - `PUT /api/1/datasets/community_resources/<id>/` — atualizar.
  - `DELETE /api/1/datasets/community_resources/<id>/` — eliminar.
  - `POST /api/1/datasets/community_resources/<id>/upload/` — upload ficheiro (multipart).
  - `GET /api/1/me/org_community_resources/` — community resources das organizações do utilizador.

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - Criar `CommunityResource`: id, title, description, url, filetype, format, dataset (ref), organization, owner, created_at, last_modified.
   - Criar `CommunityResourceCreatePayload`, `CommunityResourceUpdatePayload`.
2. **Funções em `services/api.ts`**:
   - `fetchMyCommunityResources(page?)` → `GET /api/1/datasets/community_resources/?owner=me`
   - `fetchMyOrgCommunityResources(page?)` → `GET /api/1/me/org_community_resources/`
   - `createCommunityResource(payload)` → `POST /api/1/datasets/community_resources/`
   - `updateCommunityResource(id, payload)` → `PUT /api/1/datasets/community_resources/<id>/`
   - `deleteCommunityResource(id)` → `DELETE /api/1/datasets/community_resources/<id>/`
   - `uploadCommunityResourceFile(id, file)` → `POST /api/1/datasets/community_resources/<id>/upload/`

**Critérios de Aceitação**

- [x] Tipo `CommunityResource` definido.
- [x] CRUD completo funciona.
- [x] Upload de ficheiro funciona com multipart.
- [x] Associação a dataset específico funciona.

---

## TICKET-32: Admin — Harvesters CRUD (Conexões API) ✅✅

**Descrição**
Implementar a camada de conexão para harvesters: listagem, criação, edição, eliminação, trigger de jobs, e consulta de job history.

**Contexto Arquitetural**

- Ref. original: `pages/admin/harvesters/new.vue`, `pages/admin/harvesters/[id].vue`.
- Criação no original é wizard de 3 steps: (1) descrever, (2) preview, (3) finalizar.
- Backend endpoints necessários:
  - `GET /api/1/harvest/sources/` — listar harvest sources.
  - `POST /api/1/harvest/sources/` — criar (body: name, description, url, backend, organization, schedule, config, filters, features, active, autoarchive).
  - `GET /api/1/harvest/sources/<id>/` — detalhes.
  - `PUT /api/1/harvest/sources/<id>/` — atualizar.
  - `DELETE /api/1/harvest/sources/<id>/` — eliminar.
  - `POST /api/1/harvest/sources/<id>/jobs/` — disparar harvest job.
  - `GET /api/1/harvest/sources/<id>/jobs/` — listar jobs do source.
  - `GET /api/1/harvest/sources/<id>/jobs/<job>/` — detalhes de um job.
  - `GET /api/1/harvest/sources/<id>/validation/` — validar source.

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - Criar `HarvestSource`: id, name, description, url, backend, organization, schedule, config, filters, features, active, autoarchive, created_at, last_modified, last_job.
   - Criar `HarvestJob`: id, status (pending, started, done, failed), started, ended, errors, items.
   - Criar `HarvestSourceCreatePayload`, `HarvestSourceUpdatePayload`.
2. **Funções em `services/api.ts`**:
   - `fetchHarvesters(page?)` → `GET /api/1/harvest/sources/`
   - `fetchHarvester(id)` → `GET /api/1/harvest/sources/<id>/`
   - `createHarvester(payload)` → `POST /api/1/harvest/sources/`
   - `updateHarvester(id, payload)` → `PUT /api/1/harvest/sources/<id>/`
   - `deleteHarvester(id)` → `DELETE /api/1/harvest/sources/<id>/`
   - `triggerHarvest(id)` → `POST /api/1/harvest/sources/<id>/jobs/`
   - `fetchHarvestJobs(sourceId, page?)` → `GET /api/1/harvest/sources/<id>/jobs/`
   - `validateHarvestSource(id)` → `GET /api/1/harvest/sources/<id>/validation/`

**Critérios de Aceitação**

- [x] Tipos `HarvestSource` e `HarvestJob` definidos.
- [x] CRUD de harvesters funciona.
- [x] Trigger de job retorna o job criado.
- [x] Listagem de jobs mostra status e erros.
- [x] Validação de source funciona.

---

## TICKET-33: Admin — Topics CRUD (Conexões API v2) ✅✅

**Descrição**
Implementar a camada de conexão para topics (themes) usando a API v2: listagem, criação, edição, eliminação, e gestão de elementos (datasets/reuses associados).

**Contexto Arquitetural**

- Ref. original: `pages/admin/topics/[id].vue`.
- Backend endpoints (API v2, base em `NEXT_PUBLIC_API_V2_BASE`):
  - `GET /api/2/topics/` — listar topics.
  - `POST /api/2/topics/` — criar topic (body: name, description, tags, featured, private).
  - `GET /api/2/topics/<id>/` — detalhes.
  - `PUT /api/2/topics/<id>/` — atualizar.
  - `DELETE /api/2/topics/<id>/` — eliminar.
  - `GET /api/2/topics/<id>/elements/` — listar elementos (datasets/reuses associados).
  - `POST /api/2/topics/<id>/elements/` — adicionar elemento.
  - `PUT /api/2/topics/<id>/elements/` — atualizar ordem de elementos.
  - `DELETE /api/2/topics/<id>/elements/<eid>/` — remover elemento.

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - Criar `Topic`: id, name, slug, description, tags[], featured, private, created_at, last_modified, datasets_count, reuses_count.
   - Criar `TopicElement`: id, type (dataset|reuse), content (ref to Dataset|Reuse), position.
   - Criar `TopicCreatePayload`, `TopicUpdatePayload`.
2. **Funções em `services/api.ts`** (usando v2 base):
   - `fetchTopics(page?)` → `GET /api/2/topics/`
   - `fetchTopic(id)` → `GET /api/2/topics/<id>/`
   - `createTopic(payload)` → `POST /api/2/topics/`
   - `updateTopic(id, payload)` → `PUT /api/2/topics/<id>/`
   - `deleteTopic(id)` → `DELETE /api/2/topics/<id>/`
   - `fetchTopicElements(topicId)` → `GET /api/2/topics/<id>/elements/`
   - `addTopicElement(topicId, payload)` → `POST /api/2/topics/<id>/elements/`
   - `removeTopicElement(topicId, elementId)` → `DELETE /api/2/topics/<id>/elements/<eid>/`

**Critérios de Aceitação**

- [x] Funções usam `NEXT_PUBLIC_API_V2_BASE` como base URL.
- [x] CRUD de topics funciona.
- [x] Gestão de elementos (add/remove datasets e reuses) funciona.
- [x] Tipos TS definidos e consistentes.

---

## TICKET-34: Admin — Posts CRUD (Conexões API) ✅✅

**Descrição**
Implementar a camada de conexão para posts/notícias: listagem, criação, edição, eliminação, e upload de imagens.

**Contexto Arquitetural**

- Ref. original: `pages/admin/posts/new.vue`, `pages/admin/posts/[id].vue`.
- O original suporta dois tipos de conteúdo: markdown e "blocs" (page builder). Para a nossa versão, focar em markdown.
- Backend endpoints necessários:
  - `GET /api/1/posts/` — listar posts.
  - `POST /api/1/posts/` — criar post (body: name, headline, content, body_type, kind, published, owner, tags, credit_to, credit_url).
  - `GET /api/1/posts/<id>/` — detalhes.
  - `PUT /api/1/posts/<id>/` — atualizar.
  - `DELETE /api/1/posts/<id>/` — eliminar.
  - `POST /api/1/posts/<id>/image/` — upload imagem (multipart/form-data).

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - Criar `Post`: id, name, slug, headline, content, body_type, kind, published, owner, tags[], image, credit_to, credit_url, created_at, last_modified.
   - Criar `PostCreatePayload`, `PostUpdatePayload`.
2. **Funções em `services/api.ts`**:
   - `fetchPosts(page?, pageSize?)` → `GET /api/1/posts/`
   - `fetchPost(idOrSlug)` → `GET /api/1/posts/<id>/`
   - `createPost(payload)` → `POST /api/1/posts/`
   - `updatePost(id, payload)` → `PUT /api/1/posts/<id>/`
   - `deletePost(id)` → `DELETE /api/1/posts/<id>/`
   - `uploadPostImage(id, file)` → `POST /api/1/posts/<id>/image/` (multipart)

**Critérios de Aceitação**

- [x] Tipo `Post` definido com todos os campos.
- [x] CRUD completo funciona.
- [x] Upload de imagem funciona com multipart.
- [x] Posts podem ser criados como draft (`published: false`) e publicados depois.

---

## TICKET-35: Admin — User Management (Conexões API — Sysadmin) ✅✅

**Descrição**
Implementar a camada de conexão para gestão de utilizadores por sysadmins: listagem, consulta de detalhes, edição de roles, e eliminação.

**Contexto Arquitetural**

- Ref. original: `pages/admin/users/[uid].vue`.
- Backend endpoints necessários:
  - `GET /api/1/users/` — listar todos os utilizadores (paginado, filtros: q, sort).
  - `GET /api/1/users/<id>/` — detalhes de um utilizador.
  - `PUT /api/1/users/<id>/` — atualizar (sysadmin pode alterar roles, active).
  - `DELETE /api/1/users/<id>/` — eliminar utilizador.
  - `GET /api/1/users/roles/` — lista de roles disponíveis.
  - `GET /api/1/users/suggest/?q=` — autocomplete de utilizadores.

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - Criar `UserAdmin` (extends User): roles[], active, datasets_count, reuses_count, last_login.
   - Criar `UserRole` type.
2. **Funções em `services/api.ts`**:
   - `fetchUsers(page?, q?, sort?)` → `GET /api/1/users/`
   - `fetchUser(id)` → `GET /api/1/users/<id>/`
   - `updateUser(id, payload)` → `PUT /api/1/users/<id>/`
   - `deleteUser(id)` → `DELETE /api/1/users/<id>/`
   - `fetchUserRoles()` → `GET /api/1/users/roles/`
   - `suggestUsers(query)` → `GET /api/1/users/suggest/?q=`

**Critérios de Aceitação**

- [x] Listagem de utilizadores paginada com pesquisa.
- [x] Detalhes de utilizador incluem roles e content counts.
- [x] Atualização de roles funciona.
- [x] Eliminação funciona.
- [x] Autocomplete funciona.

---

## TICKET-36: Admin — Site Management & Moderation (Conexões API — Sysadmin) ✅

**Descrição**
Implementar a camada de conexão para gestão global do site e moderação de conteúdo: stats do site, configuração, e gestão de reports.

**Contexto Arquitetural**

- Ref. original: `pages/admin/site/` (10 páginas), incluindo `moderation.vue`.
- Tipos de conteúdo moderáveis: Datasets, Dataservices, Reuses, Organizations, Discussions.
- Ações de moderação: Dismiss, Hide (toggle private), Delete.
- Backend endpoints necessários:
  - `GET /api/1/site/` — info e stats do site (nb_datasets, nb_organizations, nb_reuses, nb_users).
  - `PATCH /api/1/site/` — atualizar configuração do site.
  - `GET /api/1/reports/` — listar reports (filtros: status, page, page_size, sort).
  - `GET /api/1/reports/<id>/` — detalhes do report.
  - `PATCH /api/1/reports/<id>/` — dismiss report (body: status).
  - `GET /api/1/reports/reasons/` — razões de report disponíveis.
  - CSV exports:
    - `GET /api/1/site/datasets.csv`
    - `GET /api/1/site/organizations.csv`
    - `GET /api/1/site/reuses.csv`
    - `GET /api/1/site/tags.csv`
    - `GET /api/1/site/harvest-sources.csv`

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - Criar `SiteInfo`: id, title, metrics (nb_datasets, nb_organizations, nb_reuses, nb_users).
   - Criar `Report`: id, subject (type + id + ref), reporter, reason, message, status, created_at.
   - Criar `ReportReason` type.
2. **Funções em `services/api.ts`**:
   - `fetchSiteInfo()` → `GET /api/1/site/`
   - `updateSiteConfig(payload)` → `PATCH /api/1/site/`
   - `fetchReports(page?, status?, sort?)` → `GET /api/1/reports/`
   - `dismissReport(id)` → `PATCH /api/1/reports/<id>/`
   - `fetchReportReasons()` → `GET /api/1/reports/reasons/`
   - `getSiteExportUrl(type)` → retorna URL para download (`/api/1/site/<type>.csv`)
3. **Fluxo de moderação**:
   - GET reports filtrados por status → mostrar lista.
   - Dismiss: PATCH report com status "handled".
   - Hide: PUT no endpoint da entidade com `private: true` (usa funções CRUD existentes dos tickets anteriores).
   - Delete: DELETE no endpoint da entidade (usa funções CRUD existentes).

**Critérios de Aceitação**

- [x] `fetchSiteInfo()` retorna stats do site.
- [x] `fetchReports()` retorna lista filtrada por status.
- [x] `dismissReport()` altera status do report.
- [x] `fetchReportReasons()` retorna lista de razões.
- [x] URLs de export CSV são geradas corretamente.
- [x] Tipos TS definidos para SiteInfo, Report, ReportReason.

---

## TICKET-42: Admin — Organization Content Pages (Conexões API — `org/*`) ✅

**Descrição**
Implementar as páginas de conteúdo da organização no admin (`/admin/org/`): listagens de dataservices, reuses, harvesters, community resources, perfil da organização e estatísticas — tudo no contexto da organização do utilizador autenticado.

**Contexto Arquitetural**

- Ref. original: `pages/admin/organizations/[oid]/*` (Vue.js/Nuxt).
- A navegação lateral (`AdminSideNavigation.tsx`) já lista 9 items para "Minha organização", mas apenas 3 páginas estão implementadas (`org/datasets`, `org/discussions`, `org/members`).
- A secção "Minha organização" mostra conteúdo filtrado pela organização do utilizador — usa os mesmos endpoints dos tickets de CRUD (27–32) mas com filtro `organization=<org_id>`.
- Depende de: TICKET-29 (Organizations CRUD + Members) para contexto da organização do utilizador.
- Backend endpoints necessários (reutilizados de outros tickets, com filtro por organização):
  - `GET /api/1/organizations/<org>/datasets/` — datasets da organização (TICKET-29).
  - `GET /api/1/organizations/<org>/reuses/` — reuses da organização.
  - `GET /api/1/dataservices/?organization=<org>` — dataservices da organização.
  - `GET /api/1/harvest/sources/?organization=<org>` — harvesters da organização.
  - `GET /api/1/datasets/community_resources/?organization=<org>` — community resources da organização.
  - `GET /api/1/organizations/<org>/` — perfil da organização (para edição).
  - `GET /api/1/organizations/<org>/metrics/` — métricas da organização.
  - `GET /api/1/organizations/<org>/discussions/` — discussões da organização (já implementado).

**O que deve ser feito**

1. **Contexto de organização ativa**:
   - Determinar qual organização do utilizador está ativa (a partir de `AuthContext` → `user.organizations[]`).
   - Se o utilizador pertencer a múltiplas organizações, permitir seleção (dropdown ou similar).
2. **Páginas a implementar** (componentes em `src/components/admin/org/`):
   - `org/dataservices/page.tsx` — listagem de dataservices da org, reutilizando lógica do TICKET-28.
   - `org/reuses/page.tsx` — listagem de reuses da org, reutilizando lógica do TICKET-27.
   - `org/harvesters/page.tsx` — listagem de harvesters da org, reutilizando lógica do TICKET-32.
   - `org/community-resources/page.tsx` — listagem de community resources da org, reutilizando lógica do TICKET-31.
   - `org/profile/page.tsx` — edição do perfil da org (nome, descrição, logo), reutilizando funções do TICKET-29.
   - `org/statistics/page.tsx` — métricas da org (datasets, reuses, followers, views).
3. **Funções em `services/api.ts`** (se não existirem dos tickets anteriores):
   - `fetchOrgReuses(org, page?)` → `GET /api/1/organizations/<org>/reuses/`
   - `fetchOrgDataservices(org, page?)` → `GET /api/1/dataservices/?organization=<org>`
   - `fetchOrgHarvesters(org, page?)` → `GET /api/1/harvest/sources/?organization=<org>`
   - `fetchOrgCommunityResources(org, page?)` → `GET /api/1/datasets/community_resources/?organization=<org>`
   - `fetchOrgMetrics(org)` → `GET /api/1/organizations/<org>/metrics/`

**Critérios de Aceitação**

- [x] Todas as 6 páginas de `org/*` em falta estão implementadas e acessíveis pela navegação lateral.
- [x] Cada página filtra conteúdo pela organização do utilizador autenticado.
- [x] Se o utilizador não pertencer a nenhuma organização, a secção "Minha organização" mostra estado vazio ou está oculta.
- [x] Funções de fetch por organização estão em `services/api.ts`.
- [x] Reutilização máxima de componentes e lógica dos tickets 27–32.

---

## TICKET-43: Admin — Editorial Page (Conexões API — Sysadmin) ✅

**Descrição**
Implementar a camada de conexão para a página editorial do admin (`/admin/system/editorial`): gestão de conteúdo destacado na homepage (datasets, reuses e organizações em destaque).

**Contexto Arquitetural**

- Ref. original: `pages/admin/site/editorial.vue` (Vue.js/Nuxt).
- A página editorial permite ao sysadmin gerir o conteúdo destacado (featured) que aparece na homepage do portal.
- Backend endpoints necessários:
  - `GET /api/1/site/home/datasets/` — datasets destacados na homepage.
  - `PUT /api/1/site/home/datasets/` — atualizar lista de datasets destacados (body: array de dataset IDs).
  - `GET /api/1/site/home/reuses/` — reuses destacados na homepage.
  - `PUT /api/1/site/home/reuses/` — atualizar lista de reuses destacados.
  - `GET /api/1/datasets/suggest/?q=` — autocomplete para selecionar datasets (TICKET-05).
  - `GET /api/1/reuses/suggest/?q=` — autocomplete para selecionar reuses (TICKET-11).
  - `GET /api/1/organizations/suggest/?q=` — autocomplete para selecionar organizações (TICKET-29).

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - Criar `HomeContent`: featured_datasets (Dataset[]), featured_reuses (Reuse[]).
2. **Funções em `services/api.ts`**:
   - `fetchHomeFeaturedDatasets()` → `GET /api/1/site/home/datasets/`
   - `updateHomeFeaturedDatasets(datasetIds)` → `PUT /api/1/site/home/datasets/`
   - `fetchHomeFeaturedReuses()` → `GET /api/1/site/home/reuses/`
   - `updateHomeFeaturedReuses(reuseIds)` → `PUT /api/1/site/home/reuses/`
3. **Página editorial** (`src/components/admin/editorial/EditorialClient.tsx`):
   - Secções para datasets e reuses destacados.
   - Autocomplete para pesquisar e adicionar novos items.
   - Drag-and-drop ou botões para reordenar.
   - Botão de remover por item.
   - Guardar alterações via PUT.

**Critérios de Aceitação**

- [x] Listagem de datasets e reuses destacados carregada da API.
- [x] Autocomplete funciona para pesquisar e adicionar items.
- [x] Reordenação e remoção funcionam.
- [x] PUT envia a lista após reordenação e persiste no backend.
- [x] Tipos TS definidos para HomeContent.

---

## TICKET-44: Admin — Permission Guards & Role-Based Navigation ✅

**Descrição**
Implementar controlo de permissões no frontend do admin: esconder secções da navegação lateral com base nos roles do utilizador, proteger rotas com guards, e garantir que apenas sysadmins acedem a "Sistema" e que "Minha organização" só aparece para utilizadores com organização.

**Contexto Arquitetural**

- Atualmente todas as 3 secções (Meu perfil, Minha organização, Sistema) são visíveis para qualquer utilizador autenticado — não há verificação de roles.
- O `AuthContext` expõe `user: UserRef | null` mas `UserRef` não inclui `roles[]` — apenas `UserPublic` tem esse campo.
- O backend já retorna roles no endpoint `GET /api/1/me/` — o frontend precisa de consumir e agir sobre essa informação.
- Roles relevantes no backend: `admin` (sysadmin com acesso total) e utilizador normal.
- Depende de: TICKET-03 (Auth — Current User) para garantir que o contexto de utilizador está completo.

**O que deve ser feito**

1. **Estender `UserRef`** em `types/api.ts`:
   - Adicionar `roles: string[]` ao tipo `UserRef` (ou usar `UserPublic` no `AuthContext`).
   - Adicionar `organizations: Organization[]` (para verificar se tem organização).
2. **Atualizar `AuthContext`** (`src/context/AuthContext.tsx`):
   - Incluir roles e organizations no estado do utilizador.
   - Expor helpers: `isAdmin: boolean`, `hasOrganization: boolean`.
3. **Atualizar `AdminSideNavigation.tsx`**:
   - Consumir `useAuth()` para obter roles e organizations.
   - Esconder "Sistema" se `!isAdmin`.
   - Esconder "Minha organização" se `!hasOrganization`.
4. **Route guards** (middleware ou componente wrapper):
   - Redirecionar para `/pages/admin/me/datasets` se utilizador não-admin aceder a `/pages/admin/system/*`.
   - Redirecionar se utilizador sem organização aceder a `/pages/admin/org/*`.
   - Mostrar página 403 ou redirecionar com mensagem.

**Critérios de Aceitação**

- [x] `UserRef` / AuthContext inclui `roles[]` e `organizations[]`.
- [x] "Sistema" só é visível na navegação para utilizadores com role `admin`.
- [x] "Minha organização" só é visível para utilizadores que pertencem a pelo menos uma organização.
- [x] Acesso direto a rotas protegidas (via URL) é bloqueado com redirecionamento.
- [x] Utilizadores não autenticados são redirecionados para login ao aceder a qualquer página `/admin/*`.

---

## TICKET-45: Global Search — Unify Local Searches with CategoryToggles Navigation ✅

**Descrição**
Unificar as pesquisas locais das páginas de listagem (datasets, organizations, reuses, dataservices) numa pesquisa global integrada, seguindo o workflow do CDATA (`cdata-pt`). Cada página de listagem mantém o seu próprio `InputSearchBar` que atualiza os resultados à medida que o utilizador escreve. O componente `CategoryToggles` na sidebar deve mostrar os totais de resultados da pesquisa atual para todas as categorias, e ao clicar numa categoria, navegar para a respetiva página com `?q=` preservado, onde os resultados já aparecem filtrados.

**Contexto Arquitetural**

- **Workflow CDATA (referência a seguir)**:
  - Cada página de listagem tem um `SearchInput` que atualiza os resultados diretamente à medida que o utilizador escreve (sem dropdown, sem página de pesquisa separada).
  - Na sidebar, radio buttons (`CategoryToggles`) mostram as 4 categorias (datasets, APIs, reutilizações, organizações) com o **total de resultados da pesquisa atual** por tipo.
  - A API é chamada em paralelo para obter os totais de todas as categorias simultaneamente.
  - Ao clicar numa categoria diferente, a URL muda para a página dessa categoria com `?q=` preservado — os filtros incompatíveis são resetados.
  - A página de destino carrega com a query no `SearchInput` e os resultados já filtrados.
  - Fluxo: utilizador escreve "educação" nos datasets → `CategoryToggles` mostra (ex: datasets 45, APIs 3, reutilizações 12, organizações 7) → clica em "Organizações" → navega para `/organizations?q=educação` → página mostra 7 organizações com "educação" no input de pesquisa.
- **Estado atual (`new-dadosgov/frontend`)**:
  - Cada página de listagem (datasets, organizations, reuses) já tem `InputSearchBar` que pesquisa localmente com `?q=` — **este comportamento é o correto e deve ser mantido**.
  - `CategoryToggles` existe e mostra as 4 categorias com contagens do `SiteMetrics`, mas **não propaga a query de pesquisa** na navegação e **não mostra totais de pesquisa**.
  - `CategoryToggles` só é usado em `OrganizationsFilters.tsx` — **falta nas páginas de datasets, reuses e dataservices**.
  - Não existe página de listagem pública para dataservices (apenas `/pages/dataservices/preview/`).
  - Existe `SearchClient` em `/pages/search` como página de pesquisa unificada — deve ser atualizada para incluir dataservices.
- **Endpoints de pesquisa no backend**:
  - `GET /api/1/datasets/?q=` — pesquisa datasets
  - `GET /api/1/organizations/?q=` — pesquisa organizações
  - `GET /api/1/reuses/?q=` — pesquisa reutilizações
  - `GET /api/1/dataservices/?q=` — pesquisa dataservices (API v1)
- Dependências: TICKET-05 (Datasets Search), TICKET-10 (Organizations Search), TICKET-11 (Reuses Search).

**O que deve ser feito**

1. **Atualizar `CategoryToggles` para suportar query de pesquisa**:
   - Adicionar prop opcional `searchQuery?: string` ao componente.
   - Quando `searchQuery` estiver definido (string não vazia), propagar o parâmetro `?q=` na navegação: `router.push(item.href + '?q=' + encodeURIComponent(searchQuery))`.
   - Quando `searchQuery` estiver definido, substituir as contagens do `SiteMetrics` pelos **totais de resultados da pesquisa** para cada categoria — chamar os 4 endpoints de pesquisa em paralelo com `page_size=1` para obter apenas os totais (campo `total` da resposta paginada).
   - Adicionar estado interno (`searchTotals`) e `useEffect` para fazer fetch dos totais quando `searchQuery` muda. Usar debounce de 300ms para evitar chamadas excessivas enquanto o utilizador escreve.
   - Mostrar indicador de loading (ex: spinner ou `...`) nas Pills enquanto os totais estão a ser carregados.
   - Manter o comportamento atual (contagens `SiteMetrics`, navegação sem `?q=`) quando `searchQuery` não for fornecido ou estiver vazio.

2. **Adicionar `CategoryToggles` à página de datasets**:
   - Integrar na sidebar de filtros (`DatasetsFilters.tsx`) ou diretamente no `DatasetsClient.tsx`, acima dos filtros existentes — seguir o mesmo padrão do `OrganizationsFilters.tsx`.
   - Passar `siteMetrics` e `searchQuery` (do URL param `q`) como props.
   - O `CategoryToggles` reflete a categoria "datasets" como ativa automaticamente (via pathname).

3. **Adicionar `CategoryToggles` à página de reuses**:
   - Integrar no `ReusesClient.tsx` na sidebar, seguindo o mesmo padrão da página de organizações.
   - Passar `siteMetrics` e `searchQuery` como props.
   - O `CategoryToggles` reflete a categoria "reutilizações" como ativa automaticamente.

4. **Criar página de listagem pública de dataservices**:
   - Criar `src/app/pages/dataservices/page.tsx` (server component) com suporte a `?q=` e `?page=`.
   - Criar `src/components/dataservices/DataservicesClient.tsx` (client component) seguindo o padrão das outras páginas de listagem:
     - `InputSearchBar` no banner que atualiza resultados ao escrever/Enter.
     - `CategoryToggles` na sidebar com `searchQuery`.
     - Listagem de dataservices com cards.
     - Paginação.
   - Adicionar `fetchDataservices(page, pageSize, filters)` e `searchDataservices(query, page, pageSize)` em `services/api.ts` se não existirem.
   - Adicionar tipo `Dataservice` em `types/api.ts` se não existir.

5. **Atualizar `SearchClient` (página `/pages/search`) para incluir dataservices**:
   - Adicionar "APIs" como 4ª tab nos `TYPES`.
   - Adicionar estado e fetch para dataservices (`searchDataservices`).
   - Adicionar renderização de resultados de dataservices com cards.
   - Atualizar totais para incluir dataservices.

6. **Garantir propagação bidirecional da query entre páginas**:
   - Quando o utilizador pesquisa na página de datasets e clica em "Organizações" no `CategoryToggles`, deve navegar para `/pages/organizations?q=mesma-query`.
   - Quando chega a `/pages/organizations?q=query`, o `InputSearchBar` dessa página deve mostrar a query preenchida e os resultados devem estar filtrados.
   - O mesmo para todas as combinações: datasets↔organizations↔reuses↔dataservices.
   - Verificar que todas as páginas de listagem leem o URL param `q` ao carregar e populam o `InputSearchBar` + resultados.

7. **Atualizar `OrganizationsFilters.tsx`** para passar `searchQuery` ao `CategoryToggles`:
   - Receber a query de pesquisa atual (do URL param `q`) e passá-la ao componente `CategoryToggles` já existente.

**Critérios de Aceitação**

- [x] `CategoryToggles` aceita `searchQuery` e mostra totais de pesquisa por categoria (não apenas `SiteMetrics`) quando há query ativa.
- [x] `CategoryToggles` está presente em todas as 4 páginas de listagem: datasets, organizations, reuses, dataservices.
- [x] Ao clicar numa categoria no `CategoryToggles`, navega para a página correta com `?q=` preservado.
- [x] A página de destino mostra os resultados da pesquisa para a query recebida no `InputSearchBar` e na listagem.
- [x] Existe página de listagem pública de dataservices (`/pages/dataservices`) com pesquisa, cards e `CategoryToggles`.
- [x] `SearchClient` (`/pages/search`) inclui tab de "APIs" com resultados de dataservices.
- [x] A query de pesquisa é propagada bidireccionalmente entre todas as páginas de listagem via `CategoryToggles`.
- [x] Sem `searchQuery`, o `CategoryToggles` mantém o comportamento atual (contagens `SiteMetrics`, navegação simples).
- [x] Debounce de 300ms nos totais de pesquisa do `CategoryToggles` para evitar chamadas excessivas.

---

## TICKET-46: Explorar — Redirecionar HVDs para Datasets com tag=hvd para nao existir conflitos ✅

**Descrição**
Atualmente, o link "HVDs" no menu de navegação "Explorar" do Header aponta para `/pages/hvds`, uma página placeholder em manutenção (`StatusCard` com "Página em manutenção"). Os HVDs (High Value Datasets) são datasets com a tag `hvd` e a página de datasets já suporta filtro por tag via query param (`/pages/datasets?tag=hvd`). Este ticket consiste em redirecionar o link do menu e eliminar a página placeholder.

**Contexto Arquitetural**

- O menu "Explorar" está definido em `src/components/Header.tsx` (linhas ~462-468), com `href: "/pages/hvds"`.
- A página `/pages/hvds` é composta por:
  - `src/app/pages/hvds/page.tsx` — server component que renderiza `HvdsClient`.
  - `src/components/hvds/HvdsClient.tsx` — componente com `StatusCard` de manutenção.
- A página de datasets (`src/app/pages/datasets/page.tsx`) já suporta o filtro `tag` via query params:
  ```typescript
  if (resolved?.tag) filters.tag = resolved.tag;
  ```
- O `fetchDatasets` em `services/api.ts` já envia o parâmetro `tag` para a API backend.
- A API backend `GET /api/1/datasets/?tag=hvd` já retorna corretamente os datasets com a tag HVD.

**O que deve ser feito**

1. **Atualizar o link no Header** (`src/components/Header.tsx`):
   - Alterar o `href` do item "HVDs" no menu "Explorar" de `/pages/hvds` para `/pages/datasets?tag=hvd`.
2. **Remover a página placeholder HVD**:
   - Eliminar `src/app/pages/hvds/page.tsx`.
   - Eliminar `src/components/hvds/HvdsClient.tsx`.
   - Remover o diretório `src/app/pages/hvds/` e `src/components/hvds/` se ficarem vazios.

**Critérios de Aceitação**

- [x] O link "HVDs" no menu "Explorar" aponta para `/pages/datasets?tag=hvd`.
- [x] Ao clicar em "HVDs", o utilizador vê a listagem de datasets filtrada pela tag `hvd`.
- [x] A página placeholder `/pages/hvds` foi removida (ficheiros eliminados).
- [x] Não existem referências restantes a `/pages/hvds` no código.

---

## TICKET-47: Vulnerability Testing — Frontend (npm audit + curl + OWASP ZAP) ✅

**Descrição**
Executar testes de vulnerabilidades no frontend Next.js do projeto dados.gov.pt utilizando três ferramentas complementares: **npm audit** (dependências), **curl manual** (headers, XSS, access control), e **OWASP ZAP** (scan automático OWASP Top 10). O objetivo é identificar e corrigir vulnerabilidades de segurança nas páginas públicas, formulários de autenticação e área admin.

**Contexto Arquitetural**

- Target: frontend Next.js em `http://localhost:3000`.
- Páginas públicas: `/pages/datasets`, `/pages/organizations`, `/pages/reuses`, `/pages/themes`.
- Autenticação: `/login`, `/register` (SAML via Autenticação.gov, sem formulário local de registo).
- Admin protegido: `/pages/admin/*` (requer sessão autenticada e roles).
- Repositório: `frontend/` (submodule Next.js).

**Ferramentas utilizadas**

| Ferramenta | Objetivo | Método |
|-----------|----------|--------|
| `npm audit` | Vulnerabilidades em dependências npm | Análise estática de CVEs conhecidos |
| `curl` manual | Security headers, XSS, open redirect, path traversal, CORS, access control, file exposure | Testes HTTP manuais contra endpoints |
| OWASP ZAP (Docker) | Scan automático OWASP Top 10 — 183 URLs, 57 regras de segurança | `zap-baseline.py` via `ghcr.io/zaproxy/zaproxy:stable` |

**O que deve ser feito**

1. **npm audit — Scan de dependências**:
   - Executar `npm audit` para identificar CVEs em pacotes npm.
   - Documentar vulnerabilidades por severidade (Critical, High, Moderate, Low).
   - Avaliar se fix é possível sem breaking changes.
2. **curl — Verificar HTTP security headers**:
   - Testar presença de: X-Frame-Options, Strict-Transport-Security, X-Content-Type-Options, Content-Security-Policy, Referrer-Policy, Permissions-Policy.
   - Verificar se X-Powered-By está exposto (information disclosure).
   - Corrigir headers em falta adicionando `headers()` em `next.config.ts`.
3. **curl — Testes de XSS (Cross-Site Scripting)**:
   - Injetar `<script>alert(1)</script>` em parâmetros `?q=` de pesquisa.
   - Injetar `<img src=x onerror=alert(1)>` em parâmetros URL.
   - Injetar `" onmouseover=alert(1) "` em inputs de pesquisa.
   - Verificar se payloads são refletidos em HTML ou escapados.
4. **curl — Testes de access control, file exposure e outros**:
   - Testar acesso a páginas admin sem autenticação (`/pages/admin/*`).
   - Testar path traversal (`/../../etc/passwd`).
   - Testar open redirect (`?redirect=http://evil.com`).
   - Testar CORS com origin malicioso.
   - Verificar exposição de ficheiros sensíveis (`.env`, `.env.local`, `next.config.ts`, source maps).
   - Testar NoSQL injection em parâmetros de pesquisa.
5. **OWASP ZAP — Scan automático baseline**:
   - Executar `zap-baseline.py` contra `http://localhost:3000` via Docker.
   - Scan passivo de 183 URLs com 57 regras OWASP.
   - Gerar relatórios HTML e JSON.
   - Analisar resultados: PASS, FAIL, WARN.
6. **Corrigir vulnerabilidades encontradas**:
   - Adicionar security headers em `next.config.ts` via `headers()` async function.
   - Remover `X-Powered-By` via `poweredByHeader: false`.
   - Documentar vulnerabilidades pendentes (Next.js upgrade, admin auth guard).
7. **Gerar relatório final e plano de remediação**:
   - Relatório completo em `docs/testsprite-vulnerability-frontend-report.md`.
   - Classificar por severidade (Critical, High, Medium, Low, Info).
   - Plano de remediação para items pendentes.

**Critérios de Aceitação**

- [x] `npm audit` executado — 5 CVEs identificados no Next.js (moderate).
- [x] Security headers verificados via curl — 7 headers em falta identificados e corrigidos.
- [x] Testes XSS executados via curl — 3 vetores testados, todos escapados (SAFE).
- [x] Access control testado via curl — admin pages sem auth retornam 500 (não expõem dados).
- [x] File exposure testado — `.env`, source maps, `next.config.ts` não acessíveis (404).
- [x] OWASP ZAP baseline scan executado — 57 PASS, 0 FAIL, 10 WARN (Low/Info).
- [x] Security headers corrigidos em `next.config.ts` — validados pelo OWASP ZAP como PASS.
- [x] Relatório de vulnerabilidades gerado com classificação por severidade.
- [x] Plano de remediação documentado para vulnerabilidades pendentes.

---

## TICKET-48: Vulnerability Testing — Backend API (TestSprite MCP) ✅

**Descrição**
Executar testes de vulnerabilidades no backend Flask/udata (API REST) do projeto dados.gov.pt utilizando o TestSprite MCP (Model Context Protocol). O objetivo é identificar vulnerabilidades de segurança nos endpoints públicos e autenticados, seguindo OWASP Top 10 e melhores práticas de segurança para APIs.

**Contexto Arquitetural**

- Target: backend Flask/udata em `http://localhost:7000`.
- API REST v1: `/api/1/` (datasets, organizations, reuses, users, discussions, posts, contacts, spatial).
- API REST v2: `/api/2/` (topics).
- Autenticação: session cookies com CSRF token (`X-CSRFToken` header).
- Roles: `admin` (gestão da própria org), `sysadmin` (gestão global do site).
- Repositório: `backend/` (submodule udata/Flask).

**O que deve ser feito**

1. **Configurar o TestSprite MCP server para backend**:
   - Verificar que o TestSprite MCP está configurado e funcional.
   - Executar bootstrap do projeto backend com TestSprite.
2. **Definir o escopo dos testes de vulnerabilidades backend**:
   - NoSQL injection (MongoDB) em parâmetros de query e body.
   - Authentication bypass — acesso a endpoints protegidos sem sessão válida.
   - Broken access control — acesso a recursos de outros utilizadores, escalação de privilégios.
   - SSRF — parâmetros que aceitam URLs (e.g., `remote_url` em resources).
   - Mass assignment — enviar campos não permitidos em POST/PUT (e.g., `roles`, `active`).
   - Rate limiting — verificar proteção contra brute force.
   - CORS misconfiguration — verificar headers Access-Control-Allow-Origin.
3. **Executar os testes nos endpoints públicos** (target: `http://localhost:7000`):
   - Scan de `GET /api/1/datasets/` — injection em parâmetros `q`, `sort`, `tag`, `format`.
   - Scan de `GET /api/1/organizations/` — injection em parâmetros de pesquisa e filtros.
   - Scan de `GET /api/1/reuses/` — injection em parâmetros de pesquisa.
   - Scan de `GET /api/1/spatial/zones/` — injection em parâmetros geoespaciais.
   - Verificar headers de segurança nas respostas HTTP (HSTS, X-Content-Type-Options, X-Frame-Options).
4. **Executar os testes nos endpoints autenticados**:
   - Scan de `POST /api/1/datasets/` — mass assignment, input validation.
   - Scan de `PUT /api/1/datasets/<id>/` — broken access control (editar dataset de outro user).
   - Scan de `DELETE /api/1/datasets/<id>/` — verificar que apenas owner/admin pode eliminar.
   - Scan de `POST /api/1/organizations/` — mass assignment em roles e memberships.
   - Scan de `PUT /api/1/users/<id>/` — privilege escalation (alterar próprio role para sysadmin).
   - Testar CSRF token validation — requests sem `X-CSRFToken` devem ser rejeitados.
5. **Executar os testes nos endpoints sysadmin**:
   - Scan de `GET /api/1/users/` — acesso sem role sysadmin deve ser negado.
   - Scan de `PATCH /api/1/site/` — atualização de config sem role sysadmin.
   - Scan de `DELETE /api/1/users/<id>/` — eliminação de utilizadores sem permissão.
   - Scan de `GET /api/1/reports/` — acesso a reports de moderação sem role adequado.
6. **Gerar e analisar relatórios**:
   - Exportar relatório de vulnerabilidades encontradas.
   - Classificar por severidade (Critical, High, Medium, Low, Info).
   - Documentar cada vulnerabilidade com: descrição, endpoint afetado, severidade, recomendação de correção.
7. **Criar plano de remediação**:
   - Para cada vulnerabilidade encontrada, criar um sub-ticket ou agrupar por categoria.
   - Priorizar Critical e High para correção imediata.

**Critérios de Aceitação**

- [x] TestSprite MCP configurado e funcional para o backend.
- [x] Testes executados nos endpoints públicos (datasets, organizations, reuses, spatial).
- [x] Testes executados nos endpoints autenticados (CRUD com access control).
- [x] Testes executados nos endpoints sysadmin (user management, site config, reports).
- [x] CSRF token validation testada em todos os endpoints mutáveis.
- [x] Relatório de vulnerabilidades gerado com classificação por severidade.
- [x] Plano de remediação documentado para vulnerabilidades Critical e High.

---

## TICKET-49: Datasets Listing — Organization Link in Dataset Card ✅

**Descrição**
Na página de listagem de datasets (`/pages/datasets`), cada card de dataset mostra o nome e logo da organização. Atualmente, clicar em qualquer parte do card (incluindo no nome/logo da organização) navega para o detalhe do dataset. O comportamento esperado é que clicar no nome ou logo da organização navegue para a página da organização (`/pages/organizations/<slug>`), enquanto clicar no resto do card continua a navegar para o dataset.

**Contexto Arquitetural**

- Componente: `frontend/src/components/datasets/DatasetsClient.tsx`.
- O card usa o componente `CardLinks` do Agora Design System (`@ama-pt/agora-design-system`).
- O nome da organização é passado como prop `category` (texto estático, sem link).
- O logo da organização é passado como prop `image` (imagem estática, sem link).
- O `onClick` do card inteiro redireciona para `/pages/datasets/<slug>`.
- A página de detalhe da organização existe em `/pages/organizations/<slug>`.
- O objeto `dataset.organization` contém `slug`, `name`, `logo`, `id`.

**O que deve ser feito**

1. **Alterar o componente `DatasetsClient.tsx`**:
   - Verificar se o `CardLinks` do Agora Design System suporta link na prop `category` ou se é necessário usar um slot/render prop customizado.
   - Se `CardLinks` não suportar link nativo na `category`, usar uma alternativa: passar um elemento `<Link>` como `category` ou sobrepor com CSS o nome da organização como link clicável.
   - O nome da organização deve ser um link para `/pages/organizations/<slug>`.
   - O click no link da organização deve usar `e.stopPropagation()` para não disparar o `onClick` do card pai.
2. **Alterar o logo/imagem da organização**:
   - Se possível, tornar o logo da organização também clicável para a página da organização.
   - Se o `CardLinks` não permitir link na imagem, manter como está (apenas o nome será link).
3. **Verificar comportamento visual**:
   - O nome da organização deve ter estilo de link (underline on hover, cor de link).
   - O cursor deve mudar para pointer ao passar sobre o nome da organização.
   - O resto do card mantém o comportamento atual (click → dataset detail).

**Critérios de Aceitação**

- [x] Clicar no nome da organização no card navega para `/pages/organizations/<slug>`.
- [x] Clicar no logo da organização navega para `/pages/organizations/<slug>` (se suportado pelo componente).
- [x] Clicar no resto do card (título, descrição, métricas) continua a navegar para o dataset.
- [x] O nome da organização tem estilo visual de link (hover underline, cursor pointer).
- [x] Não há conflito entre o click do card e o click da organização (stopPropagation).

---

## TICKET-50: Frontend — Functional Testing with TestSprite MCP ✅

**Descrição**
Execução de testes funcionais automatizados no frontend Next.js utilizando o TestSprite MCP (Model Context Protocol). Cobertura de navegação, pesquisa, filtros, paginação, detalhe de entidades e formulários. Inclui correção de bugs encontrados durante os testes e correção de erros de build pré-existentes.

**Contexto Arquitetural**

- Target: frontend Next.js em `http://localhost:3001` (production build).
- TestSprite MCP configurado via `.claude.json` com API key.
- Testes gerados automaticamente pelo TestSprite com base no code summary e PRD.
- Ficheiros de teste e credenciais em `testsprite_tests/` (excluído do git via `.gitignore`).
- Relatório final em `docs/testsprite-frontend-report.md`.

**O que foi feito**

1. **Configurar o TestSprite MCP server**:
   - Adicionado TestSprite MCP ao `.claude.json` com API key.
   - Bootstrap do projeto frontend executado com sucesso.
2. **Gerar code summary e test plan**:
   - Code summary YAML gerado com todas as rotas, features e limitações conhecidas.
   - Test plan com 57 test cases gerado automaticamente (High, Medium, Low priority).
3. **Corrigir erros de build pré-existentes** (20 ficheiros):
   - Instalação de dependências em falta (`react-markdown`, `remark-gfm`).
   - Correção de tipos TypeScript incompatíveis com Agora Design System (ButtonVariant, DropdownType, PopupDimensions, DragAndDropUploader onChange).
   - Correção de interfaces duplicadas em `types/api.ts`.
   - Adição de Suspense wrappers para páginas com `useSearchParams`.
   - Remoção de componente não utilizado (`FooterInstitutional`) com referências a variáveis inexistentes.
4. **Corrigir bugs encontrados nos testes**:
   - Removido `blockedLink={true}` em `DatasetsClient.tsx` — impedia navegação pelo título do dataset.
   - Removido `blockedLink={true}` em `OrganizationsClient.tsx` — mesmo fix para cards de organizações.
5. **Executar 30 testes em modo produção**:
   - Build de produção (`npm run build && npm run start`) na porta 3001.
   - 30 testes executados (limite do plano Free em modo produção).
   - Resultado: 21/30 passed (70%) — 0 bugs reais, 9 falsos positivos/by-design.
6. **Gerar relatório final**:
   - Relatório completo em `docs/testsprite-frontend-report.md`.
   - Classificação de cada falha (falso positivo, by-design, bug real).
   - Documentação de todos os fixes aplicados.
7. **Proteger dados sensíveis**:
   - Adicionado `/testsprite_tests/` ao `.gitignore` (contém API keys e credenciais).

**Resultados dos testes**

| Grupo                    | Total  | Passed | Failed | Pass Rate |
| ------------------------ | ------ | ------ | ------ | --------- |
| Dataset Search & Listing | 7      | 7      | 0      | 100%      |
| Dataset Detail           | 4      | 3      | 1      | 75%       |
| Organizations            | 4      | 3      | 1      | 75%       |
| Reuses                   | 3      | 3      | 0      | 100%      |
| Global Search            | 4      | 3      | 1      | 75%       |
| Themes/Topics            | 3      | 2      | 1      | 67%       |
| Registration             | 4      | 0      | 4      | 0%        |
| Follow/Favorites         | 1      | 0      | 1      | 0%        |
| **Total**                | **30** | **21** | **9**  | **70%**   |

**Classificação das 9 falhas:**

- 4x By design — registo via Autenticação.gov (SAML), sem formulário local.
- 5x Falso positivo — dados de teste insuficientes ou terminologia PT vs EN.
- 0x Bugs reais.

**Critérios de Aceitação**

- [x] TestSprite MCP configurado e funcional.
- [x] 30 testes funcionais executados em modo produção.
- [x] Bugs de navegação corrigidos (`blockedLink` em dataset e organization cards).
- [x] Build de produção funcional (20 erros pré-existentes corrigidos).
- [x] Relatório documentado em `docs/testsprite-frontend-report.md`.
- [x] Dados sensíveis protegidos (`testsprite_tests/` no `.gitignore`).

---

## TICKET-51: Vulnerability Remediation — Backend (KITS24 Security Audit) ✅

**Descrição**
Remediação de vulnerabilidades de segurança identificadas nos relatórios de auditoria KITS24 (2021-2026) contra `dados.gov.pt` e `preprod.dados.gov.pt`. Fonte: `Vulnerabilidades_mapa_geral.xlsx` (38 entradas). Implementação de 7 correções cobrindo OWASP Top 10 no backend Flask/udata, abrangendo todos os 10 endpoints de upload (backoffice + API) e endpoints de autenticação.

**Contexto Arquitetural**

- Target: backend Flask/udata em `backend/`.
- VULNs endereçadas: 1532, 1533, 1534, 1377, 1688, 1496, 1550, 1378, 1379, 1593, 1515, 1595, 1878, 1879, 1498.
- Findings adicionais de análise de código: CORS origin echo, SVG/XML/PNG upload XSS, security headers, discussion XSS, CAPTCHA fail-open.
- Branch: `fix_vulnerabilities` no repositório `backend/` (origin: `git@github.com:amagovpt/udata-pt.git`).
- Documentação detalhada: `docs/vulnerability-remediation.md`.

**O que foi feito**

1. **FIX 1 — User Enumeration (MEDIUM)** — VULN-1532, 1533, 1534, 1377, 1688:
   - Alterado `SECURITY_RETURN_GENERIC_RESPONSES = True` em `settings.py` — Flask-Security retorna mensagens idênticas para todos os cenários de auth.
   - Email `welcome_existing` tornado genérico ("Account information") para não revelar existência de conta.
   - Ficheiros: `udata/settings.py`, `udata/auth/mails.py`.

2. **FIX 2 — CORS Origin Echo (CRITICAL)** — VULN-1496, 1550:
   - Adicionado `CORS_ALLOWED_ORIGINS = []` em `settings.py` (whitelist obrigatória).
   - `cors.py` agora valida Origin contra whitelist antes de ecoar headers CORS com credentials.
   - Removido wildcard `Access-Control-Allow-Origin: *` de `send_static()`.
   - Ficheiros: `udata/cors.py`, `udata/settings.py`, `udata/app.py`.

3. **FIX 3 — Malicious File Upload (CRITICAL)** — VULN-1378, 1379, 1593:
   - Criado módulo centralizado `udata/core/storages/validation.py` com `validate_upload()` e `validate_image_stream()`.
   - Validação de magic bytes (PNG, JPEG, GIF, WebP, BMP, TIFF), Pillow `Image.verify()`, scanning de `<script>`, `javascript:`, event handlers, XXE patterns.
   - Protege **todos os 10 endpoints de upload** (backoffice `/upload/<name>/` + 5 endpoints API de resources + 4 endpoints de imagens).
   - Mensagens de erro informativas com nome do ficheiro, tipo detetado e razão da rejeição.
   - Ficheiros: `udata/core/storages/validation.py` (NEW), `udata/core/storages/api.py`, `udata/core/dataset/api.py`.

4. **FIX 4 — Security Headers (HIGH)** — VULN-1515, 1595:
   - Adicionado middleware `add_security_headers()` em `app.py` com X-Frame-Options, X-Content-Type-Options, HSTS, Referrer-Policy, CSP.
   - Usa `setdefault()` para permitir override por endpoint específico.
   - Ficheiro: `udata/app.py`.

5. **FIX 5 — Discussion Content Sanitization (HIGH)** — VULN-1878:
   - Adicionado `_sanitize_html()` com `bleach.clean(tags=[], strip=True)` nos 4 formulários de discussões.
   - Sanitização aplicada antes da validação para manter DataRequired funcional.
   - Ficheiro: `udata/core/discussions/forms.py`.

6. **FIX 6 — CAPTCHA Fail-Open → Fail-Closed (MEDIUM)** — VULN-1879:
   - `check_captchetat()` agora retorna `False` (fail-closed) quando o serviço CaptchEtat não está acessível.
   - Ficheiro: `udata/auth/forms.py`.

7. **FIX 7 — Rate Limiting (MEDIUM)** — VULN-1498, 1879:
   - Adicionado `flask-limiter[redis]` como dependência.
   - Limiter global: 200/day, 50/hour por IP.
   - Rate limit de 5/minuto nos endpoints de login, register, forgot_password, reset_password.
   - `RATELIMIT_STORAGE_URI = "memory://"` configurável para Redis em produção.
   - Ficheiros: `pyproject.toml`, `udata/app.py`, `udata/auth/views.py`, `udata/settings.py`.

**Ficheiros alterados**

| Ficheiro | Fix |
|---|---|
| `udata/settings.py` | FIX 1, FIX 2, FIX 7 |
| `udata/cors.py` | FIX 2 |
| `udata/app.py` | FIX 2, FIX 4, FIX 7 |
| `udata/core/storages/validation.py` | FIX 3 (NEW) |
| `udata/core/storages/api.py` | FIX 3 |
| `udata/core/dataset/api.py` | FIX 3 |
| `udata/core/discussions/forms.py` | FIX 5 |
| `udata/auth/forms.py` | FIX 6 |
| `udata/auth/mails.py` | FIX 1 |
| `udata/auth/views.py` | FIX 7 |
| `pyproject.toml` | FIX 7 |

**Configuração necessária para produção**

```python
# udata.cfg
CORS_ALLOWED_ORIGINS = ["https://dados.gov.pt", "https://preprod.dados.gov.pt"]
RATELIMIT_STORAGE_URI = "redis://localhost:6379"
```

**Critérios de Aceitação**

- [x] CORS — Origin não whitelisted não é ecoado (`curl -H "Origin: http://evil.com"` retorna sem CORS headers).
- [x] Upload — PNG poisoned (HTML dentro de .png) rejeitado com 415 e mensagem informativa.
- [x] Upload — XML com XXE/script rejeitado com 415.
- [x] Upload — SVG com `<script>` rejeitado com 415.
- [x] Upload — Validação cobre todos os 10 endpoints (backoffice + API + imagens).
- [x] Security Headers — X-Frame-Options, CSP, HSTS, X-Content-Type-Options presentes nas respostas.
- [x] Discussions — `<script>alert(1)</script>` em título/comentário é stripped.
- [x] User Enumeration — Login/register/reset com email existente e inexistente retorna mesma resposta.
- [x] CAPTCHA — Serviço CaptchEtat inacessível resulta em rejeição (fail-closed).
- [x] Rate Limiting — 6+ tentativas de login em 1 minuto resulta em HTTP 429.
- [x] Documentação completa em `docs/vulnerability-remediation.md`.

---

## TICKET-52: Homepage — Fix CORS Blocking All Client-Side API Calls ✅

**Descrição**
Corrigir o problema em que a homepage mostrava todas as métricas a 0, "Nenhum conjunto de dados encontrado", "Nenhuma reutilização encontrada" e "Nenhuma novidade encontrada" — apesar do backend ter dados (19 842 datasets, organizações, reuses, etc.).

**Contexto Arquitetural**

- A homepage (`src/app/page.tsx`) é um componente `'use client'` — todos os fetches correm no browser.
- As funções `fetchSiteInfo()`, `fetchLatestDatasets()`, `fetchLatestReuses()`, `fetchPosts()` usavam `API_BASE_URL` definido como `http://localhost:7000/api/1` (URL absoluto cross-origin).
- O browser em `localhost:3000` fazia pedidos directos a `localhost:7000`, que é um domínio diferente (cross-origin).
- O backend tem `CORS_ALLOWED_ORIGINS = []` por defeito (`udata/settings.py:124`, `udata/cors.py:18`), o que bloqueia todos os pedidos cross-origin.
- Todos os fetches falhavam silenciosamente — os blocos `catch` retornavam fallback com zeros e arrays vazios.
- O Next.js já tinha rewrites configurados em `next.config.ts` para proxy de `/api/:path*` → backend, mas os fetches públicos não os usavam.

**Causa Raiz**

1. `NEXT_PUBLIC_API_BASE=http://localhost:7000/api/1` (URL absoluto) → fetches client-side iam directo ao backend → CORS bloqueado.
2. `BACKEND_URL` em `next.config.ts` era derivado de `NEXT_PUBLIC_API_BASE` via `.replace("/api/1", "")` — acoplamento frágil entre variável client-side e configuração server-side.
3. Os error handlers de cada fetch retornavam dados vazios sem erros visíveis na UI (design gracioso, mas esconde o problema).

**O que foi corrigido**

1. **`.env.local`** — Alterado `NEXT_PUBLIC_API_BASE` de `http://localhost:7000/api/1` para `/api/1` (URL relativo). Idem para `NEXT_PUBLIC_API_V2_BASE`. Adicionado `BACKEND_URL=http://localhost:7000` (variável server-side para o proxy).
2. **`.env.example`** — Actualizado para reflectir o novo padrão com URLs relativos e `BACKEND_URL` separado.
3. **`next.config.ts`** — `BACKEND_URL` agora lê `process.env.BACKEND_URL` directamente em vez de derivar de `NEXT_PUBLIC_API_BASE`.

**Fluxo após a correção**

```
Browser (localhost:3000)
  → fetch("/api/1/site/")          ← URL relativo
  → Next.js rewrite proxy          ← intercepta /api/:path*
  → http://localhost:7000/api/1/site/  ← server-side, sem CORS
  → resposta com metrics.datasets = 19842
```

**Ficheiros alterados**

| Ficheiro | Alteração |
|---|---|
| `frontend/.env.local` | `NEXT_PUBLIC_API_BASE=/api/1`, `NEXT_PUBLIC_API_V2_BASE=/api/2`, adicionado `BACKEND_URL=http://localhost:7000` |
| `frontend/.env.example` | Idem (template actualizado) |
| `frontend/next.config.ts` | `BACKEND_URL` lê de `process.env.BACKEND_URL` em vez de derivar de `NEXT_PUBLIC_API_BASE` |

**Nota**: Após alterar variáveis `NEXT_PUBLIC_*`, é necessário limpar o cache do Next.js (`rm -rf .next/`) e reiniciar o dev server, pois estas variáveis são embebidas no bundle JS no momento da compilação.

**Critérios de Aceitação**

- [x] `NEXT_PUBLIC_API_BASE` usa URL relativo (`/api/1`).
- [x] `BACKEND_URL` é variável separada, server-side only.
- [x] `next.config.ts` usa `BACKEND_URL` directamente para rewrites.
- [x] Homepage mostra métricas reais do backend (datasets, reuses, organizações, utilizadores).
- [x] Homepage mostra datasets recentes (3 cards).
- [x] Homepage mostra reutilizações recentes (3 cards).
- [x] Homepage mostra notícias recentes (3 cards).
- [x] Proxy Next.js responde correctamente: `curl localhost:3000/api/1/site/` retorna dados.

---

## TICKET-53: Fix Server-Side Fetches Failing with Relative API URLs ✅

**Descrição**
Corrigir o problema em que páginas com Server Components (SSR) — como `/pages/datasets` — não conseguiam carregar dados da API, mostrando "0 resultados" e "Não encontrou o que procurava?" apesar de as contagens no sidebar estarem correctas (19 842 datasets).

**Contexto Arquitetural**

- A página de datasets (`src/app/pages/datasets/page.tsx`) é um **Server Component** — o `fetchDatasets()` corre no Node.js (server-side), não no browser.
- O TICKET-52 alterou `NEXT_PUBLIC_API_BASE` de `http://localhost:7000/api/1` (absoluto) para `/api/1` (relativo) para resolver CORS em componentes client-side.
- URLs relativos (como `/api/1/datasets/`) funcionam no browser (o browser resolve contra `localhost:3000`, e o Next.js proxy redireciona para o backend).
- Mas no Node.js (server-side), `/api/1/datasets/` **não é resolvível** — o Node.js não tem hostname implícito, então o fetch falha silenciosamente.
- Os contadores no sidebar funcionavam porque eram carregados via componentes client-side (`'use client'`) onde o URL relativo funciona correctamente.

**Causa Raiz**

`API_BASE_URL` em `src/services/api.ts` era uma constante simples:
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || "https://dados.gov.pt/api/1";
// Resolvia para "/api/1" — funciona no browser, falha no Node.js
```

Server Components chamavam `fetch("/api/1/datasets/")` no Node.js → URL inválido → fetch falha → catch retorna `{ data: [], total: 0 }` → UI mostra "0 resultados".

**O que foi corrigido**

Alterado `src/services/api.ts` para detectar o ambiente de execução e usar o URL adequado:

```typescript
const isServer = typeof window === "undefined";
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:7000";
const API_BASE_URL = isServer
  ? `${BACKEND_URL}/api/1`
  : (process.env.NEXT_PUBLIC_API_BASE || "/api/1");
const API_V2_BASE_URL = isServer
  ? `${BACKEND_URL}/api/2`
  : (process.env.NEXT_PUBLIC_API_V2_BASE || "/api/2");
```

**Fluxo após a correção**

```
Server Component (Node.js — SSR):
  → fetch("http://localhost:7000/api/1/datasets/")  ← URL absoluto directo
  → backend responde com 19 842 datasets ✅

Client Component (Browser):
  → fetch("/api/1/datasets/")                       ← URL relativo
  → Next.js proxy rewrite → backend                 ← sem CORS ✅
```

**Ficheiros alterados**

| Ficheiro | Alteração |
|---|---|
| `frontend/src/services/api.ts` | `API_BASE_URL` e `API_V2_BASE_URL` agora usam URL absoluto (`BACKEND_URL`) em server-side e relativo em client-side |

**Relação com TICKET-52**

O TICKET-52 corrigiu os fetches **client-side** (homepage) mudando para URLs relativos. Este ticket completa a correção garantindo que os fetches **server-side** (SSR) continuam a funcionar com URLs absolutos.

| Cenário | TICKET-52 (antes) | TICKET-52 (depois) | TICKET-53 (depois) |
|---|---|---|---|
| Client Component (browser) | ❌ CORS blocked | ✅ Relativo `/api/1` | ✅ Relativo `/api/1` |
| Server Component (Node.js) | ✅ Absoluto `localhost:7000` | ❌ Relativo falha | ✅ Absoluto `localhost:7000` |

**Critérios de Aceitação**

- [x] `API_BASE_URL` usa URL absoluto (`BACKEND_URL/api/1`) em server-side.
- [x] `API_BASE_URL` usa URL relativo (`/api/1`) em client-side.
- [x] `API_V2_BASE_URL` segue a mesma lógica.
- [x] Página `/pages/datasets` mostra lista de datasets (SSR).
- [x] Homepage continua a funcionar (client-side fetches via proxy).
- [x] Variável `BACKEND_URL` reutilizada de `.env.local` (já existia para `next.config.ts`).

---

## TICKET-54: Admin — Organization Sections Wiring, Pagination & Harvester Fix ✅

**Descrição**
Conectar à API real as secções de backoffice da organização que estavam com dados hardcoded/placeholder (Discussões e Membros), corrigir o filtro de harvesters por organização no backend, e implementar paginação real client-side em todas as secções da organização (o componente `Table` do Agora Design System não pagina os dados automaticamente — apenas mostra o controlo visual).

**Contexto Arquitetural**

- Páginas admin da organização: `frontend/src/app/pages/admin/org/[orgId]/`
- Componentes: `frontend/src/components/admin/`
- API functions: `frontend/src/services/api.ts`
- Backend endpoints:
  - Discussões: `GET /api/1/discussions/?for=<org_id>` — discussões sobre a organização.
  - Membros: `GET /api/1/organizations/<id>/` → campo `members[]` no response.
  - Adicionar membro: `POST /api/1/organizations/<id>/member/<user_id>` (body: `{ role: "admin"|"editor" }`).
  - Editar membro: `PUT /api/1/organizations/<id>/member/<user_id>` (body: `{ role: "admin"|"editor" }`).
  - Remover membro: `DELETE /api/1/organizations/<id>/member/<user_id>`.
  - Suggest users: `GET /api/1/users/suggest/?q=<query>` — autocomplete de utilizadores.
  - Harvesters: `GET /api/1/harvest/sources/?organization=<org_id>` — filtrar por organização.

**O que deve ser feito**

1. **Discussões** — Wiring do `DiscussionsClient.tsx`:
   - Remover placeholder "Ainda não há discussões".
   - Usar `fetchOrgDiscussions(org_id)` (já existe em `services/api.ts`).
   - Mostrar lista de discussões com: título, autor (avatar + nome), data de criação, estado (aberta/fechada), número de mensagens.
   - Mostrar empty state quando não há discussões.
   - Clicar numa discussão pode abrir detalhe (opcional nesta fase).

2. **Membros** — Rewrite do `MembersClient.tsx`:
   - Remover `mockMembers` e todo o mock data.
   - Buscar membros da organização via API (`fetchOrganization(org_id)` → `org.members[]`).
   - Mostrar tabela com: avatar, nome, email, role (badge), data de adesão (`since`).
   - Implementar "Adicionar membro": popup com `suggestUsers(query)` para autocomplete, seleção de role, e `POST /api/1/organizations/<id>/member/<user_id>`.
   - Implementar "Editar role": popup para alterar role de um membro existente.
   - Implementar "Remover membro": confirmação + `DELETE /api/1/organizations/<id>/member/<user_id>`.

3. **Harvesters** — Fix filtro por organização (backend):
   - O endpoint `GET /api/1/harvest/sources/` não filtrava por `organization` — retornava todos os harvesters (38) independentemente da org selecionada.
   - Adicionado param `organization` ao `source_parser` em `udata/harvest/api.py`.
   - Adicionado filtro `sources = sources(organization=args['organization'])` na query.

4. **Paginação real client-side** em todas as secções da organização:
   - O componente `Table` do Agora Design System mostra controlos de paginação visuais (`paginationProps`) mas **não pagina os dados** — renderiza todas as `TableRow` independentemente do `currentPage`.
   - Implementada paginação manual com `useState(currentPage)`, `useState(itemsPerPage)` e `useMemo(paginatedItems)`.
   - Cada secção agora mostra apenas N items por página (default: 10), com selector "Linhas por página" (10/20/50), indicador "1–10 de 329", e setas de navegação < >.
   - Secções afetadas:
     - `OrgDatasetsClient.tsx` — Conjuntos de dados
     - `OrgReusesClient.tsx` — Reutilizações
     - `DiscussionsClient.tsx` — Discussões
     - `MembersClient.tsx` — Membros
     - `OrgHarvestersClient.tsx` — Harvesters
     - `OrgCommunityResourcesClient.tsx` — Recursos comunitários

5. **Funções API** (já existiam em `services/api.ts`):
   - `fetchOrgDiscussions(org)` — buscar discussões da organização.
   - `addMember(org, userId, role)` — adicionar membro.
   - `updateMemberRole(org, userId, role)` — editar role.
   - `removeMember(org, userId)` — remover membro.
   - `suggestUsers(query)` — autocomplete de utilizadores.

**Critérios de Aceitação**

- [ ] Discussões lista dados reais da API com título, autor, data, estado e contagem de mensagens.
- [ ] Membros lista dados reais da API (nome, role, data de adesão).
- [ ] Adicionar membro funciona com autocomplete de utilizadores (`suggestUsers`).
- [ ] Editar role de membro funciona via API.
- [ ] Remover membro funciona com confirmação.
- [ ] Sem dados hardcoded/mock restantes nas secções Discussões e Membros.
- [ ] Empty states adequados quando não há dados.
- [ ] Harvesters filtrados por organização (backend fix — endpoint retorna apenas harvesters da org selecionada).
- [ ] Paginação real funcional em todas as 6 secções da organização (datasets, reuses, discussions, members, harvesters, community resources).
- [ ] Selector "Linhas por página" com opções 10/20/50 em cada secção.
- [ ] Indicador de posição "X–Y de Z" em cada secção.

---

## Summary Table

| #                                     | Ticket                                                   | Area   | Priority | Status                             |
| ------------------------------------- | -------------------------------------------------------- | ------ | -------- | ---------------------------------- |
| **PÁGINAS PÚBLICAS — Conexões API**   |                                                          |        |          |                                    |
| 01                                    | Auth — Login (CSRF + session)                            | Auth   | High     | Route handler existe, falta wiring |
| 02                                    | Auth — Registration (proxy + form)                       | Auth   | High     | UI existe, falta wiring            |
| 03                                    | Auth — Current User (`/me/` + context)                   | Auth   | High     | Not started                        |
| 04                                    | Homepage — Dados Dinâmicos (site, featured, posts)       | Public | High     | Concluído (CORS fix: TICKET-52)    |
| 05                                    | Datasets — Search (q param + suggest)                    | Public | High     | fetchDatasets sem q                |
| 06                                    | Datasets — Filtros (licenses, schemas, tags, etc.)       | Public | Medium   | Parcialmente dinâmico              |
| 07                                    | Discussions CRUD                                         | Public | Medium   | Placeholder                        |
| 08                                    | Followers (follow/unfollow genérico)                     | Public | Medium   | Local state only                   |
| 09                                    | Organization Detail (fetch + org datasets/reuses)        | Public | High     | Página em falta                    |
| 10                                    | Organizations — Search + Filtros (q, badges, suggest)    | Public | Medium   | fetchOrganizations sem q           |
| 11                                    | Reuses — Search + Detail (q, types, datasets associados) | Public | Medium   | Parcial                            |
| 12                                    | Topics/Themes — Leitura API v2                           | Public | Medium   | Tudo estático                      |
| 13                                    | User Profile (fetch /me/datasets, /users/)               | Public | High     | Not started                        |
| 14                                    | Dataset Create & Edit                                    | Admin  | —        | → TICKET-26                        |
| 15                                    | Reuse Create & Edit                                      | Admin  | —        | → TICKET-27                        |
| 16                                    | Dataservices Wiring                                      | Admin  | —        | → TICKET-28                        |
| 17                                    | Posts/News — Leitura (fetch posts)                       | Public | Medium   | Placeholder                        |
| 18                                    | Notifications (fetch /notifications/)                    | Public | Low      | Not started                        |
| 19                                    | Global Search — Suggest Multi-Entidade                   | Public | High     | Nenhuma lógica                     |
| 20                                    | Mini-Courses — Fonte de Dados                            | Public | Low      | Tudo hardcoded                     |
| 21                                    | Password Reset (route handler + functions)               | Auth   | Medium   | Rewrites existem                   |
| 22                                    | Spatial (zones suggest, granularities, levels)           | Public | Low      | Filtros estáticos                  |
| 23                                    | Reports — Submissão (reasons + create)                   | Public | Low      | Not started                        |
| 24                                    | Organization Membership (request, accept, members)       | Public | Low      | Not started                        |
| 25                                    | CSV/Data Export (URL generators)                         | Public | Low      | Not started                        |
| **BACKOFFICE / ADMIN — Conexões API** |                                                          |        |          |                                    |
| 26                                    | Admin — Datasets CRUD (tipos TS + fetch/mutate)          | Admin  | High     | Concluído                          |
| 27                                    | Admin — Reuses CRUD (tipos TS + fetch/mutate)            | Admin  | High     | Not started                        |
| 28                                    | Admin — Dataservices CRUD (wiring form existente)        | Admin  | Medium   | UI exists, needs wiring            |
| 29                                    | Admin — Organizations CRUD + Members                     | Admin  | High     | Not started                        |
| 30                                    | Admin — User Profile & Metrics                           | Admin  | High     | Not started                        |
| 31                                    | Admin — Community Resources CRUD                         | Admin  | Low      | Not started                        |
| 32                                    | Admin — Harvesters CRUD + Jobs                           | Admin  | Medium   | Not started                        |
| 33                                    | Admin — Topics CRUD (API v2)                             | Admin  | Medium   | Not started                        |
| 34                                    | Admin — Posts CRUD                                       | Admin  | Medium   | Not started                        |
| 35                                    | Admin — User Management (Sysadmin)                       | Admin  | Low      | Not started                        |
| 36                                    | Admin — Site Management & Moderation (Sysadmin)          | Admin  | Medium   | Not started                        |
| 42                                    | Admin — Organization Content Pages (`org/*`)             | Admin  | High     | Concluído                          |
| 43                                    | Admin — Editorial Page (Sysadmin)                        | Admin  | Medium   | Concluído                          |
| 44                                    | Admin — Permission Guards & Role-Based Navigation        | Admin  | High     | Concluído                          |
| **AUTENTICAÇÃO EXTERNA**              |                                                          |        |          |                                    |
| 37                                    | Auth — Autenticação.gov / SAML (plugin + frontend)       | Auth   | High     | Concluído                          |
| 38                                    | Maintenance — Sync Login branches & resolution           | Repo   | High     | Concluído                          |
| 40                                    | Dataset Detail — Fix hardcoded content & UI bugs         | Public | High     | Not started                        |
| 41                                    | Legacy Account Migration to CMD/eIDAS                    | Auth   | High     | Concluído                          |
| **PESQUISA GLOBAL**                   |                                                          |        |          |                                    |

| 45 | Global Search — Unify Local Searches + CategoryToggles | Public | High | Concluído |
| 46 | Explorar — Redirecionar HVDs para Datasets com tag=hvd | Public | Medium | Concluído |
| **QUALIDADE & SEGURANÇA** | | | | |
| 47 | Vulnerability Testing — Frontend (TestSprite MCP) | Security | High | Not started |
| 48 | Vulnerability Testing — Backend API (TestSprite MCP) | Security | High | Not started |
| **UX & NAVEGAÇÃO** | | | | |
| 49 | Datasets Listing — Organization Link in Dataset Card | Public | Medium | Not started |
| **TESTING & QA** | | | | |
| 50 | Frontend — Functional Testing with TestSprite MCP | QA | Medium | Concluído |
| **SEGURANÇA — Remediação** | | | | |
| 51 | Vulnerability Remediation — Backend (KITS24 Audit) | Security | Critical | Concluído |
| **INFRAESTRUTURA & CONFIG** | | | | |
| 52 | Homepage — Fix CORS Blocking All Client-Side API Calls | Frontend | High | Concluído |
| 53 | Fix Server-Side Fetches Failing with Relative API URLs | Frontend | High | Concluído |
| **BACKOFFICE — Wiring pendente** | | | | |
| 54 | Admin — Organization Discussions & Members (Backend Wiring) | Admin | High | Not started |
