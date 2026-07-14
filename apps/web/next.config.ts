import type { NextConfig } from "next";

const API_ORIGIN = process.env.API_ORIGIN ?? "http://axiom-api:7200";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_ORIGIN}/:path*`,
      },
    ];
  },
};

export default nextConfig;
