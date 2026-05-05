# Bug Tickets — Estimativas

> Generated: 2026-05-05
> Project: dados.gov.pt - Portal de Dados Abertos
> Scope: Estimativas detalhadas para os bug tickets em backlog. Cada estimativa inclui breakdown por sub-tarefa e nível de confiança.

---

## Resumo

| Ticket    | Área                | Estimativa | Confiança          |
| --------- | ------------------- | ---------- | ------------------ |
| LEDG-1633 | Backend             | 3-5h       | Baixa (vago)       |
| LEDG-1628 | Frontend            | 6-8h       | Alta               |
| LEDG-1612 | Backend / Frontend  | 5-8h       | Média              |
| LEDG-1596 | Frontend            | 2-3h       | Alta               |
| LEDG-1569 | Frontend            | 4-6h       | Média              |
| **Total** |                     | **20-30h** |                    |

---

## LEDG-1633 — [BUG] DEV - Backend - Editor para acrescentar elementos em destaque não está a funcionar em DEV

**Estimativa: 3-5h**

**Confiança: Baixa** — ticket sem detalhes técnicos. A maioria do esforço é diagnóstico.

### Breakdown

| Sub-tarefa                                                                                | Tempo  |
| ----------------------------------------------------------------------------------------- | ------ |
| Reproduzir em DEV e localizar o editor de "destaques"                                     | 1h     |
| Identificar causa-raiz (config, permissões, endpoint, model, dados)                       | 1-2h   |
| Implementar fix                                                                           | 1h     |
| Smoke test em DEV                                                                         | 30min  |

### Riscos

- Pode ser problema ambiental (DEV ≠ local) → escalada para 8h.
- Pode envolver migração de dados → escalada adicional.

### Sugestão

Antes de aceitar a estimativa, pedir ao reporter para clarificar:
- URL exato onde o bug ocorre
- Mensagem de erro (browser console + network tab)
- Diferença para o ambiente local

---

## LEDG-1628 — [BUG] [1] Backend - Backoffice — "Transferir reutilização" e "Transferir conjunto de dados" não chamam a API

**Estimativa: 6-8h**

**Confiança: Alta** — ticket muito bem documentado, backend já operacional, helpers já existem.

### Estado atual verificado no código

- `suggestUsers()` existe em [services/api.ts:3247](frontend/src/services/api.ts#L3247).
- `suggestOrganizations()` existe em [services/api.ts:500](frontend/src/services/api.ts#L500).
- Endpoint `POST /api/1/transfer/` operacional ([backend/udata/features/transfer/api.py](backend/udata/features/transfer/api.py)).
- Componentes afetados:
  - [TransferReusePopupContent](frontend/src/components/admin/reuses/ReusesEditClient.tsx) (~linhas 52-126)
  - [TransferDatasetPopupContent](frontend/src/components/admin/datasets/DatasetsEditClient.tsx) (~linhas 112-178)

### Breakdown

| Sub-tarefa                                                                                | Tempo    |
| ----------------------------------------------------------------------------------------- | -------- |
| Adicionar tipo `Transfer` em `frontend/src/types/api.ts`                                  | 15min    |
| Adicionar `requestTransfer()` em `frontend/src/services/api.ts`                           | 30min    |
| Componente unificado de picker (users + organizations) — não existe equivalente           | 2-3h     |
| Wire-up de estado + `onClick` em `TransferReusePopupContent`                              | 1h       |
| Wire-up de estado + `onClick` em `TransferDatasetPopupContent`                            | 1h       |
| Feedback de sucesso/erro + mensagem "pedido pendente, recipient tem de aceitar"           | 1h       |
| Teste manual com utilizador real e organização real                                       | 30min-1h |

### Fora de âmbito

- Fluxo do recipient (UI para ver/aceitar/recusar pedido) — **trabalho separado**, criar ticket próprio.
- UI de visualização de transfer requests pending — **trabalho separado**.

### Payload de referência

```json
{
  "subject":   { "class": "Reuse" | "Dataset", "id": "<entity-id>" },
  "recipient": { "class": "User"  | "Organization", "id": "<recipient-id>" },
  "comment":   "texto opcional"
}
```

### Tipo TS a adicionar

```ts
export interface Transfer {
  id: string;
  subject: { class: string; id: string };
  recipient: { class: string; id: string };
  status: 'pending' | 'accepted' | 'refused';
  comment?: string;
  response_comment?: string;
  created: string;
  closed?: string | null;
}
```

---

## LEDG-1612 — [BUG] [2] Backend - Backoffice - Estatísticas

**Estimativa: 5-8h**

**Confiança: Média** — afeta múltiplas páginas, causa pode ser comum (agregação) ou múltipla.

### Páginas afetadas

- [admin/statistics](frontend/src/app/pages/admin/statistics/page.tsx) — estatísticas do sistema
- [admin/me/statistics](frontend/src/app/pages/admin/me/statistics/page.tsx) — estatísticas pessoais
- [admin/org/[orgId]/statistics](frontend/src/app/pages/admin/org/[orgId]/statistics/page.tsx) — estatísticas de organização

### Breakdown

| Sub-tarefa                                                                                  | Tempo  |
| ------------------------------------------------------------------------------------------- | ------ |
| Reproduzir nas 3 páginas e mapear o que está a 0 vs. errado vs. ausente                     | 1h     |
| Inspecionar endpoints backend e queries MongoEngine (provável `/site/`, `/metrics/`)        | 1-2h   |
| Corrigir agregações ou serialização (provavelmente partilhada entre as 3 páginas)           | 2-3h   |
| Validar contagens contra BD real                                                            | 1h     |
| Testes (backend + manual frontend)                                                          | 1h     |

### Riscos

- Se a causa for nos cron jobs de agregação (`tasks.py` periódico), pode chegar a 12h.
- Se cada página tiver causa diferente, multiplica por 3.

---

## LEDG-1596 — [BUG] Backend - Front Office - Acesso a data stories via diferentes ecrãs

**Estimativa: 2-3h**

**Confiança: Alta** — bug isolado em rotas/links, código existe.

### Entry points falhados

1. Homepage → clicar em data story → "abre diretamente a data story" (errado)
2. Listagem de data stories → clicar em data story → "abre diretamente a data story" (errado)
3. Reutilização que contém data story → "abre a página de detalhe da reutilização" (errado)

### Estado atual verificado

- Rotas existem em [app/pages/datastories/](frontend/src/app/pages/datastories/) com sub-rotas específicas (ex: `territorios-inteligentes/esperanca-de-vida-em-portugal`).
- Componentes existem em [components/datastories/](frontend/src/components/datastories/).

### Breakdown

| Sub-tarefa                                                                              | Tempo  |
| --------------------------------------------------------------------------------------- | ------ |
| Reproduzir os 3 fluxos e identificar destinos errados                                   | 30min  |
| Corrigir links (provável mismatch entre `slug`/`id` ou hardcoded paths)                 | 1h     |
| Verificar se é problema de routing dinâmico vs. estático                                | 30min  |
| Smoke test dos 3 fluxos                                                                 | 30min  |

### Notas

- Bug pode estar em `Link href=` em homepage card, em listagem, e em página de detalhe da reutilização (3 sítios distintos).
- Se as data stories estiverem hardcoded como rotas estáticas (parece ser o caso), o link tem de mapear `slug` → rota concreta.

---

## LEDG-1569 — [BUG] [1] Backend - Front office - Pesquisa não está a reportar resultados

**Estimativa: 4-6h**

**Confiança: Média** — bug parece de state management mas pode esconder múltiplos cenários.

### Descrição

Pesquisa global do front-office:

- 1ª pesquisa → mostra resultados (`?q=dados`, 69 resultados).
- 2ª pesquisa → **não retorna resultados**; em vez disso o dropdown da pesquisa global abre por cima da listagem (`?q=dados&page=1`).

### Estado atual verificado

- Componente do dropdown global: [components/search/SearchDropdown.tsx](frontend/src/components/search/SearchDropdown.tsx)
- Componente do header (trigger): [components/Header.tsx](frontend/src/components/Header.tsx)
- Resultados de pesquisa global: [components/search/SearchClient.tsx](frontend/src/components/search/SearchClient.tsx) e [app/pages/search/page.tsx](frontend/src/app/pages/search/page.tsx)
- Listagem de datasets (afetada nas screenshots): [app/pages/datasets/](frontend/src/app/pages/datasets/)

### Hipóteses prováveis

1. Estado do dropdown não é fechado entre navegações (`isOpen` permanece `true` quando URL muda com `&page=1`).
2. Header search intercepta o `submit` da listagem e re-abre o dropdown em vez de submeter para a página atual.
3. `useEffect` na listagem só responde à 1ª mudança do `q` (dependência mal definida).

### Breakdown

| Sub-tarefa                                                                                              | Tempo  |
| ------------------------------------------------------------------------------------------------------- | ------ |
| Reproduzir + identificar qual componente intercepta a 2ª pesquisa (DevTools, network, React state)      | 1h     |
| Tracejar fluxo: header `SearchDropdown` → URL params → listagem (`SearchClient` ou listing page)        | 1-2h   |
| Implementar fix (provável: fechar dropdown em mudança de rota OU corrigir submit handler)               | 1-2h   |
| Testar 3 entry points: header global, search input da listagem, página `/search`                        | 1h     |

### Riscos

- Se o bug for partilhado por múltiplas listagens (datasets, reuses, organizations), validar todas → +1h.
- Se a causa for paginação do backend (search engine retornar 0 na 2ª query), escalada para 8h e passa a ter componente backend.
