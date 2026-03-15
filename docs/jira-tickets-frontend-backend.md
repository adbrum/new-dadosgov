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

## TICKET-02: Authentication — Registration (Conexão API) ✅

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

## TICKET-03: Authentication — Current User State (Conexão API) ✅

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

## TICKET-04: Homepage — Dados Dinâmicos (Conexões API) ✅

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

- [ ] Tipos `SiteInfo`, `Post` e `GlobalSearchSuggestion` definidos.
- [ ] `fetchSiteInfo()` retorna métricas do site.
- [ ] `fetchFeaturedDatasets()` retorna datasets com featured=true.
- [ ] `fetchFeaturedReuses()` retorna reuses com featured=true.
- [ ] `fetchPosts()` retorna posts paginados.
- [ ] `suggestGlobalSearch()` retorna sugestões de autocomplete.
- [ ] Pesquisa global redireciona para a página de datasets com o parâmetro `q`.
- [ ] Todas as funções tratam erros graciosamente (retornam dados vazios, não crasham).

---

## TICKET-05: Datasets — Search (Conexão API)

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

- [ ] `fetchDatasets()` aceita `q` e passa ao backend.
- [ ] Resultados de pesquisa são paginados corretamente.
- [ ] `suggestDatasets()` retorna sugestões para autocomplete.
- [ ] Pesquisa vazia retorna todos os datasets.

---

## TICKET-06: Datasets — Filtros Avançados (Conexões API)

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

- [ ] Funções de fetch para licenças, frequências, schemas, badges retornam dados do backend.
- [ ] `suggestFormats()` e `suggestTags()` retornam sugestões.
- [ ] `fetchDatasets()` aceita todos os filtros e os passa como query params.
- [ ] Múltiplos filtros podem ser combinados numa só chamada.

---

## TICKET-07: Discussions (Conexões API)

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

- [ ] Tipos `Discussion` e `DiscussionMessage` definidos.
- [ ] `fetchDiscussions()` retorna lista de discussions para um dataset.
- [ ] `createDiscussion()` envia o payload correto (title + comment + subject).
- [ ] `replyToDiscussion()` adiciona mensagem a uma discussion existente.
- [ ] `closeDiscussion()` fecha a discussion.
- [ ] Erros de autenticação (401) são tratados.

---

## TICKET-08: Followers (Conexões API)

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

- [ ] Funções follow/unfollow funcionam para datasets, organizations e reuses.
- [ ] `fetchFollowers()` retorna lista de seguidores.
- [ ] POST retorna 201 em sucesso, DELETE retorna 200.
- [ ] Erros de autenticação (401) são tratados.

---

## TICKET-09: Organization Detail (Conexões API) ✅

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

## TICKET-10: Organizations — Search, Filtros e Página Completa (Conexão API) ✅

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

## TICKET-11: Reuses — Search, Filtros e Detail (Conexões API) ✅

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

## TICKET-14: Dataset Create & Edit

> **Nota**: A lógica de conexão para criação e edição de datasets está detalhada no TICKET-26 (Admin — Datasets CRUD). Este ticket é mantido como referência.

---

## TICKET-15: Reuse Create & Edit

> **Nota**: A lógica de conexão para criação e edição de reuses está detalhada no TICKET-27 (Admin — Reuses CRUD). Este ticket é mantido como referência.

---

## TICKET-16: Dataservices — Wiring do Form Existente

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

## TICKET-25: CSV/Data Export (Conexão API)

**Descrição**
Implementar funções utilitárias para gerar URLs de export CSV dos endpoints do backend.

**Contexto Arquitetural**

- Backend endpoints de export:
  - `GET /api/1/organizations/<org>/datasets.csv`
  - `GET /api/1/organizations/<org>/dataservices.csv`
  - `GET /api/1/organizations/<org>/discussions.csv`
  - `GET /api/1/organizations/<org>/datasets-resources.csv`
  - `GET /api/1/site/datasets.csv`
  - `GET /api/1/site/organizations.csv`
  - `GET /api/1/site/reuses.csv`
  - `GET /api/1/site/tags.csv`

**O que deve ser feito**

1. **Funções utilitárias** em `services/api.ts`:
   - `getOrgExportUrl(org, type)` → retorna URL completa `${API_BASE}/organizations/<org>/<type>.csv`.
   - `getSiteExportUrl(type)` → retorna URL completa `${API_BASE}/site/<type>.csv`.
   - Onde `type` é `'datasets' | 'dataservices' | 'discussions' | 'datasets-resources' | 'organizations' | 'reuses' | 'tags'`.
2. **Nota**: Não é necessário fetch — o browser abre a URL diretamente para download.

**Critérios de Aceitação**

- [ ] `getOrgExportUrl()` gera URL correta para exports de organização.
- [ ] `getSiteExportUrl()` gera URL correta para exports globais.
- [ ] URLs usam a base URL da API configurada.

---

## TICKET-37: Authentication — Login via Autenticação.gov / SAML (Conexão API) ✅

**Descrição**
Implementar o fluxo completo de autenticação via Autenticação.gov (Cartão de Cidadão) usando protocolo SAML 2.0, incluindo login, registo automático, e logout — tanto no backend (plugin SAML) como no frontend (redirect flow e callbacks).

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
- Se o utilizador já existe (por email ou NIC): faz login direto.
- Se o utilizador não existe: cria conta automaticamente via SAML.
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

---

## TICKET-38: Repository Maintenance — Login Integration & Branch Cleanup ✅

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

## TICKET-39: Global Search — Página de Pesquisa com Dropdown e Resultados (Frontend)

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

## TICKET-40: Legacy Account Migration to CMD/eIDAS ✅

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

## TICKET-26: Admin — Datasets CRUD (Conexões API)

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

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - Estender `Dataset` com campos completos: `acronym`, `private`, `featured`, `archived`, `frequency`, `temporal_coverage`, `spatial`, `quality`, `badges[]`, `owner`.
   - Criar `DatasetCreatePayload` (campos enviados no POST).
   - Criar `DatasetUpdatePayload` (campos enviados no PUT).
   - Criar `ResourceCreatePayload`, `ResourceUpdatePayload`.
   - Criar `License`, `Frequency`, `Schema`, `Activity` types.
2. **Funções em `services/api.ts`**:
   - `fetchMyDatasets(page?, pageSize?)` → `GET /api/1/me/datasets/`
   - `fetchMyOrgDatasets(page?, pageSize?)` → `GET /api/1/me/org_datasets/`
   - `createDataset(payload)` → `POST /api/1/datasets/`
   - `updateDataset(id, payload)` → `PUT /api/1/datasets/<id>/`
   - `deleteDataset(id)` → `DELETE /api/1/datasets/<id>/`
   - `uploadResource(datasetId, file)` → `POST /api/1/datasets/<id>/upload/` (multipart)
   - `createResource(datasetId, payload)` → `POST /api/1/datasets/<id>/resources/`
   - `updateResource(datasetId, resourceId, payload)` → `PUT /api/1/datasets/<id>/resources/<rid>/`
   - `deleteResource(datasetId, resourceId)` → `DELETE /api/1/datasets/<id>/resources/<rid>/`
   - `reorderResources(datasetId, resourceIds[])` → `PUT /api/1/datasets/<id>/resources/`
   - `fetchLicenses()` → `GET /api/1/datasets/licenses/`
   - `fetchFrequencies()` → `GET /api/1/datasets/frequencies/`
   - `fetchSchemas()` → `GET /api/1/datasets/schemas/`
   - `fetchResourceTypes()` → `GET /api/1/datasets/resource_types/`
   - `fetchActivity(relatedTo)` → `GET /api/1/activity/?related_to=<id>`
   - `toggleDatasetFeatured(id, featured)` → `POST|DELETE /api/1/datasets/<id>/featured/`
3. **Fluxo de criação** (dados que transitam):
   - Step 1: Escolha do modo (standard ou structured/schema).
   - Step 2: POST dataset com `private: true` + metadados → backend retorna dataset com `id`.
   - Step 3: Para cada resource, POST upload ou POST resource com URL → backend retorna resource.
   - Step 4: PUT dataset com `private: false` para publicar.
4. **Fluxo de edição** (dados que transitam):
   - GET dataset completo → preencher form.
   - PUT com campos alterados → backend retorna dataset atualizado.
   - CRUD de resources individual.
   - GET activity log para tab de atividades.

**Critérios de Aceitação**

- [ ] Todos os tipos TS estão definidos e espelham os campos do backend.
- [ ] Todas as funções fetch/mutate estão em `services/api.ts` e funcionam.
- [ ] `fetchMyDatasets()` retorna a lista paginada do utilizador.
- [ ] `createDataset()` envia o payload correto e retorna o dataset criado.
- [ ] Upload de ficheiros funciona com `multipart/form-data`.
- [ ] `updateDataset()` e `deleteDataset()` funcionam.
- [ ] Resource CRUD (create, update, delete, reorder) funciona.
- [ ] Funções auxiliares (licenses, frequencies, schemas) retornam dados corretos.
- [ ] Erros de validação do backend são retornados em formato utilizável pelo frontend.

---

## TICKET-27: Admin — Reuses CRUD (Conexões API)

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

- [ ] Tipos TS espelham os campos do backend.
- [ ] `fetchMyReuses()` retorna lista paginada.
- [ ] `createReuse()` + `uploadReuseImage()` + `linkDatasetToReuse()` funcionam em sequência.
- [ ] `updateReuse()` e `deleteReuse()` funcionam.
- [ ] Tipos e tópicos de reuse são carregados do backend.
- [ ] Erros de validação são retornados em formato utilizável.

---

## TICKET-28: Admin — Dataservices CRUD (Conexões API)

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

- [ ] Tipo `Dataservice` definido em `types/api.ts`.
- [ ] Todas as funções CRUD estão em `services/api.ts`.
- [ ] O form existente (`ApiRegistrationClient.tsx`) submete ao backend.
- [ ] Erros de validação são retornados e utilizáveis.

---

## TICKET-29: Admin — Organizations CRUD (Conexões API)

**Descrição**
Implementar a camada de conexão para organizações no admin: criação, edição, eliminação, logo upload, e gestão de membros.

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

- [ ] Tipos completos para Organization, Member, MembershipRequest.
- [ ] CRUD de organização funciona (create, update, delete).
- [ ] Upload de logo funciona com multipart.
- [ ] Gestão de membros: add, update role, remove, accept/refuse request.
- [ ] Autocomplete de organizações funciona.

---

## TICKET-30: Admin — User Profile & Metrics (Conexões API)

**Descrição**
Implementar a camada de conexão para o perfil do utilizador autenticado: edição de perfil, upload de avatar, invitations de organizações, eliminação de conta, e métricas pessoais.

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

**O que deve ser feito**

1. **Tipos TS** em `types/api.ts`:
   - Estender `User` (do TICKET-03) com: `about`, `website`, `organizations[]`, `apikey`.
   - Criar `UserUpdatePayload`: first_name, last_name, about, website.
   - Criar `OrgInvitation`: id, organization, status, created.
   - Criar `UserMetrics`: datasets, reuses, followers, views, downloads (ou conforme resposta da API).
2. **Funções em `services/api.ts`**:
   - `updateProfile(payload)` → `PUT /api/1/me/`
   - `uploadAvatar(file)` → `POST /api/1/me/avatar/` (multipart)
   - `deleteAccount()` → `DELETE /api/1/me/`
   - `fetchOrgInvitations()` → `GET /api/1/me/org_invitations/`
   - `fetchMyMetrics()` → `GET /api/1/me/metrics/`
   - `fetchUserActivity(userId?, page?)` → `GET /api/1/activity/?owner=<id>`

**Critérios de Aceitação**

- [ ] `updateProfile()` envia os campos corretos e retorna user atualizado.
- [ ] `uploadAvatar()` funciona com multipart.
- [ ] `deleteAccount()` funciona e retorna confirmação.
- [ ] `fetchOrgInvitations()` retorna lista de convites.
- [ ] `fetchMyMetrics()` retorna métricas agregadas.
- [ ] Tipos TS espelham as respostas da API.

---

## TICKET-31: Admin — Community Resources CRUD (Conexões API)

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

- [ ] Tipo `CommunityResource` definido.
- [ ] CRUD completo funciona.
- [ ] Upload de ficheiro funciona com multipart.
- [ ] Associação a dataset específico funciona.

---

## TICKET-32: Admin — Harvesters CRUD (Conexões API)

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

- [ ] Tipos `HarvestSource` e `HarvestJob` definidos.
- [ ] CRUD de harvesters funciona.
- [ ] Trigger de job retorna o job criado.
- [ ] Listagem de jobs mostra status e erros.
- [ ] Validação de source funciona.

---

## TICKET-33: Admin — Topics CRUD (Conexões API v2)

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

- [ ] Funções usam `NEXT_PUBLIC_API_V2_BASE` como base URL.
- [ ] CRUD de topics funciona.
- [ ] Gestão de elementos (add/remove datasets e reuses) funciona.
- [ ] Tipos TS definidos e consistentes.

---

## TICKET-34: Admin — Posts CRUD (Conexões API)

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

- [ ] Tipo `Post` definido com todos os campos.
- [ ] CRUD completo funciona.
- [ ] Upload de imagem funciona com multipart.
- [ ] Posts podem ser criados como draft (`published: false`) e publicados depois.

---

## TICKET-35: Admin — User Management (Conexões API — Sysadmin)

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

- [ ] Listagem de utilizadores paginada com pesquisa.
- [ ] Detalhes de utilizador incluem roles e content counts.
- [ ] Atualização de roles funciona.
- [ ] Eliminação funciona.
- [ ] Autocomplete funciona.

---

## TICKET-36: Admin — Site Management & Moderation (Conexões API — Sysadmin)

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

- [ ] `fetchSiteInfo()` retorna stats do site.
- [ ] `fetchReports()` retorna lista filtrada por status.
- [ ] `dismissReport()` altera status do report.
- [ ] `fetchReportReasons()` retorna lista de razões.
- [ ] URLs de export CSV são geradas corretamente.
- [ ] Tipos TS definidos para SiteInfo, Report, ReportReason.

---

## Summary Table

| #                                     | Ticket                                                   | Area   | Priority | Status                             |
| ------------------------------------- | -------------------------------------------------------- | ------ | -------- | ---------------------------------- |
| **PÁGINAS PÚBLICAS — Conexões API**   |                                                          |        |          |                                    |
| 01                                    | Auth — Login (CSRF + session)                            | Auth   | High     | Route handler existe, falta wiring |
| 02                                    | Auth — Registration (proxy + form)                       | Auth   | High     | UI existe, falta wiring            |
| 03                                    | Auth — Current User (`/me/` + context)                   | Auth   | High     | Not started                        |
| 04                                    | Homepage — Dados Dinâmicos (site, featured, posts)       | Public | High     | Tudo hardcoded                     |
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
| 26                                    | Admin — Datasets CRUD (tipos TS + fetch/mutate)          | Admin  | High     | Not started                        |
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
| **AUTENTICAÇÃO EXTERNA**              |                                                          |        |          |                                    |
| 37                                    | Auth — Autenticação.gov / SAML (plugin + frontend)       | Auth   | High     | Concluído                          |
| 38                                    | Maintenance — Sync Login branches & resolution           | Repo   | High     | Concluído                          |
| 40                                    | Legacy Account Migration to CMD/eIDAS                    | Auth   | High     | Concluído                          |
