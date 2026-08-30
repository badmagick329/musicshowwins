import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  agentRules: false,
  async rewrites() {
    const apiBaseUrl = (process.env.DJANGO_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");
    return [{ source: "/backend-api/:path*", destination: `${apiBaseUrl}/:path*` }];
  },
};

export default nextConfig;
