import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  compress: true,
  productionBrowserSourceMaps: false,
  images: {
    deviceSizes: [320, 576, 768, 992, 1248],
    remotePatterns: [
      {
        protocol: "http",
        hostname: "dev.local:7000",
      },
      {
        protocol: "http",
        hostname: "localhost:7000/static",
      },
    ],
  },
  // TODO: Install @sentry/nextjs and configure
  // TODO: Implement sitemap via app/sitemap.ts or next-sitemap
};

export default nextConfig;
