import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import yfinance as yf

from config import OPERATING_MARGIN_MIN, ROE_MIN, REVENUE_GROWTH_MIN, REVENUE_GROWTH_YEARS

logger = logging.getLogger(__name__)

_MAX_WORKERS = 5
_DELAY = 0.5   # Yahoo Finance 레이트 리밋 방지용 딜레이 (초)


def _get_sp500_constituents():
    """Wikipedia에서 S&P 500 구성 종목 목록 취득."""
    from io import StringIO
    import requests as _req
    html = _req.get(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        headers={"User-Agent": "Mozilla/5.0 (compatible; research script)"},
        timeout=15,
    ).text
    tables = pd.read_html(StringIO(html))
    df = tables[0][["Symbol", "Security", "GICS Sector"]].copy()
    df["Symbol"] = df["Symbol"].str.replace(".", "-", regex=False)  # BRK.B → BRK-B
    return df.rename(columns={"Symbol": "symbol", "Security": "name", "GICS Sector": "sector"})


def _calc_rev_cagr(ticker_obj):
    """
    연간 재무제표에서 REVENUE_GROWTH_YEARS 기간 매출 CAGR(%) 계산.
    데이터 부족·오류 시 None 반환.
    """
    try:
        fin = ticker_obj.financials  # 연간, 최신순 컬럼
        if fin is None or fin.empty:
            return None
        if "Total Revenue" not in fin.index:
            return None
        rev = fin.loc["Total Revenue"].dropna()
        if len(rev) <= REVENUE_GROWTH_YEARS:
            return None
        r_new = rev.iloc[0]
        r_old = rev.iloc[REVENUE_GROWTH_YEARS]
        if r_new > 0 and r_old > 0:
            return round(((r_new / r_old) ** (1 / REVENUE_GROWTH_YEARS) - 1) * 100, 1)
    except Exception:
        pass
    return None


def _fetch_company(symbol, name, sector):
    """
    단일 기업 TTM 재무 지표 + 매출 CAGR 조회.
    기준 미달·데이터 누락·오류 시 None 반환.
    """
    time.sleep(_DELAY)
    try:
        t = yf.Ticker(symbol)
        info = t.info
        if not info:
            return None

        op_raw = info.get("operatingMargins")   # TTM, 소수 (0.25 = 25%)
        roe_raw = info.get("returnOnEquity")    # TTM, 소수
        if op_raw is None or roe_raw is None:
            return None

        op_margin = op_raw * 100
        roe = roe_raw * 100

        if op_margin < OPERATING_MARGIN_MIN or roe < ROE_MIN:
            return None

        # bookValue(주당 장부가) ≤ 0 이면 자본총계 ≤ 0 → ROE 왜곡 가능, 제외
        book_value = info.get("bookValue")
        if book_value is not None and book_value <= 0:
            return None

        rev_cagr = _calc_rev_cagr(t)

        return {
            "symbol": symbol,
            "corp_name": info.get("shortName") or info.get("longName") or name,
            "sector": info.get("sector") or sector,
            "op_margin": round(op_margin, 2),
            "roe": round(roe, 2),
            "rev_cagr": rev_cagr,
            "growth_flag": rev_cagr is not None and rev_cagr >= REVENUE_GROWTH_MIN,
        }
    except Exception as e:
        logger.debug(f"yfinance {symbol}: {e}")
        return None


def screen_sp500():
    """
    S&P 500 기업 중 영업이익률 ≥ 20% AND ROE ≥ 20% (TTM) 기업 선별.
    오류 시 None 반환, 결과 없으면 빈 DataFrame 반환.
    """
    logger.info("S&P 500 구성 종목 조회 중 (Wikipedia)...")
    try:
        sp500_df = _get_sp500_constituents()
    except Exception as e:
        logger.error(f"S&P 500 목록 조회 실패: {e}")
        return None
    logger.info(f"  S&P 500 종목 수: {len(sp500_df)}개")

    results = []
    lock = threading.Lock()
    constituents = sp500_df.to_dict("records")

    def worker(item):
        res = _fetch_company(item["symbol"], item["name"], item["sector"])
        if res:
            with lock:
                results.append(res)

    logger.info(f"TTM 재무 지표 수집 중 ({len(constituents)}개)...")
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        futures = [executor.submit(worker, c) for c in constituents]
        for i, _ in enumerate(as_completed(futures), 1):
            if i % 100 == 0:
                logger.info(f"  진행: {i}/{len(constituents)}")

    if not results:
        logger.warning("S&P 500 20-20 Club 기준 충족 기업 없음")
        return pd.DataFrame()

    df = (
        pd.DataFrame(results)
        .sort_values(["op_margin", "roe"], ascending=[False, False])
        .drop_duplicates(subset=["corp_name"])   # GOOGL/GOOG 등 동일 기업 복수 주식 제거
        .reset_index(drop=True)
    )
    df.insert(0, "rank", range(1, len(df) + 1))
    logger.info(f"S&P 500 20-20 Club 선별 완료: {len(df)}개 기업")
    return df
