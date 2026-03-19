"""
구글 트렌드 크롤러 v2
- pytrends → trendspyg 교체 (2025년 현재 작동)
- 한국 실시간 급상승 + 일간 트렌드
"""

import time
import logging
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [gtrends] %(message)s")
log = logging.getLogger(__name__)


def fetch_realtime_trends() -> list[str]:
    """한국 실시간 급상승 검색어"""
    try:
        from trendspy import Trends
        tr = Trends()
        results = tr.trending_now(geo="KR")
        keywords = []
        for item in results:
            if hasattr(item, 'keyword'):
                keywords.append(item.keyword)
            elif isinstance(item, str):
                keywords.append(item)
        return keywords[:20]
    except Exception as e:
        log.warning(f"trendspy 실시간 트렌드 실패: {e}")
        return []


def fetch_daily_trends() -> list[dict]:
    """일간 급상승 검색어 (상세 정보 포함)"""
    try:
        from trendspy import Trends
        tr = Trends()
        results = tr.trending_now_by_rss(geo="KR")
        items = []
        for item in results[:20]:
            kw = getattr(item, 'keyword', str(item))
            articles = []
            if hasattr(item, 'news_articles'):
                for art in (item.news_articles or [])[:3]:
                    articles.append({
                        "title": getattr(art, 'title', ''),
                        "url":   getattr(art, 'url', ''),
                        "source": "google_news",
                    })
            items.append({
                "keyword":  kw,
                "articles": articles,
            })
        return items
    except Exception as e:
        log.warning(f"trendspy 일간 트렌드 실패: {e}")
        return []


def run():
    total_new = 0

    # 1. 실시간 급상승
    log.info("구글 실시간 급상승 수집 중...")
    realtime = fetch_realtime_trends()
    log.info(f"  → {len(realtime)}건")

    for i, kw in enumerate(realtime):
        category = classify_category(kw)
        saved = save_meme(
            title=kw,
            url=f"https://trends.google.com/trends/explore?q={kw}&geo=KR",
            source="google_trends",
            platform="domestic",
            view_count=len(realtime) - i,  # 순위 역산
            category=category,
            extra={"type": "realtime", "rank": i + 1},
        )
        if saved:
            total_new += 1

    time.sleep(3)

    # 2. 일간 트렌드 (관련 기사 포함)
    log.info("구글 일간 트렌드 수집 중...")
    daily = fetch_daily_trends()
    log.info(f"  → {len(daily)}건")

    for item in daily:
        kw       = item["keyword"]
        articles = item["articles"]
        category = classify_category(kw)

        saved = save_meme(
            title=kw,
            url=f"https://trends.google.com/trends/explore?q={kw}&geo=KR",
            source="google_trends",
            platform="domestic",
            category=category,
            related_links=articles,  # 관련 기사 자동 연결!
            extra={"type": "daily"},
        )
        if saved:
            total_new += 1

        time.sleep(1)

    log.info(f"구글 트렌드 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
