# Metrics Jobs & Commands — Atualização Permanente

Reference guide for the Celery jobs, udata CLI commands, and scheduling needed to keep metrics permanently up to date.

> For the full pipeline architecture see [metrics-dual-system.md](metrics-dual-system.md) and [metrics-workflow.md](metrics-workflow.md).

---

## Context: Two Operating Modes

The `update-metrics` job behaves differently depending on whether `METRICS_API` is configured:

| Mode         | Condition                      | Data source                                           |
| ------------ | ------------------------------ | ----------------------------------------------------- |
| **External** | `METRICS_API` is set           | Reads from the external PostgREST API (api-tabular)   |
| **Internal** | `METRICS_API = None` (default) | Aggregates `MetricEvent` documents from local MongoDB |

The other two jobs (`aggregate-metrics`, `compute-site-metrics`) are independent of this setting and must always run regardless of the mode.

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
6. `aggregate_org_downloads()` _(added in PR #27)_ — aggregates `resources_downloads` from datasets into their parent organization via MongoDB pipeline

**Internal mode** — calls `update_metrics_from_internal()`, which runs five MongoDB aggregation pipelines over `MetricEvent`:

| Pipeline           | Matches                                           | Updates                               |
| ------------------ | ------------------------------------------------- | ------------------------------------- |
| Dataset views      | `event_type="view"`, `object_type="dataset"`      | `Dataset.metrics.views`               |
| Dataset downloads  | `event_type="download"`                           | `Dataset.metrics.resources_downloads` |
| Reuse views        | `event_type="view"`, `object_type="reuse"`        | `Reuse.metrics.views`                 |
| Organization views | `event_type="view"`, `object_type="organization"` | `Organization.metrics.views`          |
| Dataservice views  | `event_type="view"`, `object_type="dataservice"`  | `Dataservice.metrics.views`           |

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
2. update-metrics            — propagate metrics to model documents
3. compute-site-metrics      — recalculate portal-wide totals
4. compute-geozones-metrics  — recalculate dataset count per spatial zone
5. purge-harvesters          — clean up deleted harvest sources
```

`aggregate-metrics` must run first (in internal mode) so `update-metrics` reads up-to-date aggregations. `compute-site-metrics` and `compute-geozones-metrics` depend on the model documents being current, so they run after. `purge-harvesters` is independent and can run at any time.

---

## Running via Docker (production)

The container name is `udata-backend-app`. Use `docker exec` to run jobs directly inside the container.

### One-shot manual execution

```bash
docker exec -it udata-backend-app udata job run aggregate-metrics
docker exec -it udata-backend-app udata job run update-metrics
docker exec -it udata-backend-app udata job run compute-site-metrics
docker exec -it udata-backend-app udata job run compute-geozones-metrics
docker exec -it udata-backend-app udata job run purge-harvesters
```

### Schedule permanent jobs

```bash
docker exec -it udata-backend-app udata job schedule "0 2 * * *" aggregate-metrics
docker exec -it udata-backend-app udata job schedule "0 3 * * *" update-metrics
docker exec -it udata-backend-app udata job schedule "0 4 * * *" compute-site-metrics
docker exec -it udata-backend-app udata job schedule "0 9 * * *" compute-geozones-metrics
docker exec -it udata-backend-app udata job schedule "10 9 * * *" purge-harvesters
```

### Manage scheduled jobs

```bash
# List all scheduled jobs
docker exec -it udata-backend-app udata job scheduled

# Remove a scheduled job
docker exec -it udata-backend-app udata job unschedule update-metrics
docker exec -it udata-backend-app udata job unschedule aggregate-metrics
docker exec -it udata-backend-app udata job unschedule compute-site-metrics
docker exec -it udata-backend-app udata job unschedule compute-geozones-metrics
docker exec -it udata-backend-app udata job unschedule purge-harvesters
```

> The cron format is standard five-field: `minute hour day-of-month month day-of-week`.
> Schedules are stored as `PeriodicTask` entries in MongoDB (collection: `schedules`).

---

## One-Shot Manual Execution (local dev)

```bash
cd backend

udata job run aggregate-metrics
udata job run update-metrics
udata job run compute-site-metrics
udata job run compute-geozones-metrics
udata job run purge-harvesters
```

---

## CLI Command: `udata metrics update`

**File:** `backend/udata/core/metrics/commands.py`

A direct synchronous command (not a Celery job) that triggers the same metric update logic. Useful for one-off runs or scripting outside of Celery.

```bash
cd backend

# Update all metrics (default)
udata metrics update

# Selective update
udata metrics update --datasets
udata metrics update --organizations
udata metrics update --reuses
udata metrics update --dataservices
udata metrics update --users
udata metrics update --geozones
udata metrics update --site

# Drop existing metrics before updating
udata metrics update --drop

# Available flags
udata metrics update --help
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

| Job                        | What it updates                                              | Queue         | Cron (recommended) |
| -------------------------- | ------------------------------------------------------------ | ------------- | ------------------ |
| `aggregate-metrics`        | `MetricAggregation` (daily + monthly history)                | `low.metrics` | `0 2 * * *`        |
| `update-metrics`           | `Dataset`, `Reuse`, `Organization`, `Dataservice` `.metrics` | `low.metrics` | `0 3 * * *`        |
| `compute-site-metrics`     | `Site.metrics` (portal totals)                               | default       | `0 4 * * *`        |
| `compute-geozones-metrics` | `GeoZone.metrics` (dataset count per zone)                   | default       | `0 9 * * *`        |
| `purge-harvesters`         | Removes deleted `HarvestSource` documents                    | `low.harvest` | `10 9 * * *`       |
| `udata metrics update`     | Same as `update-metrics` (synchronous CLI)                   | —             | —                  |
