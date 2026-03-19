"""
YouTube 급상승 쇼츠 크롤러
- KR 급상승 영상 중 쇼츠 위주 수집
- 기존 save_meme / classify_category 그대로 사용
"""

import os
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Dict

import isodate
from googleapiclient.discovery import build

from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [yt_trending] %(message)s")
log = logging.getLogger(__name__)

YT_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# 급상승 카테고리 (KR)
TRENDING_CATEGORIES = [
    ("0",  "all"),      # 전체
    ("24", "entertain"),  # 엔터테인먼트
    ("22", "people"),     # 인물/블로그
]

MAX_RESULTS = 50  # 카테고리당 최대 50개


def build_service():
    return build("youtube", "v3", developerKey=YT_API_KEY)


def _make_hash(video_id: str) -> str:
    return hashlib.md5(f"yt_trending_{video_id}".encode()).hexdigest()


def fetch_trending_videos(service, category_id: str) -> List[Dict]:
    """
    YouTube 급상승 목록 (KR) 조회
    - contentDetails까지 같이 받아서 duration 추가 호출 없이 사용
    """
    try:
        resp = service.videos().list(
            part="snippet,statistics,contentDetails",
            chart="mostPopular",
            regionCode="KR",
            videoCategoryId=category_id,
            maxResults=MAX_RESULTS,
        ).execute()
        return resp.get("items", [])
    except Exception as e:
        log.warning(f"급상승 API 실패 (category={category_id}): {e}")
        return []


def _is_shorts(item: Dict) -> bool:
    """
    쇼츠 판정:
    - duration 60초 이하
    """
    try:
        duration_str = item["contentDetails"]["duration"]
        seconds = isodate.parse_duration(duration_str).total_seconds()
        return seconds <= 60
    except Exception:
        return False


def run():
    if not YT_API_KEY:
        log.error("YOUTUBE_API_KEY 없음")
        return 0

    service = build_service()
    total_new = 0
    seen_ids = set()

    for category_id, category_name in TRENDING_CATEGORIES:
        log.info(f"수집: KR 급상승 ({category_name})")
        items = fetch_trending_videos(service, category_id)
        log.info(f"  → 급상승 {len(items)}건")

        # 쇼츠만 사용 (원하면 여기서 일반 영상까지 포함하도록 옵션 바꿀 수 있음)
        shorts_items = [it for it in items if _is_shorts(it)]
        log.info(f"  → 쇼츠 {len(shorts_items)}건")

        for item in shorts_items:
            video_id = item.get("id")
            if not video_id or video_id in seen_ids:
                continue
            seen_ids.add(video_id)

            snippet = item.get("snippet", {})
            stats   = item.get("statistics", {})

            title     = snippet.get("title", "")
            channel   = snippet.get("channelTitle", "")
            thumbnail = snippet.get("thumbnails", {}).get("high", {}).get("url", "")
            published = snippet.get("publishedAt", "")

            view_count    = int(stats.get("viewCount", 0))
            like_count    = int(stats.get("likeCount", 0))
            comment_count = int(stats.get("commentCount", 0))

            category = classify_category(title)

            saved = save_meme(
                title=title,
                url=f"https://www.youtube.com/shorts/{video_id}",
                source=f"youtube_trending_{category_name}",
                platform="domestic",  # KR 급상승 기준이니 일단 domestic으로 태깅
                image_url=thumbnail,
                view_count=view_count,
                like_count=like_count,
                comment_count=comment_count,
                content_hash=_make_hash(video_id),
                category=category,
                extra={
                    "video_id":     video_id,
                    "channel":      channel,
                    "published_at": published,
                    "trending_cat": category_name,
                    "region":       "KR",
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "is_shorts":    True,
                },
            )

            if saved:
                total_new += 1

    log.info(f"YouTube 급상승 쇼츠 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
