"""seed-owner — insert the dashboard owner User so login works (plan 02 T1.3).

The web login (platform/apps/web/app/api/auth/login) checks the shared
ADMIN_PASSWORD and that the email exists in `users`; the role is read from the
row by getCurrentUser. So all this seeds is a `users` row with role='owner'
(optionally linked to an org). No password is stored here.

Idempotent: re-running upserts on the unique email and promotes the role. Runs
against whichever DB `DATABASE_URL` selects (Neon in prod, SQLite locally).
"""
from __future__ import annotations

import uuid

import config
from utils.db import get_db


def _id(prefix: str) -> str:
    # Prisma's cuid() is client-side, so a raw INSERT must supply the PK. The
    # web reads users by email, not id, so any unique string is fine.
    return f"{prefix}_{uuid.uuid4().hex[:24]}"


def run(email: str | None = None, name: str | None = None, role: str = "owner",
        org_name: str | None = None, dry_run: bool = False, db=None) -> str:
    email = (email or getattr(config, "FOUNDER_EMAIL", "") or "").strip().lower()
    if not email:
        raise ValueError("seed-owner needs --email (or config.FOUNDER_EMAIL)")

    db = db or get_db()
    org_id = None
    if org_name:
        org_id = _id("org")
        if not dry_run:
            with db:
                db.execute(
                    "INSERT INTO orgs (id, name) VALUES (?, ?) ON CONFLICT (id) DO NOTHING",
                    (org_id, org_name),
                )

    if dry_run:
        print(f"[dry-run] would seed owner {email} (role={role}, org={org_name or '-'})")
        return email

    with db:
        db.execute(
            "INSERT INTO users (id, email, name, role, org_id) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (email) DO UPDATE SET role=excluded.role, "
            "name=COALESCE(excluded.name, users.name), "
            "org_id=COALESCE(excluded.org_id, users.org_id)",
            (_id("usr"), email, name, role, org_id),
        )
    print(f"seeded owner {email} (role={role}). Login needs ADMIN_PASSWORD set on the web tier.")
    return email
