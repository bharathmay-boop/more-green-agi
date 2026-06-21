"""seed-owner (plan 02 T1.3) — insert the dashboard owner so login works on a
fresh DB. Login checks the shared ADMIN_PASSWORD and that the email exists in
`users`; role is read from the row. So we only seed a users row with role=owner.
Tested through the shim on the conftest SQLite `db` fixture."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def test_seed_owner_inserts_normalized_owner_row(db):
    from commands import seed_owner

    email = seed_owner.run(email="  Founder@Example.COM ", db=db)
    assert email == "founder@example.com"  # trimmed + lowercased

    row = db.execute(
        "SELECT email, role, id FROM users WHERE email=?", ("founder@example.com",)
    ).fetchone()
    assert row["role"] == "owner"
    assert row["id"]  # a non-empty id was generated (cuid is client-side, not a DB default)


def test_seed_owner_is_idempotent_and_updates_role(db):
    from commands import seed_owner

    seed_owner.run(email="o@x.com", role="viewer", db=db)
    seed_owner.run(email="o@x.com", role="owner", db=db)  # re-run promotes

    rows = db.execute("SELECT role FROM users WHERE email=?", ("o@x.com",)).fetchall()
    assert len(rows) == 1 and rows[0]["role"] == "owner"


def test_seed_owner_requires_an_email(db):
    from commands import seed_owner
    import pytest

    with pytest.raises(ValueError):
        seed_owner.run(email="   ", db=db)


def test_seed_owner_links_org_when_named(db):
    from commands import seed_owner

    seed_owner.run(email="owner@brand.com", org_name="More Green", db=db)
    row = db.execute(
        "SELECT org_id FROM users WHERE email=?", ("owner@brand.com",)
    ).fetchone()
    assert row["org_id"]
    org = db.execute("SELECT name FROM orgs WHERE id=?", (row["org_id"],)).fetchone()
    assert org["name"] == "More Green"
