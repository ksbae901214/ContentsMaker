import type { NextConfig } from "next";
import { resolve } from "path";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["cmaker.store-daehaeng.com"],
  turbopack: {
    root: resolve(__dirname),
  },
  experimental: {
    serverActions: {
      bodySizeLimit: "10mb",
    },
  },
};

export default nextConfig;
