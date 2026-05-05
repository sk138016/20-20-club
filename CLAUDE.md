# 20-20 Club — 프로젝트 가이드

한국(KOSPI + KOSDAQ) 및 미국(S&P 500) 상장 기업 중 **영업이익률 ≥ 20% AND ROE ≥ 20%** 인 기업을 자동 선별하고, 분기마다 Gmail로 HTML 보고서를 발송하는 Python 툴.

- **한국**: DART API 기반, 연간 사업보고서 기준
- **미국**: yfinance 기반 TTM(최근 12개월) 기준, API 키 불필요
- **자동화**: GitHub Actions (`.github/workflows/screener.yml`) — 분기 4회 자동 실행
- **저장소**: https://github.com/sk138016/20-20-club

## 파일 구조

```
├── .env                  # 시크릿 (API 키, 이메일 비밀번호) — 절대 커밋 금지
├── .env.example          # 환경변수 템플릿
├── requirements.txt
├── config.py             # 상수 및 설정값
├── main.py               # 진입점 — 전체 파이프라인 실행
├── dart_fetcher.py       # DART API 호출 (기업 목록 + 재무제표) — 한국 시장
├── us_fetcher.py         # yfinance 기반 S&P 500 TTM 스크리닝 — 미국 시장 (API 키 불필요)
├── calculator.py         # 영업이익률·ROE 계산 및 20-20 필터 (KR)
├── email_template.py     # HTML 이메일 빌더 (KR + US 통합)
├── email_sender.py       # Gmail SMTP 발송
├── run.bat               # (레거시) 로컬 수동 실행용 배치 파일
├── scheduler_setup.ps1   # (레거시) Windows 작업 스케줄러 등록 스크립트
├── test_us.py            # US 스크리닝 단독 테스트 (콘솔 출력 + 이메일 발송)
├── .github/
│   └── workflows/
│       └── screener.yml  # GitHub Actions 분기 자동 실행 정의
└── logs/                 # 실행 로그 (자동 생성, .gitignore 대상)
```

## 실행 방법

```powershell
# venv 활성화
venv\Scripts\activate

# 실행
python main.py
```

예상 실행 시간: **약 20~25분** (재무제표 수집 ~2,658개 기업이 병목)

## 환경 설정

`.env` 파일 필수:
```
DART_API_KEY=<40자리 DART 인증키>
GMAIL_ADDRESS=kims138016@gmail.com
GMAIL_APP_PASSWORD=<Gmail 앱 비밀번호 16자리>
RECIPIENT_EMAIL=kims138016@gmail.com
```

- DART API 키: https://opendart.fss.or.kr → 인증키 신청 (무료)
- Gmail 앱 비밀번호: Google 계정 → 보안 → 2단계 인증 → 앱 비밀번호
- 미국 시장(US)은 yfinance + Wikipedia 사용 — API 키 불필요

## 의존성 (Python 3.14 호환)

`requirements.txt`에 `>=` 유연한 버전 핀 사용. `==` 고정 핀으로 바꾸지 말 것 — Python 3.14에서 pandas 2.x는 pre-built wheel이 없어 빌드 실패함.

실제 설치 버전: pandas 3.0.2, OpenDartReader 0.2.3

## 핵심 설계 결정

### 시장 구분 (KOSPI/KOSDAQ) 조회 방식
1차: **FinanceDataReader** `fdr.StockListing('KOSPI'/'KOSDAQ')` — KRX KIND 파일 다운로드 엔드포인트, ~2.5초
2차 폴백: **DART list API** `dart.list(start, end, kind='A')` — KRX 서버 의존 없음

`pykrx`는 사용하지 않음 — KRX JSON API가 공휴일/야간에 다운되는 문제가 있었음.

### DART OpenDartReader import
```python
import OpenDartReader as _ODR
dart = _ODR(DART_API_KEY)   # 모듈이 클래스를 직접 export함
```
`OpenDartReader.OpenDartReader` 같은 서브모듈 방식은 존재하지 않음.

### 재무제표 우선순위
연결재무제표(CFS) 우선 → 없으면 별도재무제표(OFS).

### 기준 연도
- 4월 이후 실행 → `현재연도 - 1` (사업보고서 공시 완료 후)
- 1~3월 실행 → `현재연도 - 2`

### pandas pickle 캐시 주의
OpenDartReader가 `docs_cache/` 에 pkl 파일을 저장함. pandas 버전이 바뀌면 (`StringDtype` 변경 등) 캐시가 깨질 수 있음 → `docs_cache/` 폴더를 지우고 재실행.

## 스크리닝 기준 (config.py)

| 지표 | 기준 |
|------|------|
| 영업이익률 | ≥ 20% |
| ROE | ≥ 20% |
| 연평균 매출 증가율 강조 기준 | ≥ 10% (고성장 뱃지) |
| CAGR 계산 기간 | 2년 |

## 이메일 출력 형식

**한국 섹션** (네이비 헤더): 순위 / 종목코드 / 종목명 / 시장 / 영업이익률 / ROE / 매출증가율 / 기준연도
- 연평균 매출증가율 ≥ 10% 기업: 금빛 배경 + 좌측 황색 테두리 + "고성장" 뱃지

**미국 섹션** (레드 헤더): 순위 / 티커 / 종목명 / 섹터 / 영업이익률 / ROE / 매출증가율 (TTM 기준)
- yfinance `ticker.info` 기반: `operatingMargins`, `returnOnEquity` (소수 → ×100으로 % 변환)
- `bookValue` (주당 장부가) ≤ 0 기업 제외 (자본총계 음수 여부 판별)
- 연평균 매출증가율 ≥ 10% 기업: 금빛 배경 + 좌측 황색 테두리 + "고성장" 뱃지
- GOOGL/GOOG 등 동일 기업 복수 주식: 스크리닝 후 `corp_name` 기준 중복 제거
- S&P 500 목록: Wikipedia `List_of_S%26P_500_companies` 첫 번째 테이블

요약 카드: US 데이터 있으면 KR 선별 N개 + US 선별 N개 + 기준값 4개 카드 표시
발송 대상: `RECIPIENT_EMAIL` (기본값 kims138016@gmail.com)

## 분기 자동 실행 스케줄

**GitHub Actions** (`.github/workflows/screener.yml`) 으로 자동 실행 — PC 켜짐 여부 무관.

| 실행일 | 의미 |
|--------|------|
| 매년 **4월 16일** 09:00 KST | 한국 사업보고서(3/31 마감) 반영 + US TTM |
| 매년 **6월 16일** 09:00 KST | US Q1 실적 반영 |
| 매년 **9월 16일** 09:00 KST | US Q2 실적 반영 |
| 매년 **12월 16일** 09:00 KST | US Q3 실적 반영 |

GitHub Secrets 필수 등록 (Settings → Secrets and variables → Actions):
- `DART_API_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `RECIPIENT_EMAIL`

수동 실행: GitHub 저장소 → Actions → 20-20 Club Screener → Run workflow

## 스로틀링 설정

- `MAX_WORKERS = 5` (스레드풀 동시 요청 수)
- `REQUEST_DELAY_SECONDS = 0.3` (요청당 딜레이)

DART API가 `{'status': '013', 'message': '조회된 데이터가 없습니다.'}` 를 간헐적으로 반환하는 것은 정상 — 해당 기업의 보고서가 없거나 해당 연도 데이터가 미공시인 경우임.
