"""
More Green Studio — Streamlit dashboard for the founder.

Run locally:  streamlit run commands/_dashboard_app.py
Deploy:       Streamlit Community Cloud → add .env vars as Streamlit Secrets
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from utils.db import get_db
from utils.logging_config import configure
configure()

st.set_page_config(
    page_title="More Green Studio",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design System ─────────────────────────────────────────────────────────────

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --mg-green:       #1B4332;
    --mg-green-mid:   #2D6A4F;
    --mg-green-light: #40916C;
    --mg-gold:        #D4AF37;
    --mg-gold-pale:   #F0D87A;
    --mg-cream:       #F8F4E9;
    --mg-cream-dark:  #EDE8D6;
    --mg-text:        #1C1C1C;
    --mg-text-muted:  #5A5A4A;
    --mg-radius:      12px;
    --mg-radius-sm:   7px;
    --shadow-card:    0 2px 16px rgba(27,67,50,0.10), 0 1px 4px rgba(27,67,50,0.06);
    --shadow-btn:     0 2px 8px rgba(212,175,55,0.25);
}

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: var(--mg-text);
}

.stApp {
    background: var(--mg-cream);
}

/* Subtle botanical texture overlay */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        radial-gradient(ellipse at 20% 50%, rgba(27,67,50,0.04) 0%, transparent 60%),
        radial-gradient(ellipse at 80% 20%, rgba(212,175,55,0.05) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--mg-green) !important;
    border-right: 1px solid rgba(212,175,55,0.20);
}

[data-testid="stSidebar"] * {
    color: var(--mg-cream) !important;
}

[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown {
    color: rgba(248,244,233,0.85) !important;
    font-size: 0.85rem;
    line-height: 1.6;
}

[data-testid="stSidebar"] h1 {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 1.6rem !important;
    font-weight: 600 !important;
    color: var(--mg-gold) !important;
    letter-spacing: 0.02em;
    margin-bottom: 0 !important;
}

[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.70rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: rgba(212,175,55,0.70) !important;
    margin-top: 1.2rem !important;
}

[data-testid="stSidebar"] hr {
    border-color: rgba(212,175,55,0.15) !important;
    margin: 0.8rem 0 !important;
}

[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] small {
    color: rgba(248,244,233,0.45) !important;
    font-size: 0.72rem !important;
}

[data-testid="stSidebar"] code {
    background: rgba(255,255,255,0.10) !important;
    color: var(--mg-gold-pale) !important;
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 0.75rem;
}

/* ── Headings ── */
h1 {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: clamp(1.8rem, 5vw, 2.6rem) !important;
    font-weight: 600 !important;
    color: var(--mg-green) !important;
    letter-spacing: -0.01em;
    line-height: 1.15 !important;
    margin-bottom: 0.25rem !important;
}

h2 {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: clamp(1.2rem, 3.5vw, 1.7rem) !important;
    font-weight: 600 !important;
    color: var(--mg-green) !important;
    letter-spacing: 0.01em;
}

h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--mg-text-muted) !important;
    margin-bottom: 0.4rem !important;
}

/* ── Buttons ── */
.stButton > button {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.04em;
    border-radius: var(--mg-radius-sm) !important;
    padding: 0.55rem 1.2rem !important;
    transition: all 0.18s ease !important;
    border: 1.5px solid var(--mg-green-mid) !important;
    background: white !important;
    color: var(--mg-green) !important;
}

.stButton > button:hover {
    background: var(--mg-green) !important;
    color: var(--mg-cream) !important;
    border-color: var(--mg-green) !important;
    box-shadow: 0 4px 12px rgba(27,67,50,0.20) !important;
    transform: translateY(-1px);
}

/* Primary buttons — gold */
.stButton > button[kind="primary"],
[data-testid="baseButton-primary"] {
    background: var(--mg-green) !important;
    color: var(--mg-gold) !important;
    border: 1.5px solid var(--mg-gold) !important;
    box-shadow: var(--shadow-btn) !important;
}

.stButton > button[kind="primary"]:hover,
[data-testid="baseButton-primary"]:hover {
    background: var(--mg-gold) !important;
    color: var(--mg-green) !important;
    border-color: var(--mg-gold) !important;
    box-shadow: 0 6px 20px rgba(212,175,55,0.35) !important;
    transform: translateY(-2px);
}

/* ── Cards / Containers ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: white !important;
    border: 1px solid var(--mg-cream-dark) !important;
    border-radius: var(--mg-radius) !important;
    box-shadow: var(--shadow-card) !important;
    padding: 1rem !important;
    transition: box-shadow 0.18s ease, transform 0.18s ease;
}

[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 6px 24px rgba(27,67,50,0.13) !important;
    transform: translateY(-1px);
}

/* ── Text Areas ── */
.stTextArea > div > div > textarea {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
    line-height: 1.65 !important;
    border: 1.5px solid var(--mg-cream-dark) !important;
    border-radius: var(--mg-radius-sm) !important;
    background: var(--mg-cream) !important;
    color: var(--mg-text) !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.stTextArea > div > div > textarea:focus {
    border-color: var(--mg-green-light) !important;
    box-shadow: 0 0 0 3px rgba(64,145,108,0.12) !important;
}

/* ── Alerts & Status ── */
.stAlert {
    border-radius: var(--mg-radius-sm) !important;
    border: none !important;
    font-size: 0.85rem !important;
}

[data-testid="stAlert"][data-baseweb="notification"] {
    background: rgba(27,67,50,0.06) !important;
}

/* ── Info / Caption ── */
.stCaption, small {
    font-size: 0.75rem !important;
    color: var(--mg-text-muted) !important;
    letter-spacing: 0.01em;
}

/* ── Dividers ── */
hr {
    border: none !important;
    border-top: 1px solid var(--mg-cream-dark) !important;
    margin: 1.5rem 0 !important;
}

/* ── Spinner ── */
.stSpinner > div {
    border-top-color: var(--mg-green) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--mg-cream); }
::-webkit-scrollbar-thumb { background: rgba(27,67,50,0.25); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: var(--mg-green-mid); }

/* ── Mobile ── */
@media (max-width: 768px) {
    [data-testid="stSidebar"] { min-width: 240px !important; }
    h1 { font-size: 1.6rem !important; }
    .stButton > button { padding: 0.65rem 1rem !important; font-size: 0.85rem !important; }
}

/* ── Status badge helper ── */
.mg-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.mg-badge-draft     { background: #F0F0E8; color: #7A7A60; }
.mg-badge-ready     { background: #E8F0EA; color: #2D6A4F; }
.mg-badge-posted    { background: rgba(212,175,55,0.15); color: #8A6D00; }
.mg-badge-failed    { background: #FDEEEE; color: #C0392B; }
.mg-badge-hold      { background: #EEF0FD; color: #3949AB; }
.mg-badge-generating{ background: rgba(27,67,50,0.08); color: var(--mg-green-mid); }
"""

# ── Sidebar ───────────────────────────────────────────────────────────────────

def _sidebar_health():
    st.sidebar.title("🌿 More Green Studio")
    st.sidebar.markdown("---")
    st.sidebar.subheader("System Health")

    checks = {
        "Anthropic API":  lambda: bool(os.environ.get("ANTHROPIC_API_KEY")),
        "fal.ai":         lambda: bool(os.environ.get("FAL_KEY")),
        "Cloudinary":     lambda: bool(os.environ.get("CLOUDINARY_CLOUD_NAME")),
        "Meta Token":     lambda: bool(os.environ.get("META_ACCESS_TOKEN")),
        "Google Sheets":  lambda: bool(os.environ.get("GOOGLE_SHEETS_ID")),
    }
    for name, fn in checks.items():
        try:
            ok = fn()
            icon = "✅" if ok else "⚠️"
        except Exception:
            ok, icon = False, "❌"
        st.sidebar.markdown(f"{icon} {name}")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Recent Activity")
    try:
        db = get_db()
        recent = db.execute(
            "SELECT post_id, pipeline_status, updated_at FROM posts ORDER BY updated_at DESC LIMIT 5"
        ).fetchall()
        for r in recent:
            icon = "✓" if r["pipeline_status"] == "posted" else ("✗" if "fail" in (r["pipeline_status"] or "") else "·")
            st.sidebar.markdown(f"{icon} `{r['post_id']}` — {r['pipeline_status']}")
    except Exception:
        st.sidebar.markdown("_No activity yet_")

    st.sidebar.markdown("---")
    try:
        db = get_db()
        db.execute("SELECT last_error FROM posts LIMIT 1").fetchall()
        st.sidebar.caption("DB connected ✓")
    except Exception:
        st.sidebar.caption("DB not initialised yet")


# ── Screen 1 — Weekly Overview ────────────────────────────────────────────────

def screen_weekly_overview():
    st.title("Weekly Overview")
    st.caption("Sunday review · approve posts · track your pipeline")
    st.markdown("---")

    col_sync, col_gen = st.columns([1, 1])
    with col_sync:
        if st.button("↻  Sync from Sheets", use_container_width=True):
            with st.spinner("Syncing..."):
                try:
                    from commands.sync_sheets import run as sync_run
                    sync_run()
                    st.success("Synced from Google Sheets")
                except Exception as e:
                    st.error(f"Sync failed: {e}")
    with col_gen:
        if st.button("✦  Generate Prompts", use_container_width=True, type="primary"):
            with st.spinner("Claude is writing your prompts..."):
                try:
                    from commands.generate_prompts import run as gen_run
                    gen_run()
                    st.success("Prompts ready — review below")
                    st.rerun()
                except Exception as e:
                    st.error(f"Prompt generation failed: {e}")

    try:
        db = get_db()
        posts = db.execute("SELECT * FROM posts ORDER BY scheduled_at ASC").fetchall()
    except Exception as e:
        st.error(f"Cannot load posts: {e}")
        return

    if not posts:
        st.markdown("")
        st.info("No posts yet. Fill in your Google Sheets content calendar, then click Sync.")
        return

    weeks = {}
    for p in posts:
        week = p["post_id"].split("_")[0] if "_" in p["post_id"] else "Other"
        weeks.setdefault(week, []).append(p)

    for week_label, week_posts in weeks.items():
        st.subheader(f"Week {week_label}")
        cols = st.columns(min(len(week_posts), 4))
        for i, post in enumerate(week_posts):
            with cols[i % len(cols)]:
                _post_card(post)


def _post_card(post):
    status = post["pipeline_status"] or "draft"

    status_map = {
        "draft":               ("⏳", "draft",      "mg-badge-draft"),
        "prompts_ready":       ("✍",  "prompts",    "mg-badge-ready"),
        "creative_generating": ("⚙",  "generating", "mg-badge-generating"),
        "creative_ready":      ("◈",  "creative",   "mg-badge-ready"),
        "approved":            ("◉",  "approved",   "mg-badge-posted"),
        "posted":              ("✓",  "posted",     "mg-badge-posted"),
        "creative_failed":     ("✗",  "failed",     "mg-badge-failed"),
    }
    icon, label, badge_cls = status_map.get(status, ("·", status, "mg-badge-draft"))

    sku_palette = {
        "sunflower":  ("#FFF8E1", "#F59E0B"),
        "blueberry":  ("#EDE7F6", "#7C3AED"),
        "moringa":    ("#E8F5E9", "#2E7D32"),
        "wheatgrass": ("#F1F8E9", "#558B2F"),
    }
    bg, accent = sku_palette.get(post["sku"], ("#F8F4E9", "#1B4332"))
    sku_icons = {"sunflower": "☀", "blueberry": "●", "moringa": "◆", "wheatgrass": "~"}
    sku_icon = sku_icons.get(post["sku"], "✿")

    with st.container(border=True):
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
            f'<span style="font-size:1.3rem;line-height:1">{sku_icon}</span>'
            f'<span style="font-family:\'Cormorant Garamond\',serif;font-size:1.05rem;'
            f'font-weight:600;color:#1B4332;letter-spacing:0.01em">{post["sku"].title()}</span>'
            f'</div>'
            f'<span class="mg-badge {badge_cls}">{icon} {label}</span>',
            unsafe_allow_html=True,
        )
        date_str = (post["scheduled_at"] or "")[:10]
        if date_str:
            st.caption(f"📅 {date_str}")
        if post["on_hold"]:
            st.markdown('<span class="mg-badge mg-badge-hold">⏸ on hold</span>', unsafe_allow_html=True)
        if post["last_error"]:
            st.caption(f"⚠ {post['last_error'][:55]}")

        if st.button("Open →", key=f"view_{post['post_id']}", use_container_width=True):
            st.session_state["selected_post_id"] = post["post_id"]
            st.session_state["screen"] = "post_detail"
            st.rerun()


# ── Screen 2 — Post Detail ────────────────────────────────────────────────────

def screen_post_detail(post_id: str):
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE post_id=?", (post_id,)).fetchone()
    if not post:
        st.error(f"Post {post_id} not found.")
        return

    if st.button("← Back"):
        st.session_state["screen"] = "overview"
        st.rerun()

    status = post["pipeline_status"] or "draft"
    sku_display = post["sku"].title() if post["sku"] else "Post"
    st.title(f"{sku_display}")
    st.caption(
        f"**{post_id}** · scheduled {(post['scheduled_at'] or '—')[:16].replace('T', ' at ')} · `{status}`"
    )
    st.markdown("---")

    left, right = st.columns([1, 1])

    with left:
        st.subheader("Image Prompt")
        img_prompt = st.text_area(
            "Image prompt",
            value=post["image_prompt"] or "",
            height=150,
            key=f"img_prompt_{post_id}",
            label_visibility="collapsed",
            placeholder="Claude will fill this in when you generate prompts…",
        )

        st.subheader("Video Prompt")
        vid_prompt = st.text_area(
            "Video prompt",
            value=post["video_prompt"] or "",
            height=110,
            key=f"vid_prompt_{post_id}",
            label_visibility="collapsed",
            placeholder="Kling motion instructions…",
        )

        st.subheader("Instagram Caption")
        ig_caption = st.text_area(
            "Instagram caption",
            value=post["caption_instagram"] or "",
            height=120,
            key=f"ig_caption_{post_id}",
            label_visibility="collapsed",
            placeholder="Pattern interrupt · fact · CTA · hashtags",
        )

        st.subheader("Facebook Caption")
        fb_caption = st.text_area(
            "Facebook caption",
            value=post["caption_facebook"] or "",
            height=100,
            key=f"fb_caption_{post_id}",
            label_visibility="collapsed",
            placeholder="Slightly longer, more educational…",
        )

        if st.button("Save Edits", use_container_width=True):
            with db:
                db.execute(
                    """UPDATE posts SET
                        image_prompt=?, video_prompt=?,
                        caption_instagram=?, caption_facebook=?,
                        updated_at=datetime('now')
                    WHERE post_id=?""",
                    (img_prompt, vid_prompt, ig_caption, fb_caption, post_id),
                )
            st.success("Saved.")

    with right:
        st.subheader("Instagram Preview")
        with st.container(border=True):
            st.markdown(
                '<p style="font-family:\'DM Sans\',sans-serif;font-weight:500;'
                'font-size:0.82rem;color:#1B4332;margin:0 0 8px">@moregreen.in</p>',
                unsafe_allow_html=True,
            )
            cloudinary_urls = json.loads(post["cloudinary_urls"] or "[]")
            if cloudinary_urls:
                st.image(cloudinary_urls[0], use_container_width=True)
            else:
                st.markdown(
                    '<div style="background:var(--mg-cream,#F8F4E9);border-radius:8px;'
                    'height:200px;display:flex;align-items:center;justify-content:center;'
                    'color:#999;font-size:0.82rem;">Creative not yet generated</div>',
                    unsafe_allow_html=True,
                )
            caption_text = (post["caption_instagram"] or "")[:120]
            if caption_text:
                st.caption(caption_text + ("…" if len(post["caption_instagram"] or "") > 120 else ""))

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        if not post["prompts_approved"]:
            if st.button("✦ Approve Prompts", use_container_width=True, type="primary"):
                with db:
                    db.execute(
                        "UPDATE posts SET prompts_approved=1, prompts_approved_at=datetime('now') WHERE post_id=?",
                        (post_id,),
                    )
                st.success("Prompts approved.")
                st.rerun()
        else:
            st.success("Prompts approved ✓")
            if not post["image_paths"]:
                if st.button("◈ Generate Creatives", use_container_width=True):
                    with st.spinner("FLUX + Kling running…"):
                        try:
                            from commands.generate_images import run as gen_img
                            from commands.upload_media import run as upload
                            gen_img(post_id=post_id)
                            upload(post_id=post_id)
                            st.success("Creatives ready.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Generation failed: {e}")

    with col2:
        hold_label = "▶ Resume" if post["on_hold"] else "⏸ Hold"
        if st.button(hold_label, use_container_width=True):
            new_hold = 0 if post["on_hold"] else 1
            with db:
                db.execute("UPDATE posts SET on_hold=? WHERE post_id=?", (new_hold, post_id))
            st.rerun()

    with col3:
        if post["image_paths"] and not post["creatives_approved"]:
            if st.button("→ Review Creatives", use_container_width=True, type="primary"):
                st.session_state["screen"] = "creative_approval"
                st.rerun()


# ── Screen 3 — Creative Approval ─────────────────────────────────────────────

def screen_creative_approval(post_id: str):
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE post_id=?", (post_id,)).fetchone()
    if not post:
        st.error("Post not found.")
        return

    if st.button("← Back to Post"):
        st.session_state["screen"] = "post_detail"
        st.rerun()

    st.title("Pick Your Creative")
    st.caption(f"{post_id} · choose the image variant to publish")
    st.markdown("---")

    image_paths = json.loads(post["image_paths"] or "[]")
    cloudinary_urls = json.loads(post["cloudinary_urls"] or "[]")

    if not image_paths and not cloudinary_urls:
        st.warning("No creatives generated yet. Go back and click Generate Creatives.")
        return

    display_urls = cloudinary_urls or []
    selected_idx = st.session_state.get(f"selected_variant_{post_id}", 0)

    variant_cols = st.columns(min(len(display_urls), 3) or 1)
    for i, url in enumerate(display_urls[:3]):
        with variant_cols[i]:
            with st.container(border=True):
                st.image(url, use_container_width=True)
                if i == selected_idx:
                    st.markdown(
                        '<div style="text-align:center;padding:4px 0;'
                        'font-family:\'DM Sans\',sans-serif;font-size:0.72rem;'
                        'font-weight:500;letter-spacing:0.08em;color:#D4AF37;">'
                        '✦ SELECTED</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    if st.button(f"Select {i+1}", key=f"sel_{i}_{post_id}", use_container_width=True):
                        st.session_state[f"selected_variant_{post_id}"] = i
                        st.rerun()

    if post["video_path"]:
        st.markdown("---")
        st.subheader("Video Preview")
        from config import PROJECT_ROOT
        video_file = PROJECT_ROOT / post["video_path"]
        if video_file.exists():
            st.video(str(video_file))
        else:
            st.caption("Video file not found locally — it will upload from Cloudinary.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✦ Approve & Schedule", type="primary", use_container_width=True):
            with db:
                db.execute(
                    "UPDATE posts SET creatives_approved=1, creatives_approved_at=datetime('now'), pipeline_status='approved' WHERE post_id=?",
                    (post_id,),
                )
            from utils.notifications import notify_founder
            notify_founder(
                subject=f"Creative approved: {post_id}",
                body=f"Post {post_id} is approved and scheduled to go live.",
            )
            st.success("Approved. Post goes live at its scheduled time.")
            st.session_state["screen"] = "overview"
            st.rerun()
    with col2:
        if st.button("↻ Regenerate All", use_container_width=True):
            with st.spinner("Regenerating…"):
                try:
                    with db:
                        db.execute(
                            "UPDATE posts SET image_paths=NULL, cloudinary_urls=NULL WHERE post_id=?",
                            (post_id,),
                        )
                    from commands.generate_images import run as gen_img
                    from commands.upload_media import run as upload
                    gen_img(post_id=post_id)
                    upload(post_id=post_id)
                    st.success("New variants ready.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Regeneration failed: {e}")


# ── Router ────────────────────────────────────────────────────────────────────

def main():
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)
    _sidebar_health()

    screen = st.session_state.get("screen", "overview")
    post_id = st.session_state.get("selected_post_id")

    if screen == "overview":
        screen_weekly_overview()
    elif screen == "post_detail" and post_id:
        screen_post_detail(post_id)
    elif screen == "creative_approval" and post_id:
        screen_creative_approval(post_id)
    else:
        screen_weekly_overview()


if __name__ == "__main__":
    main()
