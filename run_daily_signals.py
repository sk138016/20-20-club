"""
기술적 신호 일일 실행 진입점.

신호가 발견된 경우 docs/data/signals/ 에 JSON 저장.
"""

import json
import logging
import math
import sys
import numpy as np
from datetime import datetime
from pathlib import Path

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            f"logs/signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)


def _save_signals_for_web(signals: dict) -> None:
    """기술적 신호 결과를 docs/data/signals/ 에 날짜별 JSON 파일로 저장."""
    docs_dir = Path("docs/data/signals")
    docs_dir.mkdir(parents=True, exist_ok=True)

    date_str = signals["scan_date"]

    data_file = docs_dir / f"{date_str}.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(signals, f, ensure_ascii=False, indent=2, cls=_NumpyEncoder)

    index_file = docs_dir / "index.json"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = {"dates": []}

    if date_str not in index["dates"]:
        index["dates"].append(date_str)
        index["dates"].sort(reverse=True)
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    logger.info(f"웹 데이터 저장: docs/data/signals/{date_str}.json")


def main():
    logger.info("=" * 60)
    logger.info("기술적 신호 스캐너 시작")
    logger.info("=" * 60)

    from technical_screener import run_technical_screener

    signals = run_technical_screener()

    if signals["total"] == 0:
        logger.info("오늘 발동된 신호 없음 — 스캔 기록은 저장")
    else:
        logger.info(
            f"신호 발견 — A: {len(signals['A'])}개 | B: {len(signals['B'])}개 | C: {len(signals['C'])}개"
        )

    _save_signals_for_web(signals)

    logger.info("=" * 60)
    logger.info(f"완료. 총 {signals['total']}개 신호 웹 저장")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
