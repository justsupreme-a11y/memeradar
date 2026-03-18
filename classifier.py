"""
밈레이더 분류기
- 흐름 분류: inflow(해외→국내) / independent(국내 독립) / export(국내→해외)
- 생애주기:  seed(태동기) / spread(확산기) / peak(고점) / fade(쇠퇴기)
- 실행: GitHub Actions에서 크롤러 직후 자동 실행
"""

import logging
from datetime import datetime, timezone, timedelta
from utils.db import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [classifier] %(message)s")
log = logging.getLogger(__name__)

# ── 소스 분류 ──────────────────────────────────────────
GLOBAL_SOURCES   = {"reddit", "youtube"}   # 해외 플랫폼
DOMESTIC_SOURCES = {"ruliweb", "ucduk", "naver", "dcinside", "fmkorea"}

# ── 생애주기 임계값 ────────────────────────────────────
# 수집된 지 몇 시간 이내 + 조회수 기준으로 단계 판정
LIFECYCLE_RULES = [
    # (단계,       최대 수집 경과시간h, 최소 조회수, 최대 조회수)
    ("seed",       48,                 0,           500),
    ("spread",     168,                500,         5000),
    ("peak",       336,                5000,        9999999),
    ("fade",       9999,               0,           9999999),
]


# ── 흐름 분류 로직 ─────────────────────────────────────

def classify_flow(meme: dict, all_memes_index: dict) -> str:
    """
    같은 content_hash 계열 밈들의 플랫폼 + 최초 등장 시각을 비교해서
    흐름 방향을 판정한다.

    판정 규칙:
    - 해외 소스(reddit/youtube)에서 먼저 등장 → inflow
    - 국내 소스에서만 등장, 해외 동일 밈 없음 → independent
    - 국내 소스가 해외보다 48시간 이상 앞섬 → export
    """
    source   = meme["source"]
    platform = meme["platform"]

    # 제목 키워드로 유사 밈 묶기 (간단 버전: 첫 3단어 매칭)
    title_key = _title_key(meme["title"])
    related   = all_memes_index.get(title_key, [])

    if not related or len(related) == 1:
        # 관련 밈이 없으면 플랫폼으로만 판정
        if source in GLOBAL_SOURCES:
            return "inflow"
        return "independent"

    # 관련 밈들의 최초 등장 시각 분리
    global_times   = []
    domestic_times = []

    for m in related:
        t = _parse_time(m["collected_at"])
        if m["source"] in GLOBAL_SOURCES:
            global_times.append(t)
        else:
            domestic_times.append(t)

    if not global_times:
        return "independent"  # 해외 등장 없음 → 국내 독립

    if not domestic_times:
        return "inflow"  # 국내 등장 없음 → 아직 유입 전

    earliest_global   = min(global_times)
    earliest_domestic = min(domestic_times)
    diff_hours = (earliest_domestic - earliest_global).total_seconds() / 3600

    if diff_hours > 48:
        # 국내가 해외보다 48시간 이상 앞서면 역수출
        return "export"
    elif diff_hours < -6:
        # 해외가 국내보다 6시간 이상 앞서면 유입
        return "inflow"
    else:
        # 비슷한 시기 → 국내 독립 생성으로 보수적 판정
        return "independent"


def classify_lifecycle(meme: dict) -> str:
    """
    수집 경과 시간 + 조회수로 생애주기 단계 판정
    """
    collected_at = _parse_time(meme["collected_at"])
    now          = datetime.now(timezone.utc)
    hours_since  = (now - collected_at).total_seconds() / 3600
    view_count   = meme.get("view_count", 0) or 0

    for stage, max_hours, min_views, max_views in LIFECYCLE_RULES:
        if hours_since <= max_hours and min_views <= view_count <= max_views:
            return stage

    return "fade"  # 기본값


# ── 헬퍼 ──────────────────────────────────────────────

def _title_key(title: str) -> str:
    """제목 앞 3단어를 소문자로 정규화 → 유사 밈 묶기용 키"""
    words = title.strip().lower().split()
    return " ".join(words[:3])


def _parse_time(ts) -> datetime:
    """Supabase timestamp 문자열 → timezone-aware datetime"""
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

    # 아직 분류 안 된 것만 가져오기
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

    # 전체 밈 인덱스 구성 (title_key → [meme, ...])
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
    updated = 0
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
