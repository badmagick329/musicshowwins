import type { NextConfig } from "next";

const plausibleOrigin = "https://analytics.mgck.ink";

const nextConfig: NextConfig = {
  agentRules: false,
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/ingest/js/script.js",
        destination: `${plausibleOrigin}/js/script.js`,
      },
      {
        source: "/ingest/api/event",
        destination: `${plausibleOrigin}/api/event`,
      },
    ];
  },
};

export default nextConfig;
