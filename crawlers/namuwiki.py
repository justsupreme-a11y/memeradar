"""
나무위키 크롤러 v2
- 나무위키 공식 API 사용 (차단 없음)
- https://api.namu.wiki 공개 엔드포인트
"""

import time
import logging
import requests
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [namuwiki] %(message)s")
log = logging.getLogger(__name__)

API_BASE = "https://api.namu.wiki"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 밈/트렌드 관련 필터링
SKIP_PREFIXES = ["나무위키:", "위키:", "분류:", "틀:", "파일:", "사용자:"]


def is_meme_related(title: str) -> bool:
    for prefix in SKIP_PREFIXES:
        if title.startswith(prefix):
            return False
    if len(title) < 2:
        return False
    return True


def fetch_recent_changes() -> list[dict]:
    """최근 변경 문서 API"""
    try:
        resp = requests.get(
            f"{API_BASE}/v1/recentchanges",
            headers=HEADERS,
            timeout=10,
            params={"limit": 50}
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("items", [])
    except Exception as e:
        log.warning(f"나무위키 최근 변경 API 실패: {e}")
        # API 실패 시 웹 페이지 직접 파싱 시도
        return fetch_recent_changes_web()


def fetch_recent_changes_web() -> list[dict]:
    """웹 페이지 직접 파싱 (API 실패 시 폴백)"""
    try:
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        resp = requests.get("https://namu.wiki/RecentChanges", headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for link in soup.select("a[href^='/w/']")[:50]:
            title = link.text.strip()
            href = link.get("href", "")
            if title and href and is_meme_related(title):
                results.append({"title": title, "href": href})
        return results
    except Exception as e:
        log.warning(f"나무위키 웹 파싱도 실패: {e}")
        return []


def fetch_popular() -> list[dict]:
    """인기 문서 API"""
    try:
        resp = requests.get(
            f"{API_BASE}/v1/popular",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("items", [])
    except Exception as e:
        log.warning(f"나무위키 인기 문서 API 실패: {e}")
        return []


def run():
    total_new = 0
    BASE_URL = "https://namu.wiki"

    # 최근 변경
    log.info("나무위키 최근 변경 수집")
    recent = fetch_recent_changes()
    log.info(f"  → {len(recent)}건")

    for doc in recent:
        title = doc.get("title") or doc.get("name") or ""
        href  = doc.get("href") or doc.get("link") or f"/w/{title}"
        if not title or not is_meme_related(title):
            continue

        category = classify_category(title)
        saved = save_meme(
            title=title,
            url=BASE_URL + href if href.startswith("/") else href,
            source="namuwiki",
            platform="domestic",
            category=category,
            extra={"type": "recent_change"},
        )
        if saved:
            total_new += 1
        time.sleep(0.3)

    # 인기 문서
    log.info("나무위키 인기 문서 수집")
    popular = fetch_popular()
    log.info(f"  → {len(popular)}건")

    for doc in popular:
        title = doc.get("title") or doc.get("name") or ""
        href  = doc.get("href") or doc.get("link") or f"/w/{title}"
        if not title or not is_meme_related(title):
            continue

        category = classify_category(title)
        saved = save_meme(
            title=title,
            url=BASE_URL + href if href.startswith("/") else href,
            source="namuwiki",
            platform="domestic",
            category=category,
            extra={"type": "popular"},
        )
        if saved:
            total_new += 1
        time.sleep(0.3)

    log.info(f"나무위키 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
