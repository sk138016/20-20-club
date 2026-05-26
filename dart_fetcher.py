import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pandas as pd
import OpenDartReader as _ODR

from config import (
    DART_API_KEY, REPRT_CODE_ANNUAL,
    FS_DIV_CONSOLIDATED, FS_DIV_INDIVIDUAL,
    MARKET_KOSPI, MARKET_KOSDAQ,
    MAX_WORKERS, REQUEST_DELAY_SECONDS,
)

logger = logging.getLogger(__name__)


def get_dart_instance():
    return _ODR(DART_API_KEY)


def get_listed_companies(dart):
    """dart.corp_codes 에서 stock_code 가 있는 상장사만 반환."""
    logger.info("DART 전체 기업 목록 취득 중...")
    all_corps = dart.corp_codes
    listed = all_corps[
        all_corps["stock_code"].notna() &
        (all_corps["stock_code"].str.strip() != "")
    ].copy()
    logger.info(f"상장사 수: {len(listed)}개")
    return listed


def _market_tickers_via_fdr():
    """
    FinanceDataReader 로 KOSPI·KOSDAQ 종목코드 세트 반환.
    KRX KIND 파일 다운로드 엔드포인트 사용 (pykrx JSON API와 다름).
    """
    import FinanceDataReader as fdr
    kospi  = set(fdr.StockListing('KOSPI')['Code'].astype(str).str.zfill(6))
    kosdaq = set(fdr.StockListing('KOSDAQ')['Code'].astype(str).str.zfill(6))
    return kospi, kosdaq


def _market_cls_via_dart_list(dart):
    """
    DART 공시 목록(사업보고서)에서 corp_code → corp_cls 매핑 구성.
    KRX API 불필요 — DART 서버만 사용.
    """
    cls_map = {}
    now = datetime.now()
    # 최근 2개 연도 사업보고서 접수 기간 조회 (1~4월)
    for year in [now.year, now.year - 1]:
        for start, end in [
            (f"{year}0101", f"{year}0131"),
            (f"{year}0201", f"{year}0228"),
            (f"{year}0301", f"{year}0331"),
            (f"{year}0401", f"{year}0430"),
        ]:
            try:
                df = dart.list(start=start, end=end, kind='A')
                if df is not None and not df.empty and 'corp_cls' in df.columns:
                    for _, row in df.iterrows():
                        cls_map[row['corp_code']] = row['corp_cls']
            except Exception:
                pass
    return cls_map


def get_kr_sector_map(dart, stock_codes, listed_df):
    """
    DART company() API 로 선별된 종목코드 목록의 업종 매핑 반환.
    stock_codes: 조회할 종목코드 리스트 (6자리 문자열)
    listed_df: dart.corp_codes 기반 DataFrame (stock_code, corp_code 포함)
    업종코드(KSIC)를 간소화된 한국어 섹터명으로 변환.
    """
    KSIC_SECTOR = {
        "261": "반도체", "262": "전자부품", "263": "통신장비",
        "264": "소비자가전", "265": "의료기기", "266": "반도체",
        "01": "농업", "02": "임업", "03": "어업",
        "05": "석탄/석유", "06": "석탄/석유", "07": "금속광업",
        "08": "비금속광업", "10": "식품", "11": "음료", "12": "담배",
        "13": "섬유", "14": "의류/패션", "15": "가죽/신발",
        "16": "목재", "17": "제지", "18": "인쇄", "19": "석유화학",
        "20": "화학", "21": "제약", "22": "고무/플라스틱",
        "23": "비금속광물", "24": "철강/금속", "25": "금속제품",
        "26": "전자/반도체", "27": "전기장비", "28": "기계",
        "29": "자동차", "30": "기타운송", "31": "가구",
        "32": "기타제조", "33": "산업기계수리", "35": "전기/가스",
        "41": "건설", "42": "건설", "45": "자동차판매",
        "46": "도소매", "47": "소매", "49": "육상운송",
        "50": "수상운송", "51": "항공운송", "52": "물류",
        "55": "숙박", "56": "음식점", "58": "IT소프트웨어",
        "59": "영상/방송", "60": "방송", "61": "통신",
        "62": "IT서비스", "63": "인터넷", "64": "금융",
        "65": "보험", "66": "금융서비스", "68": "부동산",
        "70": "연구개발", "71": "전문서비스", "72": "과학기술",
        "73": "광고", "74": "기타전문서비스",
        "78": "고용서비스", "79": "여행", "80": "경비",
        "82": "사무지원", "85": "교육",
        "86": "의료/병원", "87": "사회복지",
        "90": "예술/창작", "91": "스포츠/오락",
    }

    stock_to_corp = dict(
        zip(
            listed_df["stock_code"].astype(str).str.zfill(6),
            listed_df["corp_code"],
        )
    )

    sector_map = {}
    logger.info(f"섹터 조회 중 ({len(stock_codes)}개 종목)...")
    for stock_code in stock_codes:
        corp_code = stock_to_corp.get(str(stock_code).zfill(6))
        if not corp_code:
            continue
        try:
            time.sleep(0.2)
            info = dart.company(corp_code)
            induty = str(info.get("induty_code", "") or "").strip()
            if not induty:
                continue
            sector = None
            for prefix_len in (3, 2):
                key = induty[:prefix_len]
                if key in KSIC_SECTOR:
                    sector = KSIC_SECTOR[key]
                    break
            if sector:
                sector_map[str(stock_code).zfill(6)] = sector
        except Exception as e:
            logger.debug(f"섹터 조회 실패 ({stock_code}): {e}")

    logger.info(f"섹터 매핑 완료: {len(sector_map)}/{len(stock_codes)}개")
    return sector_map


def enrich_with_market_type(dart, listed_df):
    """시장 구분(KOSPI/KOSDAQ) 매핑. FDR 우선, 실패 시 DART list API 폴백."""
    kospi_tickers, kosdaq_tickers = set(), set()

    # 1차: FinanceDataReader
    try:
        logger.info("FinanceDataReader 로 KOSPI/KOSDAQ 종목 목록 취득 중...")
        kospi_tickers, kosdaq_tickers = _market_tickers_via_fdr()
        logger.info(f"  KOSPI: {len(kospi_tickers)}개 / KOSDAQ: {len(kosdaq_tickers)}개")
    except Exception as e:
        logger.warning(f"FinanceDataReader 실패 ({e}), DART list API 폴백 사용")

    if not kospi_tickers and not kosdaq_tickers:
        # 2차: DART list API
        logger.info("DART 공시 목록에서 시장 구분 조회 중...")
        cls_map = _market_cls_via_dart_list(dart)
        df = listed_df.copy()
        df["corp_cls"] = df["corp_code"].map(cls_map)
        filtered = df[df["corp_cls"].isin([MARKET_KOSPI, MARKET_KOSDAQ])].copy()
        logger.info(f"KOSPI+KOSDAQ 기업 수: {len(filtered)}개")
        return filtered

    def get_cls(stock_code):
        code = str(stock_code).zfill(6)
        if code in kospi_tickers:
            return MARKET_KOSPI
        if code in kosdaq_tickers:
            return MARKET_KOSDAQ
        return None

    df = listed_df.copy()
    df["corp_cls"] = df["stock_code"].apply(get_cls)
    filtered = df[df["corp_cls"].isin([MARKET_KOSPI, MARKET_KOSDAQ])].copy()
    logger.info(f"KOSPI+KOSDAQ 기업 수: {len(filtered)}개")
    return filtered


def determine_target_year():
    """가장 최근 사업연도 결정. 4월 이후면 전년도, 1~3월이면 전전년도."""
    now = datetime.now()
    return now.year - 1 if now.month >= 4 else now.year - 2


def _fetch_finstate(dart, corp_code, bsns_year, retries=3):
    """
    단일 기업 재무제표 조회.
    연결(CFS) 우선, 없으면 별도(OFS) 반환.
    실패 시 None 반환.
    """
    for attempt in range(retries):
        try:
            df = dart.finstate(corp_code, bsns_year, reprt_code=REPRT_CODE_ANNUAL)
            if df is None or df.empty:
                return None

            cfs = df[df["fs_div"] == FS_DIV_CONSOLIDATED]
            if not cfs.empty:
                return cfs

            ofs = df[df["fs_div"] == FS_DIV_INDIVIDUAL]
            if not ofs.empty:
                return ofs

            return df
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                logger.debug(f"finstate({corp_code}, {bsns_year}) 실패: {e}")
    return None


def fetch_all_financials(dart, companies_df, bsns_year):
    """
    전체 기업 재무제표를 스레드풀로 병렬 수집.
    반환: { corp_code: DataFrame }
    """
    corp_codes = companies_df["corp_code"].tolist()
    financial_data = {}
    lock = threading.Lock()

    def worker(corp_code):
        time.sleep(REQUEST_DELAY_SECONDS)
        df = _fetch_finstate(dart, corp_code, bsns_year)
        if df is not None:
            with lock:
                financial_data[corp_code] = df

    logger.info(f"재무제표 수집 중 ({len(corp_codes)}개 기업, 기준연도={bsns_year})...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(worker, cc) for cc in corp_codes]
        for i, _ in enumerate(as_completed(futures), 1):
            if i % 200 == 0:
                logger.info(f"  재무제표 진행: {i}/{len(corp_codes)}")

    logger.info(f"재무제표 수집 완료: {len(financial_data)}개")
    return financial_data


def fetch_past_revenues(dart, corp_codes, bsns_year, years_back=2):
    """
    선별된 기업의 과거 매출액 수집 (CAGR 계산용).
    반환: { corp_code: { year: revenue_float } }
    bsns_year - years_back 부터 bsns_year - 1 까지 조회.
    """
    from calculator import REVENUE_NAMES, _find_account_value

    target_years = [bsns_year - i for i in range(1, years_back + 1)]
    results = {cc: {} for cc in corp_codes}
    lock = threading.Lock()

    def worker(corp_code, year):
        time.sleep(REQUEST_DELAY_SECONDS)
        fin_df = _fetch_finstate(dart, corp_code, year)
        revenue = _find_account_value(fin_df, REVENUE_NAMES) if fin_df is not None else None
        if revenue is not None and revenue > 0:
            with lock:
                results[corp_code][year] = revenue

    tasks = [(cc, yr) for cc in corp_codes for yr in target_years]
    logger.info(f"과거 매출액 수집 중 ({len(corp_codes)}개 기업 × {years_back}년)...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(worker, cc, yr) for cc, yr in tasks]
        for _ in as_completed(futures):
            pass

    logger.info("과거 매출액 수집 완료")
    return results
