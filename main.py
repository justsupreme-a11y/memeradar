"""
밈레이더 v2 — 통합 실행기
크롤러: Reddit / 루리웹 / 웃긴대학 / 네이버 / YouTube
"""

import sys
import os
import logging
import argparse

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

CRAWLERS = {
    "reddit":  ("Reddit",     "crawlers.reddit",  "run"),
    "ruli":    ("루리웹",      "crawlers.ruliweb", "run"),
    "ucduk":   ("웃긴대학",    "crawlers.ucduk",   "run"),
    "naver":   ("네이버",      "crawlers.naver",   "run"),
    "yt":      ("YouTube",    "crawlers.youtube", "run"),
}


def run_all(targets: list[str]):
    results = {}

    for key in targets:
        if key not in CRAWLERS:
            log.warning(f"알 수 없는 크롤러: {key}")
            continue

        name, module_path, func_name = CRAWLERS[key]
        log.info("=" * 40)
        log.info(f"{name} 크롤러 시작")
        log.info("=" * 40)

        try:
            import importlib
            module = importlib.import_module(module_path)
            func   = getattr(module, func_name)
            results[name] = func()
        except Exception as e:
            log.error(f"{name} 크롤러 오류: {e}")
            results[name] = 0

    log.info("=" * 40)
    log.info("전체 완료 요약")
    for name, count in results.items():
        log.info(f"  {name}: 신규 {count}건")
    log.info(f"  합계: {sum(results.values())}건")
    log.info("=" * 40)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only",
        choices=list(CRAWLERS.keys()),
        help="특정 크롤러만 실행",
    )
    args = parser.parse_args()

    all_targets = list(CRAWLERS.keys())
    run_all([args.only] if args.only else all_targets)
