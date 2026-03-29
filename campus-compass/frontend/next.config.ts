import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produces a self-contained build in .next/standalone for Docker
  output: "standalone",
};

export default nextConfig;
