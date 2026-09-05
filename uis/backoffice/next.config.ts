import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow both localhost and 127.0.0.1 during local DevTools testing
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  experimental: {
    externalDir: true,
  },
};

export default nextConfig;
