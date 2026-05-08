# Runbook — TICKET-59 / VULN-2078 deploy

Step-by-step actions to ship the per-endpoint rate-limit + dedup fix to PPR
and PRD. Each command is self-contained; copy-paste from your terminal.

> Prerequisites: shell access to the PPR/PRD application host with the
> `udata` venv active and `udata.cfg` already pointing at `SERVER_REDIS`.

---

## 0. Decision summary

| Item              | Value                                                                  |
| ----------------- | ---------------------------------------------------------------------- |
| Branch (backend)  | `fix/ticket-59-vuln-2078-community-resources-rate-limit`               |
| Last commit       | `08a6595f` — fix Limiter constructor shadowing config                   |
| Target            | `amagovpt/udata-pt` → `main`                                            |
| Storage backend   | Redis DB 3 (cache uses 2, Celery 0/1)                                  |
| Global limit      | `1000/day, 200/hour` (IP-keyed)                                        |
| Per-endpoint      | `5/min;30/h;100/day` (CONTENT) — see `udata/api/limits.py`             |

---

## 1. Merge the backend PR

```text
URL:  https://github.com/amagovpt/udata-pt/compare/main...fix/ticket-59-vuln-2078-community-resources-rate-limit?quick_pull=1
```

1. Open the URL.
2. Confirm 4 commits in the diff:
   - `3b83a78d` rate-limit + dedup
   - `b4d01283` Redis config + cleanup script
   - `7bc2fd68` audit-replay simulation
   - `08a6595f` fix Limiter constructor shadowing
3. Get review, merge to `main` with the squash strategy used by the team.

## 2. Bump submodule pointer in the parent repo

After the squash-merge, the backend `main` will have a new SHA. From the
parent repo on this WSL host:

```bash
cd /home/babel/workspace/AMA/ama-gov/new-dadosgov

# Pull the new backend main
git -C backend fetch origin
git -C backend checkout main
git -C backend pull --ff-only

# Bump the parent
git add backend
git commit -m "chore: bump backend submodule for TICKET-59 / VULN-2078 (rate-limit + dedup)"
git push origin main
```

## 3. Verify Redis is reachable on PPR / PRD

Substitute `<SERVER_REDIS_PPR>` / `<SERVER_REDIS_PRD>` with the IPs from
the deployment inventory:

```bash
# From the application host:
redis-cli -h <SERVER_REDIS_PPR> -p 6379 -n 3 ping
# Expected: PONG

# Optional sanity check — DB 3 should be empty (or contain only previous LIMITER/* keys):
redis-cli -h <SERVER_REDIS_PPR> -p 6379 -n 3 dbsize
```

Already verified from the dev WSL host: DEV (10.55.37.142) and TST
(10.55.37.41) both PONG cleanly with Redis 6.2.17.

## 4. Roll out to PPR

```bash
# On the PPR host — adjust paths to the actual deployment layout
cd /opt/udata
sudo systemctl stop udata-web udata-worker udata-beat

git pull --ff-only
uv sync --no-dev    # picks up flask-limiter[redis] if not yet installed

# Confirm udata.cfg is up to date — RATELIMIT_STORAGE_URI must point at Redis:
grep -E "RATELIMIT_(DEFAULT|STORAGE_URI)" udata.cfg
# Expected:
#   RATELIMIT_DEFAULT = "1000 per day;200 per hour"
#   RATELIMIT_STORAGE_URI = f"redis://{SERVER_REDIS}:6379/3"

sudo systemctl start udata-web udata-worker udata-beat
```

## 5. Smoke-validate the deployed limit

From any client with credentials on PPR (replace `<token>`, `<dataset_id>`):

```bash
TOKEN=<api-token-with-content-create-permission>
DATASET_ID=<dataset-uuid>

for i in $(seq 1 6); do
  curl -s -o /dev/null -w "request $i → %{http_code}\n" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"runbook-smoke-$i\",\"filetype\":\"remote\",\"type\":\"main\",\"format\":\"csv\",\"url\":\"https://example.com/$i.csv\",\"dataset\":\"$DATASET_ID\"}" \
    https://preprod.dados.gov.pt/api/1/datasets/community_resources/
done
```

Expected output (post-fix):

```
request 1 → 201
request 2 → 201
request 3 → 201
request 4 → 201
request 5 → 201
request 6 → 429
```

If you see anything other than `429` on the 6th request, the limit is not
firing — investigate config (`RATELIMIT_STORAGE_URI`) and process state
(restart workers).

Cleanup the smoke entries afterwards:

```bash
# On the PPR host:
UDATA_SETTINGS=/opt/udata/udata.cfg uv run python /opt/udata/scripts/cleanup_vuln_2078_poc.py \
    --dataset-id $DATASET_ID \
    --xss-payload-pattern "runbook-smoke" \
    --apply
```

## 6. Confirm Redis state is shared across workers

On a multi-worker deploy (`gunicorn -w N`), trigger a few requests from
your client and immediately:

```bash
redis-cli -h <SERVER_REDIS_PPR> -p 6379 -n 3 keys "LIMITER/*"
```

You should see counters keyed on `user:<id>` or `ip:<address>` and the
endpoint name. The presence of these keys (and not just one per process)
confirms cross-worker sharing.

## 7. Clean up the audit's PoC entries

The auditor produced ~106 community resources during the original scan.
Get the affected dataset slug and time window from them, then:

```bash
# Dry-run first — review the listing!
UDATA_SETTINGS=/opt/udata/udata.cfg uv run python /opt/udata/scripts/cleanup_vuln_2078_poc.py \
    --dataset-slug <slug-from-auditor> \
    --since 2026-04-08T00:00:00Z \
    --until 2026-04-08T23:59:59Z \
    --xss-payload-pattern "<img src=x onerror"

# Once the listing looks correct:
UDATA_SETTINGS=/opt/udata/udata.cfg uv run python /opt/udata/scripts/cleanup_vuln_2078_poc.py \
    --dataset-slug <slug-from-auditor> \
    --since 2026-04-08T00:00:00Z \
    --until 2026-04-08T23:59:59Z \
    --xss-payload-pattern "<img src=x onerror" \
    --apply
```

## 8. Roll out to PRD

Repeat steps 3–6 against the production host. After step 6 confirms shared
state, repeat step 5 from a production client to validate end-to-end.

## 9. Post-deploy follow-up

| Day      | Task                                                                            |
| -------- | ------------------------------------------------------------------------------- |
| D+0      | Watch logs for unexpected 429s; if a legitimate workflow trips, adjust the matching constant in `udata/api/limits.py` and redeploy. |
| D+7      | Pull metrics: distribution of POST request rates per user on each affected endpoint. Cross-check against the configured limits. |
| D+14     | Decide whether to tighten further or to add a `RATELIMIT_EXEMPT_USERS = [...]` whitelist for known integrators. |
| D+30     | Delete this runbook (or fold the residual notes into `vulnerability-remediation.md`). |
