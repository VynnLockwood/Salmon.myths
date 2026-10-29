import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server build used by the Docker image.
  output: "standalone",
  // Don't advertise the framework in the X-Powered-By header.
  poweredByHeader: false,
};

export default nextConfig;
