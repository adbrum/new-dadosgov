# Plan: Migrate nuxt.config.ts to Next.js Configuration

## Context

The frontend is **Next.js 16** (App Router), but a `nuxt.config.ts` was copied from the original French data.gouv.fr project (which uses Nuxt). This file contains ~80+ configuration values (API URLs, site metadata, feature flags, license definitions, external service URLs, etc.) that need to be extracted and reorganized for the Next.js ecosystem. The API base URL is also hardcoded in `src/services/api.ts` to the production URL, making local development against the backend (port 7000) impossible without manual changes.

**Goal**: Make the frontend connect to the backend properly in both dev and production, and migrate all useful configuration from nuxt.config.ts into proper Next.js locations.

---

## Architecture Decision

Nuxt's `runtimeConfig` has no single Next.js equivalent. The configuration splits into **4 locations**:

| Destination | What goes here |
|---|---|
| `.env.local` / `.env.example` | API URLs, secrets, feature flags that change per environment |
| `next.config.ts` | Rewrites (API proxy), image optimization, webpack, compression |
| `src/config/site.ts` | Static constants: metadata, licenses, UI limits, guide URLs, homepage config |
| `src/app/layout.tsx` | SEO metadata via Next.js Metadata API |

---

## Implementation Steps

### Step 1: Create `.env.example` (committed reference)

**File**: `frontend/.env.example`

Contains all variable names with documentation and placeholder values. Key variables:

```env
# Backend API
NEXT_PUBLIC_API_BASE=http://localhost:7000/api/1
NEXT_PUBLIC_API_V2_BASE=http://localhost:7000/api/2
NEXT_PUBLIC_FRONT_BASE=http://localhost:3000
NEXT_PUBLIC_BASE_URL=https://dados.gov.pt/
NEXT_PUBLIC_STATIC_URL=https://static.data.gouv.fr/static/

# Feature flags
NEXT_PUBLIC_READ_ONLY_MODE=false
NEXT_PUBLIC_REQUIRE_EMAIL_CONFIRMATION=true

# Analytics (optional)
NEXT_PUBLIC_SENTRY_DSN=
NEXT_PUBLIC_MATOMO_HOST=
NEXT_PUBLIC_MATOMO_SITE_ID=1
```

### Step 2: Create `.env.local` (git-ignored, local dev values)

**File**: `frontend/.env.local`

Same as `.env.example` but with actual development values pointing to `localhost:7000`.

### Step 3: Update `.gitignore` to allow `.env.example`

**File**: `frontend/.gitignore`

Add `!.env.example` exception after the `.env*` rule.

### Step 4: Create `src/config/site.ts` (static application config)

**File**: `frontend/src/config/site.ts`

Migrates all **constant** values from `nuxt.config.ts → runtimeConfig.public` that don't change per environment:

- `siteConfig` — name, title, description, locale
- `uiConfig` — searchDebounce, qualityDescriptionLength, preview size limits, upload limits
- `licenses` — license definitions (adapted to Portuguese categories)
- `datasetBadges` — badge type list
- `guidesConfig` — guide/documentation URLs (kept with `// TODO: Replace with PT URL`)
- `homepageConfig` — hero images, onboarding links, highlight section
- `externalServicesConfig` — metrics, schema validation, tabular API URLs
- `feedbackConfig` — feedback form URLs
- `authConfig` — auth page paths, ProConnect config
- `harvesterConfig` — harvester settings

All French-specific URLs are kept but marked with `// TODO: Replace with PT URL`.

### Step 5: Create `src/config/env.ts` (typed environment variable accessors)

**File**: `frontend/src/config/env.ts`

Typed helper that replaces Nuxt's `useRuntimeConfig()`:

```typescript
export const env = {
  apiBase: process.env.NEXT_PUBLIC_API_BASE || "https://dados.gov.pt/api/1",
  apiV2Base: process.env.NEXT_PUBLIC_API_V2_BASE || "https://dados.gov.pt/api/2",
  frontBase: process.env.NEXT_PUBLIC_FRONT_BASE || "http://localhost:3000",
  baseUrl: process.env.NEXT_PUBLIC_BASE_URL || "https://dados.gov.pt/",
  // ... feature flags, analytics, etc.
} as const;
```

### Step 6: Update `next.config.ts`

**File**: `frontend/next.config.ts`

Migrate applicable Nuxt settings to Next.js equivalents:

| Nuxt setting | Next.js equivalent |
|---|---|
| `devServer.port/host` | Not needed (Next.js defaults to 3000) |
| `nitro.compressPublicAssets` | `compress: true` |
| `sourcemap.client: "hidden"` | `productionBrowserSourceMaps: false` |
| `vite.assetsInclude: ["**/*.md"]` | `webpack` rule for `.md` files |
| `image.screens` | `images.deviceSizes: [320, 576, 768, 992, 1248]` |
| — | `images.remotePatterns` for dados.gov.pt and static CDN |
| `routeRules` (SSR) | Not needed — App Router is SSR by default |
| `modules (@sentry/nuxt)` | `// TODO: Install @sentry/nextjs` |
| `modules (@nuxtjs/sitemap)` | `// TODO: Implement via app/sitemap.ts or next-sitemap` |
| `hooks.pages:extend` | `// TODO: Create shared search route files` |
| `vue.runtimeCompiler` | Not applicable (Vue-specific) |
| `vite.optimizeDeps` | Not applicable (Vite-specific) |
| `vite.css.scss` | Not applicable (uses Tailwind, not SCSS) |
| `eslint` config | Already in `eslint.config.mjs` |

**No API proxy rewrites** — the backend already has full CORS support (`cors.py` allows any origin for `/api/*`), so direct cross-origin calls work fine. The `NEXT_PUBLIC_API_BASE` env var is sufficient.

### Step 7: Update `src/services/api.ts`

**File**: `frontend/src/services/api.ts`

Single-line change — replace hardcoded URL with env variable:

```typescript
// Before:
const API_BASE_URL = 'https://dados.gov.pt/api/1';

// After:
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'https://dados.gov.pt/api/1';
```

Also remove the `console.log` debug statements.

### Step 8: Update `src/app/layout.tsx`

**File**: `frontend/src/app/layout.tsx`

- Add `Metadata` export with title, description, favicon, openGraph (from nuxt `app.head` + `site`)
- Change `lang="en"` to `lang="pt"` (Portuguese portal)

### Step 9: Delete `nuxt.config.ts`

**File**: `frontend/nuxt.config.ts`

Remove the file — it's untracked, references `defineNuxtConfig` which isn't installed, and all useful values have been migrated.

Also remove `frontend/rollup-plugin-smol-toml` if it exists (referenced by nuxt.config.ts import).

---

## Files Modified/Created

| Action | File |
|---|---|
| **Create** | `frontend/.env.example` |
| **Create** | `frontend/.env.local` |
| **Create** | `frontend/src/config/site.ts` |
| **Create** | `frontend/src/config/env.ts` |
| **Edit** | `frontend/next.config.ts` |
| **Edit** | `frontend/src/services/api.ts` |
| **Edit** | `frontend/src/app/layout.tsx` |
| **Edit** | `frontend/.gitignore` |
| **Delete** | `frontend/nuxt.config.ts` |
| **Delete** | `frontend/rollup-plugin-smol-toml` (if exists) |

---

## Verification

1. **Create `.env.local`** with `NEXT_PUBLIC_API_BASE=http://localhost:7000/api/1`
2. **Start backend**: `cd backend && inv serve` (port 7000)
3. **Start frontend**: `cd frontend && npm run dev` (port 3000)
4. **Test**: Open `http://localhost:3000` — datasets, organizations, reuses pages should load data from the local backend
5. **Verify build**: `cd frontend && npm run build` — no TypeScript or build errors
6. **Verify lint**: `cd frontend && npm run lint` — no new lint errors

---

## Status: IMPLEMENTED

All steps completed successfully. Build and lint pass with no new errors.
