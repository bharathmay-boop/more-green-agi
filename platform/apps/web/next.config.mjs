/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Prisma client is server-only; don't bundle/trace it into the browser.
  serverExternalPackages: ["@prisma/client", ".prisma/client"],
};

export default nextConfig;
