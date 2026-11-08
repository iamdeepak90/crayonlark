import type { NextConfig } from "next";

// The FastAPI service is only reachable on the internal Docker network.
// Everything under /api/* (admin calls, OAuth callbacks, public forms) is proxied to it.
const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://api:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  images: {
    remotePatterns: [],
    localPatterns: [{ pathname: "/api/public/media/**" }, { pathname: "/brand/**" }],
  },
  async rewrites() {
    return {
      // run before Next's own routes so /api/revalidate (a Next route) still wins via afterFiles
      beforeFiles: [],
      afterFiles: [{ source: "/api/:path*", destination: `${API_INTERNAL_URL}/api/:path*` }],
      fallback: [],
    };
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
