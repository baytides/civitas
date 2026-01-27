/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required for Payload CMS in Next.js 15
  serverExternalPackages: ["payload"],
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
