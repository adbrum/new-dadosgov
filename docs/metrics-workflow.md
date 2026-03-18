# Metrics Workflow — dados.gov.pt

Complete documentation of the metrics pipeline: how page views, downloads, and statistics flow through the system.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  User visits page / downloads resource                                  │
│  (Frontend → Backend API)                                               │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  1. UDATA (Flask Backend)                                                │
│     after_request hook → TrackingEvent saved to MongoDB                  │
│     Collection: tracking_events                                          │
│     Events: "view" (page visit) | "download" (resource redirect)         │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  2. AIRFLOW DAG: exemplo_etl (runs every minute)                         │
│                                                                          │
│  Task 1: extract_tracking_events                                         │
│     → Reads tracking_events from MongoDB                                 │
│     → Aggregates views/downloads per dataset, org, reuse, dataservice    │
│     → Computes site-level statistics                                     │
│                                                                          │
│  Task 2: send_to_metrics_db                                              │
│     → Writes aggregated views + downloads to PostgreSQL (Hydra CSV DB)   │
│                                                                          │
│  Task 3: update_udata_metrics                                            │
│     → Reads datasets_total from PostgREST (api-tabular)                  │
│     → Writes metrics.views + metrics.resources_downloads to MongoDB      │
│     → Writes per-resource download counts (resources.$.metrics.views)    │
│     → Computes followers, discussions, reuses per dataset                 │
│     → Computes org stats (datasets, reuses, followers, views)            │
│     → Updates site-level metrics                                         │
│                                                                          │
│  Task 4: save_to_mongodb                                                 │
│     → Saves ETL execution log to hydra_metrics.metrics_logs              │
│                                                                          │
│  Flow: Task 1 → Task 2 → Task 3 → Task 4 (sequential)                   │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  3. API-TABULAR (PostgREST on port 8006)                                 │
│     Exposes PostgreSQL views as REST endpoints:                          │
│       /api/datasets_total/data/                                          │
│       /api/resources_total/data/                                         │
│       /api/organizations_total/data/                                     │
│       /api/reuses_total/data/                                            │
│       /api/dataservices_total/data/                                      │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  4. FRONTEND (Next.js)                                                   │
│     Reads dataset.metrics from /api/1/datasets/{slug}/                   │
│     Displays: views, resources_downloads, followers, reuses, discussions │
└──────────────────────────────────────────────────────────────────────────┘
```

## Components in Detail

### 1. Udata — Internal Tracking

**File:** `backend/udata/core/metrics/tracking.py`

The tracking system captures two types of events via a Flask `after_request` hook registered in `backend/udata/api/__init__.py`:

| Event Type | Trigger | Endpoint | What is Stored | Deduplication |
|---|---|---|---|---|
| `view` | User visits a detail page | `api.dataset`, `api.organization`, `api.reuse`, `api.dataservice`, `apiv2.dataset` | `object_type` + `object_id` + `visitor_ip` | Same IP + object: 1 view per 5 minutes |
| `download` | User downloads a resource | `api.resource_redirect` | `object_type=dataset` + parent `dataset_id` + `resource_id` + `visitor_ip` | None — every click counts |

**Deduplication rules:**
- **Views**: repeated visits from the same IP to the same object within 5 minutes (`DEDUP_WINDOW_SECONDS = 300`) are ignored. This prevents inflated counts from page refreshes or frontend re-renders.
- **Downloads**: no deduplication — each resource download click is counted individually, as each click represents an intentional user action.

**MongoDB Collection:** `tracking_events`

View event:
```json
{
    "object_type": "dataset",
    "object_id": "698c9485916701f5806d3161",
    "event_type": "view",
    "resource_id": null,
    "visitor_ip": "192.168.1.10",
    "created_at": "2026-03-18T16:49:03.431Z"
}
```

Download event:
```json
{
    "object_type": "dataset",
    "object_id": "694977089cca6dc28af160a7",
    "event_type": "download",
    "resource_id": "e56b6cfb-6ad7-4843-b624-2f4ee05d224e",
    "visitor_ip": "192.168.1.10",
    "created_at": "2026-03-18T17:02:15.812Z"
}
```

**Indexes:**
- `(object_type, event_type)` — for aggregation queries
- `(object_type, object_id)` — for per-object lookups
- `(object_id, event_type, visitor_ip, created_at)` — for deduplication queries
- `(resource_id, event_type)` — for per-resource download aggregation
- `created_at` with TTL of 90 days — automatic cleanup

**Tracked Endpoints:**

| Endpoint | URL Pattern | Event |
|---|---|---|
| `api.dataset` | `/api/1/datasets/<dataset>/` | view |
| `apiv2.dataset` | `/api/2/datasets/<dataset>/` | view |
| `api.organization` | `/api/1/organizations/<org>/` | view |
| `api.reuse` | `/api/1/reuses/<reuse>/` | view |
| `api.dataservice` | `/api/1/dataservices/<dataservice>/` | view |
| `api.resource_redirect` | `/api/1/datasets/r/<uuid>/` | download |

### 2. Airflow DAG — `exemplo_etl`

**Location:** Airflow container at `/opt/airflow/dags/exemplo.py`
**Schedule:** Every minute (`* * * * *`)
**Container:** `airflow-demo-test` (port 18080 for web UI)

#### Task 1: `extract_tracking_events`

Reads from MongoDB `tracking_events` and aggregates:

```
tracking_events (MongoDB)
    → GROUP BY object_id WHERE object_type="dataset" AND event_type="view"
    → GROUP BY object_id WHERE object_type="dataset" AND event_type="download"
    → GROUP BY resource_id WHERE event_type="download" AND resource_id exists
    → GROUP BY object_id WHERE object_type="organization" AND event_type="view"
    → GROUP BY object_id WHERE object_type="reuse" AND event_type="view"
    → GROUP BY object_id WHERE object_type="dataservice" AND event_type="view"
```

Also computes site-level counts directly from MongoDB collections:
- `dataset.count_documents({deleted: null})` → total datasets
- Aggregation on `dataset.resources` → total resources
- `organization`, `reuse`, `user`, `discussion`, `follow` counts

#### Task 2: `send_to_metrics_db`

Writes to PostgreSQL (Hydra CSV database, port 5434):

**Table:** `datasets`

| Column | Type | Description |
|---|---|---|
| `dataset_id` | varchar(50) | Dataset ObjectId |
| `metric_month` | varchar(7) | e.g. "2026-03" |
| `monthly_visit` | integer | View count from tracking |
| `monthly_download_resource` | integer | Download count from tracking |

Uses `ON CONFLICT (dataset_id, metric_month) DO UPDATE` for upsert.

#### Task 3: `update_udata_metrics`

Reads from PostgREST (api-tabular) and writes back to MongoDB:

**Step 1 — Views & Downloads from PostgreSQL:**
```
GET http://api-tabular:8006/api/datasets_total/data/?visit__greater=0&page_size=50
    → dataset.metrics.views = visit
    → dataset.metrics.resources_downloads = download_resource
```

**Step 2 — Per-resource download counts from tracking_events:**
```
tracking_events (GROUP BY resource_id WHERE event_type="download")
    → dataset.resources.$.metrics.views = download count per resource
    (uses MongoDB positional operator $ to update the matching embedded resource)
    (query: {"resources._id": resource_id} — stored as string in MongoDB)
```

**Step 3 — Per-dataset statistics from MongoDB:**
```
follow collection    → dataset.metrics.followers
discussion collection → dataset.metrics.discussions, dataset.metrics.discussions_open
reuse collection     → dataset.metrics.reuses
```

**Step 4 — Per-organization statistics from MongoDB:**
```
dataset collection  → organization.metrics.datasets
reuse collection    → organization.metrics.reuses
follow collection   → organization.metrics.followers
tracking_events     → organization.metrics.views
```

**Step 5 — Site-level metrics:**
```
site document → site.metrics.{datasets, resources, organizations, reuses, users, ...}
metrics collection → daily snapshot
```

#### Task 4: `save_to_mongodb`

Saves execution log to `hydra_metrics.metrics_logs`:

```json
{
    "timestamp": "2026-03-18T17:25:45.123Z",
    "dag_id": "exemplo_etl",
    "total_tracking_events": 156,
    "datasets_with_views": 12,
    "datasets_with_downloads": 3,
    "metrics_written_pg": 12,
    "datasets_updated_mongo": 1001,
    "site_counts": { "datasets": 20339, "organizations": 422, ... },
    "status": "success"
}
```

### 3. Hydra — PostgreSQL Database

**Container:** `hydra-pt-database-csv-1`
**Port:** 5434 (mapped from container 5432)
**Connection:** `postgres://postgres:postgres@localhost:5434/postgres`

#### Tables (written by Airflow)

| Table | Primary Key | Columns |
|---|---|---|
| `datasets` | `(dataset_id, metric_month)` | `monthly_visit`, `monthly_download_resource` |
| `organizations` | `(organization_id, metric_month)` | `monthly_visit_dataset` |
| `reuses` | `(reuse_id, metric_month)` | `monthly_visit` |
| `dataservices` | `(dataservice_id, metric_month)` | `monthly_visit` |
| `resources` | `(resource_id, metric_month)` | `download_resource` |

#### Views (consumed by PostgREST / api-tabular)

| View | Aggregation |
|---|---|
| `datasets_total` | `SUM(monthly_visit)`, `SUM(monthly_download_resource)` per dataset |
| `organizations_total` | `SUM(monthly_visit_dataset)` per organization |
| `reuses_total` | `SUM(monthly_visit)` per reuse |
| `dataservices_total` | `SUM(monthly_visit)` per dataservice |
| `resources_total` | `SUM(download_resource)` per resource |

### 4. API-Tabular — PostgREST

**Container:** `api-tabular-pt-postgrest-1`
**Port:** 8006 (external), 8080 (internal)
**Config:** Reads from Hydra PostgreSQL, exposes views as REST.

Example request:
```
GET http://localhost:8006/api/datasets_total/data/?visit__greater=1&page_size=50
```

Response:
```json
{
    "data": [
        {"dataset_id": "698c9485916701f5806d3161", "visit": 16, "download_resource": 0, "__id": 109009}
    ],
    "links": {"next": null, "prev": null},
    "meta": {"page": 1, "page_size": 50, "total": 1}
}
```

**Note:** Pagination links returned by api-tabular may contain incorrect ports (port 8005 instead of 8006). The udata `update-metrics` job has a `_rebase_url()` fix in `backend/udata/core/metrics/tasks.py` that rewrites these URLs.

### 5. Frontend — Displaying Metrics

**Type definition:** `frontend/src/types/api.ts`

```typescript
export interface Metric {
    views?: number;
    followers?: number;
    reuses?: number;
    resources_downloads?: number;
    discussions?: number;
}
```

**Components that display metrics:**

| Component | Metrics Shown |
|---|---|
| `DatasetDetailClient.tsx` | views, resources_downloads |
| `DatasetsClient.tsx` | views, resources_downloads, reuses, followers |
| `OrganizationDetailClient.tsx` | views, followers |
| `OrganizationTabs.tsx` | views, resources_downloads, reuses, followers, datasets count |
| `ReuseDetailClient.tsx` | views, followers |
| `OrgStatisticsClient.tsx` | views |
| Homepage (`page.tsx`) | site metrics (datasets, organizations, reuses) |

**Download links — tracked via backend redirect:**

Resource download links in `DatasetResourcesTable.tsx` use the backend redirect endpoint instead of linking directly to the resource URL:

```
href={`${API_BASE_URL}/datasets/r/${resource.id}/`}
```

This ensures every download click passes through `api.resource_redirect`, which creates a `TrackingEvent(event_type="download")` before redirecting (302) to the actual file URL. The `downloadUrl(resource)` helper function in `DatasetResourcesTable.tsx` builds these URLs.

## Data Flow Summary

```
User action          Storage               Process              Storage              Output
─────────────────────────────────────────────────────────────────────────────────────────────
Visit dataset   →  tracking_events     →  Airflow DAG      →  PostgreSQL        →  PostgREST
page               (MongoDB)              extract task         datasets table       /datasets_total
                                                                    │
Download        →  tracking_events     →  Airflow DAG      →  PostgreSQL        →  PostgREST
resource           (MongoDB)              extract task         datasets table       /datasets_total
                   (with resource_id)          │                    │
                                               │                    │
                                               ▼                    │
                                          resource.metrics  ←───────┘
                                          (per resource)     Airflow DAG
                                               │             update task
                                               │                    │
                                               ▼                    ▼
                                          dataset.metrics    →  /api/1/datasets/  →  Frontend
                                          (MongoDB)              {slug}/
```

The Airflow DAG update task writes at **three levels**:
1. `dataset.metrics.views` / `dataset.metrics.resources_downloads` — from PostgreSQL aggregates
2. `dataset.resources.$.metrics.views` — per-resource download count, directly from tracking_events
3. `dataset.metrics.followers/discussions/reuses` — computed from MongoDB collections

## Metrics Computed

### Per Dataset
| Metric | Source | Updated By |
|---|---|---|
| `views` | tracking_events (view) → PostgreSQL → MongoDB | Airflow DAG |
| `resources_downloads` | tracking_events (download) → PostgreSQL → MongoDB | Airflow DAG |
| `followers` | `follow` collection aggregation | Airflow DAG |
| `discussions` | `discussion` collection aggregation | Airflow DAG |
| `discussions_open` | `discussion` collection (closed=null) | Airflow DAG |
| `reuses` | `reuse` collection aggregation | Airflow DAG |

### Per Resource (embedded in Dataset)
| Metric | Source | Updated By |
|---|---|---|
| `resources.$.metrics.views` | tracking_events (download, grouped by resource_id) | Airflow DAG |

Note: the field is named `views` for legacy compatibility, but it represents **download count** for the individual resource. The resource ID is stored as `resources._id` (string) in MongoDB.

### Per Organization
| Metric | Source |
|---|---|
| `views` | tracking_events (view) |
| `datasets` | `dataset` collection count |
| `reuses` | `reuse` collection count |
| `followers` | `follow` collection count |

### Site-Level
| Metric | Source |
|---|---|
| `datasets` | `dataset.count_documents({deleted: null})` |
| `resources` | Aggregation of `dataset.resources` array sizes |
| `organizations` | `organization.count_documents({deleted: null})` |
| `reuses` | `reuse.count_documents({deleted: null})` |
| `users` | `user.estimated_document_count()` |
| `discussions` | `discussion.estimated_document_count()` |
| `dataservices` | `dataservice.count_documents({deleted: null})` |
| `followers` | `follow.estimated_document_count()` |

## Infrastructure

| Service | Container | Port | Database |
|---|---|---|---|
| udata (Flask API) | host | 7000 | MongoDB 27017 |
| MongoDB | host | 27017 | `udata` |
| PostgreSQL (Hydra CSV) | `hydra-pt-database-csv-1` | 5434 | `postgres` |
| PostgREST (api-tabular) | `api-tabular-pt-postgrest-1` | 8006 | reads from Hydra CSV |
| Airflow webserver | `airflow-demo-test` | 18080 | Airflow metadata on 15432 |
| Frontend (Next.js) | host | 3000 | — |

## Manual Operations

### Run metrics update manually (legacy, without Airflow)
```bash
cd backend
uv run udata job run update-metrics
```

### Run site metrics computation manually
```bash
cd backend
uv run udata job run compute-site-metrics
```

### Trigger Airflow DAG manually
```bash
curl -X POST -u "user:pass" "http://localhost:18080/api/v1/dags/exemplo_etl/dagRuns" \
  -H "Content-Type: application/json" -d '{"conf": {}}'
```

### Check tracking events in MongoDB
```bash
uv run python -c "
from udata.app import create_app, standalone
app = create_app()
standalone(app)
with app.app_context():
    from udata.core.metrics.tracking import TrackingEvent
    print('Total events:', TrackingEvent.objects.count())
    print('Views:', TrackingEvent.objects(event_type='view').count())
    print('Downloads:', TrackingEvent.objects(event_type='download').count())
"
```

### Check metrics in PostgreSQL
```bash
PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d postgres \
  -c "SELECT * FROM datasets_total WHERE dataset_id = '<id>'"
```

### Check Airflow DAG logs
```bash
curl -u "user:pass" \
  "http://localhost:18080/api/v1/dags/exemplo_etl/dagRuns?order_by=-start_date&limit=1"
```

## Playwright Tests

End-to-end tests in `frontend/tests/`:

| Test File | What it Tests |
|---|---|
| `metrics-update.spec.ts` | **Pipeline direto** (3 tests): PostgreSQL → udata job → MongoDB → Frontend |
| | **Pipeline Airflow** (5 tests): tracking_events → DAG → PostgreSQL → MongoDB → Frontend |
| `metrics-downloads.spec.ts` | **Downloads pipeline** (5 tests): resource redirect → tracking → DAG → PostgreSQL → MongoDB → Frontend |

Run with:
```bash
cd frontend
npx playwright test tests/metrics-update.spec.ts
npx playwright test tests/metrics-downloads.spec.ts
```

## Known Issues & Notes

1. **PostgREST pagination URLs** — api-tabular returns `links.next` with port 8005 instead of 8006. Fixed in `backend/udata/core/metrics/tasks.py` with `_rebase_url()`.
2. **TTL on tracking_events** — only the individual events in MongoDB `tracking_events` are auto-deleted after 90 days. The aggregated totals are **permanently preserved** in both PostgreSQL (`datasets` table) and MongoDB (`dataset.metrics`). After 90 days you lose the detail of "who visited when", but the totals never disappear.
3. **DAG $limit** — the legacy DAG had a `$limit: 1000` which excluded datasets. The new DAG aggregates from `tracking_events` without limits.
4. **Frontend field name** — the backend stores `resources_downloads`, not `downloads`. Frontend types and components were updated to match.
5. **View deduplication** — same IP visiting the same object within 5 minutes counts as 1 view. Configurable via `DEDUP_WINDOW_SECONDS` in `tracking.py`.
6. **Download counting** — no deduplication; every click on a resource download link counts as 1 download.
7. **Backend restart required** — after code changes to `tracking.py` or `api/__init__.py`, the backend server (`inv serve`) must be restarted for the tracking to take effect on the live server (port 7000).
