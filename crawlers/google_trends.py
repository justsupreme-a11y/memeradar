"""
구글 트렌드 크롤러
- 라이브러리: pytrends (비공식 · 무료)
- 대상: 한국 실시간 급상승 검색어 + 트렌드 점수
- API 키 불필요
"""

import time
import logging
from pytrends.request import TrendReq
from utils.db import save_meme

logging.basicConfig(level=logging.INFO, format="%(asctime)s [gtrends] %(message)s")
log = logging.getLogger(__name__)


def run():
    try:
        pytrends = TrendReq(hl="ko", tz=540)  # KST
    except Exception as e:
        log.error(f"pytrends 초기화 실패: {e}")
        return 0

    total_new = 0

    # 1. 실시간 급상승 검색어 (한국)
    log.info("실시간 급상승 검색어 수집 중...")
    try:
        trending = pytrends.trending_searches(pn="south_korea")
        keywords = trending[0].tolist()
        log.info(f"  → {len(keywords)}개 키워드")

        for kw in keywords:
            saved = save_meme(
                title=kw,
                url=f"https://trends.google.com/trends/explore?q={kw}&geo=KR",
                source="google_trends",
                platform="domestic",
                extra={"type": "realtime", "keyword": kw},
            )
            if saved:
                total_new += 1

        time.sleep(2)
    except Exception as e:
        log.warning(f"실시간 트렌드 실패: {e}")

    # 2. 일간 급상승 검색어 (한국) - 더 자세한 정보 포함
    log.info("일간 급상승 검색어 수집 중...")
    try:
        daily = pytrends.today_searches(pn="KR")
        log.info(f"  → {len(daily)}개 키워드")

        for kw in daily:
            saved = save_meme(
                title=str(kw),
                url=f"https://trends.google.com/trends/explore?q={kw}&geo=KR",
                source="google_trends",
                platform="domestic",
                extra={"type": "daily", "keyword": str(kw)},
            )
            if saved:
                total_new += 1

        time.sleep(2)
    except Exception as e:
        log.warning(f"일간 트렌드 실패: {e}")

    # 3. 밈 관련 키워드 트렌드 점수 조회
    log.info("밈 관련 키워드 트렌드 점수 조회 중...")
    meme_keywords = [
        ["버터떡", "창억떡", "봄동비빔밥"],
        ["밈", "짤방", "유행어"],
        ["챌린지", "트렌드", "바이럴"],
    ]

    for kw_group in meme_keywords:
        try:
            pytrends.build_payload(kw_group, geo="KR", timeframe="now 1-d")
            interest = pytrends.interest_over_time()

            if interest.empty:
                continue

            # 최근 점수가 높은 키워드만 저장
            latest = interest.iloc[-1]
            for kw in kw_group:
                if kw not in latest:
                    continue
                score = int(latest[kw])
                if score < 20:  # 관심도 20 미만 스킵
                    continue

                saved = save_meme(
                    title=f"{kw} (트렌드 점수: {score})",
                    url=f"https://trends.google.com/trends/explore?q={kw}&geo=KR",
                    source="google_trends",
                    platform="domestic",
                    view_count=score,
                    extra={"type": "interest", "keyword": kw, "score": score},
                )
                if saved:
                    total_new += 1

            time.sleep(3)  # 구글 트렌드 요청 제한 방지
        except Exception as e:
            log.warning(f"키워드 그룹 {kw_group} 실패: {e}")

    log.info(f"구글 트렌드 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
