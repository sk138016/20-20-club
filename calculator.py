import logging
import pandas as pd

from config import OPERATING_MARGIN_MIN, ROE_MIN, MARKET_LABEL, REVENUE_GROWTH_MIN, REVENUE_GROWTH_YEARS

logger = logging.getLogger(__name__)

# DART account_nm 매핑 — 앞쪽일수록 우선순위 높음
REVENUE_NAMES = ["매출액", "수익(매출액)", "영업수익", "매출"]
OPERATING_INCOME_NAMES = ["영업이익", "영업이익(손실)", "영업손실"]
NET_INCOME_NAMES = ["당기순이익", "당기순이익(손실)", "당기순손실", "분기순이익", "반기순이익"]
EQUITY_NAMES = ["자본총계", "자본 총계", "지배기업 소유주지분"]


def _parse_amount(value_str):
    """DART 금액 문자열("1,234,567") → float. 파싱 불가 시 None."""
    if value_str is None:
        return None
    s = str(value_str).strip().replace(",", "").replace(" ", "")
    if s in ("", "-", "N/A", "nan"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _find_account_value(df, account_names):
    """
    DataFrame 에서 account_nm 이 일치하는 계정의 thstrm_amount 반환.
    정확 일치 우선, 없으면 부분 일치.
    """
    if df is None or df.empty:
        return None

    for name in account_names:
        match = df[df["account_nm"].str.strip() == name]
        if not match.empty:
            val = _parse_amount(match.iloc[0]["thstrm_amount"])
            if val is not None:
                return val

    for name in account_names:
        match = df[df["account_nm"].str.contains(name, na=False, regex=False)]
        if not match.empty:
            val = _parse_amount(match.iloc[0]["thstrm_amount"])
            if val is not None:
                return val

    return None


def _compute_metrics(corp_code, corp_name, stock_code, corp_cls, fin_df):
    """
    영업이익률·ROE 계산.
    매출 또는 자본이 0 이하면 None 반환 (자본잠식·의미없는 비율 방지).
    """
    revenue = _find_account_value(fin_df, REVENUE_NAMES)
    op_income = _find_account_value(fin_df, OPERATING_INCOME_NAMES)
    net_income = _find_account_value(fin_df, NET_INCOME_NAMES)
    equity = _find_account_value(fin_df, EQUITY_NAMES)

    if any(v is None for v in [revenue, op_income, net_income, equity]):
        logger.debug(
            f"{corp_code}({corp_name}): 계정 누락 "
            f"rev={revenue} op={op_income} net={net_income} eq={equity}"
        )
        return None

    if revenue <= 0 or equity <= 0:
        return None

    return {
        "corp_code": corp_code,
        "stock_code": stock_code,
        "corp_name": corp_name,
        "market": MARKET_LABEL.get(corp_cls, corp_cls),
        "op_margin": round((op_income / revenue) * 100, 2),
        "roe": round((net_income / equity) * 100, 2),
        "revenue": revenue,
    }


def screen_companies(companies_df, financial_data, bsns_year):
    """
    20-20 Club 필터 적용.
    영업이익률 ≥ 20% AND ROE ≥ 20% 인 기업만 선별하여 정렬된 DataFrame 반환.
    """
    results = []

    for _, row in companies_df.iterrows():
        fin_df = financial_data.get(row["corp_code"])
        if fin_df is None:
            continue

        metrics = _compute_metrics(
            corp_code=row["corp_code"],
            corp_name=row["corp_name"],
            stock_code=row["stock_code"],
            corp_cls=row["corp_cls"],
            fin_df=fin_df,
        )
        if metrics is None:
            continue

        if metrics["op_margin"] >= OPERATING_MARGIN_MIN and metrics["roe"] >= ROE_MIN:
            metrics["base_year"] = bsns_year
            results.append(metrics)

    if not results:
        logger.warning("20-20 Club 기준을 충족하는 기업이 없습니다.")
        return pd.DataFrame()

    df = (
        pd.DataFrame(results)
        .sort_values(["op_margin", "roe"], ascending=[False, False])
        .reset_index(drop=True)
    )
    df.insert(0, "rank", range(1, len(df) + 1))
    logger.info(f"20-20 Club 선별 완료: {len(df)}개 기업")
    return df


def add_revenue_growth(result_df, past_revenues, bsns_year):
    """
    result_df 에 rev_cagr(%), growth_flag 컬럼을 추가해 반환.

    CAGR = (R_bsns_year / R_{bsns_year-REVENUE_GROWTH_YEARS})^(1/n) - 1
    과거 데이터 없으면 rev_cagr=None, growth_flag=False.
    result_df 에 'revenue' 컬럼이 있어야 함 (_compute_metrics 가 저장).
    """
    rev_cagrs = []
    growth_flags = []

    for _, row in result_df.iterrows():
        r_latest = row.get("revenue")
        r_oldest = past_revenues.get(row["corp_code"], {}).get(bsns_year - REVENUE_GROWTH_YEARS)

        cagr = None
        if r_latest and r_oldest and r_oldest > 0:
            cagr = round(((r_latest / r_oldest) ** (1 / REVENUE_GROWTH_YEARS) - 1) * 100, 1)

        rev_cagrs.append(cagr)
        growth_flags.append(cagr is not None and cagr >= REVENUE_GROWTH_MIN)

    df = result_df.copy()
    df["rev_cagr"] = rev_cagrs
    df["growth_flag"] = growth_flags
    flagged = int(df["growth_flag"].sum())
    logger.info(f"매출 고성장 기업 (연평균 ≥{REVENUE_GROWTH_MIN}%): {flagged}개")
    return df
