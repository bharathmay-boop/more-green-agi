import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
// platform/ monorepo root — contains both this app and packages/db (Prisma engine).
const tracingRoot = join(__dirname, "..", "..");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Prisma client + ioredis are server-only; don't bundle/trace into the browser.
  serverExternalPackages: ["ioredis", "@prisma/client", ".prisma/client"],
  // Pin file-tracing to platform/. Without a bounded root, node-file-trace follows
  // the Prisma engine outside the app and walks up into protected Windows home-dir
  // junctions (C:\Users\…\Cookies / Application Data) → EPERM during build.
  outputFileTracingRoot: tracingRoot,
};

export default nextConfig;
