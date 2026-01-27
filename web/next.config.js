const path = require("path");

const defaultApiBase = "https://api.projectcivitas.com";
const publicApiUrl = process.env.NEXT_PUBLIC_API_URL || "";
const fastApiUrl =
  process.env.FASTAPI_URL ||
  (publicApiUrl ? publicApiUrl.replace(/\/api\/v1\/?$/, "") : defaultApiBase);

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: __dirname,
  // Required for Payload CMS in Next.js 15
  serverExternalPackages: ["payload"],
  webpack: (config) => {
    config.resolve.alias["@payload-config"] = path.resolve(
      __dirname,
      "src/payload/payload.config.ts"
    );
    return config;
  },
  turbopack: {},
  // Skip trailing slash issues
  trailingSlash: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "baytidesstorage.blob.core.windows.net",
      },
    ],
  },
  // Rewrite API calls to FastAPI backend
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${fastApiUrl}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
