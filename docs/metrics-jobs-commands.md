# Metrics Jobs & Commands — Atualização Permanente

Reference guide for the Celery jobs, udata CLI commands, and scheduling needed to keep metrics permanently up to date.

> For the full pipeline architecture see [metrics-dual-system.md](metrics-dual-system.md) and [metrics-workflow.md](metrics-workflow.md).

---

## Context: Two Operating Modes

The `update-metrics` job behaves differently depending on whether `METRICS_API` is configured:

| Mode | Condition | Data source |
|---|---|---|
| **External** | `METRICS_API` is set | Reads from the external PostgREST API (api-tabular) |
| **Internal** | `METRICS_API = None` (default) | Aggregates `MetricEvent` documents from local MongoDB |

All other jobs and `udata metrics update` are **completely independent of `METRICS_API`** and must always run regardless of the mode.

### What each job/command reads and writes

| Job / Command | Reads from | Writes to | Affected by `METRICS_API`? |
|---|---|---|---|
| `aggregate-metrics` | `MetricEvent` (MongoDB) | `MetricAggregation` (MongoDB) | No |
| `update-metrics` | `MetricEvent` or PostgREST API | `Dataset`, `Reuse`, `Org`, `Dataservice` `.metrics.views` / `.resources_downloads` | **Yes** |
| `compute-site-metrics` | MongoDB collections (counts) | `Site.metrics` (MongoDB) | No |
| `compute-geozones-metrics` | `Dataset` collection (counts) | `GeoZone.metrics` (MongoDB) | No |
| `purge-harvesters` | `HarvestSource` collection | `HarvestSource` collection | No |
| `udata metrics update` | MongoDB relationships (counts) | `Dataset`, `Reuse`, `Org`, `Dataservice`, `User`, `Site`, `GeoZone` `.metrics` (MongoDB) | **No — always writes to MongoDB** |

> `udata metrics update` never reads from `MetricEvent` or from the external API. It counts related documents directly in MongoDB (`count_discussions()`, `count_followers()`, `count_members()`, etc.), so it always updates MongoDB regardless of whether `METRICS_API` is set or not.

---

## Additional Jobs

### `compute-geozones-metrics`

**File:** `backend/udata/core/spatial/tasks.py`

Iterates all `GeoZone` documents and recalculates the dataset count for each spatial zone (`geozone.count_datasets()`). Must run after `update-metrics` so dataset metadata is current.

---

### `purge-harvesters`

**File:** `backend/udata/harvest/tasks.py`
**Queue:** `low.harvest`

Purges `HarvestSource` documents that have been flagged as deleted. Should run periodically to keep the harvest collection clean.

---

> **Note:** `update-datasets-reuses-metrics` does not exist in the current codebase. It may belong to a different environment or a previous version of the platform. Do not schedule it.

---

## The Three Metrics Jobs

### `update-metrics`

**File:** `backend/udata/core/metrics/tasks.py`
**Queue:** `low.metrics`

Updates the `metrics` field on all model documents (Dataset, Reuse, Organization, Dataservice).

**External mode** — calls `update_metrics_for_models()`, which runs in sequence:

1. `update_datasets()` — syncs `views` and `resources_downloads` per dataset
2. `update_resources_and_community_resources()` — syncs download counts per individual resource
3. `update_dataservices()` — syncs `views` per dataservice
4. `update_reuses()` — syncs `views` per reuse
5. `update_organizations()` — syncs `views`, `resource_downloads`, `reuse_views`, `dataservice_views` per organization
6. `aggregate_org_downloads()` *(added in PR #27)* — aggregates `resources_downloads` from datasets into their parent organization via MongoDB pipeline

**Internal mode** — calls `update_metrics_from_internal()`, which runs five MongoDB aggregation pipelines over `MetricEvent`:

| Pipeline | Matches | Updates |
|---|---|---|
| Dataset views | `event_type="view"`, `object_type="dataset"` | `Dataset.metrics.views` |
| Dataset downloads | `event_type="download"` | `Dataset.metrics.resources_downloads` |
| Reuse views | `event_type="view"`, `object_type="reuse"` | `Reuse.metrics.views` |
| Organization views | `event_type="view"`, `object_type="organization"` | `Organization.metrics.views` |
| Dataservice views | `event_type="view"`, `object_type="dataservice"` | `Dataservice.metrics.views` |

> `event_type="api_call"` events are intentionally excluded — a single page visit generates multiple API calls, which would inflate view counts.

---

### `aggregate-metrics`

**File:** `backend/udata/core/metrics/tasks.py`
**Queue:** `low.metrics`

Aggregates yesterday's raw `MetricEvent` documents into permanent `MetricAggregation` records (daily and monthly granularity). This preserves historical data after the raw events are auto-deleted by the 90-day TTL index on the `metric_event` collection.

Must run **before** `update-metrics` when operating in internal mode, so the aggregations reflect the most recent events.

---

### `compute-site-metrics`

**File:** `backend/udata/core/metrics/tasks.py`

Recalculates portal-wide counters on the `Site` document:

- Total datasets, resources, organizations, reuses, dataservices, users
- Total followers, discussions, harvesters
- Stock metrics (new objects per month for the last 365 days)
- Per-entity max values (max followers, max reuses, etc.)

Emits the `on_site_metrics_computed` signal when finished.

---

## Recommended Execution Order

```
1. aggregate-metrics         — process yesterday's raw events into MetricAggregation
2. update-metrics            — propagate views/downloads to model documents
3. compute-site-metrics      — recalculate portal-wide totals
4. compute-geozones-metrics  — recalculate dataset count per spatial zone
5. purge-harvesters          — clean up deleted harvest sources
```

- `aggregate-metrics` must run first (internal mode) so `update-metrics` reads up-to-date aggregations.
- `compute-site-metrics` and `compute-geozones-metrics` depend on the model documents being current, so they run after `update-metrics`.
- `purge-harvesters` is independent and can run at any time.

---

## Running via Docker (production)

The container name is `udata-backend-app`. Use `docker exec` to run jobs directly inside the container.

### One-shot manual execution

```bash
docker exec -it udata-backend-app uv run udata job run aggregate-metrics
docker exec -it udata-backend-app uv run udata job run update-metrics
docker exec -it udata-backend-app uv run udata job run compute-site-metrics
docker exec -it udata-backend-app uv run udata job run compute-geozones-metrics
docker exec -it udata-backend-app uv run udata job run purge-harvesters
```

### Schedule permanent jobs

```bash
docker exec -it udata-backend-app uv run udata job schedule "0 2 * * *" aggregate-metrics
docker exec -it udata-backend-app uv run udata job schedule "0 3 * * *" update-metrics
docker exec -it udata-backend-app uv run udata job schedule "0 4 * * *" compute-site-metrics
docker exec -it udata-backend-app uv run udata job schedule "0 9 * * *" compute-geozones-metrics
docker exec -it udata-backend-app uv run udata job schedule "10 9 * * *" purge-harvesters
```

### Manage scheduled jobs

```bash
# List all scheduled jobs
docker exec -it udata-backend-app uv run udata job scheduled

# Remove a scheduled job
docker exec -it udata-backend-app uv run udata job unschedule aggregate-metrics
docker exec -it udata-backend-app uv run udata job unschedule update-metrics
docker exec -it udata-backend-app uv run udata job unschedule compute-site-metrics
docker exec -it udata-backend-app uv run udata job unschedule compute-geozones-metrics
docker exec -it udata-backend-app uv run udata job unschedule purge-harvesters
```

> The cron format is standard five-field: `minute hour day-of-month month day-of-week`.
> Schedules are stored as `PeriodicTask` entries in MongoDB (collection: `schedules`).

---

## One-Shot Manual Execution (local dev)

```bash
cd backend

uv run udata job run aggregate-metrics
uv run udata job run update-metrics
uv run udata job run compute-site-metrics
uv run udata job run compute-geozones-metrics
uv run udata job run purge-harvesters
```

---

## CLI Command: `udata metrics update`

**File:** `backend/udata/core/metrics/commands.py`

A synchronous CLI command (not a Celery job) that recomputes **relationship-based metrics** by iterating every document in the database. This is complementary to `update-metrics`: while `update-metrics` updates `views` and `resources_downloads` from event data, `udata metrics update` updates counters derived from relationships between objects (followers, discussions, reuses, members, etc.).

**This command must be run** — it is the only command that keeps relationship counters current. No Celery job covers all of what it does.

### What it computes (without flags — runs everything)

| Scope | Iterates | Computes per document |
|---|---|---|
| **Site** | `Site` (single document) | total users, orgs, datasets, resources, reuses, dataservices, followers, discussions, harvesters, stock metrics, per-entity maxima |
| **Datasets** | all visible `Dataset` | `discussions`, `reuses`, `dataservices`, `followers` |
| **Dataservices** | all visible `Dataservice` | `discussions`, `followers` |
| **Reuses** | all visible `Reuse` | `discussions`, `followers` |
| **Organizations** | all visible `Organization` | `datasets`, `reuses`, `dataservices`, `followers`, `members` |
| **Users** | all `User` | `datasets`, `reuses`, `dataservices`, `followers`, `following` |
| **GeoZones** | all `GeoZone` | `datasets` |

> Because it iterates every document, this command can take several minutes on large databases. Run it during off-peak hours.

### Important: not a scheduled job

`udata metrics update` is a synchronous CLI command — it **cannot** be scheduled with `udata job schedule`. It is intended for **manual execution only**, when there is suspicion that relationship counters are out of sync.

Relationship counters (followers, discussions, members) are kept current in real time via MongoEngine signals — each follow/unfollow action increments or decrements the counter immediately, without needing a periodic job. `udata metrics update` is a recovery tool to rebuild those counters from scratch if they drift.

The five Celery jobs above cover all routine metric updates. `udata metrics update` is not part of the regular schedule.

### Running via Docker (manual — production)

```bash
# Rebuild all relationship counters (run when counters seem out of sync)
docker exec -it udata-backend-app uv run udata metrics update

# Selective rebuild (faster — only the specified scope)
docker exec -it udata-backend-app uv run udata metrics update --datasets
docker exec -it udata-backend-app uv run udata metrics update --organizations
docker exec -it udata-backend-app uv run udata metrics update --reuses
docker exec -it udata-backend-app uv run udata metrics update --dataservices
docker exec -it udata-backend-app uv run udata metrics update --users

# Drop existing values before recomputing (full reset)
docker exec -it udata-backend-app uv run udata metrics update --drop
```

> `--site` and `--geozones` are already covered by the scheduled Celery jobs `compute-site-metrics` and `compute-geozones-metrics`. No need to include them in manual runs.

### Running locally (dev — manual)

```bash
cd backend

uv run udata metrics update
```

---

## Celery Worker

The jobs route to the `low.metrics` queue. The Celery worker must be running and consuming that queue:

```bash
cd backend

# Start the worker (consumes all queues including low.metrics)
inv work

# Verify the worker is running
uv run celery -A udata.tasks inspect active
```

---

## Summary Table

| Job | What it updates | Queue | Cron (recommended) |
|---|---|---|---|
| `aggregate-metrics` | `MetricAggregation` (daily + monthly history) | `low.metrics` | `0 2 * * *` |
| `update-metrics` | `views`, `resources_downloads` on Dataset, Reuse, Org, Dataservice | `low.metrics` | `0 3 * * *` |
| `compute-site-metrics` | `Site.metrics` (portal totals) | default | `0 4 * * *` |
| `compute-geozones-metrics` | `GeoZone.metrics` (dataset count per zone) | default | `0 9 * * *` |
| `purge-harvesters` | Removes deleted `HarvestSource` documents | `low.harvest` | `10 9 * * *` |

| Command | What it updates | When to run |
|---|---|---|
| `udata metrics update` | Relationship counters: `followers`, `discussions`, `members`, `reuses` on all models | Manual only — when counters seem out of sync |

> `udata metrics update` is a synchronous CLI command, not a Celery job. It **cannot** be scheduled with `udata job schedule` and is not part of the regular schedule.
