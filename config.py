import os
from dotenv import load_dotenv

load_dotenv()

# DART API
DART_API_KEY = os.getenv("DART_API_KEY")

# Gmail SMTP
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "kims138016@gmail.com")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# Screening thresholds
OPERATING_MARGIN_MIN = 20.0
ROE_MIN = 20.0
REVENUE_GROWTH_MIN = 10.0   # 연평균 매출액 증가율 강조 기준 (%)
REVENUE_GROWTH_YEARS = 2    # CAGR 계산 기간 (년)

# DART report codes
REPRT_CODE_ANNUAL = "11011"   # 사업보고서

# Financial statement division
FS_DIV_CONSOLIDATED = "CFS"   # 연결재무제표
FS_DIV_INDIVIDUAL = "OFS"     # 별도재무제표

# Market classification codes
MARKET_KOSPI = "Y"
MARKET_KOSDAQ = "K"
MARKET_LABEL = {"Y": "KOSPI", "K": "KOSDAQ"}

# Threading / rate limiting (DART)
MAX_WORKERS = 5
REQUEST_DELAY_SECONDS = 0.3
