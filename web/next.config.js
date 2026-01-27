const path = require("path");

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
