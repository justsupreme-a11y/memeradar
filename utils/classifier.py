"""
밈레이더 분류기 v2
- 흐름 분류: inflow / independent / export
- 생애주기: seed / spread / peak / fade
- 카테고리: fb / fashion / celeb / general (수집 시 이미 분류되지만 재분류 가능)
"""

import logging
from datetime import datetime, timezone
from utils.db import get_client
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [classifier] %(message)s")
log = logging.getLogger(__name__)

GLOBAL_SOURCES   = {"kym", "youtube_meme_ch"}
DOMESTIC_SOURCES = {"namuwiki", "instiz", "univ_tomorrow", "google_trends"}


def classify_flow(meme: dict) -> str:
    source   = meme["source"]
    platform = meme.get("platform", "")

    if source in GLOBAL_SOURCES or platform == "global":
        return "inflow"

    if source in DOMESTIC_SOURCES or platform == "domestic":
        return "independent"

    return "independent"


def classify_lifecycle(meme: dict) -> str:
    collected_at = _parse_time(meme["collected_at"])
    now          = datetime.now(timezone.utc)
    hours_since  = (now - collected_at).total_seconds() / 3600
    view_count   = meme.get("view_count", 0) or 0

    if hours_since <= 24 and view_count < 1000:
        return "seed"
    elif hours_since <= 72 and view_count < 10000:
        return "spread"
    elif view_count >= 10000:
        return "peak"
    else:
        return "fade"


def _parse_time(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def run():
    db = get_client()
    log.info("미분류 밈 조회 중...")

    resp = (
        db.table("memes")
        .select("*")
        .is_("flow_type", "null")
        .order("collected_at", desc=False)
        .limit(500)
        .execute()
    )
    memes = resp.data or []
    log.info(f"미분류 {len(memes)}건 처리 시작")

    if not memes:
        log.info("처리할 밈 없음")
        return 0

    updated = 0
    for meme in memes:
        flow      = classify_flow(meme)
        lifecycle = classify_lifecycle(meme)
        category  = meme.get("category") or classify_category(meme["title"])

        db.table("memes").update({
            "flow_type":       flow,
            "lifecycle_stage": lifecycle,
            "category":        category,
        }).eq("id", meme["id"]).execute()

        updated += 1

    log.info(f"분류 완료 — {updated}건 업데이트")
    return updated


if __name__ == "__main__":
    run()
