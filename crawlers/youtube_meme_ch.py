"""
YouTube 밈 전문 채널 크롤러 v2
- 국내 + 해외 밈 채널
- 카테고리 자동 분류 추가
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [yt_meme] %(message)s")
log = logging.getLogger(__name__)

YT_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

MEME_CHANNELS = [
    # 해외 밈 채널
    {"id": "UCHRFMBxHOhqBjrVnZHKmGlA", "name": "Know Your Meme",     "platform": "global"},
    {"id": "UCddiUEpeqJcYeBxX1IVBKvQ", "name": "The finest",          "platform": "global"},
    {"id": "UCpko_-a4wgz2u_DgDgd9fqA", "name": "Daily Dose of Memes", "platform": "global"},

    # 국내 유머/밈 채널
    {"id": "UCQ2KSP4dUBMoNpnnNRjT5LA", "name": "피식대학",   "platform": "domestic"},
    {"id": "UCK4s70-bFSFMVVdDTMKnorg", "name": "숏박스",     "platform": "domestic"},
    {"id": "UCo-Gj-XMXF1EiCDsWbqSEKw", "name": "흑자헬스",  "platform": "domestic"},
    {"id": "UCsJ6RuBiohBWBS7fH8f7mAg", "name": "워크맨",     "platform": "domestic"},
]

MAX_RESULTS = 10


def build_service():
    return build("youtube", "v3", developerKey=YT_API_KEY)


def fetch_channel_videos(service, channel_id: str) -> list[dict]:
    published_after = (
        datetime.now(timezone.utc) - timedelta(hours=72)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        resp = service.search().list(
            part="snippet",
            channelId=channel_id,
            order="date",
            publishedAfter=published_after,
            maxResults=MAX_RESULTS,
            type="video",
        ).execute()
        return resp.get("items", [])
    except Exception as e:
        log.warning(f"채널 {channel_id} 실패: {e}")
        return []


def fetch_stats(service, video_ids: list[str]) -> dict:
    if not video_ids:
        return {}
    try:
        resp = service.videos().list(
            part="statistics",
            id=",".join(video_ids),
        ).execute()
        return {item["id"]: item.get("statistics", {}) for item in resp.get("items", [])}
    except Exception:
        return {}


def run():
    if not YT_API_KEY:
        log.error("YOUTUBE_API_KEY 없음")
        return 0

    service   = build_service()
    total_new = 0

    for channel in MEME_CHANNELS:
        log.info(f"수집: {channel['name']}")
        videos = fetch_channel_videos(service, channel["id"])
        log.info(f"  → {len(videos)}건")

        if not videos:
            continue

        ids       = [v["id"]["videoId"] for v in videos if v.get("id", {}).get("videoId")]
        stats_map = fetch_stats(service, ids)

        for v in videos:
            video_id = v.get("id", {}).get("videoId")
            if not video_id:
                continue

            snippet   = v.get("snippet", {})
            stats     = stats_map.get(video_id, {})
            title     = snippet.get("title", "")
            thumbnail = snippet.get("thumbnails", {}).get("high", {}).get("url", "")
            published = snippet.get("publishedAt", "")

            view_count    = int(stats.get("viewCount", 0))
            like_count    = int(stats.get("likeCount", 0))
            comment_count = int(stats.get("commentCount", 0))

            category = classify_category(title)

            saved = save_meme(
                title=title,
                url=f"https://www.youtube.com/watch?v={video_id}",
                source="youtube_meme_ch",
                platform=channel["platform"],
                image_url=thumbnail,
                view_count=view_count,
                like_count=like_count,
                comment_count=comment_count,
                category=category,
                extra={
                    "video_id":     video_id,
                    "channel":      channel["name"],
                    "published_at": published,
                },
            )
            if saved:
                total_new += 1

    log.info(f"YouTube 밈채널 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
