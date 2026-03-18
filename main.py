"""
밈레이더 v2 — 통합 실행기
순서: 크롤러 실행 → 분류기 실행
"""

import sys
import os
import logging
import argparse
import importlib

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

CRAWLERS = {
    "reddit": ("Reddit",   "crawlers.reddit",  "run"),  # ← 이거 추가
    "ruli":   ("루리웹",   "crawlers.ruliweb", "run"),
    "ucduk":  ("웃긴대학", "crawlers.ucduk",   "run"),
    "naver":  ("네이버",   "crawlers.naver",   "run"),
    "yt":     ("YouTube",  "crawlers.youtube", "run"),
}


def run_crawlers(targets: list[str]):
    results = {}
    for key in targets:
        if key not in CRAWLERS:
            continue
        name, module_path, func_name = CRAWLERS[key]
        log.info("=" * 40)
        log.info(f"{name} 크롤러 시작")
        log.info("=" * 40)
        try:
            module = importlib.import_module(module_path)
            results[name] = getattr(module, func_name)()
        except Exception as e:
            log.error(f"{name} 오류: {e}")
            results[name] = 0

    log.info(f"크롤링 합계: {sum(results.values())}건 신규 저장")
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
