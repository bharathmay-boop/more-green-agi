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

/**
 * Append a row to the audit_log (who did what to which entity, before→after).
 * Best-effort: a failed audit write must never block or roll back the action it
 * records, so it swallows errors (and logs them). Call AFTER the action commits.
 */
export async function writeAudit(entry: {
  actor: string;
  action: string;
  entity: string;
  entityId: string | number;
  before?: unknown;
  after?: unknown;
}): Promise<void> {
  try {
    await prisma.auditLog.create({
      data: {
        actor: entry.actor,
        action: entry.action,
        entity: entry.entity,
        entityId: String(entry.entityId),
        beforeJson: entry.before === undefined ? null : JSON.stringify(entry.before),
        afterJson: entry.after === undefined ? null : JSON.stringify(entry.after),
      },
    });
  } catch (err) {
    console.error("[audit] write failed (action still applied):", err);
  }
}
