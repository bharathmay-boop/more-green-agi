# 30-Day Content Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 30-post Monsoon Sprint content calendar to `automation/strategy/calendar.yaml` and a `seed-calendar` CLI command that pushes all posts to Google Sheets for review before the standard pipeline runs.

**Architecture:** A new `calendar.yaml` file is the content blueprint. A new `seed_calendar.py` command reads it, filters Sundays by default, deduplicates against existing Sheet rows, and batch-appends. `brand` is added as a valid SKU in `brand.yaml` and `sync_sheets.py` so brand-awareness posts flow through the same pipeline unchanged.

**Tech Stack:** Python 3.11, PyYAML, gspread, click — all already in requirements.txt.

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Edit | `automation/config/brand.yaml` | Add `brand` SKU entry |
| Edit | `automation/commands/sync_sheets.py` | Accept `"brand"` in `SKU_VALUES` |
| Create | `automation/strategy/calendar.yaml` | 30-post content blueprint |
| Create | `automation/commands/seed_calendar.py` | CLI command: read calendar → push to Sheets |
| Create | `automation/tests/test_seed_calendar.py` | Unit tests for seed logic |
| Edit | `automation/main.py` | Register `seed-calendar` command |

---

## Task 1: Add `brand` SKU to config and validator

**Files:**
- Modify: `automation/config/brand.yaml`
- Modify: `automation/commands/sync_sheets.py:14`

- [ ] **Step 1: Append `brand` SKU entry to `brand.yaml`**

Open `automation/config/brand.yaml`. After the `wheatgrass` entry (line 97), append:

```yaml
  - id: brand
    name: "More Green"
    price_inr: null
    shopify_url: "https://moregreen.in"
    product_facts:
      - "FSSAI-approved, NABL-accredited lab testing on every batch"
      - "Single-sourced, India-grown ingredients from Bangalore polyhouse"
      - "No additives, no heat treatment — nothing on the label that isn't in the pouch"
    differentiation_angle: >
      More Green is built on one principle: honest nutrition. Every ingredient is
      single-sourced, every batch is lab-tested, and nothing is added that isn't on
      the label. Started in a Bangalore polyhouse in 2024, still grown the same way.
    image_prompt_base: >
      The More Green brand story is shown in [SCENE]. Clean, honest, India-grown.
      Keep all brand elements completely unchanged. Add [LIGHTING]. [CAMERA].
    video_prompt_base: >
      The More Green brand identity is visible throughout. [ACTION]. Brand
      elements remain sharp and fully readable throughout. [MOOD].
```

- [ ] **Step 2: Add `"brand"` to `SKU_VALUES` in `sync_sheets.py`**

In `automation/commands/sync_sheets.py`, change line 14 from:

```python
SKU_VALUES       = {"sunflower", "blueberry", "moringa", "wheatgrass"}
```

to:

```python
SKU_VALUES       = {"sunflower", "blueberry", "moringa", "wheatgrass", "brand"}
```

- [ ] **Step 3: Verify config loads `brand` SKU correctly**

```powershell
cd D:\More Green AGI\automation
python -c "from config import SKUS; print(SKUS['brand']['name'])"
```

Expected output:
```
More Green
```

- [ ] **Step 4: Commit**

```powershell
git add automation/config/brand.yaml automation/commands/sync_sheets.py
git commit -m "feat: add brand SKU for brand-awareness posts"
```

---

## Task 2: Create `automation/strategy/calendar.yaml`

**Files:**
- Create: `automation/strategy/calendar.yaml`

- [ ] **Step 1: Create the `strategy` directory**

```powershell
mkdir "D:\More Green AGI\automation\strategy"
```

- [ ] **Step 2: Create `calendar.yaml` with all 30 posts**

Create `automation/strategy/calendar.yaml` with this exact content:

```yaml
# automation/strategy/calendar.yaml
# Sprint: Monsoon — Jun 10 to Jul 9, 2026
# Run: python main.py seed-calendar [--include-sundays] [--dry-run]

meta:
  sprint: "2026-06-10"
  label: "Monsoon Sprint — June / July 2026"
  season: monsoon_immunity
  sku_split:
    sunflower: 0.37
    blueberry: 0.30
    brand: 0.33

posts:
  # ── WEEK 1: Monsoon Reset ─────────────────────────────────────────────────
  - post_id: "2026-06-10_01"
    scheduled_date: "2026-06-10"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: product
    sku: sunflower
    topic: "Monsoon is the hardest season on your gut. Sunflower microgreens: 40x more Vitamin E than mature seeds."
    theme: monsoon_reset
    tone: bold_direct
    cultural_moment: monsoon_immunity
    source_product_image: "Files/sunflower/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Open with gut health + monsoon hook. Lead stat in first line."

  - post_id: "2026-06-11_01"
    scheduled_date: "2026-06-11"
    scheduled_time: "09:00"
    platform: both
    post_type: carousel
    content_pillar: educational
    sku: blueberry
    topic: "4 reasons blueberry microgreens powder beats dried blueberry for monsoon immunity"
    theme: monsoon_reset
    tone: scientific_warm
    cultural_moment: monsoon_immunity
    source_product_image: "Files/blueberry/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Carousel: one reason per slide. Slide 4 = soft CTA, no link."

  - post_id: "2026-06-12_01"
    scheduled_date: "2026-06-12"
    scheduled_time: "09:00"
    platform: both
    post_type: reels
    content_pillar: founder_bts
    sku: brand
    topic: "Started in a small polyhouse in Bangalore. Still growing everything here. This is More Green."
    theme: monsoon_reset
    tone: transparent_founder
    cultural_moment: none
    source_product_image: "Files/brand/brand_lifestyle.jpg"
    source_lifestyle_image: ""
    reference_notes: "Founder voice. Show farm origin. No product push — pure story."

  - post_id: "2026-06-13_01"
    scheduled_date: "2026-06-13"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: social_proof
    sku: sunflower
    topic: "Pune customer: how sunflower microgreens changed her monsoon routine"
    theme: monsoon_reset
    tone: warm_authentic
    cultural_moment: monsoon_immunity
    source_product_image: "Files/sunflower/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Customer quote format. Real city name. Soft CTA with link."

  - post_id: "2026-06-14_01"  # Sunday — optional, skipped by default
    scheduled_date: "2026-06-14"
    scheduled_time: "09:00"
    platform: both
    post_type: story
    content_pillar: product
    sku: brand
    topic: "Why we test every batch for heavy metals, microbes, and nutrients. Every single one."
    theme: monsoon_reset
    tone: transparent_expert
    cultural_moment: none
    source_product_image: "Files/brand/brand_lifestyle.jpg"
    source_lifestyle_image: ""
    reference_notes: "Story format — one strong claim, lab cert visual."

  - post_id: "2026-06-15_01"
    scheduled_date: "2026-06-15"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: product
    sku: blueberry
    topic: "Anthocyanins in monsoon: what the purple pigment in blueberry microgreens does for immunity"
    theme: monsoon_reset
    tone: scientific_warm
    cultural_moment: monsoon_immunity
    source_product_image: "Files/blueberry/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Anthocyanin mechanism → gut lining protection → monsoon relevance."

  - post_id: "2026-06-16_01"
    scheduled_date: "2026-06-16"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: educational
    sku: brand
    topic: "Microgreens vs. mature plants: why harvesting at day 7 changes everything about nutrition"
    theme: monsoon_reset
    tone: scientific_warm
    cultural_moment: none
    source_product_image: "Files/brand/brand_lifestyle.jpg"
    source_lifestyle_image: ""
    reference_notes: "Explain the day-7 peak nutrient window. No specific SKU — brand-wide claim."

  # ── WEEK 2: The Science of Green ─────────────────────────────────────────
  - post_id: "2026-06-17_01"
    scheduled_date: "2026-06-17"
    scheduled_time: "09:00"
    platform: both
    post_type: carousel
    content_pillar: educational
    sku: sunflower
    topic: "40x more Vitamin E than mature sunflower seeds. The peer-reviewed data."
    theme: science_of_green
    tone: scientific_warm
    cultural_moment: none
    source_product_image: "Files/sunflower/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Carousel: slide 1 = claim, slide 2 = study citation, slide 3 = what it means for you."

  - post_id: "2026-06-18_01"
    scheduled_date: "2026-06-18"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: educational
    sku: blueberry
    topic: "Pterostilbene: the cognitive compound in blueberry microgreens that dried fruit doesn't have"
    theme: science_of_green
    tone: scientific_warm
    cultural_moment: none
    source_product_image: "Files/blueberry/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Name the compound. Explain why microgreens stage = higher pterostilbene than ripe fruit."

  - post_id: "2026-06-19_01"
    scheduled_date: "2026-06-19"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: product
    sku: brand
    topic: "FSSAI-approved, NABL-accredited. Every batch — not just the first one."
    theme: science_of_green
    tone: bold_transparent
    cultural_moment: none
    source_product_image: "Files/brand/brand_lifestyle.jpg"
    source_lifestyle_image: ""
    reference_notes: "Credibility post. Lead with the certifications. Show what they actually test for."

  - post_id: "2026-06-20_01"
    scheduled_date: "2026-06-20"
    scheduled_time: "09:00"
    platform: both
    post_type: reels
    content_pillar: product
    sku: sunflower
    topic: "Cold-pressed, no heat treatment. What happens to nutrients when processing cuts corners."
    theme: science_of_green
    tone: bold_direct
    cultural_moment: none
    source_product_image: "Files/sunflower/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Contrast: competitor heat processing destroys Vitamin E. Our cold-press preserves it."

  - post_id: "2026-06-21_01"  # Sunday — optional, skipped by default
    scheduled_date: "2026-06-21"
    scheduled_time: "09:00"
    platform: both
    post_type: story
    content_pillar: founder_bts
    sku: brand
    topic: "Sunday in the Bangalore polyhouse. This is where More Green starts."
    theme: science_of_green
    tone: transparent_founder
    cultural_moment: none
    source_product_image: "Files/brand/brand_lifestyle.jpg"
    source_lifestyle_image: ""
    reference_notes: "Behind-the-scenes story. Show growing trays, not product. Personal caption."

  - post_id: "2026-06-22_01"
    scheduled_date: "2026-06-22"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: educational
    sku: blueberry
    topic: "4-6x more anthocyanins than ripe blueberries. Why the microgreens stage matters."
    theme: science_of_green
    tone: scientific_warm
    cultural_moment: none
    source_product_image: "Files/blueberry/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Comparison angle. State the number early. Explain the anthocyanin production curve."

  - post_id: "2026-06-23_01"
    scheduled_date: "2026-06-23"
    scheduled_time: "09:00"
    platform: both
    post_type: carousel
    content_pillar: educational
    sku: brand
    topic: "What 'pure nutrition' actually means: how we source, grow, process, and test every SKU"
    theme: science_of_green
    tone: transparent_expert
    cultural_moment: none
    source_product_image: "Files/brand/brand_lifestyle.jpg"
    source_lifestyle_image: ""
    reference_notes: "4-slide carousel: Source → Grow → Process → Test. No product names — brand positioning."

  # ── WEEK 3: Mix It, Make It ───────────────────────────────────────────────
  - post_id: "2026-06-24_01"
    scheduled_date: "2026-06-24"
    scheduled_time: "09:00"
    platform: both
    post_type: reels
    content_pillar: recipe
    sku: sunflower
    topic: "Sunflower microgreens post-workout shake: the ₹13-per-serving recovery drink"
    theme: mix_it_make_it
    tone: energetic_practical
    cultural_moment: none
    source_product_image: "Files/sunflower/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Show the shake being made. Cost per serving = hook. Zinc + Vitamin E = recovery angle."

  - post_id: "2026-06-25_01"
    scheduled_date: "2026-06-25"
    scheduled_time: "09:00"
    platform: both
    post_type: reels
    content_pillar: recipe
    sku: blueberry
    topic: "Blueberry microgreens smoothie bowl: 3 ingredients, 2 minutes"
    theme: mix_it_make_it
    tone: warm_inspirational
    cultural_moment: none
    source_product_image: "Files/blueberry/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Keep it visually clean. Name the 3 ingredients in caption. No fluff."

  - post_id: "2026-06-26_01"
    scheduled_date: "2026-06-26"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: product
    sku: brand
    topic: "Single-sourced. India-grown. No additives. What you see on the label is all that's in the pouch."
    theme: mix_it_make_it
    tone: bold_transparent
    cultural_moment: none
    source_product_image: "Files/brand/brand_lifestyle.jpg"
    source_lifestyle_image: ""
    reference_notes: "Ingredient transparency post. Show the label closeup. Let the simplicity speak."

  - post_id: "2026-06-27_01"
    scheduled_date: "2026-06-27"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: recipe
    sku: sunflower
    topic: "Zinc + Vitamin E in one teaspoon: the sunflower microgreens curd rice recipe"
    theme: mix_it_make_it
    tone: warm_practical
    cultural_moment: none
    source_product_image: "Files/sunflower/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Indian food integration. Curd rice is familiar. Make the recipe truly 1-step simple."

  - post_id: "2026-06-28_01"  # Sunday — optional, skipped by default
    scheduled_date: "2026-06-28"
    scheduled_time: "09:00"
    platform: both
    post_type: story
    content_pillar: founder_bts
    sku: brand
    topic: "Why we chose microgreens over dried ingredients: the decision that defined More Green"
    theme: mix_it_make_it
    tone: transparent_founder
    cultural_moment: none
    source_product_image: "Files/brand/brand_lifestyle.jpg"
    source_lifestyle_image: ""
    reference_notes: "Founding story slide. One key decision, explained honestly. No marketing language."

  - post_id: "2026-06-29_01"
    scheduled_date: "2026-06-29"
    scheduled_time: "09:00"
    platform: both
    post_type: carousel
    content_pillar: recipe
    sku: blueberry
    topic: "5 ways to add blueberry microgreens powder to food your family already eats"
    theme: mix_it_make_it
    tone: warm_practical
    cultural_moment: none
    source_product_image: "Files/blueberry/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "5 slides, 5 Indian foods. Dahi, smoothie, roti dough, oats, lemon water."

  - post_id: "2026-06-30_01"
    scheduled_date: "2026-06-30"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: educational
    sku: sunflower
    topic: "1 tsp = 15% daily zinc. Why sunflower microgreens powder outperforms a zinc supplement"
    theme: mix_it_make_it
    tone: scientific_warm
    cultural_moment: none
    source_product_image: "Files/sunflower/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Food-form zinc vs. supplement zinc bioavailability. Cite the 15% DRV number."

  # ── WEEK 4: Real People, Real Green ──────────────────────────────────────
  - post_id: "2026-07-01_01"
    scheduled_date: "2026-07-01"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: social_proof
    sku: brand
    topic: "₹390. NABL lab-tested. Grown in India. What customers in 3 cities are saying."
    theme: real_people_real_green
    tone: warm_authentic
    cultural_moment: none
    source_product_image: "Files/brand/brand_lifestyle.jpg"
    source_lifestyle_image: ""
    reference_notes: "Lead with value + credibility. Use real city names: Bengaluru, Pune, Mumbai."

  - post_id: "2026-07-02_01"
    scheduled_date: "2026-07-02"
    scheduled_time: "09:00"
    platform: both
    post_type: carousel
    content_pillar: social_proof
    sku: blueberry
    topic: "Parent in Delhi: how she gets blueberry microgreens into her kids' food every day"
    theme: real_people_real_green
    tone: warm_relatable
    cultural_moment: none
    source_product_image: "Files/blueberry/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Parent pain point: kids won't eat greens. Show 3 kid-friendly food integrations."

  - post_id: "2026-07-03_01"
    scheduled_date: "2026-07-03"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: social_proof
    sku: sunflower
    topic: "Pune customer: 'I stopped needing a Vitamin E supplement after switching to this'"
    theme: real_people_real_green
    tone: warm_authentic
    cultural_moment: none
    source_product_image: "Files/sunflower/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Quote-style post. Real outcome, specific claim. Soft CTA with link."

  - post_id: "2026-07-04_01"
    scheduled_date: "2026-07-04"
    scheduled_time: "09:00"
    platform: both
    post_type: reels
    content_pillar: social_proof
    sku: brand
    topic: "3 cities. 200+ orders. Real reviews from people who wanted honest nutrition."
    theme: real_people_real_green
    tone: warm_authentic
    cultural_moment: none
    source_product_image: "Files/brand/brand_lifestyle.jpg"
    source_lifestyle_image: ""
    reference_notes: "Review compilation reel. Show review screenshots, not staged testimonials."

  - post_id: "2026-07-05_01"  # Sunday — optional, skipped by default
    scheduled_date: "2026-07-05"
    scheduled_time: "09:00"
    platform: both
    post_type: story
    content_pillar: product
    sku: blueberry
    topic: "Blueberry microgreens vs. dried blueberry powder — one slide, no jargon."
    theme: real_people_real_green
    tone: bold_direct
    cultural_moment: none
    source_product_image: "Files/blueberry/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Side-by-side comparison story. Two columns. Anthocyanin numbers only. No claims."

  - post_id: "2026-07-06_01"
    scheduled_date: "2026-07-06"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: product
    sku: sunflower
    topic: "Every pack harvested at exactly day 7. Not day 6. Not day 8. Here is why that matters."
    theme: real_people_real_green
    tone: transparent_expert
    cultural_moment: none
    source_product_image: "Files/sunflower/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Precision = trust. Explain the nutrient curve: peaks at day 7, falls after. Hard CTA."

  - post_id: "2026-07-07_01"
    scheduled_date: "2026-07-07"
    scheduled_time: "09:00"
    platform: both
    post_type: reels
    content_pillar: social_proof
    sku: sunflower
    topic: "Mumbai customer switched from a ₹400/month multivitamin to sunflower microgreens powder."
    theme: real_people_real_green
    tone: warm_authentic
    cultural_moment: none
    source_product_image: "Files/sunflower/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Cost comparison angle. ₹400 multivitamin vs. ₹499 for whole-food microgreens."

  # ── WEEK 5: Your Green, Your Way ─────────────────────────────────────────
  - post_id: "2026-07-08_01"
    scheduled_date: "2026-07-08"
    scheduled_time: "09:00"
    platform: both
    post_type: carousel
    content_pillar: product
    sku: blueberry
    topic: "Sunflower or blueberry? Which More Green powder fits your goal — an honest guide"
    theme: your_green_your_way
    tone: consultative_direct
    cultural_moment: none
    source_product_image: "Files/blueberry/product_front.jpg"
    source_lifestyle_image: ""
    reference_notes: "Decision-helper carousel. Slide 1: immunity → blueberry. Slide 2: energy/zinc → sunflower. Slide 3: CTA."

  - post_id: "2026-07-09_01"
    scheduled_date: "2026-07-09"
    scheduled_time: "09:00"
    platform: both
    post_type: feed_image
    content_pillar: product
    sku: brand
    topic: "30 days of More Green. What customers who started in June are saying now."
    theme: your_green_your_way
    tone: warm_authentic
    cultural_moment: monsoon_immunity
    source_product_image: "Files/brand/brand_lifestyle.jpg"
    source_lifestyle_image: ""
    reference_notes: "Sprint close post. Summarise the month. Strong CTA with link."
```

- [ ] **Step 3: Verify YAML loads without error**

```powershell
cd D:\More Green AGI\automation
python -c "
import yaml
from pathlib import Path
data = yaml.safe_load(Path('strategy/calendar.yaml').read_text(encoding='utf-8'))
posts = data['posts']
print(f'Loaded {len(posts)} posts')
print(f'First: {posts[0][\"post_id\"]} — {posts[0][\"sku\"]}')
print(f'Last:  {posts[-1][\"post_id\"]} — {posts[-1][\"sku\"]}')
"
```

Expected output:
```
Loaded 30 posts
First: 2026-06-10_01 — sunflower
Last:  2026-07-09_01 — brand
```

- [ ] **Step 4: Commit**

```powershell
git add automation/strategy/calendar.yaml
git commit -m "feat: add 30-day Monsoon Sprint content calendar"
```

---

## Task 3: Create `seed_calendar.py` with tests

**Files:**
- Create: `automation/commands/seed_calendar.py`
- Create: `automation/tests/__init__.py`
- Create: `automation/tests/test_seed_calendar.py`

- [ ] **Step 1: Create `automation/tests/__init__.py`**

Create an empty file at `automation/tests/__init__.py`.

- [ ] **Step 2: Write the failing tests**

Create `automation/tests/test_seed_calendar.py`:

```python
import sys
from pathlib import Path
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_POSTS = [
    {
        "post_id": "2026-06-10_01",
        "scheduled_date": "2026-06-10",  # Wednesday
        "scheduled_time": "09:00",
        "platform": "both",
        "post_type": "feed_image",
        "content_pillar": "product",
        "sku": "sunflower",
        "topic": "Test topic",
        "theme": "monsoon_reset",
        "tone": "bold_direct",
        "cultural_moment": "monsoon_immunity",
        "source_product_image": "Files/sunflower/product_front.jpg",
        "source_lifestyle_image": "",
        "reference_notes": "Test note",
    },
    {
        "post_id": "2026-06-14_01",
        "scheduled_date": "2026-06-14",  # Sunday
        "scheduled_time": "09:00",
        "platform": "both",
        "post_type": "story",
        "content_pillar": "product",
        "sku": "brand",
        "topic": "Sunday story topic",
        "theme": "monsoon_reset",
        "tone": "transparent_expert",
        "cultural_moment": "none",
        "source_product_image": "Files/brand/brand_lifestyle.jpg",
        "source_lifestyle_image": "",
        "reference_notes": "",
    },
]


# ── tests ─────────────────────────────────────────────────────────────────────

def test_filter_sundays_removes_sunday_posts():
    from commands.seed_calendar import _filter_posts
    result = _filter_posts(SAMPLE_POSTS, include_sundays=False)
    assert len(result) == 1
    assert result[0]["post_id"] == "2026-06-10_01"


def test_include_sundays_keeps_all_posts():
    from commands.seed_calendar import _filter_posts
    result = _filter_posts(SAMPLE_POSTS, include_sundays=True)
    assert len(result) == 2


def test_build_row_returns_16_columns():
    from commands.seed_calendar import _build_row
    row = _build_row(SAMPLE_POSTS[0])
    assert len(row) == 16


def test_build_row_maps_fields_correctly():
    from commands.seed_calendar import _build_row
    row = _build_row(SAMPLE_POSTS[0])
    assert row[0] == "2026-06-10_01"      # post_id
    assert row[1] == "2026-06-10"          # scheduled_date
    assert row[2] == "09:00"               # scheduled_time
    assert row[3] == "both"                # platform
    assert row[4] == "feed_image"          # post_type
    assert row[5] == "product"             # content_pillar
    assert row[6] == "sunflower"           # sku
    assert row[7] == "Test topic"          # topic
    assert row[8] == "monsoon_reset"       # theme
    assert row[9] == "bold_direct"         # tone
    assert row[10] == "monsoon_immunity"   # cultural_moment
    assert row[11] == "Files/sunflower/product_front.jpg"  # source_product_image
    assert row[12] == ""                   # source_lifestyle_image
    assert row[13] == "Test note"          # reference_notes
    assert row[14] == "draft"              # pipeline_status (hardcoded)
    assert row[15] == ""                   # on_hold (hardcoded empty)


def test_deduplicate_skips_existing_post_ids():
    from commands.seed_calendar import _deduplicate
    existing = {"2026-06-10_01"}
    result = _deduplicate(SAMPLE_POSTS, existing)
    assert len(result) == 1
    assert result[0]["post_id"] == "2026-06-14_01"


def test_deduplicate_keeps_all_when_no_existing():
    from commands.seed_calendar import _deduplicate
    result = _deduplicate(SAMPLE_POSTS, set())
    assert len(result) == 2


def test_filter_by_sprint_date():
    from commands.seed_calendar import _filter_posts
    result = _filter_posts(SAMPLE_POSTS, include_sundays=True, sprint="2026-06-14")
    assert len(result) == 1
    assert result[0]["post_id"] == "2026-06-14_01"
```

- [ ] **Step 3: Run tests to confirm they fail**

```powershell
cd D:\More Green AGI\automation
python -m pytest tests/test_seed_calendar.py -v 2>&1 | head -30
```

Expected: All tests fail with `ModuleNotFoundError: No module named 'commands.seed_calendar'`

- [ ] **Step 4: Implement `seed_calendar.py`**

Create `automation/commands/seed_calendar.py`:

```python
import logging
import os
from datetime import date

import gspread
import yaml

from config import CALENDAR_PATH

log = logging.getLogger(__name__)


def run(dry_run: bool = False, include_sundays: bool = False, sprint: str = None) -> None:
    data = yaml.safe_load(CALENDAR_PATH.read_text(encoding="utf-8"))
    posts = data["posts"]

    posts = _filter_posts(posts, include_sundays=include_sundays, sprint=sprint)

    sheets_id = os.environ.get("GOOGLE_SHEETS_ID")
    if not sheets_id:
        raise SystemExit("GOOGLE_SHEETS_ID not set in .env")

    gc = gspread.service_account(filename="service_account.json")
    sheet = gc.open_by_key(sheets_id).sheet1

    existing_ids = set(sheet.col_values(1))
    posts = _deduplicate(posts, existing_ids)

    if not posts:
        log.info("Nothing to add — all posts already in Sheet.")
        return

    if dry_run:
        log.info("[DRY RUN] Would add %d rows:", len(posts))
        for p in posts:
            log.info("  %s  %-12s  %s", p["post_id"], p["sku"], p["topic"][:60])
        return

    rows = [_build_row(p) for p in posts]
    sheet.append_rows(rows, value_input_option="USER_ENTERED")
    log.info("✓ Added %d posts to Sheets. Review → approve → run generate-prompts.", len(rows))


def _filter_posts(posts: list, include_sundays: bool, sprint: str = None) -> list:
    result = []
    for p in posts:
        post_date = date.fromisoformat(p["scheduled_date"])
        if sprint and p["scheduled_date"] < sprint:
            continue
        if not include_sundays and post_date.weekday() == 6:
            continue
        result.append(p)
    return result


def _deduplicate(posts: list, existing_ids: set) -> list:
    new_posts = []
    for p in posts:
        if p["post_id"] in existing_ids:
            log.info("SKIP %s — already in Sheet", p["post_id"])
            continue
        new_posts.append(p)
    return new_posts


def _build_row(post: dict) -> list:
    return [
        post["post_id"],
        post["scheduled_date"],
        post.get("scheduled_time", "09:00"),
        post.get("platform", "both"),
        post.get("post_type", "feed_image"),
        post.get("content_pillar", "product"),
        post["sku"],
        post.get("topic", ""),
        post.get("theme", ""),
        post.get("tone", "warm_inspirational"),
        post.get("cultural_moment", "none"),
        post.get("source_product_image", ""),
        post.get("source_lifestyle_image", ""),
        post.get("reference_notes", ""),
        "draft",
        "",
    ]
```

- [ ] **Step 5: Run tests — all must pass**

```powershell
cd D:\More Green AGI\automation
python -m pytest tests/test_seed_calendar.py -v
```

Expected output:
```
PASSED tests/test_seed_calendar.py::test_filter_sundays_removes_sunday_posts
PASSED tests/test_seed_calendar.py::test_include_sundays_keeps_all_posts
PASSED tests/test_seed_calendar.py::test_build_row_returns_16_columns
PASSED tests/test_seed_calendar.py::test_build_row_maps_fields_correctly
PASSED tests/test_seed_calendar.py::test_deduplicate_skips_existing_post_ids
PASSED tests/test_seed_calendar.py::test_deduplicate_keeps_all_when_no_existing
PASSED tests/test_seed_calendar.py::test_filter_by_sprint_date
7 passed in 0.XXs
```

- [ ] **Step 6: Commit**

```powershell
git add automation/commands/seed_calendar.py automation/tests/__init__.py automation/tests/test_seed_calendar.py
git commit -m "feat: add seed-calendar command with tests"
```

---

## Task 4: Register `seed-calendar` in `main.py`

**Files:**
- Modify: `automation/main.py`

- [ ] **Step 1: Add the click command**

In `automation/main.py`, add the following block after the `new-week` command (after line 203):

```python
@cli.command("seed-calendar")
@click.option("--include-sundays", is_flag=True, default=False,
              help="Include Sunday story posts (skipped by default).")
@click.option("--sprint", default=None,
              help="Only seed posts on or after this date e.g. 2026-06-10")
@click.pass_context
def seed_calendar(ctx, include_sundays, sprint):
    """Push all calendar.yaml posts to Google Sheets for review."""
    from commands.seed_calendar import run
    run(dry_run=ctx.obj["dry_run"], include_sundays=include_sundays, sprint=sprint)
```

- [ ] **Step 2: Verify the command appears in CLI help**

```powershell
cd D:\More Green AGI\automation
python main.py --help
```

Expected: `seed-calendar` listed among commands.

- [ ] **Step 3: Dry-run against the real calendar**

```powershell
cd D:\More Green AGI\automation
python main.py --dry-run seed-calendar
```

Expected: 26 rows logged (Mon–Sat only), no Sheet writes.

```powershell
python main.py --dry-run seed-calendar --include-sundays
```

Expected: 30 rows logged.

- [ ] **Step 4: Commit**

```powershell
git add automation/main.py
git commit -m "feat: register seed-calendar CLI command"
```

---

## Self-Review

**Spec coverage check:**
- ✅ `brand` SKU added to `brand.yaml` (Task 1)
- ✅ `sync_sheets.py` updated to accept `"brand"` (Task 1)
- ✅ `calendar.yaml` with all 30 posts, correct SKU split (Task 2)
- ✅ `seed-calendar` command with `--dry-run`, `--include-sundays`, `--sprint` (Tasks 3–4)
- ✅ Duplicate guard via Sheet col A lookup (Task 3 step 4)
- ✅ Sundays skipped by default (Task 3 tests + implementation)
- ✅ 16-column row format matching `new_week.py` / `sync_sheets.py` (Task 3 tests)
- ✅ Registered in `main.py` (Task 4)

**Placeholder scan:** None found. All steps have explicit commands or code.

**Type consistency:** `_filter_posts`, `_deduplicate`, `_build_row` signatures match between test file and implementation. All return types consistent (list → list).

**One known gap to handle during implementation:** `Files/brand/brand_lifestyle.jpg` does not exist yet. The `seed-calendar` command will write that path to Sheets, but `generate-creatives` will fail for brand posts until you add at least one image to `automation/Files/brand/`. Add a note in the Sheet's reference_notes column or place any brand lifestyle image there before running `generate-creatives`.
