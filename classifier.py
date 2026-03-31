"""
밈레이더 분류기
- 흐름 분류: inflow(해외→국내) / independent(국내 독립) / export(국내→해외)
- 생애주기:  seed(태동기) / spread(확산기) / peak(고점) / fade(쇠퇴기)
- 실행: GitHub Actions에서 크롤러 직후 자동 실행
"""

import logging
from datetime import datetime, timezone
from utils.db import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [classifier] %(message)s")
log = logging.getLogger(__name__)

# ── 소스 분류 ──────────────────────────────────────────
# kym 추가, reddit 제거 (크롤러 제거됨)
GLOBAL_SOURCES   = {"kym", "youtube"}
DOMESTIC_SOURCES = {"instiz", "theqoo", "pannate", "mlbpark", "gogumafarm",
                    "gqkorea", "hypebeast", "hypebeast_en", "google_trends"}

# ── 생애주기 임계값 ────────────────────────────────────
LIFECYCLE_RULES = [
    # (단계,       최대 수집 경과시간h, 최소 조회수, 최대 조회수)
    ("seed",       48,                 0,           500),
    ("spread",     168,                500,         5000),
    ("peak",       336,                5000,        9999999),
    ("fade",       9999,               0,           9999999),
]


# ── 흐름 분류 로직 ─────────────────────────────────────

def classify_flow(meme: dict, all_memes_index: dict) -> str:
    source   = meme["source"]
    platform = meme.get("platform", "")

    # 소스 기반 1차 판정
    if source == "kym":
        return "inflow"  # KYM은 해외→국내 유입

    if source in {"youtube", "youtube_meme_ch", "youtube_trending_hype", "youtube_channel_hype"}:
        return "inflow" if platform == "global" else "independent"

    if source in {"google_trends", "naver", "naver_realtime"}:
        return "independent"

    if source in DOMESTIC_SOURCES:
        return "independent"

    # 타임스탬프 비교로 inflow/export 판정
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

    earliest_global   = min(global_times)
    earliest_domestic = min(domestic_times)
    diff_hours = (earliest_domestic - earliest_global).total_seconds() / 3600

    if diff_hours > 48:
        return "export"       # 국내가 48시간 이상 앞서면 역수출
    elif diff_hours < -6:
        return "inflow"       # 해외가 6시간 이상 앞서면 유입
    else:
        return "independent"  # 비슷한 시기 → 보수적 판정


def classify_lifecycle(meme: dict) -> str:
    collected_at = _parse_time(meme["collected_at"])
    now          = datetime.now(timezone.utc)
    hours_since  = (now - collected_at).total_seconds() / 3600
    view_count   = meme.get("view_count", 0) or 0

    for stage, max_hours, min_views, max_views in LIFECYCLE_RULES:
        if hours_since <= max_hours and min_views <= view_count <= max_views:
            return stage

    return "fade"


# ── 헬퍼 ──────────────────────────────────────────────

def _title_key(title: str) -> str:
    words = title.strip().lower().split()
    return " ".join(words[:3])


def _parse_time(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


# ── 메인 실행 ──────────────────────────────────────────

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

    # 전체 밈 인덱스 (title_key → [meme, ...])
    all_resp = (
        db.table("memes")
        .select("id, title, source, collected_at")
        .order("collected_at", desc=False)
        .limit(5000)
        .execute()
    )
    all_memes = all_resp.data or []

    index: dict[str, list] = {}
    for m in all_memes:
        key = _title_key(m["title"])
        index.setdefault(key, []).append(m)

    # 분류 실행
    updated          = 0
    flow_counts      = {"inflow": 0, "independent": 0, "export": 0}
    lifecycle_counts = {"seed": 0, "spread": 0, "peak": 0, "fade": 0}

    for meme in memes:
        flow      = classify_flow(meme, index)
        lifecycle = classify_lifecycle(meme)

        db.table("memes").update({
            "flow_type":       flow,
            "lifecycle_stage": lifecycle,
        }).eq("id", meme["id"]).execute()

        flow_counts[flow]           = flow_counts.get(flow, 0) + 1
        lifecycle_counts[lifecycle] = lifecycle_counts.get(lifecycle, 0) + 1
        updated += 1

    log.info(f"분류 완료 — {updated}건 업데이트")
    log.info(f"  흐름: 유입={flow_counts['inflow']} / 독립={flow_counts['independent']} / 역수출={flow_counts['export']}")
    log.info(f"  생애주기: 태동={lifecycle_counts['seed']} / 확산={lifecycle_counts['spread']} / 고점={lifecycle_counts['peak']} / 쇠퇴={lifecycle_counts['fade']}")
    return updated


if __name__ == "__main__":
    run()
