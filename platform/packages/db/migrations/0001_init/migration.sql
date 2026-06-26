-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateTable
CREATE TABLE "posts" (
    "post_id" TEXT NOT NULL,
    "scheduled_at" TEXT,
    "platform" TEXT,
    "post_type" TEXT,
    "sku" TEXT,
    "topic" TEXT,
    "theme" TEXT,
    "content_pillar" TEXT,
    "image_prompt" TEXT,
    "video_prompt" TEXT,
    "caption_instagram" TEXT,
    "caption_facebook" TEXT,
    "alt_text" TEXT,
    "source_product_image" TEXT,
    "prompts_approved" BOOLEAN NOT NULL DEFAULT false,
    "creatives_approved" BOOLEAN NOT NULL DEFAULT false,
    "on_hold" BOOLEAN NOT NULL DEFAULT false,
    "media_path" TEXT,
    "video_path" TEXT,
    "cloudinary_url" TEXT,
    "ig_post_id" TEXT,
    "fb_post_id" TEXT,
    "youtube_video_id" TEXT,
    "pipeline_status" TEXT NOT NULL DEFAULT 'draft',
    "last_error" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "posts_pkey" PRIMARY KEY ("post_id")
);

-- CreateTable
CREATE TABLE "ad_campaigns" (
    "campaign_key" TEXT NOT NULL,
    "sku" TEXT,
    "campaign_date" TEXT,
    "campaign_phase" INTEGER,
    "campaign_id" TEXT,
    "adset_id" TEXT,
    "creative_id" TEXT,
    "ad_id" TEXT,
    "status" TEXT,
    "daily_budget_inr" DOUBLE PRECISION,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ad_campaigns_pkey" PRIMARY KEY ("campaign_key")
);

-- CreateTable
CREATE TABLE "insights_cache" (
    "ad_id" TEXT NOT NULL,
    "fetched_date" TEXT NOT NULL,
    "spend_inr" DOUBLE PRECISION,
    "impressions" INTEGER,
    "clicks" INTEGER,
    "purchases" INTEGER,
    "purchase_value_inr" DOUBLE PRECISION,
    "raw" TEXT,

    CONSTRAINT "insights_cache_pkey" PRIMARY KEY ("ad_id","fetched_date")
);

-- CreateTable
CREATE TABLE "influencers" (
    "id" SERIAL NOT NULL,
    "username" TEXT NOT NULL,
    "full_name" TEXT,
    "followers" INTEGER,
    "email" TEXT,
    "bio" TEXT,
    "status" TEXT NOT NULL DEFAULT 'discovered',
    "discovered_via" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "influencers_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "influencer_conversations" (
    "id" SERIAL NOT NULL,
    "influencer_id" INTEGER NOT NULL,
    "direction" TEXT,
    "message" TEXT,
    "channel" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "influencer_conversations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "hashtag_usage" (
    "hashtag" TEXT NOT NULL,
    "last_used" TEXT,
    "count" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "hashtag_usage_pkey" PRIMARY KEY ("hashtag")
);

-- CreateTable
CREATE TABLE "creatives" (
    "id" SERIAL NOT NULL,
    "post_id" TEXT NOT NULL,
    "kind" TEXT NOT NULL,
    "variant_index" INTEGER NOT NULL DEFAULT 0,
    "local_path" TEXT,
    "cloudinary_url" TEXT,
    "cloudinary_public_id" TEXT,
    "status" TEXT NOT NULL DEFAULT 'generating',
    "score" DOUBLE PRECISION,
    "cost_usd" DOUBLE PRECISION,
    "error" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "creatives_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "orders" (
    "order_id" TEXT NOT NULL,
    "sku" TEXT NOT NULL,
    "created_at" TEXT,
    "quantity" INTEGER NOT NULL DEFAULT 1,
    "revenue_inr" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "discount_inr" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "customer_hash" TEXT,
    "landing_ref" TEXT,
    "raw_json" TEXT,
    "ingested_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "orders_pkey" PRIMARY KEY ("order_id","sku")
);

-- CreateTable
CREATE TABLE "ad_spend_daily" (
    "ad_id" TEXT NOT NULL,
    "date" TEXT NOT NULL,
    "campaign_id" TEXT,
    "sku" TEXT,
    "spend_inr" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "impressions" INTEGER NOT NULL DEFAULT 0,
    "clicks" INTEGER NOT NULL DEFAULT 0,
    "purchases" INTEGER NOT NULL DEFAULT 0,
    "purchase_value_inr" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "cpm_inr" DOUBLE PRECISION,
    "ctr" DOUBLE PRECISION,
    "frequency" DOUBLE PRECISION,
    "fetched_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ad_spend_daily_pkey" PRIMARY KEY ("ad_id","date")
);

-- CreateTable
CREATE TABLE "attribution" (
    "scope" TEXT NOT NULL,
    "scope_id" TEXT NOT NULL,
    "date" TEXT NOT NULL,
    "spend_inr" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "revenue_inr" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "paid_roas" DOUBLE PRECISION,
    "blended_roas" DOUBLE PRECISION,
    "organic_assist_inr" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "computed_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "attribution_pkey" PRIMARY KEY ("scope","scope_id","date")
);

-- CreateTable
CREATE TABLE "approval_queue" (
    "id" SERIAL NOT NULL,
    "action_type" TEXT NOT NULL,
    "entity_ref" TEXT NOT NULL,
    "payload_json" TEXT,
    "expected_impact_json" TEXT,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "requested_by" TEXT,
    "requested_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "decided_by" TEXT,
    "decided_at" TIMESTAMP(3),
    "applied_at" TIMESTAMP(3),
    "error" TEXT,
    "expires_at" TIMESTAMP(3),

    CONSTRAINT "approval_queue_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "build_tasks" (
    "id" TEXT NOT NULL,
    "epic" TEXT,
    "story" TEXT,
    "title" TEXT,
    "depends_on" TEXT,
    "status" TEXT NOT NULL DEFAULT 'todo',
    "agent" TEXT,
    "acceptance" TEXT,
    "verify" TEXT,
    "artifacts" TEXT,
    "last_run_at" TIMESTAMP(3),
    "last_error" TEXT,

    CONSTRAINT "build_tasks_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "audit_log" (
    "id" SERIAL NOT NULL,
    "actor" TEXT,
    "action" TEXT,
    "entity" TEXT,
    "entity_id" TEXT,
    "before_json" TEXT,
    "after_json" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "audit_log_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "orgs" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "plan" TEXT NOT NULL DEFAULT 'free',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "orgs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "name" TEXT,
    "role" TEXT NOT NULL DEFAULT 'viewer',
    "org_id" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "posts_sku_scheduled_at_idx" ON "posts"("sku", "scheduled_at");

-- CreateIndex
CREATE INDEX "posts_pipeline_status_idx" ON "posts"("pipeline_status");

-- CreateIndex
CREATE INDEX "ad_campaigns_sku_status_idx" ON "ad_campaigns"("sku", "status");

-- CreateIndex
CREATE UNIQUE INDEX "influencers_username_key" ON "influencers"("username");

-- CreateIndex
CREATE INDEX "influencers_status_idx" ON "influencers"("status");

-- CreateIndex
CREATE INDEX "influencer_conversations_influencer_id_idx" ON "influencer_conversations"("influencer_id");

-- CreateIndex
CREATE INDEX "creatives_post_id_status_idx" ON "creatives"("post_id", "status");

-- CreateIndex
CREATE INDEX "orders_sku_created_at_idx" ON "orders"("sku", "created_at");

-- CreateIndex
CREATE INDEX "orders_created_at_idx" ON "orders"("created_at");

-- CreateIndex
CREATE INDEX "ad_spend_daily_sku_date_idx" ON "ad_spend_daily"("sku", "date");

-- CreateIndex
CREATE INDEX "attribution_scope_scope_id_date_idx" ON "attribution"("scope", "scope_id", "date");

-- CreateIndex
CREATE INDEX "approval_queue_status_requested_at_idx" ON "approval_queue"("status", "requested_at");

-- CreateIndex
CREATE INDEX "build_tasks_status_idx" ON "build_tasks"("status");

-- CreateIndex
CREATE INDEX "audit_log_entity_entity_id_idx" ON "audit_log"("entity", "entity_id");

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE INDEX "users_org_id_idx" ON "users"("org_id");

-- AddForeignKey
ALTER TABLE "influencer_conversations" ADD CONSTRAINT "influencer_conversations_influencer_id_fkey" FOREIGN KEY ("influencer_id") REFERENCES "influencers"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "creatives" ADD CONSTRAINT "creatives_post_id_fkey" FOREIGN KEY ("post_id") REFERENCES "posts"("post_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "users" ADD CONSTRAINT "users_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "orgs"("id") ON DELETE SET NULL ON UPDATE CASCADE;

