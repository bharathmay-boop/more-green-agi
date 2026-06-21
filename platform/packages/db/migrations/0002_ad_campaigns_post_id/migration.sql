-- AlterTable: pipeline (create_ads.py) writes ad_campaigns.post_id; the SQLite
-- schema already had it, Prisma 0001 missed it. Add it so the PG insert matches.
ALTER TABLE "ad_campaigns" ADD COLUMN "post_id" TEXT;
