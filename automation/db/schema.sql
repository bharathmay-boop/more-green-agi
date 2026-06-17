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
