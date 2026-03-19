"""
밈레이더 v3 — 통합 실행기
크롤러: 나무위키 / 인스티즈 / 대학내일 / KYM / YouTube 밈채널 / 구글 트렌드
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
    "namuwiki":  ("나무위키",    "crawlers.namuwiki",        "run"),
    "instiz":    ("인스티즈",    "crawlers.instiz",           "run"),
    "univ":      ("대학내일",    "crawlers.univ_tomorrow",    "run"),
    "kym":       ("KYM",        "crawlers.kym",              "run"),
    "yt":        ("YouTube",    "crawlers.youtube_meme_ch",  "run"),
    "gtrends":   ("구글 트렌드", "crawlers.google_trends",    "run"),
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

    total = sum(results.values())
    log.info(f"크롤링 합계: {total}건 신규 저장")
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
