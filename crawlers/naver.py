"""
네이버 검색 API 크롤러
- API: 네이버 오픈 API (완전 무료 · 하루 25,000건)
- 발급: https://developers.naver.com/apps/#/register
- 대상: 카페·블로그에서 밈/짤 키워드 검색
"""

import os
import logging
import requests
from utils.db import save_meme

logging.basicConfig(level=logging.INFO, format="%(asctime)s [naver] %(message)s")
log = logging.getLogger(__name__)

NAVER_CLIENT_ID     = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")

SEARCH_URL = "https://openapi.naver.com/v1/search/{type}.json"

# 검색할 키워드 + 타입 조합
QUERIES = [
    {"keyword": "밈",       "type": "cafearticle"},
    {"keyword": "짤방",     "type": "cafearticle"},
    {"keyword": "유머짤",   "type": "cafearticle"},
    {"keyword": "밈",       "type": "blog"},
    {"keyword": "인터넷밈", "type": "blog"},
]

DISPLAY = 20  # 쿼리당 20건 (총 100건 · 하루 한도 여유)


def search(keyword: str, search_type: str) -> list[dict]:
    headers = {
        "X-Naver-Client-Id":     NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query":   keyword,
        "display": DISPLAY,
        "sort":    "date",  # 최신순
    }

    url = SEARCH_URL.format(type=search_type)
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("items", [])
    except Exception as e:
        log.warning(f"네이버 검색 실패 '{keyword}' ({search_type}): {e}")
        return []


def run():
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        log.error("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수 없음")
        return 0

    total_new = 0

    for q in QUERIES:
        keyword     = q["keyword"]
        search_type = q["type"]
        log.info(f"검색: '{keyword}' ({search_type})")

        items = search(keyword, search_type)
        log.info(f"  → {len(items)}건 발견")

        for item in items:
            # HTML 태그 제거
            title = item.get("title", "").replace("<b>", "").replace("</b>", "")
            url   = item.get("link") or item.get("url", "")

            if not title or not url:
                continue

            saved = save_meme(
                title=title,
                url=url,
                source="naver",
                platform="domestic",
                extra={
                    "type":        search_type,
                    "keyword":     keyword,
                    "description": item.get("description", "")[:200],
                    "cafe_name":   item.get("cafename", ""),
                    "pub_date":    item.get("postdate") or item.get("pubDate", ""),
                },
            )
            if saved:
                total_new += 1

    log.info(f"네이버 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
