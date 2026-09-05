"""
레딧 크롤러 v1
- 공식 Reddit API(PRAW) 사용 — 과거 무인증 스크래핑으로 시도했다가 403 전체 차단당한 것과
  다르게, OAuth 등록된 read-only 앱으로 접근하므로 안정적으로 동작함
- 무료 티어: 분당 60회 요청 (여기서는 서브레딧당 1회 hot() 호출만 쓰므로 여유 충분)
- score(추천수) + num_comments 기준으로 필터링해 "바이럴 급"만 수집
"""

import os
import time
import random
import logging

import praw
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [reddit] %(message)s")
log = logging.getLogger(__name__)

REDDIT_CLIENT_ID     = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT    = os.environ.get("REDDIT_USER_AGENT", "memeradar-crawler/1.0")

# 국내 밈의 역수출 흐름 추적용 서브 + 글로벌 밈 흐름 비교용 서브를 같이 둠
SUBREDDITS = [
    {"name": "memes",      "label": "memes (글로벌 일반)"},
    {"name": "dankmemes",  "label": "dankmemes (글로벌 하드코어)"},
    {"name": "196",        "label": "196 (글로벌 서브컬처)"},
    {"name": "korea",      "label": "korea (한국 관련 역수출 추적)"},
    {"name": "kpopmemes",  "label": "kpopmemes (K-pop 밈 역수출 추적)"},
]

POST_LIMIT   = 25
MIN_SCORE    = 300
MIN_COMMENTS = 30

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".gifv", ".webp")

def get_reddit() -> "praw.Reddit | None":
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        log.warning("REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET 미설정 — 스킵")
        return None
    try:
        # username/password 없이도 read-only 모드로 공개 데이터 조회 가능
        return praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
    except Exception as e:
        log.error(f"Reddit 클라이언트 초기화 실패: {e}")
        return None


def extract_image_url(post) -> str:
    try:
        url = getattr(post, "url", "") or ""
        if url.lower().endswith(IMAGE_EXTS):
            return url
        thumb = getattr(post, "thumbnail", "") or ""
        if thumb.startswith("http"):
            return thumb
    except Exception:
        pass
    return ""

def fetch_subreddit(reddit: "praw.Reddit", name: str, label: str) -> list[dict]:
    try:
        sub = reddit.subreddit(name)
        posts = []
        for post in sub.hot(limit=POST_LIMIT):
            if getattr(post, "stickied", False):
                continue

            title = (post.title or "").strip()
            if not title or len(title) < 2:
                continue

            score    = int(getattr(post, "score", 0) or 0)
            comments = int(getattr(post, "num_comments", 0) or 0)

            if score < MIN_SCORE and comments < MIN_COMMENTS:
                continue

            posts.append({
                "title":         title,
                "url":           f"https://reddit.com{post.permalink}",
                "image_url":     extract_image_url(post),
                "like_count":    score,
                "comment_count": comments,
            })

        return posts

    except Exception as e:
        log.warning(f"레딧 r/{name} 실패: {e}")
        return []

def run():
    total_new = 0

    reddit = get_reddit()
    if reddit is None:
        return 0

    for sub in SUBREDDITS:
        log.info(f"수집: 레딧 {sub['label']}")
        posts = fetch_subreddit(reddit, sub["name"], sub["label"])
        log.info(f"  → {len(posts)}건 (필터 후)")

        for post in posts:
            category = classify_category(post["title"])
            saved = save_meme(
                title=post["title"],
                url=post["url"],
                source="reddit",
                platform="global",
                image_url=post["image_url"],
                like_count=post["like_count"],
                comment_count=post["comment_count"],
                category=category,
                extra={"subreddit": sub["name"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(1.5, 3.0))

    log.info(f"레딧 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
