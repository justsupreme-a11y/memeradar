"""
Know Your Meme 크롤러
- 대상: kym.com 트렌딩 + 최신 밈 (사람이 검증한 밈 DB)
- 방식: requests + BeautifulSoup
- API 키 불필요
- 특징: "이게 밈인가" 검증이 이미 되어있음
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme

logging.basicConfig(level=logging.INFO, format="%(asctime)s [kym] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

BASE_URL = "https://knowyourmeme.com"

PAGES = [
    {"url": f"{BASE_URL}/memes/trending", "label": "트렌딩"},
    {"url": f"{BASE_URL}/memes",          "label": "최신"},
]


def fetch_meme_list(url: str) -> list[dict]:
    """KYM 밈 목록 파싱"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning(f"요청 실패 {url}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    memes = []

    for item in soup.select("table.entry-grid-body td, .entry-grid-body .cell"):
        title_el = item.select_one("h2 a, .entry-title a")
        img_el   = item.select_one("img")
        views_el = item.select_one(".views, .view-count")
        status_el = item.select_one(".status, .meme-status")

        if not title_el:
            continue

        href = title_el.get("href", "")
        if not href.startswith("/"):
            continue

        # 확인됨(Confirmed) 상태만 수집 — Draft/Researching 제외
        status = status_el.text.strip().lower() if status_el else ""
        if status and "confirmed" not in status and "submission" not in status:
            continue

        image_url = ""
        if img_el:
            image_url = img_el.get("data-src") or img_el.get("src") or ""
            if image_url.startswith("//"):
                image_url = "https:" + image_url

        views = 0
        if views_el:
            try:
                views = int(views_el.text.strip().replace(",", "").replace("K", "000").replace("M", "000000"))
            except Exception:
                pass

        memes.append({
            "title":     title_el.text.strip(),
            "url":       BASE_URL + href,
            "image_url": image_url,
            "views":     views,
            "status":    status,
        })

    return memes


def fetch_meme_detail(url: str) -> dict:
    """밈 상세 페이지에서 추가 정보 파싱"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        # 기원 설명
        origin_el = soup.select_one("#origin p, .body-copy p")
        origin    = origin_el.text.strip()[:200] if origin_el else ""

        # 태그
        tags = [t.text.strip() for t in soup.select(".tag a")][:5]

        # 조회수
        views_el = soup.select_one(".views-count, #views-count")
        views = 0
        if views_el:
            try:
                views = int(views_el.text.strip().replace(",", ""))
            except Exception:
                pass

        return {"origin": origin, "tags": tags, "views": views}
    except Exception:
        return {}


def run():
    total_new = 0

    for page_cfg in PAGES:
        url   = page_cfg["url"]
        label = page_cfg["label"]
        log.info(f"수집: KYM {label} ({url})")

        memes = fetch_meme_list(url)
        log.info(f"  → {len(memes)}건 발견")

        for meme in memes:
            # 상세 페이지 추가 정보
            detail = fetch_meme_detail(meme["url"])
            views  = detail.get("views") or meme["views"]

            saved = save_meme(
                title=meme["title"],
                url=meme["url"],
                source="knowyourmeme",
                platform="global",
                image_url=meme["image_url"],
                view_count=views,
                extra={
                    "status": meme["status"],
                    "tags":   detail.get("tags", []),
                    "origin": detail.get("origin", ""),
                },
            )
            if saved:
                total_new += 1

            time.sleep(random.uniform(1.5, 3.0))

        time.sleep(random.uniform(2.0, 4.0))

    log.info(f"Know Your Meme 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
