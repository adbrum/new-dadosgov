# Logrotate Setup - Backend Logs

How backend logs are collected on the host and rotated with `logrotate`.

This document covers the **dadosgov backend** (uwsgi + Celery worker + Celery beat) running under Docker Compose on a Linux host.

## Overview

Each backend container writes its log file to `/logs/` inside the container. That directory is bind-mounted from `./logs/` on the host, so logs are readable directly from the host without `docker exec` or `sudo`. A `logrotate` config caps file size at 10 MB and keeps a long history of compressed archives.

```
Container                           Host
─────────────────────────────────────────────────────────
udata-backend-app    /logs/app.log     →  ./logs/app.log
udata-backend-worker /logs/worker.log  →  ./logs/worker.log
udata-backend-beat   /logs/beat.log    →  ./logs/beat.log

                                      logrotate (cron)
                                      ├─ rotates at 10 MB
                                      ├─ keeps 50 historical files
                                      └─ gzips all but the most recent
```

What lands in each file:

| File         | Contents                                                                                                                     |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `app.log`    | uwsgi master events (workers buried, harakiri, deadlock), HTTP 4xx/5xx access lines, Python tracebacks from request handlers |
| `worker.log` | Celery worker output: task lifecycle, broker connection events, task tracebacks (e.g. failed downloads to `/dadosgov/fs/`)   |
| `beat.log`   | Celery scheduler events                                                                                                      |

## Prerequisites

1. **Host user `dadosgov`** with a stable UID/GID. The same UID/GID is used inside the containers so bind-mounted files have consistent ownership. On dadosgov hosts this is conventionally **UID/GID 10001**:

   ```sh
   id dadosgov
   # uid=10001(dadosgov) gid=10001(dadosgov) groups=10001(dadosgov),10(wheel),979(docker)
   ```

   If the user does not exist, create it: `sudo useradd --system --uid 10001 --gid 10001 --shell /sbin/nologin dadosgov` (after creating the matching group).

2. **The deploying user belongs to `wheel`** (or to `dadosgov`) so they can read the rotated logs without `sudo`. The `wheel` group works because the bind-mount directory inherits group `wheel` via setgid, and rotated files inherit it too.

3. **Docker Compose v2** and `logrotate` (already installed by default on RHEL 9 / Rocky 9 / Alma 9).

## Installation

### 1. Persist the host UID/GID for Docker builds

The backend `Dockerfile` accepts `UDATA_UID` / `UDATA_GID` as build args. Without these, the container's `dadosgov` user defaults to UID 10001 and bind-mounted files written from the host become unreachable from inside the container (and vice-versa).

Append to `backend/.env`:

```ini
# Host UID/GID for the 'dadosgov' user — keeps bind-mounted files writable by the host owner.
UDATA_UID=10001
UDATA_GID=10001
```

Adjust the values if `id dadosgov` returns something different on your host.

### 2. Confirm the bind-mounts in `backend/docker-compose.yml`

Each service must mount the host `./logs` directory:

```yaml
services:
  app:
    volumes:
      - ./logs:/logs
      # ...
  worker:
    volumes:
      - ./logs:/logs
      # ...
  beat:
    volumes:
      - ./logs:/logs
      # ...
```

The `app` service should also mount `./uwsgi:/app/uwsgi:ro` so changes to `front.ini` don't require a rebuild.

### 3. Confirm the uwsgi log destination in `backend/uwsgi/front.ini`

```ini
disable-logging = true       ; suppress per-request access logs
log-level = warning
log-master = true
umask = 022                  ; rotated files are 0644
logto = /logs/app.log
log-5xx = true
log-4xx = true
```

Do **not** set `log-maxsize` here — rotation is delegated to logrotate.

### 4. Confirm the Celery commands write to file

In `backend/docker-compose.yml`:

```yaml
worker:
  command: uv run celery -A udata.worker worker --events --concurrency=4 -l info --logfile=/logs/worker.log

beat:
  command: uv run celery -A udata.worker beat -l info --logfile=/logs/beat.log
```

### 5. Create the host log directory with the right permissions

```sh
mkdir -p /opt/dadosgov/backend/logs
chgrp wheel /opt/dadosgov/backend/logs
chmod 1777 /opt/dadosgov/backend/logs   # sticky bit + setgid effect via wheel group
```

Mode `1777` (`drwxrwxrwt`) lets the container write while the sticky bit prevents users from deleting each other's files. The setgid on the parent group propagates `wheel` to new files, which is what makes the logs readable by anyone in `wheel`.

### 6. Install the logrotate config

The repository ships the config under `backend/scripts/logrotate-dadosgov.conf`:

```sh
sudo cp /opt/dadosgov/backend/scripts/logrotate-dadosgov.conf /etc/logrotate.d/dadosgov
```

Contents:

```
/opt/dadosgov/backend/logs/*.log {
    su dadosgov dadosgov
    daily
    size 10M
    rotate 50
    compress
    delaycompress
    missingok
    notifempty
    dateext
    dateformat .%Y-%m-%d-%s
    copytruncate
}
```

Directive-by-directive:

| Directive                             | Effect                                                                                                                                                                                                                                                     |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `su dadosgov dadosgov`                | Run rotation as the file owner so permissions stay consistent.                                                                                                                                                                                             |
| `daily`                               | Eligible to rotate once per day (driven by `/etc/cron.daily/logrotate`).                                                                                                                                                                                   |
| `size 10M`                            | Rotate only when the file is at least 10 MB. Suppresses time-based rotation when the file is small (you'll see `'size' overrides previously specified 'daily'` — that's intentional).                                                                      |
| `rotate 50`                           | Keep 50 historical files; older ones are deleted on rotation.                                                                                                                                                                                              |
| `compress` + `delaycompress`          | gzip old files, but keep the most recent rotation uncompressed for fast `grep`.                                                                                                                                                                            |
| `missingok`                           | Don't error if a `.log` file is missing (e.g. before first run).                                                                                                                                                                                           |
| `notifempty`                          | Skip rotation when the file is empty.                                                                                                                                                                                                                      |
| `dateext` + `dateformat .%Y-%m-%d-%s` | Suffix archives with `.YYYY-MM-DD-<unix_ts>` — unique even if rotation triggers multiple times per day.                                                                                                                                                    |
| `copytruncate`                        | Copy + truncate in place. The container processes keep the same file descriptor and continue writing without needing a SIGHUP. There's a small race window (sub-millisecond) where a log line written during the copy is lost — acceptable for these logs. |

### 7. Bring up the stack

```sh
cd /opt/dadosgov/backend
docker compose build app worker beat
docker compose up -d
```

## Verification

### Containers are healthy

```sh
docker ps --filter "name=udata-backend" --format "table {{.Names}}\t{{.Status}}"
```

All three should be `Up`.

### Container UID matches host

```sh
docker exec udata-backend-app id
# uid=10001(dadosgov) gid=10001(dadosgov)
```

If you get `uid=10001`, step 1 was skipped or `.env` wasn't picked up. Rebuild with the env vars set.

### Logs are being written to the host directory

```sh
ls -la /opt/dadosgov/backend/logs/
# -rw-r-----  1 dadosgov wheel  ...  app.log
# -rw-r--r--  1 dadosgov wheel  ...  worker.log
# -rw-r--r--  1 dadosgov wheel  ...  beat.log
```

The files should be growing. If they're owned by `10001` rather than `dadosgov`, check the host has the user with that UID.

### Logrotate config is valid (dry-run)

```sh
sudo logrotate -d /etc/logrotate.d/dadosgov
```

The expected warning is `'size' overrides previously specified 'daily'`. Anything else is a real problem.

### Force an actual rotation to confirm it works end-to-end

```sh
sudo logrotate -f /etc/logrotate.d/dadosgov
ls -la /opt/dadosgov/backend/logs/
```

You should see the originals truncated to 0 bytes and new archives next to them, e.g.:

```
-rw-r----- dadosgov wheel       0  app.log
-rw-r----- dadosgov wheel  26152  app.log.2026-05-06-1778078439
-rw-r--r-- dadosgov wheel       0  worker.log
-rw-r--r-- dadosgov wheel    2665  worker.log.2026-05-06-1778078439
-rw-r--r-- dadosgov wheel       0  beat.log
-rw-r--r-- dadosgov wheel     625  beat.log.2026-05-06-1778078439
```

After a few seconds, `app.log`, `worker.log` and `beat.log` start growing again — the containers' open file descriptors survived the truncate.

## Customization

### Rotate more frequently than once a day

The default cron job at `/etc/cron.daily/logrotate` calls logrotate once a day. With `size 10M`, that means a file can grow well past 10 MB if it produces a lot in 24h. To check hourly:

```sh
sudo tee /etc/cron.hourly/logrotate-dadosgov > /dev/null <<'EOF'
#!/bin/sh
/usr/sbin/logrotate /etc/logrotate.d/dadosgov
EOF
sudo chmod +x /etc/cron.hourly/logrotate-dadosgov
```

### Change the size threshold

Edit `size 10M` in `/etc/logrotate.d/dadosgov`. Common alternatives: `size 50M` for high-volume hosts, `size 1M` for low-volume.

### Change the retention count

Edit `rotate 50`. With `size 10M` + `rotate 50` + `compress`, total disk usage is bounded by roughly 50 × ~1 MB compressed = 50 MB per file (3 files = ~150 MB worst case). For longer retention, increase `rotate`; for less, decrease.

### Disable compression

Remove `compress` and `delaycompress`. Easier `tail`/`grep` on archives at the cost of more disk space.

## Troubleshooting

### `PermissionError: [Errno 13] Permission denied: '/logs/worker.log'` and the container restart-loops

The container's `dadosgov` UID does not match the host owner of the existing log files. Cause: image was built without `UDATA_UID/UDATA_GID` so it defaulted to 10001, while existing files are owned by 10001. Fix:

1. Add `UDATA_UID=10001` and `UDATA_GID=10001` to `backend/.env`.
2. Rebuild: `docker compose build app worker beat`.
3. Recreate: `docker compose up -d`.

### `[entrypoint] Waiting for MongoDB...` repeats many times in `docker logs`

The container is in a restart loop, but `docker inspect` shows `RestartCount: 0` because `restart: unless-stopped` doesn't count clean exits as failures. Look for the underlying error in `docker logs udata-backend-app | tail -40` — typically it's a permission issue on `/logs/` or a missing config file.

### `logrotate -d` shows `Creating new state` for every file

Normal on the first run — `/var/lib/logrotate/logrotate.status` doesn't yet have entries for these paths. After one real rotation it will, and subsequent dry-runs become silent.

### Logs are empty in `app.log` after enabling everything

`disable-logging = true` in `front.ini` means uwsgi only writes warnings, 4xx, 5xx and Python errors. Healthy traffic produces no entries. Trigger a 404 to confirm the file is reachable:

```sh
curl -s -o /dev/null http://localhost:7000/api/1/this-does-not-exist
tail -1 /opt/dadosgov/backend/logs/app.log
```

### Want to read logs as a non-`wheel`/non-`dadosgov` user

Either add the user to the `wheel` or `dadosgov` group, or use `docker exec udata-backend-app cat /logs/app.log`.

## Related files

| Path                                      | Purpose                                                          |
| ----------------------------------------- | ---------------------------------------------------------------- |
| `backend/.env`                            | Holds `UDATA_UID` / `UDATA_GID` for build-time alignment         |
| `backend/docker-compose.yml`              | Bind-mounts `./logs:/logs` and configures `--logfile` for Celery |
| `backend/uwsgi/front.ini`                 | uwsgi log target, levels, and 4xx/5xx capture                    |
| `backend/scripts/logrotate-dadosgov.conf` | Source of truth for the logrotate config                         |
| `/etc/logrotate.d/dadosgov`               | Installed copy that the system actually reads                    |
