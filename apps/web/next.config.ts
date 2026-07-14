import type { NextConfig } from "next";

const API_ORIGIN = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7200";

const nextConfig: NextConfig = {
  output: "standalone",
  eslint: {
    ignoreDuringBuilds: false,
  },
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
