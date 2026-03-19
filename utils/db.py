import os
import hashlib
from datetime import datetime, timezone
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

_client: Client | None = None

def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def make_hash(title: str, source: str) -> str:
    raw = f"{source}:{title.strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()


def save_meme(
    title: str,
    url: str,
    source: str,
    platform: str,
    image_url: str = "",
    view_count: int = 0,
    like_count: int = 0,
    comment_count: int = 0,
    category: str = "general",       # fb | fashion | celeb | general
    related_links: list = [],         # [{title, url, source}]
    extra: dict = {},
) -> bool:
    db = get_client()
    content_hash = make_hash(title, source)

    try:
        existing = db.table("memes").select("id").eq("content_hash", content_hash).execute()
        if existing.data:
            return False
    except Exception:
        return False

    try:
        db.table("memes").insert({
            "title":         title,
            "url":           url,
            "source":        source,
            "platform":      platform,
            "image_url":     image_url,
            "view_count":    view_count,
            "like_count":    like_count,
            "comment_count": comment_count,
            "category":      category,
            "related_links": related_links,
            "content_hash":  content_hash,
            "extra":         extra,
            "collected_at":  datetime.now(timezone.utc).isoformat(),
        }).execute()
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"DB 저장 실패: {e}")
        return False
