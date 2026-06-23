# Análise de Páginas do Portal dados.gov.pt

**Âmbito:** inventário e complexidade das páginas do frontend (Next.js App Router)
**Data:** 17 de junho de 2026
**Fonte:** enumeração das rotas `page.tsx` em `frontend/src/app/` e deteção de bibliotecas/componentes

## Sumário

| Indicador | Valor |
| --- | --- |
| Total de páginas (rotas `page.tsx`) | 120 |
| Frontoffice (público) | 46 |
| Backoffice (`/pages/admin/`) | 74 |
| Bibliotecas de gráficos | Nenhuma |
| Bibliotecas de mapas | Nenhuma |
| Bibliotecas de formulários | Nenhuma (Agora DS + estado React) |

## 1. Frontoffice — 46 páginas

| Área | Páginas | Conteúdo |
| --- | --- | --- |
| Home | 1 | dados agregados, hero, cards |
| Datasets | 4 (lista, detalhe, discussões, preview) | dados + pré-visualização tabular |
| Reuses | 4 (lista, detalhe, discussões, preview) | dados |
| Organizations | 2 (lista, detalhe) | dados + filtros |
| Dataservices | 2 (lista, preview) | dados |
| Áreas temáticas / Themes | 3 | dados + filtros |
| Datastories | 2 (índice, `[...slug]`) | conteúdo rico (secções dinâmicas) |
| Posts / Publicações | 3 | markdown / CMS |
| Search | 1 | dados + filtros (facetas) |
| FAQs | 9 | conteúdo estático |
| docapi (documentação / tutorial API) | 2 | estático / markdown |
| Learn / mini-courses | 4 | conteúdo passo-a-passo |
| About / Roadmap / Support | 3 | estático (+ formulário no Support) |
| Autenticação (login, register, loginregister, migrate-account, reset-password) | 5 | formulários |
| Perfil público de utilizador | 1 | dados |

## 2. Backoffice — 74 páginas

O número elevado deve-se ao facto de o backoffice **replicar a gestão das mesmas entidades em três âmbitos de permissão**:

- **Pessoal** — `/admin/me/...`
- **Organização** — `/admin/org/...` e `/admin/org/[orgId]/...`
- **Sistema** — `/admin/system/...`

**Entidades geridas** (cada uma normalmente com lista, novo, editar e detalhe): datasets, reuses, dataservices, community-resources, organizations, harvesters (e respetivos jobs), posts, users, topics, discussions, members, profiles, statistics, logs, editorial e notificações.

Das 74 páginas, **cerca de 30 são páginas de formulário** (`new` / `edit` / `profile`); as restantes são sobretudo **tabelas/listagens de dados** com filtros e ações.

## 3. Complexidade — gráficos, mapas, dados, formulários

**Conclusão arquitetural:** o portal **não tem biblioteca de gráficos nem de mapas** (sem recharts/chart.js/d3, sem leaflet/mapbox/maplibre/openlayers) e **não usa biblioteca de formulários** (sem react-hook-form/formik). A interface assenta no **Agora Design System + Tailwind CSS**, com estado React nativo.

| Dimensão | Situação no portal |
| --- | --- |
| Gráficos | Sem gráficos interativos nativos. Nas estatísticas existe apenas um ícone `bar_chart.svg` decorativo sobre tabelas de métricas numéricas. Conteúdo visual rico existe apenas nos datastories, através de `BigNumbers` (destaques numéricos), `Timeline` e, sobretudo, `Iframe` (embeds de dashboards/visualizações externas, não renderizadas pela aplicação). |
| Mapas interativos | Inexistentes — nenhuma biblioteca de mapas em todo o código. Os dados geográficos (distrito/concelho/spatial) aparecem apenas como texto ou filtros. |
| Dados | A maioria das páginas é orientada a dados (listagens da API, páginas de detalhe, tabelas de métricas, facetas de pesquisa). |
| Formulários | Concentrados na autenticação (5), no Support (1) e em praticamente todo o backoffice de criação/edição (cerca de 30 páginas), além do `HarvesterConfigForm` e do editor de posts (TipTap, rich-text). Construídos com primitivas do Agora (`Input`, `Select`, etc.) + React. |

### Resumo por nível de complexidade

- **Alta:** datasets/detalhe (dados + pré-visualização tabular + discussões); datastories (`[...slug]`, secções dinâmicas + iframes); search (facetas); formulários CRUD do backoffice (datasets/reuses com vários separadores, harvesters).
- **Média:** listagens com filtros (organizations, reuses, dataservices, áreas temáticas); estatísticas (tabelas de métricas); editor de posts (rich-text TipTap).
- **Baixa:** FAQs, docapi, about/roadmap, learn, páginas estáticas/markdown.

## Nota sobre visualização de dados e IA

Caso o objetivo seja introduzir **gráficos e mapas interativos** no portal, não existe atualmente fundação técnica para isso no frontend. Seria necessário adotar bibliotecas dedicadas (visualização de gráficos e um stack de mapas) ou continuar a depender de embeds via iframe nos datastories. Este é um dado de esforço relevante para o planeamento.
