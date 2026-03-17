"""
밈레이더 크롤러 메인 실행기
GitHub Actions에서 호출하거나 로컬에서 직접 실행 가능.

사용법:
  python main.py                  # 전체 실행
  python main.py --only dci       # 디시만
  python main.py --only fmk       # 에펨만
  python main.py --only yt        # 유튜브만
"""

import sys
import logging
import argparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def run_all(targets: list[str]):
    results = {}

    if "dci" in targets:
        log.info("=" * 40)
        log.info("디시인사이드 크롤러 시작")
        log.info("=" * 40)
        from crawlers.dcinside import run as run_dci
        results["dcinside"] = run_dci(pages=3)

    if "fmk" in targets:
        log.info("=" * 40)
        log.info("에펨코리아 크롤러 시작")
        log.info("=" * 40)
        from crawlers.fmkorea import run as run_fmk
        results["fmkorea"] = run_fmk(pages=3)

    if "yt" in targets:
        log.info("=" * 40)
        log.info("YouTube Shorts 크롤러 시작")
        log.info("=" * 40)
        from crawlers.youtube import run as run_yt
        results["youtube"] = run_yt()

    log.info("=" * 40)
    log.info("전체 완료 요약")
    for source, count in results.items():
        log.info(f"  {source}: 신규 {count}건")
    log.info(f"  합계: {sum(results.values())}건")
    log.info("=" * 40)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only",
        choices=["dci", "fmk", "yt"],
        help="특정 크롤러만 실행",
    )
    args = parser.parse_args()

    if args.only:
        run_all([args.only])
    else:
        run_all(["dci", "fmk", "yt"])
