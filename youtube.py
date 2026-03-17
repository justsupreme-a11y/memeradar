"""
YouTube Shorts 크롤러
- API: YouTube Data API v3 (무료 · 하루 10,000 유닛)
- 대상: 밈 관련 한국어 + 글로벌 트렌딩 Shorts
- 비용: 검색 1회 = 100유닛 → 하루 최대 100회 검색 가능
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from utils.db import save_meme

logging.basicConfig(level=logging.INFO, format="%(asctime)s [yt] %(message)s")
log = logging.getLogger(__name__)

YT_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# 검색 키워드 세트 — 국내 + 해외 구분
QUERIES = [
    # 국내
    {"q": "밈 #shorts",          "platform": "domestic", "lang": "ko"},
    {"q": "유머짤 #shorts",       "platform": "domestic", "lang": "ko"},
    {"q": "개드립 #shorts",       "platform": "domestic", "lang": "ko"},
    # 해외
    {"q": "meme compilation #shorts", "platform": "global", "lang": "en"},
    {"q": "funny meme #shorts",       "platform": "global", "lang": "en"},
    {"q": "trending meme 2024",       "platform": "global", "lang": "en"},
]

MAX_RESULTS_PER_QUERY = 10  # 유닛 절약: 10개씩 (100유닛/회)


def build_service():
    return build("youtube", "v3", developerKey=YT_API_KEY)


def search_shorts(service, query: str, lang: str, max_results: int = 10) -> list[dict]:
    """Shorts 검색 — 최근 48시간 이내 영상만"""
    published_after = (
        datetime.now(timezone.utc) - timedelta(hours=48)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        resp = service.search().list(
            part="snippet",
            q=query,
            type="video",
            videoDuration="short",       # 60초 이하 = Shorts
            publishedAfter=published_after,
            relevanceLanguage=lang,
            maxResults=max_results,
            order="viewCount",
        ).execute()
    except Exception as e:
        log.warning(f"검색 실패 '{query}': {e}")
        return []

    results = []
    for item in resp.get("items", []):
        snippet = item["snippet"]
        video_id = item["id"]["videoId"]
        results.append({
            "video_id":    video_id,
            "title":       snippet["title"],
            "url":         f"https://www.youtube.com/shorts/{video_id}",
            "thumbnail":   snippet["thumbnails"].get("high", {}).get("url", ""),
            "channel":     snippet["channelTitle"],
            "published_at": snippet["publishedAt"],
        })

    return results


def fetch_video_stats(service, video_ids: list[str]) -> dict[str, dict]:
    """영상 통계(조회수, 좋아요) 배치 조회 — 1회 API 호출로 최대 50개"""
    if not video_ids:
        return {}
    try:
        resp = service.videos().list(
            part="statistics",
            id=",".join(video_ids),
        ).execute()
    except Exception as e:
        log.warning(f"통계 조회 실패: {e}")
        return {}

    stats = {}
    for item in resp.get("items", []):
        s = item.get("statistics", {})
        stats[item["id"]] = {
            "view_count":    int(s.get("viewCount", 0)),
            "like_count":    int(s.get("likeCount", 0)),
            "comment_count": int(s.get("commentCount", 0)),
        }
    return stats


def run():
    if not YT_API_KEY:
        log.error("YOUTUBE_API_KEY 환경변수가 없습니다.")
        return 0

    service = build_service()
    total_new = 0

    for query_cfg in QUERIES:
        q        = query_cfg["q"]
        platform = query_cfg["platform"]
        lang     = query_cfg["lang"]

        log.info(f"검색: '{q}' ({platform})")
        videos = search_shorts(service, q, lang, MAX_RESULTS_PER_QUERY)
        log.info(f"  → {len(videos)}건 발견")

        if not videos:
            continue

        # 통계 배치 조회 (유닛 절약)
        ids = [v["video_id"] for v in videos]
        stats_map = fetch_video_stats(service, ids)

        for v in videos:
            s = stats_map.get(v["video_id"], {})

            # 조회수 낮은 건 스킵
            if s.get("view_count", 0) < 1000:
                continue

            saved = save_meme(
                title=v["title"],
                url=v["url"],
                source="youtube",
                platform=platform,
                image_url=v["thumbnail"],
                view_count=s.get("view_count", 0),
                like_count=s.get("like_count", 0),
                comment_count=s.get("comment_count", 0),
                extra={
                    "video_id":    v["video_id"],
                    "channel":     v["channel"],
                    "published_at": v["published_at"],
                    "query":       q,
                },
            )
            if saved:
                total_new += 1

    log.info(f"YouTube Shorts 완료 — 신규 {total_new}건 저장")
    return total_new


if __name__ == "__main__":
    run()
