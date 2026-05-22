# Runbook — LEDG-1728 / VULN-2083 verification

Step-by-step actions to confirm that the mass-form-submission finding on
`POST /api/1/discussions/` and `POST /api/1/discussions/<id>/` is already
remediated on preprod, and to wire the regression tests added by this
ticket into the CI flow.

> The remediation itself was shipped earlier as part of FIX 11
> (TICKET-59 / VULN-2078); both endpoints carry the per-user
> `COMMENT_CREATE_LIMIT` decorator since commit `3b83a78d`. This runbook
> only validates that the mitigation is **effective on preprod** and
> documents the regression tests added under LEDG-1728.

---

## 0. Decision summary

| Item              | Value                                                                  |
| ----------------- | ---------------------------------------------------------------------- |
| Branch (backend)  | `fix/ledg-1728-vuln-2083-discussions-rate-limit-tests`                 |
| Linked FIX        | FIX 11 (existing mitigation) + FIX 12 (this regression coverage)       |
| Endpoints         | `POST /api/1/discussions/`, `POST /api/1/discussions/<id>/`            |
| Limit profile     | `COMMENT_CREATE_LIMIT = 5/min; 30/h; 100/day` — per-user               |
| Storage backend   | Redis DB 3 (same as TICKET-59)                                         |

---

## 1. Confirm preprod runs the post-FIX-11 backend

Connect to the preprod application host and read the backend SHA:

```bash
cd /opt/udata
git log -1 --oneline
# The current main MUST include 3b83a78d or its squash-merged equivalent.
# Verify by grepping for the limiter wiring in the deployed code:
grep -n "COMMENT_CREATE_LIMIT" udata/core/discussions/api.py
# Expected matches at the top imports + two `decorators = [limiter.limit(...)]` blocks.
```

If the grep returns nothing on preprod, the FIX 11 deploy never reached
preprod — escalate to operations and re-run the FIX 11 deploy via
`runbook-ticket-59-vuln-2078.md` before proceeding. **Stop here** in that
case; the rest of this runbook assumes FIX 11 is live.

## 2. Confirm Redis storage is configured

```bash
grep -E "RATELIMIT_(DEFAULT|STORAGE_URI)" udata.cfg
# Expected:
#   RATELIMIT_DEFAULT = "1000 per day;200 per hour"
#   RATELIMIT_STORAGE_URI = f"redis://{SERVER_REDIS}:6379/3"

# Smoke Redis connectivity (substitute the preprod IP):
redis-cli -h <SERVER_REDIS_PPR> -p 6379 -n 3 ping
# Expected: PONG
```

If `RATELIMIT_STORAGE_URI` is missing or still points at `memory://`, the
per-endpoint counters are NOT shared across gunicorn workers and a
multi-worker deploy will silently multiply every limit by the worker
count. Fix the config before continuing.

## 3. Smoke-validate the limit on `/api/1/discussions/`

Pick any dataset on preprod and use credentials with `content:create`
scope. Replace `<token>` and `<dataset_id>` below.

```bash
TOKEN=<api-token>
DATASET_ID=<dataset-id-on-preprod>

for i in $(seq 1 6); do
  curl -s -o /dev/null -w "create $i → %{http_code}\n" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"vuln2083-smoke-$i\",\"comment\":\"x\",\"subject\":{\"class\":\"Dataset\",\"id\":\"$DATASET_ID\"}}" \
    https://preprod.dados.gov.pt/api/1/discussions/
done
```

Expected output:

```
create 1 → 201
create 2 → 201
create 3 → 201
create 4 → 201
create 5 → 201
create 6 → 429
```

If the 6th request is not `429`, the limit is not firing on this
endpoint — see § 5 troubleshooting.

## 4. Smoke-validate the limit on `/api/1/discussions/<id>/`

Pick one of the discussions created in § 3 (capture its `id` from the
`201` response body), then hammer the comment endpoint:

```bash
DISCUSSION_ID=<id-returned-by-step-3>

for i in $(seq 1 6); do
  curl -s -o /dev/null -w "comment $i → %{http_code}\n" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"comment\":\"vuln2083-comment-$i\"}" \
    https://preprod.dados.gov.pt/api/1/discussions/$DISCUSSION_ID/
done
```

Expected output:

```
comment 1 → 200
comment 2 → 200
comment 3 → 200
comment 4 → 200
comment 5 → 200
comment 6 → 429
```

> Note: because the test user just consumed 5 of their per-minute slots
> in step 3, you may need to wait until the start of the next minute
> before running step 4. The limit is shared across the two endpoints
> only at the `200/hour` and `100/day` levels — the per-minute counter
> is per-key per-endpoint.

## 5. Troubleshooting

| Symptom                                  | Likely cause                                           | Action                                                                                |
| ---------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| 6th request returns `201` / `200`        | Memory-backed limiter on multi-worker deploy           | Set `RATELIMIT_STORAGE_URI` in `udata.cfg`, restart workers                           |
| All requests return `401` / `403`        | Token/cookie wrong or insufficient scope               | Fix auth; the limiter only fires after `@api.secure` validates the principal           |
| 6th request returns `500`                | Redis unreachable from app host                        | Check firewall + `redis-cli ... ping`                                                  |
| 6th request returns `429` but only one of the two endpoints | One decorator was accidentally removed             | `grep COMMENT_CREATE_LIMIT udata/core/discussions/api.py`; re-deploy FIX 11 backend SHA |

## 6. Run the new regression tests locally

```bash
cd backend
uv run pytest udata/tests/test_discussions.py -k rate_limited -v
```

Expected:

```
PASSED  test_create_discussion_rate_limited
PASSED  test_comment_discussion_rate_limited
```

These two tests guard the FIX 11 decorators from accidental removal. They
exercise the limiter against the in-process app with `memory://` storage
(the limiter is enabled by default in the testing config).

## 7. Clean up smoke entries

After step 3 / 4 you have ~10 throwaway discussions on the chosen dataset.
Delete them from the Mongo shell (or via the existing admin UI):

```bash
# Connect to the preprod Mongo replica set then:
db.discussion.deleteMany({ title: { $regex: "^vuln2083-smoke-" } })
```

## 8. Close the ticket

If steps 3 + 4 + 6 all pass, comment on LEDG-1728 with:

- The exact preprod backend SHA from § 1.
- The cURL output transcript from § 3 + § 4 showing the `429` on the 6th
  request of each endpoint.
- A link to the merged PR for this branch.

Then transition the issue to **Done** with resolution **Já estava
mitigado por VULN-2078; cobertura de regressão adicionada**.

## 9. Post-deploy follow-up

| Day      | Task                                                                            |
| -------- | ------------------------------------------------------------------------------- |
| D+0      | Watch preprod logs for unexpected 429s on discussions. If a legitimate workflow trips, adjust `COMMENT_CREATE_LIMIT` in `udata/api/limits.py` and redeploy. |
| D+7      | Repeat steps 3 + 4 against PRD to confirm the same behaviour there.             |
| D+30     | Delete this runbook or fold residual notes into `vulnerability-remediation.md`. |
