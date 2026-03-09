/**
 * Typed environment variable accessors.
 * Replaces Nuxt's useRuntimeConfig() with Next.js env vars.
 * All NEXT_PUBLIC_ vars are available in both server and client code.
 */
export const env = {
  apiBase:
    process.env.NEXT_PUBLIC_API_BASE || "https://dados.gov.pt/api/1",
  apiV2Base:
    process.env.NEXT_PUBLIC_API_V2_BASE || "https://dados.gov.pt/api/2",
  frontBase:
    process.env.NEXT_PUBLIC_FRONT_BASE || "http://localhost:3000",
  baseUrl:
    process.env.NEXT_PUBLIC_BASE_URL || "https://dados.gov.pt/",
  staticUrl:
    process.env.NEXT_PUBLIC_STATIC_URL || "https://static.data.gouv.fr/static/",

  readOnlyMode: process.env.NEXT_PUBLIC_READ_ONLY_MODE === "true",
  requireEmailConfirmation:
    process.env.NEXT_PUBLIC_REQUIRE_EMAIL_CONFIRMATION !== "false",

  sentryDsn: process.env.NEXT_PUBLIC_SENTRY_DSN || "",
  matomoHost: process.env.NEXT_PUBLIC_MATOMO_HOST || "",
  matomoSiteId: parseInt(process.env.NEXT_PUBLIC_MATOMO_SITE_ID || "1", 10),
} as const;
