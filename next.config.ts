import type { NextConfig } from "next";
import { join } from "path";

const nextConfig: NextConfig = {
  distDir: ".next",
  experimental: {
    serverActions: {
      bodySizeLimit: "10mb",
    },
  },
};

export default nextConfig;
