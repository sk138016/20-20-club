"""
기술적 신호 일일 실행 진입점.

신호가 발견된 경우에만 이메일 발송 (신호 없으면 발송 생략).
"""

import logging
import sys
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


def main():
    logger.info("=" * 60)
    logger.info("기술적 신호 스캐너 시작")
    logger.info("=" * 60)

    from technical_screener import run_technical_screener
    from technical_email_template import build_signal_email, build_signal_subject
    from email_sender import send_email

    signals = run_technical_screener()

    if signals["total"] == 0:
        logger.info("오늘 발동된 신호 없음 — 이메일 발송 생략")
        return

    logger.info(
        f"신호 발견 — A: {len(signals['A'])}개 | B: {len(signals['B'])}개 | C: {len(signals['C'])}개"
    )

    html = build_signal_email(signals)
    subject = build_signal_subject(signals)
    send_email(subject, html)

    logger.info("=" * 60)
    logger.info(f"완료. 총 {signals['total']}개 신호 발송")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
