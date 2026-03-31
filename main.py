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
    # 국내 트렌드/미디어
    "goguma":       ("고구마팜",      "crawlers.gogumafarm",       "run"),
    # 패션
    "fashion":      ("패션매거진",    "crawlers.fashion_mag",      "run"),
    # 해외
    "kym":          ("KYM",           "crawlers.kym",              "run"),
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
    # "reddit":   403 전체 차단
    # "imgur":    모듈 파일 없음
    # "wikipedia":실시간성 없음, KYM과 역할 중복
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
