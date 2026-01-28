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
  // Avoid trailing-slash redirects to prevent redirect loops on Cloudflare/OpenNext
  trailingSlash: false,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "baytidesstorage.blob.core.windows.net",
      },
    ],
  },
  // Rewrite API calls to FastAPI backend
  // Both with and without trailing slash to avoid redirect loops
  // (trailingSlash: true adds slashes, but FastAPI routes don't have them)
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: "/api/v1/:path*/",
          destination: `${fastApiUrl}/api/v1/:path*`,
        },
        {
          source: "/api/v1/:path*",
          destination: `${fastApiUrl}/api/v1/:path*`,
        },
      ],
    };
  },
};

module.exports = nextConfig;
