import functools
import logging

import click

from utils.db import get_db

log = logging.getLogger(__name__)


def require_approval(field: str, friendly_name: str):
    """Decorator: abort if any target post lacks the required approval gate."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            db = get_db()
            post_id = kwargs.get("post_id") or kwargs.get("post")
            query = (
                f"SELECT post_id FROM posts WHERE {field} = 0 AND on_hold = 0"
            )
            params = []
            if post_id:
                query += " AND post_id = ?"
                params.append(post_id)
            blocked = [r["post_id"] for r in db.execute(query, params).fetchall()]
            if blocked:
                raise click.ClickException(
                    f"Cannot proceed — {friendly_name} not approved for: {blocked}\n"
                    f"Approve in the dashboard or run: python main.py approve-prompts --all"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
