"""
Wikipedia 신규 등재 크롤러
- 대상: 영문 위키피디아 최근 생성 문서 중 밈/문화 관련
- 밈이 위키피디아에 등재 = 글로벌 공식화 신호
- 방식: Wikipedia API (무료 · 공식)
"""

import time
import logging
import requests
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [wikipedia] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "meme-radar/1.0 (personal research project)",
}

# Wikipedia API 엔드포인트
API_URL = "https://en.wikipedia.org/w/api.php"

# 밈/트렌드 관련 카테고리
MEME_CATEGORIES = [
    "Internet memes",
    "Internet memes introduced in 2025",
    "Internet memes introduced in 2024",
    "Viral videos",
    "TikTok",
]


def fetch_recent_new_pages() -> list[dict]:
    """최근 24시간 내 생성된 문서 중 밈 관련"""
    params = {
        "action":   "query",
        "list":     "recentchanges",
        "rctype":   "new",          # 새로 생성된 문서만
        "rcnamespace": 0,           # 일반 문서만 (토크/사용자 페이지 제외)
        "rclimit":  100,
        "rcprop":   "title|timestamp|ids",
        "format":   "json",
    }

    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        changes = resp.json().get("query", {}).get("recentchanges", [])
        return changes
    except Exception as e:
        log.warning(f"Wikipedia 최근 변경 실패: {e}")
        return []


def fetch_category_members(category: str) -> list[dict]:
    """특정 카테고리의 최신 문서"""
    params = {
        "action":  "query",
        "list":    "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": 20,
        "cmsort":  "timestamp",
        "cmdir":   "desc",
        "cmprop":  "title|timestamp",
        "format":  "json",
    }

    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        members = resp.json().get("query", {}).get("categorymembers", [])
        return members
    except Exception as e:
        log.warning(f"Wikipedia 카테고리 {category} 실패: {e}")
        return []


def fetch_page_summary(title: str) -> dict:
    """문서 요약 정보 (첫 문단 + 이미지)"""
    try:
        resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "extract":   data.get("extract", "")[:200],
            "image_url": data.get("thumbnail", {}).get("source", ""),
        }
    except Exception:
        return {}


def is_meme_related(title: str) -> bool:
    """밈/트렌드 관련 문서인지 1차 필터링"""
    meme_keywords = [
        "meme", "viral", "trend", "internet", "slang",
        "tiktok", "youtube", "twitter", "reddit",
        "challenge", "dance", "song", "catchphrase",
    ]
    title_lower = title.lower()
    return any(kw in title_lower for kw in meme_keywords)


def run():
    total_new = 0

    # 1. 밈 카테고리별 최신 등재 문서
    for category in MEME_CATEGORIES:
        log.info(f"수집: Wikipedia 카테고리 '{category}'")
        members = fetch_category_members(category)
        log.info(f"  → {len(members)}건")

        for member in members:
            title = member.get("title", "")
            if not title:
                continue

            summary   = fetch_page_summary(title)
            category_ = classify_category(title)

            saved = save_meme(
                title=title,
                url=f"https://en.wikipedia.org/wiki/{requests.utils.quote(title.replace(' ', '_'))}",
                source="wikipedia",
                platform="global",
                image_url=summary.get("image_url", ""),
                category=category_,
                extra={
                    "wiki_category": category,
                    "extract":       summary.get("extract", ""),
                },
            )
            if saved:
                total_new += 1

            time.sleep(0.5)

        time.sleep(2)

    # 2. 최근 24시간 신규 등재 중 밈 관련
    log.info("수집: Wikipedia 최근 신규 등재")
    recent = fetch_recent_new_pages()
    log.info(f"  → {len(recent)}건 중 밈 관련 필터링")

    for page in recent:
        title = page.get("title", "")
        if not title or not is_meme_related(title):
            continue

        summary   = fetch_page_summary(title)
        category_ = classify_category(title)

        saved = save_meme(
            title=title,
            url=f"https://en.wikipedia.org/wiki/{requests.utils.quote(title.replace(' ', '_'))}",
            source="wikipedia",
            platform="global",
            image_url=summary.get("image_url", ""),
            category=category_,
            extra={
                "type":    "new_page",
                "extract": summary.get("extract", ""),
            },
        )
        if saved:
            total_new += 1

        time.sleep(0.5)

    log.info(f"Wikipedia 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
