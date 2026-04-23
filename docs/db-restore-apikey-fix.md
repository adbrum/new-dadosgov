# Fix: apikey migration after MongoDB restore

When restoring a database dump that still contains the `apikey` field on `User` documents,
the backend crashes on login with:

```
mongoengine.errors.FieldDoesNotExist: The fields "{'apikey'}" do not exist on the document "User"
```

This happens because the dump includes the `migrations` collection (recording which migrations
already ran on the source system). The migration `2026-01-28-migrate-apikeys-to-api-tokens.py`,
which removes `apikey` from User documents, may be marked as applied or blocked by a prior failure.

## Steps

### 1. Restore the dump as normal

```bash
docker exec -i udata-mongodb mongorestore --drop --db udata /dump/udata
```

### 2. Mark all pending migrations as recorded (without executing them)

This avoids re-running migrations that the source system already applied.

```bash
cd backend
uv run udata db migrate --record
```

### 3. Remove the false record for the apikey migration

```bash
uv run udata db unrecord 2026-01-28-migrate-apikeys-to-api-tokens.py
```

### 4. Run the migration for real

```bash
uv run udata db migrate
```

This executes `2026-01-28-migrate-apikeys-to-api-tokens.py`, which:

- Migrates existing `User.apikey` values into the `api_token` collection
- Removes the `apikey` field from all User documents via `$unset`

### 5. Verify

```bash
uv run udata db status | grep apikey
```

Expected output:

```
2026-01-28-migrate-apikeys-to-api-tokens .......... [2026-xx-xx xx:xx]
```

## Why `--record` first?

The `migrate` command stops on the first failure and skips all subsequent migrations.
If any migration between the last recorded one and `2026-01-28` fails (e.g. because
the data it targets does not exist locally), the apikey migration never runs.
Using `--record` first marks those intermediate migrations as done, then unrecording
`2026-01-28` lets it run in isolation on the next `migrate` call.

## Temporary workaround (if migration cannot run)

Add `"strict": False` to the `User` model meta in `udata/core/user/models.py`
so mongoengine ignores unknown fields instead of crashing:

```python
meta = {
    ...
    "strict": False,
}
```

Remove this once the migration has been applied and the dump no longer contains `apikey`.
