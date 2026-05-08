"""
Daily technical signal screener for KOSPI/KOSDAQ stocks.

Conditions:
  A. [Bandwidth15%이하, 상단터치]  — 일봉 BB(20) 밴드폭 ≤ 15% + 종가 ≥ 상단선
  B. [포카라 80일 BB, 하방터치]   — 일봉 BB(80) 종가 ≤ 하단선
  C. [RSI<30, MACD OSC 추세 전환] — 주봉 RSI(14) < 30 + MACD 오실레이터 2봉 연속 상승
"""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import FinanceDataReader as fdr

logger = logging.getLogger(__name__)

TECH_MAX_WORKERS = 15
DAILY_LOOKBACK_DAYS = 310  # BB(80) + 충분한 여유

# Bollinger Band
BB_SHORT = 20
BB_LONG = 80
BB_STD = 2
BANDWIDTH_MAX = 0.15  # 15%

# RSI / MACD (주봉)
RSI_PERIOD = 14
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL_PERIOD = 9


# ---------------------------------------------------------------------------
# 지표 계산
# ---------------------------------------------------------------------------

def _normalize(df):
    """열 이름 대문자 통일 + DatetimeIndex 보장."""
    df = df.copy()
    df.columns = df.columns.str.capitalize()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    return df


def _bb_last(close: pd.Series, period: int, std_mult: float = 2.0):
    """BB 마지막 행 → (upper, lower, bandwidth). 데이터 부족 시 None 튜플."""
    if len(close) < period:
        return None, None, None
    ma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = (ma + std_mult * std).iloc[-1]
    lower = (ma - std_mult * std).iloc[-1]
    mid = ma.iloc[-1]
    if mid == 0:
        return None, None, None
    return upper, lower, (upper - lower) / mid


def _rsi_last(close: pd.Series, period: int = 14):
    """EWM 방식 RSI 마지막 값. 데이터 부족 시 None."""
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return (100 - 100 / (1 + rs)).iloc[-1]


def _macd_hist_last3(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD 히스토그램 마지막 3개 값 → (h-2, h-1, h0). 부족 시 None."""
    if len(close) < slow + signal:
        return None
    ema_f = close.ewm(span=fast, adjust=False).mean()
    ema_s = close.ewm(span=slow, adjust=False).mean()
    hist = (ema_f - ema_s) - (ema_f - ema_s).ewm(span=signal, adjust=False).mean()
    if len(hist) < 3:
        return None
    return hist.iloc[-3], hist.iloc[-2], hist.iloc[-1]


# ---------------------------------------------------------------------------
# 데이터 수집
# ---------------------------------------------------------------------------

def _fetch(code: str, start_date: str):
    """FDR 일봉 OHLCV 수집. 실패 또는 데이터 부족 시 None."""
    try:
        df = fdr.DataReader(code, start=start_date)
        if df is None or df.empty:
            return None
        df = _normalize(df)
        if "Close" not in df.columns:
            return None
        df = df[df["Close"] > 0].dropna(subset=["Close"])
        return df if len(df) >= 25 else None
    except Exception:
        return None


def _to_weekly(df_daily: pd.DataFrame) -> pd.DataFrame:
    """일봉 → 주봉 리샘플."""
    return (
        df_daily.resample("W")
        .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
        .dropna(subset=["Close"])
    )


# ---------------------------------------------------------------------------
# 신호 판별
# ---------------------------------------------------------------------------

def _check_signals(code: str, name: str, market: str, df: pd.DataFrame) -> dict:
    """세 가지 조건을 순차 체크. 발동된 조건만 dict에 포함."""
    close = df["Close"]
    signals = {}

    # A. 일봉 BB(20) 밴드폭 ≤ 15% + 종가 ≥ 상단선
    upper20, _, bw20 = _bb_last(close, BB_SHORT, BB_STD)
    if bw20 is not None and bw20 <= BANDWIDTH_MAX and close.iloc[-1] >= upper20:
        signals["A"] = {
            "bandwidth_pct": round(bw20 * 100, 2),
            "upper_band": round(upper20, 0),
            "close": round(close.iloc[-1], 0),
        }

    # B. 일봉 BB(80) 종가 ≤ 하단선
    if len(close) >= BB_LONG:
        _, lower80, _ = _bb_last(close, BB_LONG, BB_STD)
        if lower80 is not None and close.iloc[-1] <= lower80:
            signals["B"] = {
                "lower_band": round(lower80, 0),
                "close": round(close.iloc[-1], 0),
            }

    # C. 주봉 RSI < 30 + MACD 오실레이터 2봉 연속 상승
    df_w = _to_weekly(df)
    if len(df_w) >= 35:
        w_close = df_w["Close"]
        rsi = _rsi_last(w_close, RSI_PERIOD)
        hist3 = _macd_hist_last3(w_close, MACD_FAST, MACD_SLOW, MACD_SIGNAL_PERIOD)
        if rsi is not None and hist3 is not None:
            h2, h1, h0 = hist3
            if rsi < RSI_OVERSOLD and h0 > h1 > h2:
                signals["C"] = {
                    "rsi": round(rsi, 1),
                    "macd_hist": round(h0, 4),
                    "close": round(close.iloc[-1], 0),
                }

    return signals


# ---------------------------------------------------------------------------
# 보조 함수
# ---------------------------------------------------------------------------

def _get_stock_list() -> pd.DataFrame:
    """FDR에서 KOSPI + KOSDAQ 종목 목록 반환 (Code, Name, Market)."""
    kospi = fdr.StockListing("KOSPI")[["Code", "Name"]].copy()
    kospi["Market"] = "KOSPI"
    kosdaq = fdr.StockListing("KOSDAQ")[["Code", "Name"]].copy()
    kosdaq["Market"] = "KOSDAQ"
    df = pd.concat([kospi, kosdaq], ignore_index=True)
    df["Code"] = df["Code"].astype(str).str.zfill(6)
    df["Name"] = df["Name"].fillna("(이름 없음)")
    return df.drop_duplicates(subset=["Code"])


def _load_club_codes():
    """캐시된 20-20 Club 종목코드 로딩. 파일 없으면 (빈 set, None) 반환."""
    path = Path("data/2020_club.json")
    if not path.exists():
        logger.warning("data/2020_club.json 없음 — 20-20 Club 표시 비활성")
        return set(), None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    codes = {str(c).zfill(6) for c in data.get("kr_stock_codes", [])}
    return codes, data.get("updated_at")


# ---------------------------------------------------------------------------
# 메인 진입점
# ---------------------------------------------------------------------------

def run_technical_screener() -> dict:
    """
    KOSPI+KOSDAQ 전종목 기술적 신호 스캔.
    반환: {"A": [...], "B": [...], "C": [...], "scan_date": str,
           "club_updated": str, "total": int}
    """
    start_date = (datetime.now() - timedelta(days=DAILY_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    scan_date = datetime.now().strftime("%Y-%m-%d")

    logger.info("종목 목록 로딩 중...")
    stocks = _get_stock_list()
    logger.info(f"스캔 대상: {len(stocks)}개 종목")

    club_codes, club_updated = _load_club_codes()
    logger.info(f"20-20 Club 캐시: {len(club_codes)}개 (기준일: {club_updated})")

    results: dict[str, list] = {"A": [], "B": [], "C": []}
    lock = threading.Lock()

    def worker(row):
        code = row["Code"]
        df = _fetch(code, start_date)
        if df is None:
            return
        fired = _check_signals(code, row["Name"], row["Market"], df)
        if not fired:
            return
        base = {
            "code": code,
            "name": row["Name"],
            "market": row["Market"],
            "is_2020_club": code in club_codes,
        }
        with lock:
            for key, extra in fired.items():
                results[key].append({**base, **extra})

    logger.info("기술적 신호 스캔 시작...")
    with ThreadPoolExecutor(max_workers=TECH_MAX_WORKERS) as executor:
        futures = [executor.submit(worker, row) for _, row in stocks.iterrows()]
        total = len(futures)
        for i, _ in enumerate(as_completed(futures), 1):
            if i % 500 == 0:
                logger.info(f"  진행: {i}/{total}")

    # 20-20 Club 먼저, 이후 종목코드 순
    for key in results:
        results[key].sort(key=lambda x: (not x["is_2020_club"], x["code"]))

    count_a, count_b, count_c = len(results["A"]), len(results["B"]), len(results["C"])
    logger.info(f"스캔 완료 — A: {count_a}개 | B: {count_b}개 | C: {count_c}개")

    return {
        **results,
        "scan_date": scan_date,
        "club_updated": club_updated or "(미업데이트)",
        "total": count_a + count_b + count_c,
    }
