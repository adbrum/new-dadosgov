# Runbook — LEDG-1729 / VULN-2084 deploy + verification

Step-by-step actions to ship the harvest source SSRF guard (FIX 13) to PPR
and PRD and validate that the audit payload no longer triggers an
out-of-band interaction.

> Prerequisites: shell access to the PPR/PRD application host, with the
> `udata` venv active and `udata.cfg` already pointing at the deployment
> infrastructure (Redis, MongoDB, etc.).

---

## 0. Decision summary

| Item              | Value                                                                  |
| ----------------- | ---------------------------------------------------------------------- |
| Branch (backend)  | `fix/ledg-1729-vuln-2084-harvest-ssrf`                                  |
| Target            | `amagovpt/udata-pt` → `main`                                            |
| Affected endpoint | `POST /api/1/harvest/source/preview/` (primary) + all harvest create/update + scheduled runs |
| Default denylist  | 14 hostname glob patterns (Burp Collaborator, Interactsh, oast.*, webhook.site, …) |
| Default allowlist | `None` (not enforced — operators opt in when they want strict filtering) |

---

## 1. Merge the backend PR

```text
URL:  https://github.com/amagovpt/udata-pt/compare/main...fix/ledg-1729-vuln-2084-harvest-ssrf?quick_pull=1
```

1. Open the URL.
2. Confirm the diff matches the file list in FIX 13 of `vulnerability-remediation.md`.
3. Get review, merge to `main` (squash strategy).

## 2. Bump submodule pointer in the parent repo

```bash
cd /home/babel/workspace/AMA/ama-gov/new-dadosgov

git -C backend fetch origin
git -C backend checkout main
git -C backend pull --ff-only

git add backend
git commit -m "chore: bump backend submodule for LEDG-1729 / VULN-2084 (harvest SSRF guard)"
git push origin main
```

## 3. Roll out to PPR

```bash
# On the PPR host — adjust paths to the actual deployment layout
cd /opt/udata
sudo systemctl stop udata-web udata-worker udata-beat

git pull --ff-only

# (Optional) tighten the harvest URL filter on preprod by enabling the
# allowlist. Edit /opt/udata/udata.cfg and append, e.g.:
#
#   HARVEST_URL_HOST_ALLOWLIST = (
#       "*.gov.pt",
#       "ec.europa.eu",
#       "data.europa.eu",
#   )
#
# Skip this step on first deploy if you prefer to keep the default
# (denylist-only) posture and turn it on later.

sudo systemctl start udata-web udata-worker udata-beat
```

## 4. Smoke-validate the form-level gate

Replay the exact audit payload from a client with credentials on PPR.

```bash
TOKEN=<api-token-with-harvest-permissions>

curl -s -o /tmp/r.json -w "%{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"vuln2084-audit-replay","url":"http://ama.http.interaction.s.inty.io","backend":"dcat"}' \
  https://preprod.dados.gov.pt/api/1/harvest/source/preview/

cat /tmp/r.json | python -m json.tool
```

Expected output:

```
400
{
  "errors": {
    "url": ["Host 'ama.http.interaction.s.inty.io' is blocked for harvest sources"]
  }
}
```

Cross-check that the auditor's Burp Collaborator (or your equivalent OOB
service) sees **no incoming DNS request** for that hostname while you
run the cURL above. The form-level gate runs strictly before
`socket.getaddrinfo`, so a denied URL must produce zero out-of-band
traffic.

## 5. Smoke-validate the rest of the canary list

Iterate through a few representative patterns to make sure every entry
in the default denylist still trips:

```bash
for u in \
  "http://x.interact.sh/" \
  "https://abc.oast.fun/" \
  "https://collaborator.burpcollaborator.net/" \
  "http://webhook.site/abc-123" \
  "http://requestbin.com/r/abcdef"; do
  curl -s -o /dev/null -w "$u → %{http_code}\n" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"vuln2084-canary\",\"url\":\"$u\",\"backend\":\"dcat\"}" \
    https://preprod.dados.gov.pt/api/1/harvest/source/preview/
done
```

Expected: every line ends with `→ 400`.

## 6. Smoke-validate a *legitimate* harvest source still works

```bash
curl -s -o /tmp/r.json -w "%{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"vuln2084-ok","url":"https://dados.gov.pt/sample-catalog.xml","backend":"dcat"}' \
  https://preprod.dados.gov.pt/api/1/harvest/source/preview/
```

Expected: `200` (or `400` only for a real validation problem, e.g. invalid
DCAT — not for the SSRF guard). If you get `400 ... blocked for harvest
sources` here, the allowlist set in step 3 is too restrictive — relax it
or remove the setting.

## 7. (Optional) Verify the fetch-time guard

The fetch-time guard fires when something bypassed the form (programmatic
source creation, fixture, DNS rebinding). Easiest live verification:

```bash
# Trigger a manual run of an existing source with a transient hostname.
# OR: temporarily add a denied URL via Mongo shell and trigger the worker:

mongo udata <<'EOF'
db.harvest_source.insertOne({
  name: "vuln2084-rebinding",
  url: "http://x.oast.fun/",
  backend: "dcat",
  active: false,
})
EOF

# In the worker logs you should see HarvestException with "blocked for
# harvest sources" if any code path picks this row up.
```

Cleanup:

```bash
mongo udata <<'EOF'
db.harvest_source.deleteOne({ name: "vuln2084-rebinding" })
EOF
```

## 8. Close the ticket

If steps 4, 5, 6 all match expectations, comment on LEDG-1729 with:

- The cURL output from step 4 showing `400` + error message.
- The status-code list from step 5 (5 × `→ 400`).
- The legitimate `200` from step 6.
- A link to the merged PR for this branch.
- Confirmation that the auditor's collaborator saw no DNS hit during the test.

Then transition the issue to **Concluída** with resolution **Mitigado por
HarvestURLField + denylist + fetch-time guard**.

## 9. Post-deploy follow-up

| Day      | Task                                                                            |
| -------- | ------------------------------------------------------------------------------- |
| D+0      | Watch logs for unexpected `HarvestException: ... blocked for harvest sources`. A legitimate harvester tripping the guard means the denylist matches one of its sources — escalate to product owner and either delist (if low-risk) or shift the source to a different host. |
| D+7      | Sweep the existing `harvest_source` collection for hostnames matching any denylist pattern. Any such row was created BEFORE this fix; coordinate with the data team to decide whether to keep, retire, or replace each. |
| D+14     | Re-run the audit replay (step 4) against PRD after the rollout there. |
| D+30     | Decide whether to switch from denylist-only to allowlist-tightened posture on PRD. |
