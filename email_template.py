from datetime import datetime


def build_subject(result_df, bsns_year, us_result_df=None):
    kr_count = len(result_df)
    month = datetime.now().strftime("%Y년 %m월")
    if us_result_df is not None and not us_result_df.empty:
        us_count = len(us_result_df)
        return f"[20-20 Club] {month} 선별: KR {kr_count}개 · US {us_count}개 ({bsns_year}년 / TTM)"
    return f"[20-20 Club] {month} 선별 결과: {kr_count}개 기업 ({bsns_year}년 기준)"


def _build_kr_rows(result_df):
    has_growth = "growth_flag" in result_df.columns
    rows_html = ""
    for _, row in result_df.iterrows():
        badge_color = "#1a73e8" if row["market"] == "KOSPI" else "#34a853"
        is_growth = has_growth and bool(row.get("growth_flag", False))

        if is_growth:
            bg = "#fffde7"
            left_border = "border-left:4px solid #f9a825;"
        else:
            bg = "#fafafa" if int(row["rank"]) % 2 == 0 else "#ffffff"
            left_border = ""

        if has_growth:
            cagr = row.get("rev_cagr")
            if cagr is not None:
                cagr_color = "#e65100" if is_growth else "#555"
                cagr_html = (f'<td style="padding:10px 12px;text-align:right;font-weight:bold;'
                             f'color:{cagr_color}">{cagr:.1f}%</td>')
            else:
                cagr_html = '<td style="padding:10px 12px;text-align:center;color:#bbb">-</td>'
        else:
            cagr_html = ""

        growth_badge = (' <span style="background:#f9a825;color:white;padding:1px 6px;'
                        'border-radius:8px;font-size:10px;font-weight:bold">고성장</span>') if is_growth else ""

        rows_html += f"""
        <tr style="background:{bg};{left_border}">
          <td style="padding:10px 12px;text-align:center;font-weight:bold;color:#555">{int(row['rank'])}</td>
          <td style="padding:10px 12px;font-family:monospace;font-size:13px">{row['stock_code']}</td>
          <td style="padding:10px 12px;font-weight:bold">{row['corp_name']}{growth_badge}</td>
          <td style="padding:10px 12px;text-align:center">
            <span style="background:{badge_color};color:white;padding:2px 8px;
                         border-radius:10px;font-size:11px;font-weight:bold">
              {row['market']}
            </span>
          </td>
          <td style="padding:10px 12px;text-align:right;font-weight:bold;color:#c62828">{row['op_margin']:.1f}%</td>
          <td style="padding:10px 12px;text-align:right;font-weight:bold;color:#1b5e20">{row['roe']:.1f}%</td>
          {cagr_html}
          <td style="padding:10px 12px;text-align:center;color:#666">{int(row['base_year'])}</td>
        </tr>"""
    return rows_html, has_growth


def _build_us_section(us_result_df):
    """미국 시장 섹션 HTML 전체 생성."""
    if us_result_df is None:
        return ""

    has_growth = "growth_flag" in us_result_df.columns
    growth_count = int(us_result_df["growth_flag"].sum()) if has_growth else 0

    if us_result_df.empty:
        colspan = "7" if has_growth else "6"
        rows_html = f"""
        <tr>
          <td colspan="{colspan}" style="padding:40px;text-align:center;color:#999;font-size:14px">
            이번 기준을 충족하는 S&amp;P 500 기업이 없습니다.
          </td>
        </tr>"""
    else:
        rows_html = ""
        for _, row in us_result_df.iterrows():
            is_growth = has_growth and bool(row.get("growth_flag", False))

            if is_growth:
                bg = "#fffde7"
                left_border = "border-left:4px solid #f9a825;"
            else:
                bg = "#fafafa" if int(row["rank"]) % 2 == 0 else "#ffffff"
                left_border = ""

            if has_growth:
                cagr = row.get("rev_cagr")
                if cagr is not None:
                    cagr_color = "#e65100" if is_growth else "#555"
                    cagr_html = (f'<td style="padding:10px 12px;text-align:right;font-weight:bold;'
                                 f'color:{cagr_color}">{cagr:.1f}%</td>')
                else:
                    cagr_html = '<td style="padding:10px 12px;text-align:center;color:#bbb">-</td>'
            else:
                cagr_html = ""

            growth_badge = (' <span style="background:#f9a825;color:white;padding:1px 6px;'
                            'border-radius:8px;font-size:10px;font-weight:bold">고성장</span>') if is_growth else ""

            rows_html += f"""
        <tr style="background:{bg};{left_border}">
          <td style="padding:10px 12px;text-align:center;font-weight:bold;color:#555">{int(row['rank'])}</td>
          <td style="padding:10px 12px;font-family:monospace;font-size:13px;font-weight:bold">{row['symbol']}</td>
          <td style="padding:10px 12px;font-weight:bold">{row['corp_name']}{growth_badge}</td>
          <td style="padding:10px 12px;color:#555;font-size:12px">{row['sector']}</td>
          <td style="padding:10px 12px;text-align:right;font-weight:bold;color:#c62828">{row['op_margin']:.1f}%</td>
          <td style="padding:10px 12px;text-align:right;font-weight:bold;color:#1b5e20">{row['roe']:.1f}%</td>
          {cagr_html}
        </tr>"""

    growth_note = (f"&nbsp;|&nbsp; <span style='color:#f9a825;font-weight:bold'>★ 고성장</span>"
                   f" = 연평균 매출증가율 ≥ 10% ({growth_count}개)") if has_growth else ""

    return f"""
  <!-- 미국 시장 섹션 헤더 -->
  <div style="padding:24px 32px 0;border-top:2px solid #e8e8e8;margin-top:8px">
    <div style="font-size:15px;font-weight:bold;color:#b71c1c;
                padding-bottom:10px;border-bottom:2px solid #b71c1c">
      미국 시장 (S&amp;P 500)
    </div>
  </div>

  <!-- 미국 필터 안내 -->
  <div style="padding:10px 32px;background:#fff8f8;
              border-bottom:1px solid #e8e8e8;font-size:12px;color:#666">
    영업이익률 = 영업이익 ÷ 매출액 × 100 &nbsp;|&nbsp;
    ROE = 당기순이익 ÷ 자본총계 × 100 &nbsp;|&nbsp;
    기준: TTM (최근 12개월) &nbsp;|&nbsp;
    자본총계 ≤ 0 기업 제외 &nbsp;|&nbsp;
    데이터: yfinance (Yahoo Finance)
    {growth_note}
  </div>

  <!-- 미국 결과 테이블 -->
  <div style="padding:24px 32px">
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="background:#f1f3f4">
          <th style="padding:11px 12px;text-align:center;border-bottom:2px solid #b71c1c;
                     color:#333;white-space:nowrap">순위</th>
          <th style="padding:11px 12px;text-align:left;border-bottom:2px solid #b71c1c;
                     color:#333;white-space:nowrap">티커</th>
          <th style="padding:11px 12px;text-align:left;border-bottom:2px solid #b71c1c;
                     color:#333">종목명</th>
          <th style="padding:11px 12px;text-align:left;border-bottom:2px solid #b71c1c;
                     color:#333">섹터</th>
          <th style="padding:11px 12px;text-align:right;border-bottom:2px solid #b71c1c;
                     color:#c62828;white-space:nowrap">영업이익률(%)</th>
          <th style="padding:11px 12px;text-align:right;border-bottom:2px solid #b71c1c;
                     color:#1b5e20;white-space:nowrap">ROE(%)</th>
          {"<th style='padding:11px 12px;text-align:right;border-bottom:2px solid #b71c1c;color:#e65100;white-space:nowrap'>매출증가율(%)</th>" if has_growth else ""}
        </tr>
      </thead>
      <tbody>{rows_html}
      </tbody>
    </table>
  </div>"""


def build_html_email(result_df, bsns_year, us_result_df=None):
    run_date = datetime.now().strftime("%Y년 %m월 %d일")
    kr_count = len(result_df)
    has_us = us_result_df is not None
    us_count = len(us_result_df) if has_us and not us_result_df.empty else 0

    has_growth = "growth_flag" in result_df.columns
    growth_count = int(result_df["growth_flag"].sum()) if has_growth else 0

    # 요약 카드
    if has_us:
        summary_cards = f"""
    <div style="flex:1;padding:22px 0;text-align:center;border-right:1px solid #e8e8e8">
      <div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">한국 (KOSPI+KOSDAQ)</div>
      <div style="font-size:34px;font-weight:bold;color:#1a237e">{kr_count}</div>
      <div style="font-size:12px;color:#999;margin-top:4px">선별 기업 수</div>
    </div>
    <div style="flex:1;padding:22px 0;text-align:center;border-right:1px solid #e8e8e8">
      <div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">미국 (S&amp;P 500)</div>
      <div style="font-size:34px;font-weight:bold;color:#b71c1c">{us_count}</div>
      <div style="font-size:12px;color:#999;margin-top:4px">선별 기업 수</div>
    </div>
    <div style="flex:1;padding:22px 0;text-align:center;border-right:1px solid #e8e8e8">
      <div style="font-size:34px;font-weight:bold;color:#c62828">≥ 20%</div>
      <div style="font-size:12px;color:#999;margin-top:4px">최소 영업이익률</div>
    </div>
    <div style="flex:1;padding:22px 0;text-align:center">
      <div style="font-size:34px;font-weight:bold;color:#1b5e20">≥ 20%</div>
      <div style="font-size:12px;color:#999;margin-top:4px">최소 ROE</div>
    </div>"""
    else:
        summary_cards = f"""
    <div style="flex:1;padding:22px 0;text-align:center;border-right:1px solid #e8e8e8">
      <div style="font-size:38px;font-weight:bold;color:#1a237e">{kr_count}</div>
      <div style="font-size:12px;color:#999;margin-top:4px">선별 기업 수</div>
    </div>
    <div style="flex:1;padding:22px 0;text-align:center;border-right:1px solid #e8e8e8">
      <div style="font-size:38px;font-weight:bold;color:#c62828">≥ 20%</div>
      <div style="font-size:12px;color:#999;margin-top:4px">최소 영업이익률</div>
    </div>
    <div style="flex:1;padding:22px 0;text-align:center">
      <div style="font-size:38px;font-weight:bold;color:#1b5e20">≥ 20%</div>
      <div style="font-size:12px;color:#999;margin-top:4px">최소 ROE</div>
    </div>"""

    # 한국 결과 테이블 행
    kr_rows_html, has_growth = _build_kr_rows(result_df)
    if kr_count == 0:
        colspan = "8" if has_growth else "7"
        kr_rows_html = f"""
        <tr>
          <td colspan="{colspan}" style="padding:40px;text-align:center;color:#999;font-size:14px">
            이번 분기 기준을 충족하는 기업이 없습니다.
          </td>
        </tr>"""

    # 미국 섹션
    us_section_html = _build_us_section(us_result_df)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>20-20 Club 보고서</title>
</head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:'Malgun Gothic',Arial,sans-serif">
<div style="max-width:900px;margin:32px auto;background:white;
            border-radius:12px;overflow:hidden;
            box-shadow:0 4px 24px rgba(0,0,0,0.10)">

  <!-- 헤더 -->
  <div style="background:linear-gradient(135deg,#1a237e 0%,#283593 100%);
              padding:36px 40px;color:white">
    <div style="font-size:28px;font-weight:bold;letter-spacing:-0.5px">
      20-20 Club
    </div>
    <div style="font-size:14px;opacity:0.80;margin-top:6px">
      영업이익률 ≥ 20% &amp; ROE ≥ 20% 우량기업 선별 보고서
    </div>
    <div style="margin-top:14px;font-size:12px;opacity:0.65">
      기준일: {run_date} &nbsp;|&nbsp; KR: {bsns_year}년 사업보고서 (연결재무제표 우선) &nbsp;|&nbsp; US: TTM (최근 12개월)
    </div>
  </div>

  <!-- 요약 카드 -->
  <div style="display:flex;border-bottom:1px solid #e8e8e8">
    {summary_cards}
  </div>

  <!-- 한국 시장 섹션 헤더 -->
  <div style="padding:24px 32px 0">
    <div style="font-size:15px;font-weight:bold;color:#1a237e;
                padding-bottom:10px;border-bottom:2px solid #1a237e">
      한국 시장 (KOSPI + KOSDAQ)
    </div>
  </div>

  <!-- 한국 필터 안내 -->
  <div style="padding:10px 32px;background:#f8f9fa;
              border-bottom:1px solid #e8e8e8;font-size:12px;color:#666">
    영업이익률 = 영업이익 ÷ 매출액 × 100 &nbsp;|&nbsp;
    ROE = 당기순이익 ÷ 자본총계 × 100 &nbsp;|&nbsp;
    대상: KOSPI + KOSDAQ 상장사 전체 &nbsp;|&nbsp;
    자본잠식(자본총계 ≤ 0) 기업 제외
    {f"&nbsp;|&nbsp; <span style='color:#f9a825;font-weight:bold'>★ 고성장</span> = 연평균 매출증가율 ≥ 10% ({growth_count}개)" if has_growth else ""}
  </div>

  <!-- 한국 결과 테이블 -->
  <div style="padding:24px 32px">
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="background:#f1f3f4">
          <th style="padding:11px 12px;text-align:center;border-bottom:2px solid #1a237e;
                     color:#333;white-space:nowrap">순위</th>
          <th style="padding:11px 12px;text-align:left;border-bottom:2px solid #1a237e;
                     color:#333;white-space:nowrap">종목코드</th>
          <th style="padding:11px 12px;text-align:left;border-bottom:2px solid #1a237e;
                     color:#333">종목명</th>
          <th style="padding:11px 12px;text-align:center;border-bottom:2px solid #1a237e;
                     color:#333">시장</th>
          <th style="padding:11px 12px;text-align:right;border-bottom:2px solid #1a237e;
                     color:#c62828;white-space:nowrap">영업이익률(%)</th>
          <th style="padding:11px 12px;text-align:right;border-bottom:2px solid #1a237e;
                     color:#1b5e20;white-space:nowrap">ROE(%)</th>
          {"<th style='padding:11px 12px;text-align:right;border-bottom:2px solid #1a237e;color:#e65100;white-space:nowrap'>매출증가율(%)</th>" if has_growth else ""}
          <th style="padding:11px 12px;text-align:center;border-bottom:2px solid #1a237e;
                     color:#333;white-space:nowrap">기준연도</th>
        </tr>
      </thead>
      <tbody>{kr_rows_html}
      </tbody>
    </table>
  </div>

  {us_section_html}

  <!-- 푸터 -->
  <div style="padding:18px 32px;background:#f8f9fa;border-top:1px solid #e8e8e8;
              font-size:11px;color:#aaa;text-align:center;line-height:1.8">
    본 보고서는 DART(dart.fss.or.kr) 및 Financial Modeling Prep(financialmodelingprep.com) 데이터를 기반으로 자동 생성됩니다.<br>
    투자 판단의 참고 자료로만 활용하시기 바라며, 투자 손실에 대한 책임은 투자자 본인에게 있습니다.<br>
    생성: 20-20 Club Auto Screener
  </div>

</div>
</body>
</html>"""
