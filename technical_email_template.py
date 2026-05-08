"""HTML 이메일 빌더 — 기술적 신호 알림 (KOSPI + KOSDAQ 일일 스캔)."""

from datetime import datetime


_CLUB_BADGE = (
    ' <span style="background:#f9a825;color:#333;padding:1px 6px;'
    'border-radius:8px;font-size:10px;font-weight:bold">★ 20-20</span>'
)


def _market_badge(market: str) -> str:
    color = "#1a73e8" if market == "KOSPI" else "#34a853"
    return (
        f'<span style="background:{color};color:white;padding:2px 8px;'
        f'border-radius:10px;font-size:11px;font-weight:bold">{market}</span>'
    )


def _row_bg(idx: int, is_club: bool) -> str:
    if is_club:
        return 'style="background:#fffde7;border-left:4px solid #f9a825"'
    return f'style="background:{"#fafafa" if idx % 2 == 0 else "#ffffff"}"'


def _no_signal_row(colspan: int) -> str:
    return (
        f'<tr><td colspan="{colspan}" '
        f'style="padding:32px;text-align:center;color:#bbb;font-size:13px">'
        f'오늘 해당 신호 없음</td></tr>'
    )


# ---------------------------------------------------------------------------
# 섹션별 행 생성
# ---------------------------------------------------------------------------

def _rows_a(stocks: list) -> str:
    if not stocks:
        return _no_signal_row(6)
    rows = ""
    for i, s in enumerate(stocks, 1):
        club = _CLUB_BADGE if s["is_2020_club"] else ""
        rows += f"""
        <tr {_row_bg(i, s["is_2020_club"])}>
          <td style="padding:10px 12px;text-align:center;font-weight:bold;color:#555">{i}</td>
          <td style="padding:10px 12px;font-family:monospace;font-size:13px">{s["code"]}</td>
          <td style="padding:10px 12px;font-weight:bold">{s["name"]}{club}</td>
          <td style="padding:10px 12px;text-align:center">{_market_badge(s["market"])}</td>
          <td style="padding:10px 12px;text-align:right;color:#e65100;font-weight:bold">{s["bandwidth_pct"]:.1f}%</td>
          <td style="padding:10px 12px;text-align:right;font-weight:bold;color:#c62828">{int(s["close"]):,}</td>
        </tr>"""
    return rows


def _rows_b(stocks: list) -> str:
    if not stocks:
        return _no_signal_row(5)
    rows = ""
    for i, s in enumerate(stocks, 1):
        club = _CLUB_BADGE if s["is_2020_club"] else ""
        rows += f"""
        <tr {_row_bg(i, s["is_2020_club"])}>
          <td style="padding:10px 12px;text-align:center;font-weight:bold;color:#555">{i}</td>
          <td style="padding:10px 12px;font-family:monospace;font-size:13px">{s["code"]}</td>
          <td style="padding:10px 12px;font-weight:bold">{s["name"]}{club}</td>
          <td style="padding:10px 12px;text-align:center">{_market_badge(s["market"])}</td>
          <td style="padding:10px 12px;text-align:right;font-weight:bold;color:#1565c0">{int(s["close"]):,}</td>
        </tr>"""
    return rows


def _rows_c(stocks: list) -> str:
    if not stocks:
        return _no_signal_row(6)
    rows = ""
    for i, s in enumerate(stocks, 1):
        club = _CLUB_BADGE if s["is_2020_club"] else ""
        rows += f"""
        <tr {_row_bg(i, s["is_2020_club"])}>
          <td style="padding:10px 12px;text-align:center;font-weight:bold;color:#555">{i}</td>
          <td style="padding:10px 12px;font-family:monospace;font-size:13px">{s["code"]}</td>
          <td style="padding:10px 12px;font-weight:bold">{s["name"]}{club}</td>
          <td style="padding:10px 12px;text-align:center">{_market_badge(s["market"])}</td>
          <td style="padding:10px 12px;text-align:right;font-weight:bold;color:#7b1fa2">{s["rsi"]:.1f}</td>
          <td style="padding:10px 12px;text-align:right;font-weight:bold;color:#c62828">{int(s["close"]):,}</td>
        </tr>"""
    return rows


# ---------------------------------------------------------------------------
# 섹션 컨테이너
# ---------------------------------------------------------------------------

def _section(title: str, desc: str, note: str, color: str, thead_html: str,
             rows_html: str, count: int) -> str:
    count_badge = (
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:12px;font-size:13px;font-weight:bold;margin-left:10px">'
        f'{count}개</span>'
    )
    return f"""
  <div style="padding:28px 32px 0;border-top:2px solid #e8e8e8">
    <div style="display:flex;align-items:center;padding-bottom:10px;border-bottom:2px solid {color}">
      <span style="font-size:16px;font-weight:bold;color:{color}">{title}</span>
      {count_badge}
    </div>
    <div style="font-size:12px;color:#555;margin:10px 0 4px">{desc}</div>
    <div style="font-size:11px;color:#999;margin-bottom:16px">{note}</div>
  </div>
  <div style="padding:0 32px 32px">
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="background:#f1f3f4">
          {thead_html}
        </tr>
      </thead>
      <tbody>{rows_html}
      </tbody>
    </table>
  </div>"""


def _th(text: str, align: str = "center", color: str = "#333") -> str:
    return (
        f'<th style="padding:11px 12px;text-align:{align};'
        f'border-bottom:2px solid #555;color:{color};white-space:nowrap">{text}</th>'
    )


# ---------------------------------------------------------------------------
# 퍼블릭 API
# ---------------------------------------------------------------------------

def build_signal_subject(signals: dict) -> str:
    total = signals.get("total", 0)
    date = signals.get("scan_date", datetime.now().strftime("%Y-%m-%d"))
    if total == 0:
        return f"[20-20 Club] 기술적 신호 없음 — {date}"
    return f"[20-20 Club] 기술적 신호 {date} — 총 {total}개 종목"


def build_signal_email(signals: dict) -> str:
    scan_date = signals.get("scan_date", datetime.now().strftime("%Y-%m-%d"))
    club_updated = signals.get("club_updated", "(미업데이트)")
    count_a = len(signals["A"])
    count_b = len(signals["B"])
    count_c = len(signals["C"])
    total = signals.get("total", count_a + count_b + count_c)

    def summary_card(label: str, count: int, color: str, border: bool = True) -> str:
        border_style = "border-right:1px solid #e8e8e8;" if border else ""
        return f"""
    <div style="flex:1;padding:20px 0;text-align:center;{border_style}">
      <div style="font-size:10px;color:#888;font-weight:bold;margin-bottom:6px;line-height:1.4">{label}</div>
      <div style="font-size:34px;font-weight:bold;color:{color}">{count}</div>
      <div style="font-size:11px;color:#bbb;margin-top:4px">신호 종목</div>
    </div>"""

    cards = (
        summary_card("A. Bandwidth15%↓<br>상단터치", count_a, "#c62828")
        + summary_card("B. 포카라 80일 BB<br>하방터치", count_b, "#1565c0")
        + summary_card("C. RSI&lt;30<br>MACD OSC 전환", count_c, "#6a1b9a")
        + summary_card("전체 신호 수<br>KOSPI + KOSDAQ", total, "#333", border=False)
    )

    # Section A
    thead_a = (
        _th("순위")
        + _th("종목코드", "left")
        + _th("종목명", "left")
        + _th("시장")
        + _th("밴드폭(%)", "right", "#e65100")
        + _th("현재가(원)", "right", "#c62828")
    )
    sec_a = _section(
        "A. Bandwidth15%이하, 상단터치",
        "볼린저밴드 20일 | 밴드폭(Band Width) ≤ 15% 상태에서 종가가 상단선 터치 또는 상방 돌파",
        "밴드폭 = (상단선 − 하단선) ÷ 중심선 × 100% &nbsp;|&nbsp; 기준: 일봉 · 2σ &nbsp;|&nbsp; 거래정지·스팩 제외",
        "#c62828", thead_a, _rows_a(signals["A"]), count_a,
    )

    # Section B
    thead_b = (
        _th("순위")
        + _th("종목코드", "left")
        + _th("종목명", "left")
        + _th("시장")
        + _th("현재가(원)", "right", "#1565c0")
    )
    sec_b = _section(
        "B. 포카라 80일 BB, 하방터치",
        "볼린저밴드 80일 | 종가 ≤ 하단선 (저가매수 관점 — 80일 기준 과매도 구간 진입)",
        "하단선 = 80일 이동평균 − 2σ &nbsp;|&nbsp; 기준: 일봉 &nbsp;|&nbsp; 거래정지·스팩 제외",
        "#1565c0", thead_b, _rows_b(signals["B"]), count_b,
    )

    # Section C
    thead_c = (
        _th("순위")
        + _th("종목코드", "left")
        + _th("종목명", "left")
        + _th("시장")
        + _th("주봉 RSI(14)", "right", "#7b1fa2")
        + _th("현재가(원)", "right", "#c62828")
    )
    sec_c = _section(
        "C. RSI&lt;30, MACD OSC 추세 전환",
        "주봉 기준 | RSI(14) &lt; 30 (과매도 구간) 상태에서 MACD 오실레이터 2봉 연속 상승",
        "MACD(12, 26, 9) 히스토그램 기준 &nbsp;|&nbsp; 2봉 연속 상승 = 이번 주 &gt; 지난 주 &gt; 2주 전",
        "#6a1b9a", thead_c, _rows_c(signals["C"]), count_c,
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>20-20 Club 기술적 신호</title>
</head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:'Malgun Gothic',Arial,sans-serif">
<div style="max-width:900px;margin:32px auto;background:white;
            border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10)">

  <!-- 헤더 -->
  <div style="background:linear-gradient(135deg,#263238 0%,#455a64 100%);padding:32px 40px;color:white">
    <div style="font-size:11px;font-weight:bold;opacity:0.6;letter-spacing:3px;text-transform:uppercase">
      20-20 Club
    </div>
    <div style="font-size:26px;font-weight:bold;margin-top:8px;letter-spacing:-0.5px">
      기술적 신호 알림
    </div>
    <div style="margin-top:12px;font-size:12px;opacity:0.60">
      스캔일: {scan_date}
      &nbsp;|&nbsp; 대상: KOSPI + KOSDAQ 전종목
      &nbsp;|&nbsp; 20-20 Club 기준: {club_updated}
    </div>
  </div>

  <!-- 요약 카드 -->
  <div style="display:flex;border-bottom:1px solid #e8e8e8">
    {cards}
  </div>

  <!-- 20-20 Club 범례 -->
  <div style="padding:10px 32px;background:#fffde7;border-bottom:1px solid #f0cc00;
              font-size:12px;color:#555">
    {_CLUB_BADGE}
    &nbsp; 표시 = 20-20 Club 등재 종목 (영업이익률 ≥ 20% &amp; ROE ≥ 20%,
    &nbsp;{club_updated} 기준)
  </div>

  {sec_a}
  {sec_b}
  {sec_c}

  <!-- 푸터 -->
  <div style="padding:18px 32px;background:#f8f9fa;border-top:2px solid #e8e8e8;
              font-size:11px;color:#aaa;text-align:center;line-height:1.9">
    데이터 출처: FinanceDataReader (KRX) &nbsp;|&nbsp; 볼린저밴드: 2σ 기준<br>
    본 신호는 투자 참고용이며, 투자 손실에 대한 책임은 투자자 본인에게 있습니다.
  </div>

</div>
</body>
</html>"""
