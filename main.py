"""
20-20 Club — 한국 주식 자동 선별 시스템
영업이익률 >= 20% AND ROE >= 20% 인 KOSPI+KOSDAQ 기업을 선별해 Gmail로 발송.
데이터 출처: 금융감독원 전자공시시스템(DART)
"""

import json
import logging
import math
import sys
from datetime import datetime
from pathlib import Path

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            f"logs/screener_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def _safe_float(v):
    """NaN/None → None, 나머지는 float 반환."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _save_club_for_web(result_df, bsns_year, us_result_df=None):
    """20-20 Club 선별 결과를 docs/data/club/ 에 날짜별 JSON 파일로 저장."""
    docs_dir = Path("docs/data/club")
    docs_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")

    kr_records = []
    for _, row in result_df.iterrows():
        kr_records.append({
            "rank": int(row["rank"]),
            "stock_code": str(row["stock_code"]).zfill(6),
            "corp_name": str(row["corp_name"]),
            "market": str(row["market"]),
            "op_margin": float(row["op_margin"]),
            "roe": float(row["roe"]),
            "rev_cagr": _safe_float(row.get("rev_cagr")),
            "growth_flag": bool(row.get("growth_flag", False)),
            "base_year": int(row["base_year"]),
        })

    us_records = []
    if us_result_df is not None and not us_result_df.empty:
        for i, (_, row) in enumerate(us_result_df.iterrows(), 1):
            us_records.append({
                "rank": i,
                "symbol": str(row["symbol"]),
                "corp_name": str(row["corp_name"]),
                "sector": str(row.get("sector", "")),
                "op_margin": float(row["op_margin"]),
                "roe": float(row["roe"]),
                "rev_cagr": _safe_float(row.get("rev_cagr")),
                "growth_flag": bool(row.get("growth_flag", False)),
            })

    data = {
        "updated_at": date_str,
        "bsns_year": int(bsns_year),
        "kr": kr_records,
        "us": us_records,
    }

    data_file = docs_dir / f"{date_str}.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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

    logger.info(
        f"웹 데이터 저장: docs/data/club/{date_str}.json "
        f"(KR {len(kr_records)}개, US {len(us_records)}개)"
    )


def _save_2020_club_cache(result_df, bsns_year):
    """분기 스크리닝 결과를 JSON 캐시로 저장 (일일 신호 스캐너가 참조)."""
    Path("data").mkdir(exist_ok=True)
    codes = result_df["stock_code"].astype(str).str.zfill(6).tolist()
    cache = {
        "updated_at": datetime.now().strftime("%Y-%m-%d"),
        "bsns_year": bsns_year,
        "kr_stock_codes": codes,
    }
    with open("data/2020_club.json", "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    logger.info(f"20-20 Club 캐시 저장 완료: {len(codes)}개 → data/2020_club.json")


def main():
    logger.info("=" * 60)
    logger.info("20-20 Club 스크리너 시작")
    logger.info("=" * 60)

    from dart_fetcher import (
        get_dart_instance,
        get_listed_companies,
        enrich_with_market_type,
        determine_target_year,
        fetch_all_financials,
        fetch_past_revenues,
    )
    from calculator import screen_companies, add_revenue_growth
    from config import REVENUE_GROWTH_YEARS
    from us_fetcher import screen_sp500
    from email_template import build_html_email, build_subject
    from email_sender import send_email

    dart = get_dart_instance()

    logger.info("[1/7] 상장사 목록 취득")
    listed_df = get_listed_companies(dart)

    logger.info("[2/7] 시장 구분 보강 (KOSPI / KOSDAQ)")
    companies_df = enrich_with_market_type(dart, listed_df)
    if companies_df.empty:
        logger.error("KOSPI/KOSDAQ 기업을 찾을 수 없습니다. 종료합니다.")
        sys.exit(1)

    logger.info("[3/7] 기준 연도 결정")
    bsns_year = determine_target_year()
    logger.info(f"  기준 연도: {bsns_year}년")

    logger.info("[4/7] 재무제표 수집")
    financial_data = fetch_all_financials(dart, companies_df, bsns_year)

    logger.info("[5/7] 20-20 필터 적용")
    result_df = screen_companies(companies_df, financial_data, bsns_year)

    logger.info("[5.5/7] 매출 성장률 계산 (선별 기업 대상)")
    past_revenues = fetch_past_revenues(
        dart, result_df["corp_code"].tolist(), bsns_year, years_back=REVENUE_GROWTH_YEARS
    )
    result_df = add_revenue_growth(result_df, past_revenues, bsns_year)

    logger.info("[6/7] S&P 500 스크리닝 (미국 시장)")
    us_result_df = screen_sp500()

    _save_2020_club_cache(result_df, bsns_year)
    _save_club_for_web(result_df, bsns_year, us_result_df)

    logger.info("[7/7] 이메일 작성 및 발송")
    html_body = build_html_email(result_df, bsns_year, us_result_df=us_result_df)
    subject = build_subject(result_df, bsns_year, us_result_df=us_result_df)
    send_email(subject, html_body)

    us_count = len(us_result_df) if us_result_df is not None and not us_result_df.empty else 0
    logger.info("=" * 60)
    logger.info(f"완료. KR 선별: {len(result_df)}개 / US 선별: {us_count}개")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
