# 30-Day Content Calendar — Design Spec
**Date:** 2026-06-10
**Sprint window:** June 10 – July 9, 2026
**Season:** Monsoon Immunity

---

## Overview

A pre-planned 30-post content calendar for More Green, covering Instagram and Facebook. The calendar is stored as `automation/strategy/calendar.yaml` and pushed to Google Sheets via a new `seed-calendar` command. From Sheets the standard pipeline (sync-sheets → generate-prompts → generate-images → post-organic) runs unchanged.

---

## SKU Split

| SKU | Posts | % |
|---|---|---|
| sunflower | 11 | 37% |
| blueberry | 9 | 30% |
| brand (awareness) | 10 | 33% |

`brand` is a new SKU entry added to `automation/config/brand.yaml`. It carries brand-level `product_facts` and `differentiation_angle` so `generate_prompts.py` can write captions without referencing a specific product.

---

## Weekly Themes

| Theme slug | Dates | Goal |
|---|---|---|
| `monsoon_reset` | Jun 10–16 | Hook audience at season change. Immunity + gut health. |
| `science_of_green` | Jun 17–23 | Build credibility. Lab testing, nutrient facts, convert skeptics. |
| `mix_it_make_it` | Jun 24–30 | Drive engagement. Recipes + daily habit content. Lower purchase barrier. |
| `real_people_real_green` | Jul 1–7 | Social proof. UGC-style. Convert warm audience. |
| `your_green_your_way` | Jul 8–9 | Direct CTA. Purchase intent close. |

---

## Content Pillar & Format Mix

| Pillar | Count | Formats |
|---|---|---|
| product | 8 | feed_image, reels, carousel |
| educational | 8 | carousel, feed_image |
| recipe | 6 | reels, feed_image, carousel |
| social_proof | 5 | feed_image, carousel, reels |
| founder_bts | 3 | story, reels |

Sales-driving posts (product + social_proof with direct CTA): 13 of 30.

---

## All 30 Posts

### Week 1 — Monsoon Reset

| # | Date | SKU | Pillar | Format | Topic | Tone | Cultural Moment |
|---|---|---|---|---|---|---|---|
| 1 | Jun 10 Wed | sunflower | product | feed_image | "Monsoon is the hardest season on your gut. Sunflower microgreens: 40x more Vitamin E than mature seeds." | bold_direct | monsoon_immunity |
| 2 | Jun 11 Thu | blueberry | educational | carousel | "4 reasons blueberry microgreens powder beats dried blueberry for monsoon immunity" | scientific_warm | monsoon_immunity |
| 3 | Jun 12 Fri | brand | founder_bts | reels | "Started in a small polyhouse in Bangalore. Still growing everything here. This is More Green." | transparent_founder | none |
| 4 | Jun 13 Sat | sunflower | social_proof | feed_image | "Pune customer: how sunflower microgreens changed her monsoon routine" | warm_authentic | monsoon_immunity |
| 5 | Jun 14 Sun* | brand | product | story | "Why we test every batch for heavy metals, microbes, and nutrients. Every single one." | transparent_expert | none |
| 6 | Jun 15 Mon | blueberry | product | feed_image | "Anthocyanins in monsoon: what the purple pigment in blueberry microgreens does for immunity" | scientific_warm | monsoon_immunity |
| 7 | Jun 16 Tue | brand | educational | feed_image | "Microgreens vs. mature plants: why harvesting at day 7 changes everything about nutrition" | scientific_warm | none |

### Week 2 — The Science of Green

| # | Date | SKU | Pillar | Format | Topic | Tone | Cultural Moment |
|---|---|---|---|---|---|---|---|
| 8 | Jun 17 Wed | sunflower | educational | carousel | "40x more Vitamin E than mature sunflower seeds. The peer-reviewed data." | scientific_warm | none |
| 9 | Jun 18 Thu | blueberry | educational | feed_image | "Pterostilbene: the cognitive compound in blueberry microgreens that dried fruit doesn't have" | scientific_warm | none |
| 10 | Jun 19 Fri | brand | product | feed_image | "FSSAI-approved, NABL-accredited. Every batch — not just the first one." | bold_transparent | none |
| 11 | Jun 20 Sat | sunflower | product | reels | "Cold-pressed, no heat treatment. What happens to nutrients when processing cuts corners." | bold_direct | none |
| 12 | Jun 21 Sun* | brand | founder_bts | story | "Sunday in the Bangalore polyhouse. This is where More Green starts." | transparent_founder | none |
| 13 | Jun 22 Mon | blueberry | educational | feed_image | "4-6x more anthocyanins than ripe blueberries. Why the microgreens stage matters." | scientific_warm | none |
| 14 | Jun 23 Tue | brand | educational | carousel | "What 'pure nutrition' actually means: how we source, grow, process, and test every SKU" | transparent_expert | none |

### Week 3 — Mix It, Make It

| # | Date | SKU | Pillar | Format | Topic | Tone | Cultural Moment |
|---|---|---|---|---|---|---|---|
| 15 | Jun 24 Wed | sunflower | recipe | reels | "Sunflower microgreens post-workout shake: the ₹13-per-serving recovery drink" | energetic_practical | none |
| 16 | Jun 25 Thu | blueberry | recipe | reels | "Blueberry microgreens smoothie bowl: 3 ingredients, 2 minutes" | warm_inspirational | none |
| 17 | Jun 26 Fri | brand | product | feed_image | "Single-sourced. India-grown. No additives. What you see on the label is all that's in the pouch." | bold_transparent | none |
| 18 | Jun 27 Sat | sunflower | recipe | feed_image | "Zinc + Vitamin E in one teaspoon: the sunflower microgreens curd rice recipe" | warm_practical | none |
| 19 | Jun 28 Sun* | brand | founder_bts | story | "Why we chose microgreens over dried ingredients: the decision that defined More Green" | transparent_founder | none |
| 20 | Jun 29 Mon | blueberry | recipe | carousel | "5 ways to add blueberry microgreens powder to food your family already eats" | warm_practical | none |
| 21 | Jun 30 Tue | sunflower | educational | feed_image | "1 tsp = 15% daily zinc. Why sunflower microgreens powder outperforms a zinc supplement" | scientific_warm | none |

### Week 4 — Real People, Real Green

| # | Date | SKU | Pillar | Format | Topic | Tone | Cultural Moment |
|---|---|---|---|---|---|---|---|
| 22 | Jul 1 Wed | brand | social_proof | feed_image | "₹390. NABL lab-tested. Grown in India. What customers in 3 cities are saying." | warm_authentic | none |
| 23 | Jul 2 Thu | blueberry | social_proof | carousel | "Parent in Delhi: how she gets blueberry microgreens into her kids' food every day" | warm_relatable | none |
| 24 | Jul 3 Fri | sunflower | social_proof | feed_image | "Pune customer: 'I stopped needing a Vitamin E supplement after switching to this'" | warm_authentic | none |
| 25 | Jul 4 Sat | brand | social_proof | reels | "3 cities. 200+ orders. Real reviews from people who wanted honest nutrition." | warm_authentic | none |
| 26 | Jul 5 Sun* | blueberry | product | story | "Blueberry microgreens vs. dried blueberry powder — one slide, no jargon." | bold_direct | none |
| 27 | Jul 6 Mon | sunflower | product | feed_image | "Every pack harvested at exactly day 7. Not day 6. Not day 8. Here is why that matters." | transparent_expert | none |
| 28 | Jul 7 Tue | sunflower | social_proof | reels | "Mumbai customer switched from a ₹400/month multivitamin to sunflower microgreens powder." | warm_authentic | none |

### Week 5 — Your Green, Your Way

| # | Date | SKU | Pillar | Format | Topic | Tone | Cultural Moment |
|---|---|---|---|---|---|---|---|
| 29 | Jul 8 Wed | blueberry | product | carousel | "Sunflower or blueberry? Which More Green powder fits your goal — an honest guide" | consultative_direct | none |
| 30 | Jul 9 Thu | brand | product | feed_image | "30 days of More Green. What customers who started in June are saying now." | warm_authentic | none |

*Sunday posts are optional — skipped by default in `seed-calendar`, included with `--include-sundays` flag.*

---

## Files Changed / Created

| File | Action | Purpose |
|---|---|---|
| `automation/config/brand.yaml` | Edit — append | Add `brand` SKU entry |
| `automation/strategy/calendar.yaml` | Create | 30-post content plan (source of truth) |
| `automation/commands/seed_calendar.py` | Create | Pushes calendar posts to Google Sheets |
| `automation/main.py` | Edit | Register `seed-calendar` command |

---

## `seed-calendar` Command

**Location:** `automation/commands/seed_calendar.py`

**Args:**
- `--dry-run` — print rows, no writes
- `--include-sundays` — include 4 Sunday story posts (default: skip)
- `--sprint YYYY-MM-DD` — filter to posts on or after this date (for future multi-sprint calendars)

**Duplicate guard:** fetches existing `post_id` values from Sheet column A before appending — safe to re-run.

**Sheet columns written (matches `new_week.py` format):**
A=post_id, B=scheduled_date, C=scheduled_time, D=platform, E=post_type, F=content_pillar, G=sku, H=topic, I=theme, J=tone, K=cultural_moment, L=source_product_image, M=source_lifestyle_image, N=reference_notes, O=pipeline_status (hardcoded `draft`), P=on_hold (empty)

---

## Post-Command Workflow

```
seed-calendar          → 30 rows in Sheets (review + edit freely)
sync-sheets            → rows land in DB
generate-prompts       → Claude writes captions + image/video prompts
generate-images        → FLUX Kontext renders creatives
post-organic           → publishes to Instagram + Facebook
```

---

## Adjustment Points

| Stage | How to edit |
|---|---|
| Before `seed-calendar` | Edit `calendar.yaml` directly |
| After push (rows in Sheets) | Edit cells directly in Sheets — sync-sheets picks up changes |
| After sync (post in DB) | Use dashboard — edit or mark `on_hold` |
