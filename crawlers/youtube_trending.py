"""
YouTube 실시간 급상승 + Shorts 크롤러
- 국내(KR) + 해외(US) 급상승 영상
- Shorts 필터링 포함
- YouTube Data API v3
"""

import os
import logging
from googleapiclient.discovery import build
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [yt_trending] %(message)s")
log = logging.getLogger(__name__)

YT_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

REGIONS = [
    {"code": "KR", "platform": "domestic", "label": "국내 급상승"},
    {"code": "US", "platform": "global",   "label": "해외 급상승"},
]

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
    {"id": "UCM2PEMvNjFOPMhBJJrCEBzA", "name": "침착맨",     "platform": "domestic"},
    # F&B 채널
    {"id": "UCuPDTBDvDpXciCBJsQNRSOQ", "name": "젼언니",     "platform": "domestic"},
]


def build_service():
    return build("youtube", "v3", developerKey=YT_API_KEY)


def fetch_trending(service, region_code: str, max_results: int = 30) -> list[dict]:
    """실시간 급상승 영상"""
    try:
        resp = service.videos().list(
            part="snippet,statistics,contentDetails",
            chart="mostPopular",
            regionCode=region_code,
            maxResults=max_results,
            videoCategoryId="0",
        ).execute()
        return resp.get("items", [])
    except Exception as e:
        log.warning(f"급상승 {region_code} 실패: {e}")
        return []


def fetch_shorts(service, region_code: str) -> list[dict]:
    """Shorts 급상승 (videoCategoryId=26 이나 검색으로 대체)"""
    try:
        resp = service.search().list(
            part="snippet",
            type="video",
            videoDuration="short",
            order="viewCount",
            regionCode=region_code,
            maxResults=20,
            q="#shorts",
        ).execute()
        items = resp.get("items", [])
        # 통계 배치 조회
        ids = [i["id"]["videoId"] for i in items if i.get("id", {}).get("videoId")]
        if not ids:
            return []
        stats_resp = service.videos().list(
            part="statistics,contentDetails",
            id=",".join(ids),
        ).execute()
        stats_map = {i["id"]: i for i in stats_resp.get("items", [])}

        result = []
        for item in items:
            vid = item.get("id", {}).get("videoId")
            if not vid:
                continue
            detail = stats_map.get(vid, {})
            result.append({
                "id": {"videoId": vid},
                "snippet": item["snippet"],
                "statistics": detail.get("statistics", {}),
                "contentDetails": detail.get("contentDetails", {}),
            })
        return result
    except Exception as e:
        log.warning(f"Shorts {region_code} 실패: {e}")
        return []


def fetch_channel_videos(service, channel_id: str) -> list[dict]:
    """밈 채널 최신 영상 (72시간 이내)"""
    from datetime import datetime, timedelta, timezone
    published_after = (
        datetime.now(timezone.utc) - timedelta(hours=72)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        resp = service.search().list(
            part="snippet",
            channelId=channel_id,
            order="date",
            publishedAfter=published_after,
            maxResults=10,
            type="video",
        ).execute()
        items = resp.get("items", [])
        if not items:
            return []
        ids = [i["id"]["videoId"] for i in items if i.get("id", {}).get("videoId")]
        stats_resp = service.videos().list(
            part="statistics",
            id=",".join(ids),
        ).execute()
        stats_map = {i["id"]: i.get("statistics", {}) for i in stats_resp.get("items", [])}
        for item in items:
            vid = item.get("id", {}).get("videoId")
            item["statistics"] = stats_map.get(vid, {})
        return items
    except Exception as e:
        log.warning(f"채널 {channel_id} 실패: {e}")
        return []


def parse_video(item: dict, platform: str, content_type: str) -> dict:
    snippet   = item.get("snippet", {})
    stats     = item.get("statistics", {})
    vid       = item.get("id", {})
    video_id  = vid.get("videoId") or item.get("id", "")
    if isinstance(video_id, dict):
        video_id = video_id.get("videoId", "")

    title     = snippet.get("title", "")
    thumbnail = snippet.get("thumbnails", {}).get("high", {}).get("url", "")
    published = snippet.get("publishedAt", "")
    channel   = snippet.get("channelTitle", "")

    return {
        "title":         title,
        "url":           f"https://www.youtube.com/watch?v={video_id}",
        "image_url":     thumbnail,
        "view_count":    int(stats.get("viewCount", 0)),
        "like_count":    int(stats.get("likeCount", 0)),
        "comment_count": int(stats.get("commentCount", 0)),
        "platform":      platform,
        "extra": {
            "video_id":     video_id,
            "channel":      channel,
            "published_at": published,
            "content_type": content_type,
        },
    }


def run():
    if not YT_API_KEY:
        log.error("YOUTUBE_API_KEY 없음")
        return 0

    service   = build_service()
    total_new = 0

    # 1. 국내/해외 급상승
    for region in REGIONS:
        log.info(f"수집: {region['label']}")
        videos = fetch_trending(service, region["code"])
        log.info(f"  → {len(videos)}건")
        for v in videos:
            data     = parse_video(v, region["platform"], "trending")
            category = classify_category(data["title"])
            saved = save_meme(
                title=data["title"], url=data["url"],
                source="youtube_trending", platform=data["platform"],
                image_url=data["image_url"],
                view_count=data["view_count"], like_count=data["like_count"],
                comment_count=data["comment_count"],
                category=category, extra=data["extra"],
            )
            if saved:
                total_new += 1

    # 2. Shorts
    for region in REGIONS:
        log.info(f"수집: {region['label']} Shorts")
        shorts = fetch_shorts(service, region["code"])
        log.info(f"  → {len(shorts)}건")
        for v in shorts:
            data     = parse_video(v, region["platform"], "shorts")
            category = classify_category(data["title"])
            saved = save_meme(
                title=data["title"], url=data["url"],
                source="youtube_shorts", platform=data["platform"],
                image_url=data["image_url"],
                view_count=data["view_count"], like_count=data["like_count"],
                comment_count=data["comment_count"],
                category=category, extra=data["extra"],
            )
            if saved:
                total_new += 1

    # 3. 밈 채널
    for channel in MEME_CHANNELS:
        log.info(f"수집: {channel['name']}")
        videos = fetch_channel_videos(service, channel["id"])
        log.info(f"  → {len(videos)}건")
        for v in videos:
            data     = parse_video(v, channel["platform"], "meme_channel")
            category = classify_category(data["title"])
            saved = save_meme(
                title=data["title"], url=data["url"],
                source="youtube_meme_ch", platform=channel["platform"],
                image_url=data["image_url"],
                view_count=data["view_count"], like_count=data["like_count"],
                comment_count=data["comment_count"],
                category=category, extra={**data["extra"], "channel_name": channel["name"]},
            )
            if saved:
                total_new += 1

    log.info(f"YouTube 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
