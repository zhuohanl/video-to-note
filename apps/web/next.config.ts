import type { NextConfig } from "next";

const apiBaseUrl = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL;

const nextConfig: NextConfig = {
  async rewrites() {
    if (!apiBaseUrl) {
      return [];
    }

    return [
      { source: "/login", destination: `${apiBaseUrl}/login` },
      { source: "/jobs/:path*", destination: `${apiBaseUrl}/jobs/:path*` },
      { source: "/clips/:path*", destination: `${apiBaseUrl}/clips/:path*` },
      { source: "/media/:path*", destination: `${apiBaseUrl}/media/:path*` },
    ];
  },
};

export default nextConfig;
