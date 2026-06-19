// Prisma client singleton (E1-T3).
//
// Next.js dev hot-reload re-imports modules, which would otherwise spawn a new
// PrismaClient (and a new connection pool) on every reload until Postgres runs
// out of connections. Caching the instance on globalThis avoids that. In
// production a single module instance is created normally.
import { PrismaClient } from "@prisma/client";

const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === "development" ? ["error", "warn"] : ["error"],
  });

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;

/**
 * Run a Prisma query, returning `fallback` if the database is unreachable.
 *
 * Screens render at request time and must not 500 (or break `next build`'s
 * data collection) just because Postgres isn't up locally. Real errors are
 * logged; callers get a safe empty result and can show an "offline" state.
 */
export async function safeQuery<T>(fn: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    console.error("[db] query failed, returning fallback:", err);
    return fallback;
  }
}
