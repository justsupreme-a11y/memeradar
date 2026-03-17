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


def make_content_hash(title: str, source: str) -> str:
    """제목+소스로 중복 감지용 해시 생성"""
    raw = f"{source}:{title.strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()


def save_meme(
    title: str,
    url: str,
    source: str,          # "dcinside" | "fmkorea" | "youtube"
    platform: str,        # "domestic" | "global"
    image_url: str = "",
    view_count: int = 0,
    like_count: int = 0,
    comment_count: int = 0,
    extra: dict = {},
) -> bool:
    """
    밈 데이터를 Supabase memes 테이블에 저장.
    content_hash로 중복이면 스킵하고 False 반환.
    """
    db = get_client()
    content_hash = make_content_hash(title, source)

    # 중복 체크
    existing = (
        db.table("memes")
        .select("id")
        .eq("content_hash", content_hash)
        .execute()
    )
    if existing.data:
        return False  # 이미 존재

    db.table("memes").insert({
        "title": title,
        "url": url,
        "source": source,
        "platform": platform,
        "image_url": image_url,
        "view_count": view_count,
        "like_count": like_count,
        "comment_count": comment_count,
        "content_hash": content_hash,
        "flow_type": None,       # 분류 레이어에서 채워짐
        "lifecycle_stage": None, # 분류 레이어에서 채워짐
        "extra": extra,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    return True  # 새로 저장됨
