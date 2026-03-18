"""
YouTube 트렌딩 크롤러 v2
- 키워드 검색 대신 트렌딩/급상승 영상 수집
- 한국(KR) + 미국(US) 트렌딩 각각 수집
- 카테고리: 엔터테인먼트(23), 코미디(34) 위주
- API 비용: videChart 1회 = 1유닛 (매우 저렴)
"""

import os
import logging
from googleapiclient.discovery import build
from utils.db import save_meme

logging.basicConfig(level=logging.INFO, format="%(asctime)s [yt] %(message)s")
log = logging.getLogger(__name__)

YT_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# 트렌딩 수집 설정
REGIONS = [
    {"code": "KR", "platform": "domestic", "label": "한국"},
    {"code": "US", "platform": "global",   "label": "미국"},
]

# 수집할 카테고리 ID (없으면 전체)
# 1=영화, 2=자동차, 10=음악, 15=동물, 17=스포츠,
# 23=엔터테인먼트, 24=뉴스, 28=과학기술, 34=코미디
CATEGORY_IDS = ["23", "34"]  # 엔터테인먼트 + 코미디

MAX_RESULTS = 50  # 지역당 최대 50개


def fetch_trending(service, region_code: str, category_id: str = "") -> list[dict]:
    """특정 지역 + 카테고리의 트렌딩 영상 수집"""
    try:
        params = {
            "part": "snippet,statistics,contentDetails",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": MAX_RESULTS,
            "hl": "ko" if region_code == "KR" else "en",
        }
        if category_id:
            params["videoCategoryId"] = category_id

        resp = service.videos().list(**params).execute()
        return resp.get("items", [])
    except Exception as e:
        log.warning(f"트렌딩 수집 실패 {region_code} cat={category_id}: {e}")
        return []


def is_short(item: dict) -> bool:
    """Shorts 여부 판별 (60초 이하)"""
    duration = item.get("contentDetails", {}).get("duration", "")
    # PT1M = 1분, PT30S = 30초 등
    if "H" in duration:
        return False
    if "M" in duration:
        try:
            minutes = int(duration.split("PT")[1].split("M")[0])
            return minutes <= 1
        except Exception:
            return False
    return True  # 분 단위 없으면 60초 이하


def run():
    if not YT_API_KEY:
        log.error("YOUTUBE_API_KEY 없음")
        return 0

    service = build("youtube", "v3", developerKey=YT_API_KEY)
    total_new = 0

    for region in REGIONS:
        code     = region["code"]
        platform = region["platform"]
        label    = region["label"]

        # 카테고리별 수집 + 전체 트렌딩도 수집
        targets = CATEGORY_IDS + [""]  # 빈 문자열 = 전체 카테고리

        seen_ids = set()  # 중복 방지

        for cat_id in targets:
            cat_label = {
                "23": "엔터테인먼트",
                "34": "코미디",
                "":   "전체 트렌딩",
            }.get(cat_id, cat_id)

            log.info(f"수집: {label} / {cat_label}")
            items = fetch_trending(service, code, cat_id)
            log.info(f"  → {len(items)}건")

            for item in items:
                video_id = item["id"]
                if video_id in seen_ids:
                    continue
                seen_ids.add(video_id)

                snippet    = item.get("snippet", {})
                statistics = item.get("statistics", {})

                title      = snippet.get("title", "")
                channel    = snippet.get("channelTitle", "")
                thumbnail  = snippet.get("thumbnails", {}).get("high", {}).get("url", "")
                published  = snippet.get("publishedAt", "")
                view_count = int(statistics.get("viewCount", 0))
                like_count = int(statistics.get("likeCount", 0))
                comment_count = int(statistics.get("commentCount", 0))

                # 조회수 너무 낮으면 스킵
                if view_count < 10000:
                    continue

                # Shorts vs 일반 영상 구분
                video_type = "shorts" if is_short(item) else "video"
                url = (
                    f"https://www.youtube.com/shorts/{video_id}"
                    if video_type == "shorts"
                    else f"https://www.youtube.com/watch?v={video_id}"
                )

                saved = save_meme(
                    title=title,
                    url=url,
                    source="youtube",
                    platform=platform,
                    image_url=thumbnail,
                    view_count=view_count,
                    like_count=like_count,
                    comment_count=comment_count,
                    extra={
                        "video_id":    video_id,
                        "channel":     channel,
                        "published_at": published,
                        "region":      code,
                        "category_id": cat_id,
                        "video_type":  video_type,
                    },
                )
                if saved:
                    total_new += 1

    log.info(f"YouTube 트렌딩 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
