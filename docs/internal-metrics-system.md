# Sistema Interno de Métricas (Substituir METRICS_API externo)

## Context

Atualmente o udata depende de um serviço externo (`METRICS_API`) para obter métricas de views e downloads. O sinal `on_api_call` já é disparado em cada request API mas ninguém o ouve. O objetivo é capturar esses eventos internamente no MongoDB, eliminando a dependência externa, e adicionando tracking do frontend (page views, downloads, pesquisas, cliques).

---

## Guia Rápido de Operações

### Configuração necessária

Para usar o sistema interno, o `METRICS_API` **não pode estar definido** (deve ser `None`).
Verificar no ficheiro `backend/.env`:

```bash
# METRICS_API=http://localhost:8006/api  # Comentado — usar sistema interno
```

Se `METRICS_API` estiver definido com uma URL, o sistema usa o serviço externo (comportamento legacy).

Configurações em `backend/udata/settings.py`:

```python
METRICS_API = None            # None = sistema interno; URL = serviço externo
TRACKING_ENABLED = True       # Ativa o listener de api_call e o endpoint /tracking/
TRACKING_EVENT_TTL_DAYS = 90  # Eventos raw auto-deletados após 90 dias
```

### Comandos CLI (backend)

Todos os comandos correm a partir de `cd backend`.

```bash
# Atualizar views/downloads nos modelos (Dataset, Reuse, Organization, Dataservice)
# Este é o comando principal — agrega os MetricEvent e escreve nos campos metrics.*
uv run udata job run update-metrics

# Agregar eventos raw em MetricAggregation (daily/monthly) — para dados históricos
uv run udata job run aggregate-metrics

# Atualizar métricas de contagem (followers, reuses, discussions, etc.)
uv run udata job run compute-site-metrics

# Atualizar todas as métricas de contagem por modelo (sem views/downloads)
uv run udata metrics update

# Listar todas as jobs disponíveis
uv run udata job list

# Ver jobs agendadas
uv run udata job scheduled
```

### Agendar tasks no Celery beat (produção)

```bash
# Atualizar views/downloads a cada hora
uv run udata job schedule update-metrics "0 * * * *"

# Agregar dados históricos diariamente às 2h
uv run udata job schedule aggregate-metrics "0 2 * * *"
```

Para que o agendamento funcione, o Celery worker e beat devem estar a correr:

```bash
inv work   # worker
inv beat   # scheduler
```

### Endpoint de tracking (frontend → backend)

| Método | URL | Auth | Descrição |
|--------|-----|------|-----------|
| `POST` | `/api/1/tracking/` | Sem auth | Registar evento de tracking |

**Request body:**

```json
{
  "event_type": "view",
  "object_type": "dataset",
  "object_id": "698c9485916701f5806d3161",
  "extra": {}
}
```

- `event_type` (obrigatório): `view`, `download`, `search`, `click`, `api_call`, `custom`
- `object_type` (opcional): `dataset`, `resource`, `reuse`, `organization`, `dataservice`, `page`
- `object_id` (opcional): ObjectId ou slug do objeto
- `extra` (opcional): dados adicionais (ex: `{"query": "saúde"}` para pesquisas, `{"dataset_id": "..."}` para downloads)

**Response:** `201 {"status": "ok"}`

### Testar manualmente com curl

```bash
# Enviar um page view para um dataset
curl -X POST http://localhost:7000/api/1/tracking/ \
  -H "Content-Type: application/json" \
  -d '{"event_type":"view","object_type":"dataset","object_id":"698c9485916701f5806d3161"}'

# Enviar um evento de pesquisa
curl -X POST http://localhost:7000/api/1/tracking/ \
  -H "Content-Type: application/json" \
  -d '{"event_type":"search","extra":{"query":"educação"}}'

# Enviar um download de resource (com referência ao dataset pai)
curl -X POST http://localhost:7000/api/1/tracking/ \
  -H "Content-Type: application/json" \
  -d '{"event_type":"download","object_type":"resource","object_id":"<RESOURCE-ID>","extra":{"dataset_id":"<DATASET-ID>"}}'

# Depois, atualizar os modelos
uv run udata job run update-metrics
```

### Verificar dados no MongoDB

```bash
cd backend && uv run python -c "
from udata.app import create_app
app = create_app()
with app.app_context():
    from udata.core.metrics.events import MetricEvent
    from udata.core.metrics.aggregations import MetricAggregation
    from udata.models import Dataset, Organization, Reuse

    # Contar eventos por tipo
    print(f'MetricEvent total: {MetricEvent.objects.count()}')
    for t in ['view','api_call','download','search','click']:
        c = MetricEvent.objects(event_type=t).count()
        if c: print(f'  {t}: {c}')

    # Ver agregações
    print(f'MetricAggregation total: {MetricAggregation.objects.count()}')

    # Ver métricas nos datasets
    print('Datasets:')
    for ds in Dataset.objects.limit(10):
        v = ds.metrics.get('views', 0)
        d = ds.metrics.get('resources_downloads', 0)
        if v or d: print(f'  {ds.slug}: views={v} downloads={d}')

    # Ver métricas nas organizations
    print('Organizations:')
    for org in Organization.objects.limit(10):
        v = org.metrics.get('views', 0)
        if v: print(f'  {org.slug}: views={v}')

    # Ver métricas nos reuses
    print('Reuses:')
    for r in Reuse.objects.limit(10):
        v = r.metrics.get('views', 0)
        if v: print(f'  {r.slug}: views={v}')
"
```

### Fluxo completo de dados

```
                         ┌─────────────────────────────────────────┐
                         │         Utilizador no browser           │
                         └───────────┬────────────┬────────────────┘
                                     │            │
                         Visita página       Clica download
                                     │            │
                                     ▼            ▼
                         usePageTracking()   trackDownload()
                         (1x por sessão)     (1x por click)
                                     │            │
                                     ▼            ▼
                          POST /api/1/tracking/
                          event_type="view"   event_type="download"
                                     │            │
                                     ▼            ▼
                         ┌─────────────────────────────────────────┐
                         │  MetricEvent (MongoDB: metric_event)    │
                         │  TTL: 90 dias auto-delete               │
                         └───────────┬─────────────────────────────┘
                                     │
              ┌──────────────────────┤
              │                      │
              ▼                      ▼
   udata job run              udata job run
   update-metrics             aggregate-metrics
              │                      │
              ▼                      ▼
   Dataset.metrics.views      MetricAggregation
   Dataset.metrics.              (daily/monthly)
     resources_downloads
   Reuse.metrics.views
   Organization.metrics.views
              │
              ▼
   Frontend lê via API:
   dataset.metrics.views
   dataset.metrics.resources_downloads
```

**Separação de eventos (importante):**
- `view` — contado como visualização de página (1x por sessão por objeto, via `sessionStorage`)
- `download` — contado como download de resource (1x por click)
- `api_call` — registado pelo listener de `on_api_call`, **NÃO contado como view** (uma página gera múltiplas chamadas API)
- `search` — registado quando o utilizador submete uma pesquisa
- `click` — registado para clicks em links externos

---

## Frontend — Integração de tracking

### Componentes com tracking ativo

| Componente | Tipo de tracking | Evento |
|------------|-----------------|--------|
| `DatasetDetailClient.tsx` | Page view | `usePageTracking("dataset", dataset?.id)` |
| `OrganizationDetailClient.tsx` | Page view | `usePageTracking("organization", organization?.id)` |
| `ReuseDetailClient.tsx` | Page view | `usePageTracking("reuse", reuse?.id)` |
| `DatasetResourcesTable.tsx` | Download | `trackDownload(resource.id, datasetId)` no click |
| `DatasetsClient.tsx` | Pesquisa | `trackSearch(query)` ao submeter pesquisa |

### Funções de tracking disponíveis

Em `frontend/src/services/tracking.ts`:

```typescript
import { trackPageView, trackDownload, trackSearch, trackClick } from '@/services/tracking';

// Page view (usado automaticamente pelo hook usePageTracking)
trackPageView("dataset", "698c9485916701f5806d3161");

// Download de resource (com referência ao dataset pai)
trackDownload("resource-id", "dataset-id");

// Pesquisa
trackSearch("educação");

// Click externo
trackClick("https://example.com", "dataset", "dataset-id");
```

### Hook `usePageTracking`

Em `frontend/src/hooks/usePageTracking.ts`:

```typescript
import { usePageTracking } from '@/hooks/usePageTracking';

// Dentro de um componente 'use client'
usePageTracking("dataset", dataset?.id);
```

**Deduplicação por sessão**: o hook usa `sessionStorage` para garantir que cada objeto é contado apenas **uma vez por sessão de browser**. Isto previne:
- Re-mounts do React / Next.js App Router
- React 19 Strict Mode (double effects em dev)
- Navegar para a mesma página várias vezes
- Voltar ao tab depois de clicar num download (`target="_blank"`)

A sessão reseta quando o utilizador fecha o tab ou o browser.

### Downloads — Campo na API

O backend armazena downloads no campo `metrics.resources_downloads` (não `metrics.downloads`).
O frontend deve sempre ler `dataset.metrics?.resources_downloads`:

```typescript
// Correto
dataset.metrics?.resources_downloads

// Incorreto (campo não existe na serialização da API)
dataset.metrics?.downloads
```

Isto porque o modelo `Dataset` define `__metrics_keys__` que inclui `resources_downloads`, e `get_metrics()` só retorna keys dessa lista.

---

## Ficheiros do sistema

| Ficheiro | Descrição |
|----------|-----------|
| `backend/udata/core/metrics/events.py` | Modelo `MetricEvent` — eventos raw com TTL 90 dias |
| `backend/udata/core/metrics/aggregations.py` | Modelo `MetricAggregation` — dados pré-agregados daily/monthly |
| `backend/udata/core/metrics/listeners.py` | Listener `on_api_call` — regista chamadas API como eventos |
| `backend/udata/core/metrics/api.py` | Endpoint `POST /api/1/tracking/` — recebe eventos do frontend |
| `backend/udata/core/metrics/tasks.py` | Tasks Celery: `update-metrics` e `aggregate-metrics` |
| `backend/udata/core/metrics/helpers.py` | `get_metrics_for_model()` — fallback para dados internos |
| `backend/udata/core/metrics/__init__.py` | `init_app()` — conecta listeners quando `TRACKING_ENABLED=True` |
| `backend/udata/api/__init__.py` | Registo do endpoint de tracking |
| `backend/udata/settings.py` | Configurações: `TRACKING_ENABLED`, `TRACKING_EVENT_TTL_DAYS` |
| `backend/udata/migrations/2026-03-17-*` | Migração para criar índices |
| `frontend/src/services/tracking.ts` | Serviço de tracking — `sendBeacon` com fallback para `fetch` |
| `frontend/src/hooks/usePageTracking.ts` | Hook — 1 view por sessão por objeto |
| `frontend/src/components/datasets/DatasetResourcesTable.tsx` | Tracking de downloads nos links de resources |
| `frontend/src/components/datasets/DatasetDetailClient.tsx` | Tracking de page view para datasets |
| `frontend/src/components/organizations/OrganizationDetailClient.tsx` | Tracking de page view para organizations |
| `frontend/src/components/reuses/ReuseDetailClient.tsx` | Tracking de page view para reuses |
| `frontend/src/components/datasets/DatasetsClient.tsx` | Tracking de pesquisa |

---

## Decisões de design

- **IP anonimizado**: último octeto zerado antes de guardar (RGPD)
- **TTL 90 dias** nos eventos raw: MongoDB auto-deleta; dados agregados em `MetricAggregation` ficam indefinidamente
- **`navigator.sendBeacon`** no frontend: não bloqueia navegação
- **Backward compat**: se `METRICS_API` está configurado com uma URL, comportamento antigo continua
- **Sem auth no /tracking/**: tracking deve funcionar para utilizadores anónimos
- **Rate limiting**: deve ser tratado ao nível do reverse proxy (nginx)
- **Lookup por slug ou ObjectId**: o listener captura slugs do URL da API; a task `update_metrics_from_internal()` usa `save_model_by_id_or_slug()` que tenta por ObjectId primeiro e depois por slug
- **Regex do listener**: só aceita slugs com pelo menos um hífen (ex: `meu-dataset-1`) ou ObjectIds hex de 24 chars; ignora sub-endpoints como `badges`, `licenses`, `frequencies`, `schemas`
- **Views contam apenas `event_type: "view"`**: eventos `api_call` são registados mas **não** contados como views, porque uma única visita a uma página gera múltiplas chamadas API (4-7 por página)
- **Deduplicação de views por sessão**: o hook `usePageTracking` usa `sessionStorage` para evitar contagens repetidas na mesma sessão de browser
- **Downloads separados de views**: cada evento tem o seu `event_type` (`view` vs `download`), e são agregados em campos diferentes (`metrics.views` vs `metrics.resources_downloads`)

---

## Troubleshooting

### Views não atualizam após correr `update-metrics`

1. **Verificar `METRICS_API`**: se estiver definido no `.env` ou `udata.cfg`, a task usa o serviço externo (legacy). Comentar ou remover para usar o sistema interno:
   ```bash
   grep METRICS_API backend/.env
   # Se aparecer uma URL, comentar a linha
   ```

2. **Verificar se existem eventos**: se não houver `MetricEvent` no MongoDB, não há nada para agregar:
   ```bash
   cd backend && uv run python -c "
   from udata.app import create_app; app = create_app()
   with app.app_context():
       from udata.core.metrics.events import MetricEvent
       print(f'Total: {MetricEvent.objects.count()}')
       print(f'Views: {MetricEvent.objects(event_type=\"view\").count()}')
       print(f'Downloads: {MetricEvent.objects(event_type=\"download\").count()}')
   "
   ```

3. **Verificar se o listener está ativo**: o listener só se conecta quando `TRACKING_ENABLED=True` em `settings.py`

### Views inflacionadas (múltiplas views por visita)

**Causa**: eventos `api_call` estavam a ser contados como views. Uma página gera 4-7 chamadas API.

**Solução aplicada**: a pipeline de agregação em `update_metrics_from_internal()` filtra apenas `event_type: "view"`, excluindo `api_call`. Os eventos `api_call` ficam registados para estatísticas de uso da API mas não inflacionam as views.

### Downloads registam-se como views

**Causa**: ao clicar num link de download (`<a target="_blank">`), o browser pode re-montar o componente React ao voltar ao tab, disparando o `usePageTracking` outra vez.

**Solução aplicada**: o hook `usePageTracking` usa `sessionStorage` para deduplicar — cada combinação `objectType:objectId` é rastreada apenas uma vez por sessão de browser.

### Downloads não aparecem na UI

**Causa**: o frontend lia `metrics.downloads` mas a API devolve `metrics.resources_downloads`. O campo `downloads` não existe no `__metrics_keys__` do modelo Dataset, por isso era filtrado na serialização.

**Solução aplicada**: o frontend foi corrigido para ler `metrics.resources_downloads` em todos os componentes (DatasetDetailClient, DatasetsClient, OrganizationTabs, ReuseDetailClient).

### Eventos com object_id inválido (sub-endpoints)

O regex do listener (`listeners.py`) filtra sub-endpoints. Se aparecerem eventos com `object_id` como `badges` ou `licenses`, o regex precisa de ser atualizado. O padrão atual aceita:
- Slugs: devem conter pelo menos um hífen (ex: `meu-dataset-1`)
- ObjectIds: hex de 24 chars (ex: `698c9485916701f5806d3161`)

### Frontend não envia tracking

1. Verificar que `NEXT_PUBLIC_API_BASE` aponta para o backend:
   ```bash
   grep NEXT_PUBLIC_API_BASE frontend/.env.local
   # Deve ser: http://localhost:7000/api/1
   ```

2. No browser, abrir Network tab e filtrar por `tracking` — deve aparecer um POST ao navegar para um dataset

3. Verificar `sessionStorage` no browser — se a key `tracked:dataset:<id>` existir, o view já foi enviado nesta sessão. Limpar sessionStorage para forçar novo envio.

---

## Verificação

1. **Teste rápido end-to-end**:
   ```bash
   # 1. Enviar um view
   curl -X POST http://localhost:7000/api/1/tracking/ \
     -H "Content-Type: application/json" \
     -d '{"event_type":"view","object_type":"dataset","object_id":"<DATASET-ID>"}'

   # 2. Enviar um download
   curl -X POST http://localhost:7000/api/1/tracking/ \
     -H "Content-Type: application/json" \
     -d '{"event_type":"download","object_type":"resource","object_id":"<RESOURCE-ID>","extra":{"dataset_id":"<DATASET-ID>"}}'

   # 3. Atualizar modelos
   cd backend && uv run udata job run update-metrics

   # 4. Verificar na API
   curl -s http://localhost:7000/api/1/datasets/<SLUG> | python3 -c "
   import sys,json; d=json.load(sys.stdin); m=d['metrics']
   print(f'views: {m.get(\"views\",0)}, downloads: {m.get(\"resources_downloads\",0)}')"
   ```

2. **Teste frontend**: navegar para página de dataset, verificar no Network tab que:
   - Um `POST /api/1/tracking/` com `event_type: "view"` é enviado ao carregar a página
   - Um `POST /api/1/tracking/` com `event_type: "download"` é enviado ao clicar num link de download
   - O view **não** é reenviado ao clicar num download ou ao voltar à mesma página

3. **Teste de agregação**: correr task `aggregate-metrics`, verificar que `MetricAggregation` contém dados

4. **Backward compat**: com `METRICS_API` configurado com URL, verificar que task antiga continua a funcionar

### Migração de base de dados

Criar os índices (correr uma vez após deploy):

```bash
cd backend && uv run udata db upgrade
```

A migração `2026-03-17-create-metrics-events-collection.py` cria:
- Collection `metric_event` com TTL index (90 dias) e índices compostos
- Collection `metric_aggregation` com índice único composto
