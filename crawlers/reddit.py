"""
Reddit RSS 크롤러
- API 키 불필요 — Reddit 공개 JSON 엔드포인트 사용
- 대상: 글로벌 밈 원산지 + 한국 관련 서브레딧
"""

import time
import random
import logging
import requests
from utils.db import save_meme

logging.basicConfig(level=logging.INFO, format="%(asctime)s [reddit] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "meme-radar/1.0 (personal project)",
}

SUBREDDITS = [
    {"name": "memes",       "platform": "global"},
    {"name": "dankmemes",   "platform": "global"},
    {"name": "me_irl",      "platform": "global"},
    {"name": "funny",       "platform": "global"},
    {"name": "korea",       "platform": "global"},
    {"name": "koreanmemes", "platform": "global"},
]

LIMIT = 50


def fetch_subreddit(name: str) -> list[dict]:
    url = f"https://www.reddit.com/r/{name}/hot.json?limit={LIMIT}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json().get("data", {}).get("children", [])
    except Exception as e:
        log.warning(f"r/{name} 실패: {e}")
        return []


def run():
    total_new = 0

    for sr in SUBREDDITS:
        name     = sr["name"]
        platform = sr["platform"]
        log.info(f"수집: r/{name}")

        posts = fetch_subreddit(name)
        log.info(f"  → {len(posts)}건")

        for post in posts:
            d = post.get("data", {})
            if d.get("stickied") or d.get("score", 0) < 100:
                continue

            title     = d.get("title", "")
            permalink = d.get("permalink", "")
            score     = d.get("score", 0)
            comments  = d.get("num_comments", 0)
            ratio     = d.get("upvote_ratio", 0)
            post_url  = d.get("url", "")

            image_url = ""
            if any(post_url.endswith(e) for e in [".jpg",".jpeg",".png",".gif",".webp"]):
                image_url = post_url
            elif "preview" in d:
                try:
                    image_url = d["preview"]["images"][0]["source"]["url"].replace("&amp;","&")
                except Exception:
                    pass

            saved = save_meme(
                title=title,
                url=f"https://reddit.com{permalink}",
                source="reddit",
                platform=platform,
                image_url=image_url,
                view_count=score,
                like_count=score,
                comment_count=comments,
                extra={
                    "subreddit":    name,
                    "upvote_ratio": round(ratio, 2),
                    "flair":        d.get("link_flair_text") or "",
                },
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(2.0, 4.0))

    log.info(f"Reddit 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
