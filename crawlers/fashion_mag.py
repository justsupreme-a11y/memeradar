"""
패션 매거진 통합 크롤러 v2
- 실제 URL 재확인 버전
- 하입비스트KR / GQ코리아 / 코스모폴리탄 / 보그코리아 / 엘르코리아
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [fashion_mag] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

MAGAZINES = [
    {
        "name":     "하입비스트 KR",
        "source":   "hypebeast",
        "urls":     ["https://hypebeast.kr/", "https://hypebeast.kr/footwear"],
        "selectors":["a.post-title", "h1 a", "h2 a", "h3 a", ".archive__item-title a"],
        "base":     "https://hypebeast.kr",
        "platform": "domestic",
    },
    {
        "name":     "하입비스트 EN",
        "source":   "hypebeast_en",
        "urls":     ["https://hypebeast.com/", "https://hypebeast.com/fashion"],
        "selectors":["a.post-title", "h1 a", "h2 a", "h3 a"],
        "base":     "https://hypebeast.com",
        "platform": "global",
    },
    {
        "name":     "GQ 코리아",
        "source":   "gqkorea",
        "urls":     ["https://www.gqkorea.co.kr/style/", "https://www.gqkorea.co.kr/culture/"],
        "selectors":[".entry-title a", "h2 a", "h3 a", ".post-title a", "article a"],
        "base":     "https://www.gqkorea.co.kr",
        "platform": "domestic",
    },
    {
        "name":     "코스모폴리탄",
        "source":   "cosmopolitan",
        "urls":     ["https://www.cosmopolitan.co.kr/fashion/", "https://www.cosmopolitan.co.kr/beauty/"],
        "selectors":[".article-title a", "h2 a", "h3 a", ".tit a", "a.title"],
        "base":     "https://www.cosmopolitan.co.kr",
        "platform": "domestic",
    },
    {
        "name":     "보그 코리아",
        "source":   "vogue",
        "urls":     ["https://www.vogue.co.kr/fashion/", "https://www.vogue.co.kr/beauty/"],
        "selectors":[".entry-title a", "h2 a", "h3 a", ".post-title a"],
        "base":     "https://www.vogue.co.kr",
        "platform": "domestic",
    },
    {
        "name":     "엘르 코리아",
        "source":   "elle",
        "urls":     ["https://www.elle.co.kr/fashion/", "https://www.elle.co.kr/beauty/"],
        "selectors":[".article-title a", "h2 a", "h3 a", ".tit a"],
        "base":     "https://www.elle.co.kr",
        "platform": "domestic",
    },
]


def fetch_magazine(mag: dict) -> list[dict]:
    items = []
    seen  = set()

    for url in mag["urls"]:
        try:
            headers = {**HEADERS, "Referer": mag["base"] + "/"}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for sel in mag["selectors"]:
                for el in soup.select(sel):
                    title = el.text.strip()
                    href  = el.get("href", "")
                    if not title or not href or href in seen:
                        continue
                    if len(title) < 5:
                        continue
                    if href in ("#", "/", mag["base"], mag["base"] + "/"):
                        continue
                    seen.add(href)

                    if not href.startswith("http"):
                        href = mag["base"] + href

                    img_el = el.find_previous("img") or el.find_next("img")
                    image_url = ""
                    if img_el:
                        image_url = img_el.get("src") or img_el.get("data-src") or ""
                        if image_url.startswith("//"):
                            image_url = "https:" + image_url

                    items.append({"title": title, "url": href, "image_url": image_url})

            time.sleep(random.uniform(1.0, 2.0))

        except Exception as e:
            log.warning(f"{mag['name']} {url} 실패: {e}")

    return items[:25]


def run():
    total_new = 0

    for mag in MAGAZINES:
        log.info(f"수집: {mag['name']}")
        items = fetch_magazine(mag)
        log.info(f"  → {len(items)}건")

        for item in items:
            category = classify_category(item["title"])
            if category == "general":
                category = "fashion"

            saved = save_meme(
                title=item["title"], url=item["url"],
                source=mag["source"], platform=mag["platform"],
                image_url=item["image_url"], category=category,
                extra={"magazine": mag["name"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(2.0, 4.0))

    log.info(f"패션 매거진 완료 — 신규 {total_new}건")
    return total_new

if __name__ == "__main__":
    run()
