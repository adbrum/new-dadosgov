# HTTP Method Override — Tunneling PUT/PATCH/DELETE through POST

## Problem

A NetScaler ADC WAF in front of `ppr-dadosgov.arte.gov.pt` (and the same fronting PRD) enforces an *HTTP Verb Tampering* rule that **blocks any request whose method is not `GET` or `POST`**. The block manifests as:

- `HTTP/2 500` with `content-type: text/html` (the WAF block page rendered as 500).
- Response carries `cookie_adc_ext=...` and `Attack ID: 20000001` (Citrix ADC fingerprints).
- The block happens **before** the request reaches the Flask backend, so application logs show nothing.

Every mutating call from the frontend (43 PUT/PATCH/DELETE call sites in `frontend/src/services/api.ts`) was rejected. Concretely, profile editing at `/pages/admin/me/profile` failed with a 500 on `PUT /api/1/me/`.

The CORS hardening from KITS24 (FIX 2, VULN-1496/1550 — see [vulnerability-remediation.md](./vulnerability-remediation.md)) is unrelated: it constrains the **origin** whitelist, not the methods. The verb filter is set at the WAF layer, outside the application repo.

## Solution

Tunnel mutating verbs through a `POST` request that carries an `X-HTTP-Method-Override: <verb>` header. The WAF lets the `POST` through (it does not inspect the header), and a WSGI middleware on the Flask side rewrites `REQUEST_METHOD` before routing.

```
Browser                  Citrix ADC                  Flask (gunicorn)
  │                         │                            │
  │  POST /api/1/me/        │                            │
  │  X-HTTP-Method-Override:│                            │
  │  PUT                    │                            │
  ├────────────────────────►│  POST forwarded as-is      │
  │                         ├───────────────────────────►│ MethodOverrideMiddleware
  │                         │                            │   POST + header → PUT
  │                         │                            │
  │                         │                            │ MeAPI.put(...)
  │                         │                            │   marshalled response
  │                         │◄───────────────────────────┤
  │◄────────────────────────┤                            │
  │   200 OK + JSON         │                            │
```

The pattern is industry-standard: Rails, Symfony, Laravel, ASP.NET Core, and many CDN/WAF vendors implement or whitelist it natively.

## Backend

**Module:** `backend/udata/method_override.py`

```python
ALLOWED_OVERRIDES = frozenset({"PUT", "PATCH", "DELETE"})

class MethodOverrideMiddleware:
    def __call__(self, environ, start_response):
        if environ.get("REQUEST_METHOD", "").upper() == "POST":
            override = environ.pop("HTTP_X_HTTP_METHOD_OVERRIDE", "").upper()
            if override in ALLOWED_OVERRIDES:
                environ["REQUEST_METHOD"] = override
                environ["udata.original_method"] = "POST"
        return self.app(environ, start_response)
```

**Wired in `backend/udata/app.py`** (inside `create_app()`):

```python
app.wsgi_app = MethodOverrideMiddleware(
    ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
)
```

Ordering matters: `ProxyFix` normalizes `X-Forwarded-*` first, then `MethodOverrideMiddleware` rewrites the method **before** Flask routing, CSRF (`csrf.exempt` on `/api/*` blueprints), the rate limiter, or any `before_request` hook sees the request. Handlers behave exactly as if the real verb had been sent.

### Security guarantees

- Only `POST` requests may carry an override. A `GET` with `X-HTTP-Method-Override: DELETE` is **ignored** — prevents verb smuggling through cacheable methods.
- Only `PUT`, `PATCH`, `DELETE` are allowlisted as override targets. `OPTIONS`, `HEAD`, `TRACE`, `CONNECT`, custom verbs are rejected.
- The header is `environ.pop`'ed after consumption so downstream code observes a clean request.
- Original method preserved in `environ["udata.original_method"]` for future audit logging.

### Tests

`backend/udata/tests/test_method_override.py` — 14 tests:

- 11 unit tests (pure WSGI, no Flask app): allowlisted verbs, case normalization, unsupported overrides, GET→DELETE smuggling refused, missing header passthrough.
- 3 integration tests via `APITestCase` against real dataset endpoints: `POST` + override `DELETE` deletes; `POST` + override `PUT` updates; plain `POST` without header still returns 404/405/410 (sanity).

Run with `uv run pytest udata/tests/test_method_override.py -v` from `backend/`.

## Frontend

**File:** `frontend/src/services/api.ts`

```ts
const METHOD_OVERRIDE_VERBS = new Set(["PUT", "PATCH", "DELETE"]);

export function applyMethodOverride(init?: RequestInit): RequestInit | undefined {
  if (process.env.NEXT_PUBLIC_USE_METHOD_OVERRIDE !== "true" || !init?.method) return init;
  const method = init.method.toUpperCase();
  if (!METHOD_OVERRIDE_VERBS.has(method)) return init;
  const headers = new Headers(init.headers);
  headers.set("X-HTTP-Method-Override", method);
  return { ...init, method: "POST", headers };
}

function fetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  return globalThis.fetch(input, applyMethodOverride(init));
}
```

The module-local `fetch` shadows the global so **all 43 mutating call sites** in `api.ts` transparently pick up the transformation — no per-site edits. Capture is at call time (`globalThis.fetch(...)` inside the wrapper) to preserve Next.js's request-time `fetch` instrumentation (caching, revalidation).

### Tests

`frontend/src/services/__tests__/methodOverride.test.ts` — 9 Vitest cases covering: flag off passthrough, undefined init, every allowlisted verb, header preservation, lowercase method normalization, GET/POST/OPTIONS/HEAD untouched, init without method untouched.

Run with `npx vitest run src/services/__tests__/methodOverride.test.ts` from `frontend/`.

## Configuration

The frontend transform is **opt-in** via the build-time env var:

```env
# frontend/.env
NEXT_PUBLIC_USE_METHOD_OVERRIDE=true
```

| Environment | Setting | Rationale |
|---|---|---|
| Local dev (`npm run dev`) | `false` (default) | `inv serve` backend has no WAF; real verbs work and are easier to debug in DevTools. |
| Pre-prod (PPR) | `true` | NetScaler ADC blocks non-GET/POST. |
| Production (PRD) | `true` | Same WAF policy as PPR. |

**Build requirement:** `NEXT_PUBLIC_*` vars are inlined at build time. After changing the value, the frontend **must** be rebuilt and restarted:

```bash
cd /path/to/frontend
echo "NEXT_PUBLIC_USE_METHOD_OVERRIDE=true" >> .env
npm run build
# Restart via the deployment's process manager (pm2 / systemd / docker compose).
```

The backend middleware is always active and harmless when no override header is present, so no toggle is needed on the Flask side.

## Verification

### Diagnose the WAF behaviour

From any machine on the public internet (or a workstation that traverses the same WAF):

```bash
COOKIE="session=...; remember_token=..."     # from DevTools → Application → Cookies
DATASET_ID="<an existing dataset id>"

# 1. Real PUT — should be blocked by the WAF (HTML 500, cookie_adc_ext)
curl -i -X PUT "https://ppr-dadosgov.arte.gov.pt/api/1/datasets/${DATASET_ID}/" \
     -H "Content-Type: application/json" \
     -H "Cookie: $COOKIE" \
     -d '{}' | head -20

# 2. POST + override — should reach Flask and behave like the real PUT (200/4xx JSON)
curl -i -X POST "https://ppr-dadosgov.arte.gov.pt/api/1/datasets/${DATASET_ID}/" \
     -H "Content-Type: application/json" \
     -H "X-HTTP-Method-Override: PUT" \
     -H "Cookie: $COOKIE" \
     -d '{}' | head -20
```

Confirm via `server: dados.gov` on the 200 response that Flask, not the ADC, produced it.

### Smoke test post-deploy

1. Open DevTools → Network at `https://ppr-dadosgov.arte.gov.pt/pages/admin/me/profile`.
2. Edit the profile and submit.
3. In the Network panel the request **must** be:
   - Method: `POST` (not PUT)
   - Request header: `X-HTTP-Method-Override: PUT`
   - Status: `200`
4. Repeat for a destructive action (delete a test dataset/organization) to validate the `DELETE` override path.

## Operational notes

- **Rollback:** Set `NEXT_PUBLIC_USE_METHOD_OVERRIDE=false` (or remove the line) and rebuild the frontend. The backend middleware stays in place and is a no-op without the header — leaving it deployed is the recommended state.
- **Observability:** Mutating requests appear as `POST /api/1/...` in nginx/gunicorn access logs. To correlate with the real verb, log `environ["udata.original_method"]` alongside `request.method` in any custom access-log hook.
- **Rate limits:** Flask-Limiter is configured per-endpoint via decorators (`udata.api.limits`), keyed on `user_or_ip`. The limiter runs after the middleware rewrite, so quotas attached to a `put`/`delete` resource are consumed correctly — they are not collapsed into a generic `POST` bucket.
- **API consumers outside the browser:** External clients (harvesters, journalists, government integrations) continue to use real `PUT`/`DELETE`. They are expected to traffic from inside networks that bypass the public WAF, or to be allowlisted there. The override is an *alternative*, not a replacement.

## Security considerations

- **HTTP Verb Tampering (CWE-650):** The pattern intentionally enables clients to express a verb through a header. Mitigations baked into the middleware: POST-only entry point, strict verb allowlist, header stripped after consumption. This was flagged for the next KITS24 audit cycle so the rationale is recorded.
- **Forensics:** Access logs no longer distinguish a destructive call from a benign POST without inspecting the override header. When investigating an incident, query both `request.method` and the `X-HTTP-Method-Override` header from the log pipeline.
- **CSRF:** Both API blueprints (`apiv1_blueprint`, `apiv2_blueprint`) are decorated with `csrf.exempt` in `backend/udata/api/__init__.py`. The override path therefore inherits the same posture as the original PUT/DELETE — no new CSRF surface introduced. Browser sessions still rely on the `credentials: "include"` cookies (`session`, `remember_token`) for authentication.
- **CORS:** No allowlist change required. The preflight handler in `backend/udata/cors.py` (`add_preflight_request_headers`) mirrors the browser's `Access-Control-Request-Headers` back in `Access-Control-Allow-Headers`, so `X-HTTP-Method-Override` is accepted automatically.

## File map

| Path | Role |
|---|---|
| `backend/udata/method_override.py` | WSGI middleware |
| `backend/udata/app.py` | Middleware wiring (`create_app`) |
| `backend/udata/tests/test_method_override.py` | 14 tests (unit + integration) |
| `frontend/src/services/api.ts` | Module-local `fetch` shadow + `applyMethodOverride` |
| `frontend/src/services/__tests__/methodOverride.test.ts` | 9 Vitest cases |
| `frontend/.env` | `NEXT_PUBLIC_USE_METHOD_OVERRIDE` flag |
| `docs/vulnerability-remediation.md` | KITS24 audit context (CORS hardening) |
