"""
나무위키 크롤러
- 대상: 최근 변경된 문서 + 인기 문서
- 밈/유행어/인물 관련 문서 필터링
- API 불필요
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [namuwiki] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

BASE_URL = "https://namu.wiki"

# 밈/트렌드 관련 분류 키워드
MEME_CATEGORIES = [
    "유행어", "인터넷 밈", "신조어", "짤방", "드립",
    "음식", "패션", "연예인", "아이돌", "유튜버",
]

PAGES = [
    {"url": f"{BASE_URL}/RecentChanges",     "label": "최근 변경"},
    {"url": f"{BASE_URL}/w/%EB%82%98%EB%AC%B4%EC%9C%84%ED%82%A4:%EC%9D%B8%EA%B8%B0%EB%AC%B8%EC%84%9C", "label": "인기 문서"},
]


def is_meme_related(title: str) -> bool:
    """밈/트렌드 관련 문서인지 판별"""
    skip_prefixes = ["나무위키:", "위키:", "분류:", "틀:", "파일:"]
    for prefix in skip_prefixes:
        if title.startswith(prefix):
            return False

    # 너무 짧거나 일반적인 제목 스킵
    if len(title) < 2:
        return False

    return True


def fetch_recent_changes() -> list[dict]:
    """최근 변경 문서 수집"""
    try:
        resp = requests.get(f"{BASE_URL}/RecentChanges", headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        for link in soup.select("a[href^='/w/']")[:50]:
            title = link.text.strip()
            href  = link.get("href", "")
            if not title or not href or not is_meme_related(title):
                continue
            results.append({
                "title": title,
                "url":   BASE_URL + href,
            })
        return results
    except Exception as e:
        log.warning(f"최근 변경 수집 실패: {e}")
        return []


def fetch_popular_docs() -> list[dict]:
    """인기 문서 수집"""
    try:
        resp = requests.get(
            f"{BASE_URL}/w/%EB%82%98%EB%AC%B4%EC%9C%84%ED%82%A4:%EC%9D%B8%EA%B8%B0%EB%AC%B8%EC%84%9C",
            headers=HEADERS, timeout=10
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        for link in soup.select("a[href^='/w/']")[:100]:
            title = link.text.strip()
            href  = link.get("href", "")
            if not title or not href or not is_meme_related(title):
                continue
            results.append({
                "title": title,
                "url":   BASE_URL + href,
            })
        return results
    except Exception as e:
        log.warning(f"인기 문서 수집 실패: {e}")
        return []


def run():
    total_new = 0

    log.info("나무위키 최근 변경 수집")
    recent = fetch_recent_changes()
    log.info(f"  → {len(recent)}건")

    for doc in recent:
        category = classify_category(doc["title"])
        saved = save_meme(
            title=doc["title"],
            url=doc["url"],
            source="namuwiki",
            platform="domestic",
            category=category,
            extra={"type": "recent_change"},
        )
        if saved:
            total_new += 1
        time.sleep(random.uniform(0.5, 1.0))

    log.info("나무위키 인기 문서 수집")
    popular = fetch_popular_docs()
    log.info(f"  → {len(popular)}건")

    for doc in popular:
        category = classify_category(doc["title"])
        saved = save_meme(
            title=doc["title"],
            url=doc["url"],
            source="namuwiki",
            platform="domestic",
            category=category,
            extra={"type": "popular"},
        )
        if saved:
            total_new += 1
        time.sleep(random.uniform(0.5, 1.0))

    log.info(f"나무위키 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
