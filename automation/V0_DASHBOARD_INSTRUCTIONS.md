# More Green Automation — Setup & Usage Guide

## Who this is for
You — the founder. No coding required. This guide takes you from zero to a live dashboard you can use from your phone in about 2 hours.

---

## Part 1 — One-Time Setup (do this once)

### Step 1: Copy the secrets file

1. Open the `automation/` folder on your laptop.
2. Find the file called `.env.example`.
3. Make a copy of it in the same folder. Rename the copy to `.env` (just `.env`, no `.example`).
4. Open `.env` in any text editor (Notepad is fine).

You will now fill in each line. Every section below tells you exactly where to get the value.

---

### Step 2: Fill in your API keys

Work through each block below. Every key in `.env.example` is covered here.

---

#### ANTHROPIC_API_KEY — Claude (writes your captions and prompts)

- Go to: https://console.anthropic.com/settings/keys
- Click "Create Key". Copy the key that starts with `sk-ant-`.
- Paste it next to `ANTHROPIC_API_KEY=` in your `.env` file.

---

#### FAL_KEY — fal.ai (generates product images and videos)

- Go to: https://fal.ai/dashboard/keys
- You must add a payment method first (credit card). Then click "Create Key".
- Copy the key that starts with `fal-`. Paste next to `FAL_KEY=`.

---

#### GOOGLE_API_KEY — Google AI (background scene generation)

- Go to: https://aistudio.google.com
- Click "Get API key" → "Create API key". Copy it.
- Paste next to `GOOGLE_API_KEY=`.

---

#### CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET — media hosting

- Go to: https://cloudinary.com → sign up for a free account.
- After logging in, your Dashboard shows **Cloud Name**, **API Key**, and **API Secret**.
- Copy each one to the three matching lines in `.env`:
  ```
  CLOUDINARY_CLOUD_NAME=your-cloud-name
  CLOUDINARY_API_KEY=123456789012345
  CLOUDINARY_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
  ```

---

#### Meta keys — Instagram + Facebook posting and ads

This takes 30–60 minutes the first time. Follow these steps in order.

**META_APP_ID and META_APP_SECRET**

1. Go to https://developers.facebook.com → click "My Apps" → "Create App".
2. Choose "Business" type. Name it "More Green Automation".
3. Inside the app, click "Add Product" → add both "Marketing API" and "Instagram Graph API".
4. Go to the app's **Settings → Basic** page. Copy the **App ID** and **App Secret**.
5. Paste them:
   ```
   META_APP_ID=your_app_id
   META_APP_SECRET=your_app_secret
   ```

**META_ACCESS_TOKEN**

6. Go to https://business.facebook.com → Settings → Users → System Users → click "Add".
7. Name the system user "More Green Bot". Role: Admin.
8. Click the system user → "Generate New Token". Select your app.
9. Enable these permissions: `ads_management`, `ads_read`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `pages_read_engagement`, `business_management`.
10. Copy the token. Paste next to `META_ACCESS_TOKEN=`.

**META_AD_ACCOUNT_ID**

11. Go to Business Settings → Ad Accounts. Your ID looks like `act_1234567890`.
12. Paste next to `META_AD_ACCOUNT_ID=` (include the `act_` prefix).

**META_PAGE_ID**

13. Go to your Facebook Page → About → scroll to "Page ID".
14. Paste next to `META_PAGE_ID=`.

**META_IG_ACCOUNT_ID**

15. Go to Business Settings → Instagram Accounts → click your account. The number in the URL is your ID.
16. Paste next to `META_IG_ACCOUNT_ID=`.

**META_PIXEL_ID**

17. Go to https://business.facebook.com → Events Manager → your Pixel → Settings.
18. Copy the Pixel ID. Paste next to `META_PIXEL_ID=`.

**META_CUSTOMER_AUDIENCE_ID**

19. Go to Ads Manager → Audiences → "Create Audience" → "Custom Audience" → "Customer List" → create an empty one named "More Green Customers".
20. Copy the Audience ID from the URL or audience details. Paste next to `META_CUSTOMER_AUDIENCE_ID=`.

---

#### SENDGRID_API_KEY and FOUNDER_EMAIL — email notifications

- Go to: https://app.sendgrid.com/settings/api_keys
- Click "Create API Key" → Full Access. Copy it. Paste next to `SENDGRID_API_KEY=`.
- `FOUNDER_EMAIL=bs.moregreen@gmail.com` is already pre-filled. Leave it as-is.

---

#### YOUTUBE_API_KEY — YouTube (Week 4 expansion)

This key is only needed when you activate YouTube features in Week 4. You can leave it blank until then.

- Go to: https://console.cloud.google.com → APIs & Services → Credentials → "Create Credentials" → "API key".
- Enable the **YouTube Data API v3** in the Library first.
- Paste the key next to `YOUTUBE_API_KEY=`.

---

#### SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN — Shopify audience sync + blog posts

- `SHOPIFY_STORE_URL` is already pre-filled as `https://moregreen.myshopify.com`. Confirm it matches your store and leave it.
- For `SHOPIFY_ACCESS_TOKEN`:
  1. Go to your Shopify admin → Settings → Apps and sales channels → Develop apps → "Create an app".
  2. Name it "More Green Automation". Under API scopes, enable: `read_customers`, `write_customers`, `read_orders`, `write_script_tags`, `write_content`.
  3. Install the app → copy the Admin API access token.
  4. Paste next to `SHOPIFY_ACCESS_TOKEN=`.

---

#### GOOGLE_SHEETS_ID — content calendar

- Create a new Google Sheet. Name it "More Green Content Calendar".
- The sheet URL looks like: `https://docs.google.com/spreadsheets/d/XXXXXXXXXXX/edit`
- Copy the long ID between `/d/` and `/edit`. Paste next to `GOOGLE_SHEETS_ID=`.
- You will also need `service_account.json` — see Step 3.

---

### Step 3: Google Sheets service account (one-time)

1. Go to: https://console.cloud.google.com
2. Create a new project called "More Green" (or select it if it already exists).
3. Go to APIs & Services → Library → search "Google Sheets API" → Enable it.
4. Go to APIs & Services → Credentials → "Create Credentials" → "Service Account".
5. Name it "more-green-sheets". Click through to finish.
6. Click the service account → Keys tab → "Add Key" → JSON.
7. A file downloads. Rename it `service_account.json`.
8. Move it into the `automation/` folder (same folder as `.env`).
9. Open your Google Sheet → Share → paste the service account email (the `client_email` field inside the JSON) → give Editor access.

> **Important:** `service_account.json` is gitignored and must never be committed. See Part 5 for how to handle it on Streamlit Cloud.

---

### Step 4: Push to GitHub (using GitHub Desktop — no terminal)

1. Download GitHub Desktop: https://desktop.github.com
2. Install it and sign in with your GitHub account (create one free at github.com if needed).
3. Click "Add" → "Add Existing Repository" → choose the `More Green AGI` folder.
4. You will see a list of changed files. **Important:** make sure `.env` and `service_account.json` are NOT in the list. If they appear, stop — ask for help before proceeding.
5. Write a commit message like "Initial automation setup" and click "Commit to master".
6. Click "Publish repository". Keep it **Private**.

---

## Part 2 — Weekly Workflow (15 minutes every Sunday evening)

### Your Sunday routine

**Step 1 (5 min) — Fill in the content calendar**
- Open your Google Sheet "More Green Content Calendar" on your phone.
- Each row is one post. Fill in: date, SKU (sunflower/blueberry/moringa/wheatgrass), topic (what you want to say), and source product image path (e.g. `Files/moringa/product_front.jpg`).
- You can leave Theme, Tone, and Cultural Moment blank — the system uses defaults.

**Step 2 (1 min) — Sync and generate**
- Open your dashboard on your phone (the streamlit.app link).
- Click "🔄 Sync from Sheets". This pulls your new rows.
- Click "✨ Generate Prompts". Claude writes image prompts, video prompts, and captions for each post.
- Wait about 20 seconds.

**Step 3 (5 min) — Review and approve prompts**
- Each post card now shows "✍️ prompts_ready".
- Tap any card → "View" to open the post detail screen.
- Read the captions. Edit anything that doesn't sound right.
- Tap "✅ Approve Prompts" when you're happy.
- The system will automatically start generating images and videos in the background (about 4 minutes total).

**Step 4 (5 min) — Approve creatives**
- When images are ready, the card shows "🖼️ creative_ready".
- Tap View → "🚀 Approve Creatives".
- You'll see 3 image variants. Tap "✅ Use Variant X" to pick your favourite.
- Preview the video if one was generated.
- Tap "🚀 Approve & Schedule Post".
- Done. Posts go live automatically at the times you set in the sheet.

---

## Part 3 — Customising the Dashboard (using v0 by Vercel)

If you want to change the look of the dashboard — colours, layout, fonts — you can do it without writing Python.

**How to use v0 for dashboard changes:**

1. Go to: https://v0.dev (sign in free with GitHub).
2. Open your dashboard `.streamlit` app. Take a screenshot of the part you want to change.
3. In v0, click "New chat". Describe what you want: _"I want the post cards to have a dark green background with white text, and the approve button should be gold"_.
4. v0 will generate a CSS/component suggestion. Look for the `st.markdown("""<style>...""")` block.
5. Copy just that CSS block.
6. In the `_dashboard_app.py` file, find the `main()` function at the bottom. Add your CSS right at the top of `main()`:
   ```python
   def main():
       st.markdown("""<style>YOUR CSS HERE</style>""", unsafe_allow_html=True)
       # ... rest of the function
   ```
7. Save the file. Push to GitHub via GitHub Desktop (commit → push). Streamlit Cloud auto-redeploys in ~60 seconds.

**Example changes you can ask v0 for:**
- "Make the sidebar dark green with the More Green logo at the top"
- "Change the card borders to use the brand colour #2D5016"
- "Make buttons larger and easier to tap on mobile"
- "Add a progress bar that shows how many posts are approved this week"

---

## Part 4 — Common Questions

**Q: I see "⚠️ Meta Token" in the health panel.**
A: Your Meta System User Token needs to be re-checked. Go to Business Manager → System Users → click your bot → re-generate the token. Update `META_ACCESS_TOKEN` in your Streamlit Secrets (Settings → Secrets in the Streamlit Cloud dashboard).

**Q: A post shows "creative_failed".**
A: Tap the post card. You'll see the error message. Most common cause: the source image path in your Google Sheet doesn't match a real file. Check the Files/ folder and correct the path in the sheet, then re-sync.

**Q: How do I run ads?**
A: After a post's creative is approved, go to your laptop terminal (or ask for help) and run:
`python main.py create-ads --post W24_MON_01`
This creates a campaign in Meta Ads Manager in PAUSED state. Log into ads.facebook.com to review and activate it manually. Never let the system activate ads automatically until you've verified the targeting and budget.

**Q: How do I know what my ads cost?**
A: Open the dashboard → check the sidebar "Recent Activity". For a full breakdown, ask for the weekly report. The creative pipeline costs about ₹650/month. Ad spend is whatever you set in Meta Ads Manager (start with ₹500/day in Phase 1).

**Q: Can I use this from my phone completely?**
A: Yes. The dashboard (Streamlit Cloud) is fully mobile-accessible. The only thing that requires a laptop is the initial setup and running ad commands (once per week at most).

---

## Part 5 — Streamlit Community Cloud Deployment

### 5.1 Deploy the app

1. Go to: https://share.streamlit.io — sign in with GitHub.
2. Click "New app".
3. Repository: select your More Green repo (must be the private repo you pushed in Step 4).
4. Branch: `master` (or `main`).
5. **Main file path:** `automation/commands/_dashboard_app.py`
   _(This is the exact path Streamlit Cloud needs. Do not change it.)_
6. Click "Advanced settings" → "Secrets". See section 5.2 below before clicking Deploy.
7. Click "Deploy". Wait 2–3 minutes.
8. Your dashboard is live at `https://yourappname.streamlit.app`. Bookmark this on your phone.

---

### 5.2 Adding ALL secrets to Streamlit Cloud

Streamlit Cloud Secrets replace your `.env` file in the cloud. You paste the same key=value lines directly into the Secrets field.

**How to add them:**

1. In Streamlit Cloud → your app → top-right menu → "Settings" → "Secrets".
2. Paste the full contents of your `.env` file into the text box. It should look like this:

```
ANTHROPIC_API_KEY=sk-ant-...
FAL_KEY=fal-...
GOOGLE_API_KEY=AIza...
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
META_ACCESS_TOKEN=your_long_token
META_AD_ACCOUNT_ID=act_1234567890
META_PAGE_ID=1234567890
META_IG_ACCOUNT_ID=1234567890
META_PIXEL_ID=1234567890
META_CUSTOMER_AUDIENCE_ID=1234567890
SENDGRID_API_KEY=SG.xxxx
FOUNDER_EMAIL=bs.moregreen@gmail.com
YOUTUBE_API_KEY=AIza...
SHOPIFY_STORE_URL=https://moregreen.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_xxxx
GOOGLE_SHEETS_ID=your_sheet_id_here
GOOGLE_SERVICE_ACCOUNT_B64=<see section 5.3>
```

3. Click "Save". Streamlit Cloud will restart the app with the new secrets.

> Every key from `.env.example` must appear here. If any line is missing or blank, the feature that depends on it will fail silently or show an error in the dashboard health panel.

---

### 5.3 Handling service_account.json on Streamlit Cloud

`service_account.json` is a file, not a simple key=value string, so it **cannot** be pasted directly into Streamlit Secrets. Instead, you encode it as a base64 string and store that string as a secret. The app then decodes it at runtime.

**Step A — Encode the file**

On Linux or Mac, run in your terminal:
```bash
base64 -w 0 service_account.json
```

On Windows (PowerShell), run:
```powershell
[Convert]::ToBase64String([System.IO.File]::ReadAllBytes("service_account.json"))
```

Both commands print a long single-line string. Copy the entire output.

**Step B — Add it to Streamlit Secrets**

In Streamlit Cloud → Settings → Secrets, add this line (paste your copied string as the value):
```
GOOGLE_SERVICE_ACCOUNT_B64=eyJ0eXBlIjoic2...very long string...
```

**Step C — Add the decoder to `utils/secrets.py`**

Open `automation/utils/secrets.py` and add the following function. This is the only code change needed — the rest of the app calls `get_service_account_path()` automatically:

```python
import base64, json, tempfile, os
from pathlib import Path

def get_service_account_path() -> str:
    """Return path to service_account.json — handles both local file and Streamlit Cloud."""
    local = Path(__file__).parent.parent / "service_account.json"
    if local.exists():
        return str(local)
    encoded = os.environ.get("GOOGLE_SERVICE_ACCOUNT_B64")
    if not encoded:
        raise SystemExit("service_account.json not found and GOOGLE_SERVICE_ACCOUNT_B64 not set.")
    decoded = base64.b64decode(encoded).decode("utf-8")
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    tmp.write(decoded)
    tmp.close()
    return tmp.name
```

**How it works:**
- Locally: the function finds `service_account.json` on disk and returns that path. No changes to your local workflow.
- On Streamlit Cloud: the file doesn't exist, so the function reads `GOOGLE_SERVICE_ACCOUNT_B64`, decodes it, writes it to a temporary file, and returns that path. The rest of the app never knows the difference.

---

### 5.4 Updating secrets after deployment

Whenever you rotate a token or add a new key:

1. Go to Streamlit Cloud → your app → Settings → Secrets.
2. Find the line for the key you want to update and replace the value.
3. Click "Save". The app restarts automatically — no re-deploy needed.

---

*Guide version: 2.0 — More Green Automation System*
*For help: refer to `plan.md` or open a Claude Code session.*
