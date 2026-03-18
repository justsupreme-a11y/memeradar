"""
네이버 DataLab 크롤러
- API: 네이버 DataLab 검색어 트렌드 (무료)
- 네이버 검색 API와 다름 — DataLab은 트렌드 점수 제공
- 발급: https://developers.naver.com/apps/#/register
  → 사용 API에서 "데이터랩(검색어 트렌드)" 체크

추가로 네이버 실시간 급상승 검색어도 수집
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from utils.db import save_meme

logging.basicConfig(level=logging.INFO, format="%(asctime)s [naver_dl] %(message)s")
log = logging.getLogger(__name__)

NAVER_CLIENT_ID     = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")

DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"

# 밈/트렌드 관련 키워드 그룹
# 각 그룹은 하나의 트렌드로 묶여서 비교됨
KEYWORD_GROUPS = [
    {
        "groupName": "음식밈",
        "keywords": ["버터떡", "창억떡", "봄동비빔밥", "먹방밈"]
    },
    {
        "groupName": "유행어",
        "keywords": ["밈", "짤", "유행어", "챌린지"]
    },
    {
        "groupName": "신조어",
        "keywords": ["갓생", "킹받다", "억텐", "현타"]
    },
    {
        "groupName": "바이럴",
        "keywords": ["바이럴", "트렌드", "화제", "핫이슈"]
    },
]


def fetch_datalab_trend(keyword_groups: list) -> dict:
    """네이버 DataLab 검색어 트렌드 조회"""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return {}

    today     = datetime.now()
    week_ago  = today - timedelta(days=7)

    payload = {
        "startDate": week_ago.strftime("%Y-%m-%d"),
        "endDate":   today.strftime("%Y-%m-%d"),
        "timeUnit":  "date",
        "keywordGroups": keyword_groups,
        "device": "mo",  # 모바일 위주 (밈은 모바일에서 퍼짐)
        "ages": ["2", "3", "4"],  # 13~34세
        "gender": "f",
    }

    headers = {
        "X-Naver-Client-Id":     NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        "Content-Type":          "application/json",
    }

    try:
        resp = requests.post(DATALAB_URL, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.warning(f"DataLab 요청 실패: {e}")
        return {}


def fetch_naver_realtime() -> list[str]:
    """네이버 실시간 급상승 검색어 (비공식 파싱)"""
    try:
        resp = requests.get(
            "https://signal.bz/news",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        keywords = []
        for item in soup.select(".list-header-item span, .keyword span")[:20]:
            kw = item.text.strip()
            if kw:
                keywords.append(kw)
        return keywords
    except Exception as e:
        log.warning(f"실시간 검색어 수집 실패: {e}")
        return []


def run():
    total_new = 0

    # 1. 네이버 DataLab 트렌드
    if NAVER_CLIENT_ID and NAVER_CLIENT_SECRET:
        log.info("네이버 DataLab 트렌드 수집 중...")

        for group_batch in [KEYWORD_GROUPS[:2], KEYWORD_GROUPS[2:]]:
            result = fetch_datalab_trend(group_batch)

            for item in result.get("results", []):
                group_name = item.get("title", "")
                data_points = item.get("data", [])

                if not data_points:
                    continue

                # 최근 점수
                latest_ratio = data_points[-1].get("ratio", 0)
                if latest_ratio < 10:
                    continue

                saved = save_meme(
                    title=f"{group_name} (트렌드 {latest_ratio:.0f}점)",
                    url=f"https://datalab.naver.com/keyword/trendResult.naver?hashKey={group_name}",
                    source="naver_datalab",
                    platform="domestic",
                    view_count=int(latest_ratio),
                    extra={
                        "group_name":   group_name,
                        "latest_ratio": latest_ratio,
                        "type":         "datalab_trend",
                    },
                )
                if saved:
                    total_new += 1
    else:
        log.warning("NAVER_CLIENT_ID/SECRET 없음 — DataLab 스킵")

    # 2. 실시간 급상승 검색어 (signal.bz 파싱)
    log.info("실시간 급상승 검색어 수집 중...")
    realtime_keywords = fetch_naver_realtime()
    log.info(f"  → {len(realtime_keywords)}개")

    for i, kw in enumerate(realtime_keywords):
        saved = save_meme(
            title=kw,
            url=f"https://search.naver.com/search.naver?query={kw}",
            source="naver_realtime",
            platform="domestic",
            view_count=len(realtime_keywords) - i,  # 순위 역산
            extra={"rank": i + 1, "type": "realtime"},
        )
        if saved:
            total_new += 1

    log.info(f"네이버 DataLab 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
