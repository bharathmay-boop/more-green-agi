/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // ioredis is a server-only dependency; never bundle it for the browser.
  serverExternalPackages: ["ioredis"],
};

export default nextConfig;
