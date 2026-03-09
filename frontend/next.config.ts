import type { NextConfig } from "next";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_BASE?.replace("/api/1", "") || "http://localhost:7000";

const nextConfig: NextConfig = {
  compress: true,
  productionBrowserSourceMaps: false,
  images: {
    deviceSizes: [320, 576, 768, 992, 1248],
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost:7000",
      },
      {
        protocol: "http",
        hostname: "localhost:7000/static",
      },
    ],
  },
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: "/logout/",
          destination: `${BACKEND_URL}/logout/`,
        },
        {
          source: "/get-csrf",
          destination: `${BACKEND_URL}/get-csrf`,
        },
        {
          source: "/reset/",
          destination: `${BACKEND_URL}/reset/`,
        },
        {
          source: "/reset/:token",
          destination: `${BACKEND_URL}/reset/:token`,
        },
      ],
      afterFiles: [],
      fallback: [
        {
          source: "/api/:path*",
          destination: `${BACKEND_URL}/api/:path*`,
        },
      ],
    };
  },
  // TODO: Install @sentry/nextjs and configure
  // TODO: Implement sitemap via app/sitemap.ts or next-sitemap
};

export default nextConfig;
