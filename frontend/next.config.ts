import type { NextConfig } from "next";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_BASE?.replace("/api/1", "") || "http://localhost:7000";

const nextConfig: NextConfig = {
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
};

export default nextConfig;
