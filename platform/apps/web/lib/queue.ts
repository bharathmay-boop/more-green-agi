/**
 * lib/queue.ts — Redis-backed job queue bridge.
 *
 * The Next.js control plane enqueues jobs here; Python workers in
 * `platform/workers/*` consume them and call the existing
 * `automation/commands/*` integrations. The web app polls job status.
 *
 * Money-safety: enqueueing a job is NOT the same as applying spend. Any
 * spend-affecting job (apply-approved) must be gated by an approved
 * `approval_queue` row before it is enqueued — see doc 04.
 *
 * Connection is lazy: importing this module (e.g. during `next build`)
 * never opens a socket. A connection is only attempted on first use, so
 * builds succeed with no Redis available.
 */

import type { Redis as RedisClient } from "ioredis";

/** Job types the Python workers know how to consume. */
export type JobType =
  | "generate" // prompts/images/videos for a post
  | "post_organic" // organic publish
  | "create_ads" // create campaign (PAUSED)
  | "monitor_ads" // pull insights
  | "tune_ads" // produce scale/pause proposals
  | "sync_orders" // Shopify order ingest
  | "attribution" // recompute ROAS rollups
  | "apply_approved" // apply an approved proposal (spend-gated)
  | "strategize"; // strategist allocation pass

export type JobStatus = "queued" | "running" | "done" | "failed";

export interface Job<T = Record<string, unknown>> {
  id: string;
  type: JobType;
  payload: T;
  status: JobStatus;
  enqueuedAt: string; // ISO timestamp
  error?: string | null;
}

const QUEUE_KEY = "moregreen:jobs:queue"; // LPUSH/BRPOP work list
const JOB_KEY_PREFIX = "moregreen:job:"; // per-job hash

function jobKey(id: string): string {
  return `${JOB_KEY_PREFIX}${id}`;
}

let client: RedisClient | null = null;

/**
 * Lazily construct a single shared ioredis client. `lazyConnect` keeps the
 * socket closed until the first command, so module import (and `next build`)
 * stays offline-safe.
 */
async function getRedis(): Promise<RedisClient> {
  if (client) return client;
  const { default: Redis } = await import("ioredis");
  client = new Redis(process.env.REDIS_URL ?? "redis://localhost:6379", {
    lazyConnect: true,
    maxRetriesPerRequest: 2,
    enableOfflineQueue: false,
  });
  return client;
}

function newId(): string {
  // Stable, dependency-free id: time + random suffix.
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * Enqueue a job for the Python workers. Returns the created Job. Throws if
 * Redis is unreachable — callers (route handlers / server actions) should
 * surface a "queue down" state to the UI rather than swallow the error.
 */
export async function enqueueJob<T extends Record<string, unknown>>(
  type: JobType,
  payload: T,
): Promise<Job<T>> {
  const job: Job<T> = {
    id: newId(),
    type,
    payload,
    status: "queued",
    enqueuedAt: new Date().toISOString(),
    error: null,
  };

  const redis = await getRedis();
  await redis
    .multi()
    .hset(jobKey(job.id), {
      id: job.id,
      type: job.type,
      payload: JSON.stringify(job.payload),
      status: job.status,
      enqueuedAt: job.enqueuedAt,
      error: "",
    })
    .lpush(QUEUE_KEY, job.id)
    .exec();

  return job;
}

/** Read a job's current state for status polling. Returns null if unknown. */
export async function getJob(id: string): Promise<Job | null> {
  const redis = await getRedis();
  const raw = await redis.hgetall(jobKey(id));
  if (!raw || !raw.id) return null;
  return {
    id: raw.id,
    type: raw.type as JobType,
    payload: raw.payload ? JSON.parse(raw.payload) : {},
    status: (raw.status as JobStatus) || "queued",
    enqueuedAt: raw.enqueuedAt,
    error: raw.error || null,
  };
}

/** True when Redis answers a PING — used to drive the "queue down" banner. */
export async function isQueueHealthy(): Promise<boolean> {
  try {
    const redis = await getRedis();
    const pong = await redis.ping();
    return pong === "PONG";
  } catch {
    return false;
  }
}
