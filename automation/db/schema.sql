CREATE TABLE IF NOT EXISTS posts (
    post_id             TEXT PRIMARY KEY,
    scheduled_at        TEXT NOT NULL,
    platform            TEXT NOT NULL,
    post_type           TEXT NOT NULL,
    content_pillar      TEXT,
    sku                 TEXT NOT NULL,
    topic               TEXT NOT NULL,
    theme               TEXT,
    tone                TEXT,
    cultural_moment     TEXT DEFAULT 'none',
    source_product_image TEXT NOT NULL,
    source_lifestyle_image TEXT,
    reference_notes     TEXT,

    image_prompt        TEXT,
    video_prompt        TEXT,
    caption_instagram   TEXT,
    caption_facebook    TEXT,
    ad_headline         TEXT,
    ad_primary_text     TEXT,
    alt_text            TEXT,

    prompts_approved    INTEGER DEFAULT 0,
    prompts_approved_at TEXT,
    creatives_approved  INTEGER DEFAULT 0,
    creatives_approved_at TEXT,
    on_hold             INTEGER DEFAULT 0,

    image_paths         TEXT,
    video_path          TEXT,
    cloudinary_urls     TEXT,
    cloudinary_public_ids TEXT,

    ig_post_id          TEXT,
    fb_post_id          TEXT,
    youtube_video_id    TEXT,
    meta_scheduled_post_id TEXT,

    pipeline_status     TEXT DEFAULT 'draft',
    last_error          TEXT,
    last_error_at       TEXT,

    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ad_campaigns (
    campaign_key        TEXT PRIMARY KEY,
    sku                 TEXT NOT NULL,
    campaign_date       TEXT NOT NULL,
    campaign_phase      INTEGER NOT NULL,
    campaign_id         TEXT,
    adset_id            TEXT,
    creative_id         TEXT,
    ad_id               TEXT,
    status              TEXT DEFAULT 'PAUSED',
    daily_budget_inr    INTEGER,
    post_id             TEXT REFERENCES posts(post_id),
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS insights_cache (
    ad_id               TEXT NOT NULL,
    fetched_date        TEXT NOT NULL,
    impressions         INTEGER,
    clicks              INTEGER,
    ctr                 REAL,
    spend_inr           REAL,
    frequency           REAL,
    cost_per_atc_inr    REAL,
    roas                REAL,
    action_taken        TEXT,
    PRIMARY KEY (ad_id, fetched_date)
);

CREATE TABLE IF NOT EXISTS influencers (
    handle                  TEXT PRIMARY KEY,
    full_name               TEXT,
    email                   TEXT,
    ig_user_id              TEXT,       -- IGSID from conversations endpoint (NOT Business Discovery)
    follower_count          INTEGER,
    engagement_rate         REAL,       -- (like_count + comments_count) / follower_count
    source_hashtag          TEXT,
    post_url                TEXT,
    like_count              INTEGER,
    comments_count          INTEGER,
    template_used           TEXT,
    last_reply_preview      TEXT,
    last_message_at         TEXT,
    last_checked_at         TEXT,       -- last time check-replies polled this thread
    shipping_address        TEXT,
    product_dispatched_at   TEXT,
    agreed_post_date        TEXT,
    post_live_url           TEXT,
    status                  TEXT DEFAULT 'discovered',
    notes                   TEXT,
    outreach_sent_at        TEXT,
    dm_draft_generated_at   TEXT,
    reply_received_at       TEXT,
    collab_agreed           INTEGER DEFAULT 0,
    product_shipped         INTEGER DEFAULT 0,
    tracking_code           TEXT,
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS influencer_conversations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    handle              TEXT NOT NULL,
    ig_thread_id        TEXT,
    direction           TEXT NOT NULL,
    message_text        TEXT NOT NULL,
    sent_at             TEXT NOT NULL,
    meta_message_id     TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS hashtag_usage (
    hashtag             TEXT NOT NULL,
    queried_date        TEXT NOT NULL,
    PRIMARY KEY (hashtag, queried_date)
);

-- ════════════════════════════════════════════════════════════════════════════
-- Autonomous Marketing Platform — new tables (docs/plan/moregreen/01-data-model.md)
-- Additive only. SQLite stays usable for the CLI; Postgres/Prisma is canonical.
-- ════════════════════════════════════════════════════════════════════════════

-- One row per generated asset variant (decouples assets from posts).
CREATE TABLE IF NOT EXISTS creatives (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id             TEXT REFERENCES posts(post_id),
    kind                TEXT CHECK (kind IN ('image','video')),
    variant_index       INTEGER DEFAULT 0,
    local_path          TEXT,
    cloudinary_url      TEXT,
    cloudinary_public_id TEXT,
    status              TEXT DEFAULT 'generating'
                        CHECK (status IN ('generating','ready','failed','selected','rejected')),
    cost_usd            REAL,
    error               TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_creatives_post_status ON creatives(post_id, status);

-- Shopify orders — financial record, never deleted. One row per (order_id, sku)
-- line item so multi-SKU orders split cleanly for per-SKU attribution (doc 03).
-- Re-sync upserts by the composite key.
CREATE TABLE IF NOT EXISTS orders (
    order_id            TEXT NOT NULL,
    sku                 TEXT NOT NULL,        -- 'unmapped' when product not in config.SKUS
    created_at          TEXT,
    quantity            INTEGER DEFAULT 1,
    revenue_inr         REAL DEFAULT 0,       -- line subtotal (negative for refunds)
    discount_inr        REAL DEFAULT 0,
    customer_hash       TEXT,                 -- sha256(lower(email))
    landing_ref         TEXT,                 -- utm/referrer if available
    raw_json            TEXT,
    ingested_at         TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (order_id, sku)
);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_sku_created ON orders(sku, created_at);

-- Per-ad per-day spend + conversions (lifetime snapshot stays in insights_cache).
CREATE TABLE IF NOT EXISTS ad_spend_daily (
    ad_id               TEXT NOT NULL,
    date                TEXT NOT NULL,        -- YYYY-MM-DD (IST bucket)
    campaign_id         TEXT,
    sku                 TEXT,
    spend_inr           REAL DEFAULT 0,
    impressions         INTEGER DEFAULT 0,
    clicks              INTEGER DEFAULT 0,
    purchases           INTEGER DEFAULT 0,
    purchase_value_inr  REAL DEFAULT 0,
    cpm_inr             REAL,
    ctr                 REAL,
    frequency           REAL,
    fetched_at          TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (ad_id, date)
);
CREATE INDEX IF NOT EXISTS idx_spend_sku_date ON ad_spend_daily(sku, date);

-- Computed ROAS rollups (recompute overwrites).
CREATE TABLE IF NOT EXISTS attribution (
    scope               TEXT NOT NULL CHECK (scope IN ('sku','campaign','blended')),
    scope_id            TEXT NOT NULL,
    date                TEXT NOT NULL,
    paid_roas           REAL,
    blended_roas        REAL,
    organic_assist_inr  REAL DEFAULT 0,
    spend_inr           REAL DEFAULT 0,
    revenue_inr         REAL DEFAULT 0,
    computed_at         TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (scope, scope_id, date)
);
CREATE INDEX IF NOT EXISTS idx_attr_scope_date ON attribution(scope, scope_id, date);

-- Money/state proposals awaiting human decision. Status transitions guarded in code (doc 04).
CREATE TABLE IF NOT EXISTS approval_queue (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type         TEXT NOT NULL CHECK (action_type IN
                        ('activate_ad','scale_budget','reallocate','price_test',
                         'publish_post','product_copy_change')),
    entity_ref          TEXT,                 -- polymorphic ref (ad_id, campaign_key, post_id, sku…)
    payload_json        TEXT,                 -- {current, proposed, …}
    expected_impact_json TEXT,                -- {projected_roas, projected_spend, …}
    status              TEXT DEFAULT 'pending' CHECK (status IN
                        ('pending','approved','rejected','applied','failed','expired')),
    requested_by        TEXT DEFAULT 'orchestrator',
    requested_at        TEXT DEFAULT (datetime('now')),
    decided_by          TEXT,
    decided_at          TEXT,
    applied_at          TEXT,
    error               TEXT,
    expires_at          TEXT
);
CREATE INDEX IF NOT EXISTS idx_approval_status_req ON approval_queue(status, requested_at);
-- Dedupe key for identical pending proposals (entity + action + proposed payload).
CREATE UNIQUE INDEX IF NOT EXISTS uq_approval_pending
    ON approval_queue(action_type, entity_ref, payload_json)
    WHERE status = 'pending';

-- Mirror of backlog.yaml for the web Build screen.
CREATE TABLE IF NOT EXISTS build_tasks (
    id                  TEXT PRIMARY KEY,
    epic                TEXT,
    story               TEXT,
    title               TEXT,
    depends_on          TEXT,                 -- json array
    status              TEXT DEFAULT 'todo'
                        CHECK (status IN ('todo','in_progress','done','blocked')),
    agent               TEXT,
    acceptance          TEXT,
    verify              TEXT,
    artifacts           TEXT,                 -- json array
    last_run_at         TEXT,
    last_error          TEXT
);
CREATE INDEX IF NOT EXISTS idx_build_tasks_status ON build_tasks(status);

-- Append-only audit trail for every mutating action.
CREATE TABLE IF NOT EXISTS audit_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    actor               TEXT,                 -- human | orchestrator | worker
    action              TEXT,
    entity              TEXT,
    entity_id           TEXT,
    before_json         TEXT,
    after_json          TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity, entity_id);
