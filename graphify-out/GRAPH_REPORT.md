# Graph Report - D:\More Green AGI\automation  (2026-06-01)

## Corpus Check
- Corpus is ~11,206 words - fits in a single context window. You may not need a graph.

## Summary
- 228 nodes · 382 edges · 23 communities (16 shown, 7 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.85)
- Token cost: 8,500 input · 2,100 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Weekly Orchestration & Onboarding|Weekly Orchestration & Onboarding]]
- [[_COMMUNITY_Streamlit Dashboard Commands Layer|Streamlit Dashboard Commands Layer]]
- [[_COMMUNITY_Dashboard UI Screens|Dashboard UI Screens]]
- [[_COMMUNITY_Audience Sync & Config|Audience Sync & Config]]
- [[_COMMUNITY_Organic Post Publishing|Organic Post Publishing]]
- [[_COMMUNITY_Image Generation & Upload|Image Generation & Upload]]
- [[_COMMUNITY_Meta Ad Campaign Creation|Meta Ad Campaign Creation]]
- [[_COMMUNITY_Video Generation Pipeline|Video Generation Pipeline]]
- [[_COMMUNITY_Ad Tuning & Founder Notifications|Ad Tuning & Founder Notifications]]
- [[_COMMUNITY_Meta Ads Lifecycle (Semantic)|Meta Ads Lifecycle (Semantic)]]
- [[_COMMUNITY_Ad Performance Monitoring|Ad Performance Monitoring]]
- [[_COMMUNITY_Brand & SKU Config|Brand & SKU Config]]
- [[_COMMUNITY_YouTube Publishing|YouTube Publishing]]
- [[_COMMUNITY_Pipeline Status & Dashboard App|Pipeline Status & Dashboard App]]
- [[_COMMUNITY_Secrets & Security Setup|Secrets & Security Setup]]
- [[_COMMUNITY_Setup Entry Point|Setup Entry Point]]
- [[_COMMUNITY_Ads Log JSON File|Ads Log JSON File]]
- [[_COMMUNITY_Onboard Run Entry|Onboard Run Entry]]
- [[_COMMUNITY_Instagram Posting|Instagram Posting]]
- [[_COMMUNITY_Facebook Posting|Facebook Posting]]

## God Nodes (most connected - your core abstractions)
1. `get_db()` - 38 edges
2. `run()` - 11 edges
3. `run()` - 10 edges
4. `run()` - 10 edges
5. `run()` - 9 edges
6. `resume_pending()` - 9 edges
7. `notify_founder()` - 9 edges
8. `run()` - 8 edges
9. `require_approval()` - 8 edges
10. `screen_creative_approval()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Dashboard Setup Guide (V0)` --references--> `cli()`  [EXTRACTED]
  automation/V0_DASHBOARD_INSTRUCTIONS.md → main.py
- `screen_creative_approval()` --calls--> `notify_founder()`  [EXTRACTED]
  commands/_dashboard_app.py → utils/notifications.py
- `run()` --calls--> `get_db()`  [EXTRACTED]
  commands/create_ads.py → utils/db.py
- `run()` --calls--> `get_db()`  [EXTRACTED]
  commands/generate_images.py → utils/db.py
- `run()` --calls--> `get_db()`  [EXTRACTED]
  commands/generate_videos.py → utils/db.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Content Production Pipeline (Prompts → Images → Upload → Post)** — generate_prompts_run, generate_images_run, upload_media_run, post_organic_run [INFERRED 0.95]
- **Meta Ads Lifecycle (Create → Monitor → Tune)** — create_ads_run, monitor_ads_run, tune_ads_run [INFERRED 0.95]
- **Weekly Founder Workflow (New Week → Sync Sheets → Dashboard Review)** — new_week_run, sync_sheets_run, dashboard_screen_weekly_overview [INFERRED 0.85]
- **Content Pipeline Approval Gate** — utils_guards, db_posts_table, main_cli [INFERRED 0.85]
- **YAML Config Loading into Runtime Constants** — config_module, config_brand_yaml, config_hashtags_yaml, config_cultural_calendar_yaml [EXTRACTED 1.00]
- **Meta API Safety Layer** — utils_meta_auth, utils_retry, db_ad_campaigns_table [INFERRED 0.75]

## Communities (23 total, 7 thin omitted)

### Community 0 - "Weekly Orchestration & Onboarding"
Cohesion: 0.05
Nodes (38): run(), _load_existing(), run(), _write_env(), approve_prompts(), check(), create_ads(), dashboard() (+30 more)

### Community 1 - "Streamlit Dashboard Commands Layer"
Cohesion: 0.13
Nodes (23): Anthropic, main(), _post_card(), str, More Green Studio — Streamlit dashboard for the founder.  Run locally:  streamli, screen_creative_approval(), screen_post_detail(), screen_weekly_overview() (+15 more)

### Community 2 - "Dashboard UI Screens"
Cohesion: 0.12
Nodes (21): main (Dashboard Router), screen_creative_approval (Dashboard Screen), screen_post_detail (Dashboard Screen), screen_weekly_overview (Dashboard Screen), _sidebar_health (Dashboard Sidebar), _process_post (Image Generation per Post), generate_images.run (FLUX Kontext Image Generator), _generate_one (Single Post Claude Prompt Call) (+13 more)

### Community 3 - "Audience Sync & Config"
Cohesion: 0.15
Nodes (16): bool, Sync Shopify customer emails to Meta Custom Audience (SHA-256 hashed)., run(), Cultural Calendar YAML, Hashtags Config YAML, Config Module, ad_campaigns Table, insights_cache Table (+8 more)

### Community 4 - "Organic Post Publishing"
Cohesion: 0.16
Nodes (17): APIBodyError Exception Class, _fetch_approved_posts(), _post_facebook(), _post_instagram(), bool, str, run(), Exception (+9 more)

### Community 5 - "Image Generation & Upload"
Cohesion: 0.18
Nodes (16): _fetch_posts(), _process_post(), bool, str, run(), _fetch_posts(), _init_cloudinary(), bool (+8 more)

### Community 6 - "Meta Ad Campaign Creation"
Cohesion: 0.18
Nodes (12): AdAccount, _create_campaign_for_post(), _fetch_approved_posts(), bool, str, run(), _load(), str (+4 more)

### Community 7 - "Video Generation Pipeline"
Cohesion: 0.26
Nodes (14): _fetch_posts(), _load_pending(), _poll(), _process_post(), bool, str, Poll any video jobs saved in pending_video_jobs.json., resume_pending() (+6 more)

### Community 8 - "Ad Tuning & Founder Notifications"
Cohesion: 0.33
Nodes (8): _apply_action(), _evaluate(), bool, str, run(), notify_founder(), str, Send email via SendGrid. Silent no-op if SENDGRID_API_KEY is not set.

### Community 9 - "Meta Ads Lifecycle (Semantic)"
Cohesion: 0.20
Nodes (10): _create_campaign_for_post (Ad Campaign Builder), create_ads.run (Meta Ad Campaign Creator), export_report.run (Weekly Report Printer), _extract_roas (ROAS Extractor), _fetch_insights (Ad Insight Fetcher), monitor_ads.run (Meta Insights Fetcher), Idempotency Pattern (campaign_key dedup), _apply_action (Ad Action Applier) (+2 more)

### Community 10 - "Ad Performance Monitoring"
Cohesion: 0.38
Nodes (6): _extract_roas(), _fetch_insights(), str, Extract purchase ROAS from the actions array., run(), float

### Community 11 - "Brand & SKU Config"
Cohesion: 0.33
Nodes (6): Brand Voice & Banned Phrases, Brand Config YAML, SKU: Blueberry Microgreens, SKU: Moringa Microgreens, SKU: Sunflower Microgreens, SKU: Wheatgrass Microgreens

### Community 12 - "YouTube Publishing"
Cohesion: 0.50
Nodes (4): _fetch_posts(), bool, str, run()

## Knowledge Gaps
- **35 isolated node(s):** `str`, `str`, `str`, `int`, `str` (+30 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_db()` connect `Streamlit Dashboard Commands Layer` to `Weekly Orchestration & Onboarding`, `Audience Sync & Config`, `Organic Post Publishing`, `Image Generation & Upload`, `Meta Ad Campaign Creation`, `Video Generation Pipeline`, `Ad Tuning & Founder Notifications`, `Ad Performance Monitoring`, `YouTube Publishing`?**
  _High betweenness centrality (0.203) - this node is a cross-community bridge._
- **Why does `Config Module` connect `Audience Sync & Config` to `Brand & SKU Config`, `Meta Ad Campaign Creation`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `run()` connect `Organic Post Publishing` to `Ad Tuning & Founder Notifications`, `Streamlit Dashboard Commands Layer`, `Meta Ad Campaign Creation`, `Weekly Orchestration & Onboarding`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **What connects `More Green Studio — Streamlit dashboard for the founder.  Run locally:  streamli`, `str`, `str` to the rest of the system?**
  _74 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Weekly Orchestration & Onboarding` be split into smaller, more focused modules?**
  _Cohesion score 0.05121951219512195 - nodes in this community are weakly interconnected._
- **Should `Streamlit Dashboard Commands Layer` be split into smaller, more focused modules?**
  _Cohesion score 0.13227513227513227 - nodes in this community are weakly interconnected._
- **Should `Dashboard UI Screens` be split into smaller, more focused modules?**
  _Cohesion score 0.11904761904761904 - nodes in this community are weakly interconnected._