"""
밈레이더 분류기
- 흐름 분류: inflow(해외→국내) / independent(국내 독립) / export(국내→해외)
- lifecycle_stage 판정 제거 — 스냅샷 데이터 없이는 의미 없음
"""
import logging
from datetime import datetime, timezone
from utils.db import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [classifier] %(message)s")
log = logging.getLogger(__name__)

# 해외 소스: KYM + YouTube 전체
GLOBAL_SOURCES = {
    "kym",
    "youtube_channel_hype",
    "youtube_meme_ch",
    "youtube_trending_hype",
}

# 국내 독립 소스 (해외 유입 가능성 없는 순수 국내)
DOMESTIC_SOURCES = {
    "instiz", "theqoo", "pannate", "gogumafarm",
    "gqkorea", "hypebeast", "hypebeast_en", "google_trends",
}

# YouTube source 전체 집합 (platform 무관하게 inflow 처리)
YOUTUBE_SOURCES = {
    "youtube_channel_hype",
    "youtube_meme_ch",
    "youtube_trending_hype",
}


def classify_flow(meme: dict, all_memes_index: dict) -> str:
    source = meme["source"]

    # KYM → 항상 inflow
    if source == "kym":
        return "inflow"

    # YouTube → platform 무관하게 inflow
    # (국내 YouTube 채널도 밈 확산 경로상 inflow로 간주)
    if source in YOUTUBE_SOURCES:
        return "inflow"

    # 구글트렌드 / 네이버 계열 → 독립
    if source in {"google_trends", "naver", "naver_realtime"}:
        return "independent"

    # 국내 커뮤니티·패션 매거진 → 독립
    if source in DOMESTIC_SOURCES:
        return "independent"

    # 그 외: 타이틀 기반 타임스탬프 비교로 판별
    title_key = _title_key(meme["title"])
    related   = all_memes_index.get(title_key, [])

    if not related or len(related) == 1:
        return "independent"

    global_times   = []
    domestic_times = []
    for m in related:
        t = _parse_time(m["collected_at"])
        if m["source"] in GLOBAL_SOURCES:
            global_times.append(t)
        else:
            domestic_times.append(t)

    if not global_times:
        return "independent"
    if not domestic_times:
        return "inflow"

    diff_hours = (min(domestic_times) - min(global_times)).total_seconds() / 3600

    if diff_hours > 48:
        return "export"
    elif diff_hours < -6:
        return "inflow"
    else:
        return "independent"


def _title_key(title: str) -> str:
    return " ".join(title.strip().lower().split()[:3])


def _parse_time(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


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

    all_resp = (
        db.table("memes")
        .select("id, title, source, collected_at")
        .order("collected_at", desc=False)
        .limit(5000)
        .execute()
    )
    index: dict[str, list] = {}
    for m in (all_resp.data or []):
        key = _title_key(m["title"])
        index.setdefault(key, []).append(m)

    updated     = 0
    flow_counts = {"inflow": 0, "independent": 0, "export": 0}

    for meme in memes:
        flow = classify_flow(meme, index)
        db.table("memes").update({"flow_type": flow}).eq("id", meme["id"]).execute()
        flow_counts[flow] = flow_counts.get(flow, 0) + 1
        updated += 1

    log.info(f"분류 완료 — {updated}건 업데이트")
    log.info(f"  유입={flow_counts['inflow']} / 독립={flow_counts['independent']} / 역수출={flow_counts['export']}")
    return updated


if __name__ == "__main__":
    run()
