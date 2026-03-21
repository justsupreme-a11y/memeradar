import os
import math
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [yt_trending] %(message)s")
log = logging.getLogger(__name__)

YT_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

REGIONS = [
    {"code": "KR", "platform": "domestic", "label": "국내 급상승"},
    {"code": "US", "platform": "global",   "label": "해외 급상승"},
]

# YouTube videoCategoryId
# 0=all, 10=Music, 17=Sports, 20=Gaming, 22=People & Blogs, 23=Comedy, 24=Entertainment
TREND_CATEGORIES = [
    {"id": "0",  "name": "all",           "weight": 1.00},
    {"id": "24", "name": "entertainment", "weight": 1.15},
    {"id": "23", "name": "comedy",        "weight": 1.15},
    {"id": "22", "name": "people",        "weight": 1.08},
    {"id": "10", "name": "music",         "weight": 1.00},
    {"id": "20", "name": "gaming",        "weight": 0.95},
    {"id": "17", "name": "sports",        "weight": 0.90},
]

# 워크맨 제외
# 채널 ID는 필요시 운영 중 교체
MEME_CHANNELS = [
    # 해외
    {"id": "UCHRFMBxHOhqBjrVnZHKmGlA", "name": "Know Your Meme",      "platform": "global"},
    {"id": "UCpko_-a4wgz2u_DgDgd9fqA", "name": "Daily Dose of Memes", "platform": "global"},

    # 국내
    {"id": "UCQ2KSP4dUBMoNpnnNRjT5LA", "name": "피식대학", "platform": "domestic"},
    {"id": "UCK4s70-bFSFMVVdDTMKnorg", "name": "숏박스",   "platform": "domestic"},
    {"id": "UCM2PEMvNjFOPMhBJJrCEBzA", "name": "침착맨",   "platform": "domestic"},
    {"id": "UCuPDTBDvDpXciCBJsQNRSOQ", "name": "젼언니",   "platform": "domestic"},
]

TREND_MAX_RESULTS = 20
CHANNEL_LOOKBACK_HOURS = 72
MAX_SAVE_PER_REGION = 60
MAX_SAVE_CHANNELS = 80


def build_service():
    return build("youtube", "v3", developerKey=YT_API_KEY, cache_discovery=False)


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(iso_str: str | None) -> datetime | None:
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except Exception:
        return None


def execute_request(req, label: str, default=None):
    try:
        return req.execute()
    except HttpError as e:
        status = getattr(e.resp, "status", "unknown")
        try:
            detail = e.content.decode("utf-8", errors="ignore")[:500]
        except Exception:
            detail = str(e)
        log.warning(f"{label} HttpError status={status}: {detail}")
        return {} if default is None else default
    except Exception as e:
        log.warning(f"{label} error: {e}")
        return {} if default is None else default


def iso_duration_to_seconds(duration: str | None) -> int:
    """
    ISO8601 duration parser
    e.g. PT59S, PT1M2S, PT2M, PT1H3M4S
    """
    import re

    if not duration:
        return 0

    pattern = re.compile(
        r"^P"
        r"(?:(?P<days>\d+)D)?"
        r"(?:T"
        r"(?:(?P<hours>\d+)H)?"
        r"(?:(?P<minutes>\d+)M)?"
        r"(?:(?P<seconds>\d+)S)?"
        r")?$"
    )
    m = pattern.match(duration)
    if not m:
        return 0

    days = safe_int(m.group("days"))
    hours = safe_int(m.group("hours"))
    minutes = safe_int(m.group("minutes"))
    seconds = safe_int(m.group("seconds"))

    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def get_thumbnail(snippet: dict) -> str:
    thumbs = snippet.get("thumbnails", {}) or {}
    return (
        thumbs.get("maxres", {}).get("url")
        or thumbs.get("standard", {}).get("url")
        or thumbs.get("high", {}).get("url")
        or thumbs.get("medium", {}).get("url")
        or thumbs.get("default", {}).get("url")
        or ""
    )


def detect_shorts(item: dict) -> bool:
    """
    공식 Shorts 전용 플래그가 YouTube Data API v3에서 직접 오지 않으므로
    60초 이하 + 제목/설명 힌트로 판단
    """
    snippet = item.get("snippet", {}) or {}
    content = item.get("contentDetails", {}) or {}

    title = (snippet.get("title") or "").lower()
    desc = (snippet.get("description") or "").lower()
    duration_sec = iso_duration_to_seconds(content.get("duration"))

    if duration_sec == 0 or duration_sec > 60:
        return False

    if "#shorts" in title or "#shorts" in desc:
        return True
    if "shorts" in title or "쇼츠" in title:
        return True

    return True


def calc_hours_since_published(item: dict) -> float:
    snippet = item.get("snippet", {}) or {}
    published_at = parse_dt(snippet.get("publishedAt"))
    if not published_at:
        return 9999.0
    delta = now_utc() - published_at
    return max(delta.total_seconds() / 3600.0, 1.0)


def calc_hype_score(
    item: dict,
    *,
    category_weight: float = 1.0,
    source_weight: float = 1.0,
) -> float:
    """
    조회수 절대값보다 '지금 뜨는 정도'를 보기 위한 점수
    """
    stats = item.get("statistics", {}) or {}
    views = safe_int(stats.get("viewCount"))
    likes = safe_int(stats.get("likeCount"))
    comments = safe_int(stats.get("commentCount"))
    hours = calc_hours_since_published(item)
    is_shorts = detect_shorts(item)

    # 너무 큰 채널/누적 영상 쏠림 완화 위해 로그 스케일
    view_signal = math.log10(max(views, 1))
    like_signal = math.log10(max(likes + 1, 1))
    comment_signal = math.log10(max(comments + 1, 1))

    freshness = 1.0 / math.sqrt(max(hours, 1.0))
    shorts_bonus = 1.12 if is_shorts else 1.0

    score = (
        (view_signal * 0.55)
        + (like_signal * 0.20)
        + (comment_signal * 0.25)
    ) * freshness * category_weight * source_weight * shorts_bonus

    return round(score, 6)


def fetch_trending_by_category(service, region_code: str, category_id: str, max_results: int = TREND_MAX_RESULTS) -> list[dict]:
    resp = execute_request(
        service.videos().list(
            part="snippet,statistics,contentDetails",
            chart="mostPopular",
            regionCode=region_code,
            videoCategoryId=category_id,
            maxResults=max_results,
        ),
        label=f"videos.list mostPopular region={region_code} category={category_id}",
        default={},
    )
    return resp.get("items", [])


def fetch_channel_uploads_playlist_id(service, channel_id: str) -> str:
    resp = execute_request(
        service.channels().list(
            part="contentDetails",
            id=channel_id,
            maxResults=1,
        ),
        label=f"channels.list channel={channel_id}",
        default={},
    )

    items = resp.get("items", [])
    if not items:
        return ""

    return (
        items[0]
        .get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads", "")
    )


def fetch_playlist_video_ids(service, playlist_id: str, max_pages: int = 2) -> list[str]:
    video_ids: list[str] = []
    next_page_token = None

    for _ in range(max_pages):
        resp = execute_request(
            service.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token,
            ),
            label=f"playlistItems.list playlist={playlist_id}",
            default={},
        )

        for item in resp.get("items", []):
            vid = item.get("contentDetails", {}).get("videoId")
            if vid:
                video_ids.append(vid)

        next_page_token = resp.get("nextPageToken")
        if not next_page_token:
            break

    seen = set()
    deduped = []
    for vid in video_ids:
        if vid not in seen:
            seen.add(vid)
            deduped.append(vid)

    return deduped


def fetch_videos_by_ids(service, video_ids: list[str]) -> list[dict]:
    if not video_ids:
        return []

    result = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        resp = execute_request(
            service.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(chunk),
                maxResults=len(chunk),
            ),
            label="videos.list by ids",
            default={},
        )
        result.extend(resp.get("items", []))
    return result


def parse_video(
    item: dict,
    platform: str,
    source: str,
    *,
    trend_category: str | None = None,
    category_weight: float = 1.0,
    source_weight: float = 1.0,
    channel_name: str | None = None,
) -> dict:
    snippet = item.get("snippet", {}) or {}
    stats = item.get("statistics", {}) or {}
    content = item.get("contentDetails", {}) or {}

    raw_id = item.get("id", "")
    if isinstance(raw_id, dict):
        video_id = raw_id.get("videoId", "")
    else:
        video_id = raw_id

    title = snippet.get("title", "")
    duration = content.get("duration", "")
    duration_sec = iso_duration_to_seconds(duration)
    hype_score = calc_hype_score(
        item,
        category_weight=category_weight,
        source_weight=source_weight,
    )

    return {
        "title": title,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "image_url": get_thumbnail(snippet),
        "view_count": safe_int(stats.get("viewCount")),
        "like_count": safe_int(stats.get("likeCount")),
        "comment_count": safe_int(stats.get("commentCount")),
        "platform": platform,
        "source": source,
        "category": classify_category(title),
        "extra": {
            "video_id": video_id,
            "channel": snippet.get("channelTitle", ""),
            "channel_name": channel_name or snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "duration": duration,
            "duration_sec": duration_sec,
            "content_type": "shorts" if detect_shorts(item) else "video",
            "trend_category": trend_category,
            "hype_score": hype_score,
        },
    }


def dedupe_ranked(items: list[dict]) -> list[dict]:
    best_by_video_id: dict[str, dict] = {}

    for item in items:
        video_id = item.get("extra", {}).get("video_id", "")
        if not video_id:
            continue

        prev = best_by_video_id.get(video_id)
        if not prev:
            best_by_video_id[video_id] = item
            continue

        prev_score = prev.get("extra", {}).get("hype_score", 0)
        curr_score = item.get("extra", {}).get("hype_score", 0)
        if curr_score > prev_score:
            best_by_video_id[video_id] = item

    ranked = list(best_by_video_id.values())
    ranked.sort(key=lambda x: x.get("extra", {}).get("hype_score", 0), reverse=True)
    return ranked


def collect_region_hype(service, region: dict) -> list[dict]:
    collected: list[dict] = []

    for cat in TREND_CATEGORIES:
        log.info(f"수집: {region['label']} / {cat['name']}")
        videos = fetch_trending_by_category(service, region["code"], cat["id"], TREND_MAX_RESULTS)
        log.info(f"  → {len(videos)}건")

        for v in videos:
            data = parse_video(
                v,
                region["platform"],
                "youtube_trending_hype",
                trend_category=cat["name"],
                category_weight=cat["weight"],
                source_weight=1.0,
            )
            collected.append(data)

    ranked = dedupe_ranked(collected)
    return ranked[:MAX_SAVE_PER_REGION]


def collect_channel_hype(service) -> list[dict]:
    threshold = now_utc() - timedelta(hours=CHANNEL_LOOKBACK_HOURS)
    collected: list[dict] = []

    for channel in MEME_CHANNELS:
        log.info(f"수집: {channel['name']}")

        uploads_playlist_id = fetch_channel_uploads_playlist_id(service, channel["id"])
        if not uploads_playlist_id:
            log.warning(f"채널 uploads playlist 조회 실패: {channel['name']} ({channel['id']})")
            continue

        candidate_ids = fetch_playlist_video_ids(service, uploads_playlist_id, max_pages=2)
        if not candidate_ids:
            log.info(f"  → 0건")
            continue

        videos = fetch_videos_by_ids(service, candidate_ids)
        kept = 0

        for v in videos:
            published_at = parse_dt((v.get("snippet", {}) or {}).get("publishedAt"))
            if not published_at or published_at < threshold:
                continue

            data = parse_video(
                v,
                channel["platform"],
                "youtube_channel_hype",
                trend_category="channel_watch",
                category_weight=1.05,
                source_weight=1.08,
                channel_name=channel["name"],
            )
            collected.append(data)
            kept += 1

        log.info(f"  → {kept}건")

    ranked = dedupe_ranked(collected)
    return ranked[:MAX_SAVE_CHANNELS]


def save_items(items: list[dict]) -> int:
    total_new = 0

    for item in items:
        saved = save_meme(
            title=item["title"],
            url=item["url"],
            source=item["source"],
            platform=item["platform"],
            image_url=item["image_url"],
            view_count=item["view_count"],
            like_count=item["like_count"],
            comment_count=item["comment_count"],
            category=item["category"],
            extra=item["extra"],
        )
        if saved:
            total_new += 1

    return total_new


def run():
    if not YT_API_KEY:
        log.error("YOUTUBE_API_KEY 없음")
        return 0

    service = build_service()
    total_new = 0

    # 1. KR / US 급상승 hype 수집
    region_items: list[dict] = []
    for region in REGIONS:
        items = collect_region_hype(service, region)
        log.info(f"{region['label']} 최종 후보 → {len(items)}건")
        region_items.extend(items)

    new_region = save_items(region_items)
    total_new += new_region
    log.info(f"지역 급상승 저장 완료 → 신규 {new_region}건")

    # 2. 밈/유머 채널 최근 업로드 수집
    channel_items = collect_channel_hype(service)
    new_channel = save_items(channel_items)
    total_new += new_channel
    log.info(f"채널 watch 저장 완료 → 신규 {new_channel}건")

    log.info(f"YouTube 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
