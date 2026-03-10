# Frontend - dados.gov.pt

## Stack
- Next.js 16 (App Router), React 19, TypeScript 5 (strict mode)
- UI: @ama-pt/agora-design-system 3.4.2 (Portuguese government design system)
- Styling: Tailwind CSS 4
- Date utils: date-fns 4

## Commands

```bash
# Install dependencies
npm install

# Dev server (port 3000)
npm run dev

# Production build & start
npm run build
npm run start

# Lint
npm run lint
```

## Code Style

- **Prettier**: double quotes, semicolons, trailing commas (ES5), 100 char width, 2-space indent
- **ESLint**: Next.js core-web-vitals + TypeScript rules, max line length 100 (warning)
- **EditorConfig**: 2 spaces, LF line endings, UTF-8, trim trailing whitespace

## Architecture

- **App Router**: routes in `src/app/pages/`
- **Components**: `src/components/` organized by feature (datasets/, reuses/, organizations/, etc.)
- **API layer**: `src/services/api.ts` - all backend API calls centralized here
- **Types**: `src/types/api.ts` - TypeScript interfaces for API responses
- **Path alias**: `@/*` maps to `./src/*`

## Component Conventions

- `'use client'` directive required for interactive components and design system usage
- PascalCase for component names
- Suffix `Client` for components managing full page state (e.g., `DatasetsClient.tsx`)
- Named exports for components
- Props interfaces defined at component level
- Tailwind utility classes for styling (use design tokens: `primary-*`, `neutral-*`, `brand-*`)

## API Integration

- Base URL: `https://dados.gov.pt/api/1` (configured in `src/services/api.ts`)
- All requests use `cache: 'no-store'` for fresh data
- Error handling: graceful fallbacks returning empty states

### Dynamic Data Fetching Pattern (Client Components)

When fetching dynamic data in a client component, enforce the following pattern using `useEffect` and `useState` with functions from `src/services/api.ts`:

1. Define state for the data array/object and a loading boolean (`isLoading`).
2. Inside `useEffect()`, wrap the API call in an `async function`.
3. Use a `try/catch/finally` block:
   - `try`: `const response = await fetchDatasets(...)` and `setData(response.data)`.
   - `catch`: Log the error `console.error(...)`.
   - `finally`: `setIsLoading(false)`.
4. Render conditionally based on `isLoading` (show loading state vs mapped data). 
5. Provide a fallback empty state if no data is returned.

## Key Paths

- `src/app/page.tsx` - Homepage
- `src/app/layout.tsx` - Root layout (Header + Footer)
- `src/app/globals.css` - Global styles & design tokens
- `src/services/api.ts` - API integration layer
- `src/types/api.ts` - TypeScript type definitions
- `src/components/Header.tsx` / `Footer.tsx` - Layout components
- `tailwind.config.ts` - Theme config with Agora design system
