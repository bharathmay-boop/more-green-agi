# Filing Meta App Review — `instagram_manage_messages`

Required for `check-replies` to work. The command is already built and guarded —
it will skip with a warning until `IG_MESSAGES_APPROVED=1` is set in `.env`.

---

## Before You Start — Have These Ready

- A screen recording (2–5 min) showing how your app uses the permission
- Your app's Privacy Policy URL (must be live, not localhost)
- A brief written description of the use case

---

## Step 1 — Open Your App in Meta Developer Portal

Go to `developers.facebook.com` → My Apps → select your More Green app.

---

## Step 2 — Switch App to Live Mode

Left sidebar → **App Settings** → **Basic**.
At the top, toggle from **Development** to **Live**.
You'll need a Privacy Policy URL entered here first — it won't let you go Live without one.

---

## Step 3 — Navigate to App Review

Left sidebar → **App Review** → **Permissions and Features**.

---

## Step 4 — Find the Permission

Search for `instagram_manage_messages`. Click **Request**.

---

## Step 5 — Fill In the Use Case

Meta will ask:

**How will you use this permission?**

> We use this permission to read incoming DMs from customers and collaborators on our
> brand's Instagram account (@moregreen.in), and to send replies from our own automation
> system. All messages are initiated by the other party first. We do not send unsolicited
> messages.

**Which users will use this feature?**

Select: **My app's admins, developers, and testers only**
(sufficient for a single-brand tool; faster to approve than "All users").

---

## Step 6 — Record and Upload the Screencast

Meta requires a video showing:
1. A user sends your Instagram account a DM
2. Your app reads that message via the API
3. Your app sends a reply

Since the code isn't live yet, demo it using Graph API Explorer:
- Go to `developers.facebook.com/tools/explorer`
- Make a `GET /{instagram-account-id}/conversations` call — show the response
- Make a `POST /{message-id}/replies` call — show the reply being sent
- Narrate what you're doing throughout

Keep it under 5 minutes. Loom works well for recording.

---

## Step 7 — Submit

Click **Submit for Review**.
You'll get a confirmation email. Meta typically responds in **5–14 business days**.
Check the developer portal notifications for follow-up questions.

---

## After Approval

Add this line to `automation/.env`:

```
IG_MESSAGES_APPROVED=1
```

Then run:

```powershell
cd D:\More Green AGI\automation
python main.py check-replies
```
