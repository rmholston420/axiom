import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost", "192.168.1.208"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:7200/:path*",
      },
    ];
  },
};

export default nextConfig;
