const apiInternalUrl = process.env.API_INTERNAL_URL ?? "http://api:8000";

const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // Type checking runs as an explicit, blocking npm script before this build.
  // Next's duplicate checker is disabled because Next 16's config parser cannot
  // consume TypeScript's 5.8 --showConfig output in this runtime.
  typescript: {
    ignoreBuildErrors: true,
  },
  experimental: {
    useTypeScriptCli: false,
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiInternalUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
