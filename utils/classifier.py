"""
밈레이더 분류기 v2
- 흐름 분류: inflow / independent / export
- 생애주기: seed / spread / peak / fade
- 카테고리: fb / fashion / celeb / general (수집 시 이미 분류되지만 재분류 가능)
- 교차 검증: 실시간 검색어 소스와 동시에 언급되는 콘텐츠에 검증 배지 부여
"""

import logging
from datetime import datetime, timedelta, timezone
from utils.db import get_client
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [classifier] %(message)s")
log = logging.getLogger(__name__)

GLOBAL_SOURCES   = {"kym", "youtube_meme_ch"}
DOMESTIC_SOURCES = {"namuwiki", "instiz", "univ_tomorrow", "google_trends"}

# 교차 검증에 쓰는 키워드 풀 — 제목 자체가 순수 검색어인 소스만 사용.
# naver_datalab은 제목이 "{그룹명} (트렌드 {점수}점)" 형태로 그룹명이 너무
# 포괄적(예: "유행어", "바이럴")이라 오탐이 크므로 제외.
CROSS_VERIFY_SOURCES = {"google_trends", "naver_realtime"}
CROSS_VERIFY_LOOKBACK_HOURS = 48
MIN_KEYWORD_LEN = 2
MAX_MATCHED_TRENDS = 3


def classify_flow(meme: dict) -> str:
    source   = meme["source"]
    platform = meme.get("platform", "")

    if source in GLOBAL_SOURCES or platform == "global":
        return "inflow"

    if source in DOMESTIC_SOURCES or platform == "domestic":
        return "independent"

    return "independent"


def classify_lifecycle(meme: dict) -> str:
    collected_at = _parse_time(meme["collected_at"])
    now          = datetime.now(timezone.utc)
    hours_since  = (now - collected_at).total_seconds() / 3600
    view_count   = meme.get("view_count", 0) or 0

    if hours_since <= 24 and view_count < 1000:
        return "seed"
    elif hours_since <= 72 and view_count < 10000:
        return "spread"
    elif view_count >= 10000:
        return "peak"
    else:
        return "fade"


def _parse_time(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def get_active_trend_keywords(db, hours: int = CROSS_VERIFY_LOOKBACK_HOURS) -> list[str]:
    """최근 N시간 내 실시간 검색어 소스에서 수집된 순수 키워드 목록.

    구글 트렌드·네이버 실검은 title이 곧 검색어라 바로 매칭에 쓸 수 있음.
    """
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    try:
        resp = (
            db.table("memes")
            .select("title")
            .in_("source", list(CROSS_VERIFY_SOURCES))
            .gte("collected_at", since)
            .execute()
        )
    except Exception as e:
        log.warning(f"트렌드 키워드 조회 실패: {e}")
        return []

    keywords = {
        (row.get("title") or "").strip()
        for row in (resp.data or [])
        if len((row.get("title") or "").strip()) >= MIN_KEYWORD_LEN
    }
    # 긴 키워드부터 매칭 — 짧은 키워드가 긴 키워드의 부분 문자열이라 중복
    # 매칭되는 경우 더 구체적인 쪽을 우선 노출
    return sorted(keywords, key=len, reverse=True)


def find_matched_trends(title: str, keywords: list[str]) -> list[str]:
    if not title:
        return []
    matched = [kw for kw in keywords if kw and kw in title]
    return matched[:MAX_MATCHED_TRENDS]


def run():
    db = get_client()
    log.info("미분류 밈 조회 중...")

    resp = (
        db.table("memes")
        .select("*")
        .is_("flow_type", "null")
        .order("collected_at", desc=False)
        .limit(500)
        .execute()
    )
    memes = resp.data or []
    log.info(f"미분류 {len(memes)}건 처리 시작")

    if not memes:
        log.info("처리할 밈 없음")
        return 0

    trend_keywords = get_active_trend_keywords(db)
    log.info(f"교차 검증용 활성 검색어 {len(trend_keywords)}개 (최근 {CROSS_VERIFY_LOOKBACK_HOURS}시간)")

    updated  = 0
    verified = 0
    for meme in memes:
        flow      = classify_flow(meme)
        lifecycle = classify_lifecycle(meme)
        category  = meme.get("category") or classify_category(meme["title"])

        # extra는 기존 값(video_id, description, hype_score 등)을 보존한 채
        # cross_verified/matched_trends만 덧붙임
        extra = dict(meme.get("extra") or {})
        if meme["source"] not in CROSS_VERIFY_SOURCES:
            matched = find_matched_trends(meme["title"], trend_keywords)
            if matched:
                extra["cross_verified"] = True
                extra["matched_trends"] = matched
                verified += 1

        db.table("memes").update({
            "flow_type":       flow,
            "lifecycle_stage": lifecycle,
            "category":        category,
            "extra":           extra,
        }).eq("id", meme["id"]).execute()

        updated += 1

    log.info(f"분류 완료 — {updated}건 업데이트, 교차 검증 {verified}건")
    return updated


if __name__ == "__main__":
    run()
