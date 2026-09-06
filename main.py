"""
밈레이더 최종 — 통합 실행기
"""
import sys, os, logging, argparse, importlib
sys.path.insert(0, os.path.dirname(__file__))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

CRAWLERS = {
    # 국내 커뮤니티
    "instiz":       ("인스티즈",      "crawlers.instiz",          "run"),
    "theqoo":       ("더쿠",          "crawlers.theqoo",           "run"),
    "pannate":      ("네이트판",      "crawlers.pannate",          "run"),
    "humoruniv":    ("웃긴대학",      "crawlers.humoruniv",        "run"),
    # 국내 트렌드/미디어
    "goguma":       ("고구마팜",      "crawlers.gogumafarm",       "run"),
    "naver_dl":     ("네이버 데이터랩","crawlers.naver_datalab",    "run"),
    # 패션
    "fashion":      ("패션매거진",    "crawlers.fashion_mag",      "run"),
    # 해외
    "kym":          ("KYM",           "crawlers.kym",              "run"),
    "giphy":        ("Giphy",         "crawlers.giphy_trending",   "run"),
    # 영상
    "yt":           ("YouTube",       "crawlers.youtube_trending", "run"),
    # 트렌드 데이터
    "gtrends":      ("구글 트렌드",   "crawlers.google_trends",    "run"),

    # ── 제거된 크롤러 ────────────────────────────────────
    # "mlbpark":  매번 0건
    # "dispatch": 매번 0건 — JS 렌더링
    # "univ":     매번 0건 — 사이트 구조 변경
    # "mkt":      DNS 없음 / 전체 404
    # "dfashion": DNS 없음
    # "imgur":    모듈 파일 없음
    # "wikipedia":실시간성 없음, KYM과 역할 중복
    # "reddit":   2025-11 Responsible Builder Policy 이후 신규 앱 발급 사실상 불가
    # "namuwiki": 2026-09 확인 — 나무위키가 완전 클라이언트 렌더링(SPA) 전환,
    #             원본 HTTP 응답에 실 콘텐츠 없음(순수 앱 셸) → requests로 수집 불가
    # "mkt_insight": 2026-09 확인 — 대상 3개 사이트 중 2개 폐쇄(hsad/daehong),
    #             나머지 1개(opensurvey)는 셀렉터 매칭 0건 → 전면 비활성
    # "ucduk":    2026-09 확인 — 존재하지 않는 도메인(ucduk.com) 사용,
    #             실제 웃긴대학 도메인은 web.humoruniv.com → humoruniv로 대체
    # "naver":    2026-09 확인 — sort=date 키워드 검색이라 관련성 필터 없음,
    #             카페/블로그 검색 API 특성상 썸네일도 없어 밈 콘텐츠와 성격 불일치.
    #             수집물 대부분이 실제 밈이 아닌 정보성 블로그 글로 품질 미달 → 비활성
}

def run_crawlers(targets):
    results = {}
    for key in targets:
        if key not in CRAWLERS:
            continue
        name, mod, fn = CRAWLERS[key]
        log.info("=" * 40)
        log.info(f"{name} 크롤러 시작")
        log.info("=" * 40)
        try:
            m = importlib.import_module(mod)
            results[name] = getattr(m, fn)()
        except Exception as e:
            log.error(f"{name} 오류: {e}")
            results[name] = 0
    log.info("=" * 40)
    log.info("전체 완료 요약")
    for n, c in results.items():
        log.info(f"  {n}: {c}건")
    log.info(f"  합계: {sum(results.values())}건")
    log.info("=" * 40)
    return results

def run_classifier():
    log.info("=" * 40)
    log.info("분류기 시작")
    log.info("=" * 40)
    try:
        from utils.classifier import run
        return run()
    except Exception as e:
        log.error(f"분류기 오류: {e}")
        return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=list(CRAWLERS.keys()) + ["classify"])
    args = parser.parse_args()

    if args.only == "classify":
        run_classifier()
    elif args.only:
        run_crawlers([args.only])
    else:
        run_crawlers(list(CRAWLERS.keys()))
        run_classifier()
