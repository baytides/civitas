/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // Required for Payload CMS
    serverComponentsExternalPackages: ["payload"],
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
