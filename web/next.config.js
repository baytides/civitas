const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: __dirname,
  // Static export for Cloudflare Pages
  output: "export",
  // Required for Payload CMS in Next.js 15 (when not using static export)
  serverExternalPackages: ["payload"],
  webpack: (config) => {
    config.resolve.alias["@payload-config"] = path.resolve(
      __dirname,
      "src/payload/payload.config.ts"
    );
    return config;
  },
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
        destination: `${process.env.FASTAPI_URL || "http://localhost:8000"}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
