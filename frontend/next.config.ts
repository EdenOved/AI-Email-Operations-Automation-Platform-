import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  basePath: "/ops",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8001"}/:path*`
      }
    ];
  }
};

export default nextConfig;
