"""
X (Twitter) 트렌딩 크롤러
- 방식: requests로 공개 트렌딩 API 파싱 (API 키 불필요)
- 대상: 한국 + 글로벌 트렌딩 해시태그
- 트위터 트렌딩은 Nitter 퍼블릭 인스턴스로 파싱
"""

import time
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme

logging.basicConfig(level=logging.INFO, format="%(asctime)s [x_trends] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

# Nitter 퍼블릭 인스턴스 (트위터 미러 · API 없이 접근 가능)
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.cz",
]

# 한국 밈 관련 트위터 검색 키워드
KR_SEARCH_QUERIES = [
    {"q": "lang:ko min_faves:500 짤",     "platform": "domestic"},
    {"q": "lang:ko min_faves:500 밈",     "platform": "domestic"},
    {"q": "lang:ko min_faves:1000 유행",  "platform": "domestic"},
    {"q": "lang:ko min_faves:500 레전드", "platform": "domestic"},
]

GLOBAL_SEARCH_QUERIES = [
    {"q": "meme min_faves:5000",       "platform": "global"},
    {"q": "#meme min_faves:3000",      "platform": "global"},
    {"q": "viral meme min_faves:3000", "platform": "global"},
]


def fetch_nitter_search(instance: str, query: str) -> list[dict]:
    """Nitter에서 검색 결과 파싱"""
    url = f"{instance}/search?f=tweets&q={requests.utils.quote(query)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        for tweet in soup.select(".timeline-item"):
            content_el = tweet.select_one(".tweet-content")
            link_el    = tweet.select_one(".tweet-link")
            stats      = tweet.select_one(".tweet-stats")

            if not content_el or not link_el:
                continue

            text = content_el.text.strip()
            href = link_el.get("href", "")
            url_full = f"https://x.com{href}" if href.startswith("/") else href

            # 좋아요 수 파싱
            likes = 0
            if stats:
                for stat in stats.select(".icon-container"):
                    txt = stat.text.strip().replace(",", "")
                    if txt.isdigit():
                        likes = max(likes, int(txt))

            results.append({
                "title":  text[:100],
                "url":    url_full,
                "likes":  likes,
            })

        return results
    except Exception as e:
        log.warning(f"Nitter {instance} 실패: {e}")
        return []


def get_working_instance() -> str:
    """살아있는 Nitter 인스턴스 찾기"""
    for inst in NITTER_INSTANCES:
        try:
            resp = requests.get(inst, timeout=5)
            if resp.status_code == 200:
                log.info(f"Nitter 인스턴스 사용: {inst}")
                return inst
        except Exception:
            continue
    return ""


def run():
    total_new = 0

    instance = get_working_instance()
    if not instance:
        log.warning("살아있는 Nitter 인스턴스 없음 — X 트렌딩 스킵")
        return 0

    all_queries = KR_SEARCH_QUERIES + GLOBAL_SEARCH_QUERIES

    for query_cfg in all_queries:
        q        = query_cfg["q"]
        platform = query_cfg["platform"]
        log.info(f"검색: '{q}' ({platform})")

        tweets = fetch_nitter_search(instance, q)
        log.info(f"  → {len(tweets)}건")

        for t in tweets:
            if t["likes"] < 100:
                continue

            saved = save_meme(
                title=t["title"],
                url=t["url"],
                source="x_trends",
                platform=platform,
                like_count=t["likes"],
                view_count=t["likes"] * 10,  # 좋아요 기반 조회수 추정
                extra={"query": q, "likes": t["likes"]},
            )
            if saved:
                total_new += 1

        time.sleep(2)

    log.info(f"X 트렌딩 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
