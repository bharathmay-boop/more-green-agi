"""Python workers for the More Green platform.

These entrypoints consume jobs enqueued by the Next.js control plane
(``platform/apps/web/lib/queue.ts``) and dispatch each to the matching
``automation/commands/*`` integration. See docs/plan/moregreen/05.
"""
