"""US 스크리닝 단독 테스트 — 결과를 콘솔 출력 후 이메일 발송."""
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
            f"logs/test_us_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(sys.stdout),
    ],
)

from us_fetcher import screen_sp500
from email_template import build_html_email, build_subject
from email_sender import send_email

us_df = screen_sp500()

if us_df is None:
    print("ERROR: screen_sp500() None 반환 - 로그 확인 필요")
    sys.exit(1)

print(f"\n{'='*50}")
print(f"선별 결과: {len(us_df)}개 기업")
print(f"{'='*50}")
if not us_df.empty:
    cols = ["rank", "symbol", "corp_name", "sector", "op_margin", "roe"]
    if "rev_cagr" in us_df.columns:
        cols += ["rev_cagr", "growth_flag"]
    print(us_df[cols].to_string(index=False))
    if "growth_flag" in us_df.columns:
        print(f"\n고성장 기업 수: {us_df['growth_flag'].sum()}개")

import pandas as pd
kr_empty = pd.DataFrame()
html = build_html_email(kr_empty, datetime.now().year - 1, us_result_df=us_df)
subject = build_subject(kr_empty, datetime.now().year - 1, us_result_df=us_df)
send_email(subject, html)
