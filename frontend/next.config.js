/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Only affects `next build` (production), not `next dev` - produces a
  // minimal, self-contained server bundle so the production image
  // doesn't need to ship the full node_modules tree. See
  // frontend/Dockerfile.prod.
  output: "standalone",
};

module.exports = nextConfig;
