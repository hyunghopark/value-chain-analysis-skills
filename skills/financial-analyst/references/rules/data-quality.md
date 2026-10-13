# 데이터 품질 규칙 (원본)

코드: `scripts/data_checks.py`, `scripts/get_financial_stats.py`, 정기 점검 `scripts/check_data_sources.py`
사건 기록: 스킬 저장소 `wiki/known-issues/` (경고의 `[KI-xxx]` 번호와 같은 번호)

## 항목별 출처

| 항목 | 해외 종목 | 한국 종목 |
|---|---|---|
| 현재가·가격 이력·지수 | Yahoo | Yahoo, **거래소 종가(다음 금융)로 보완·교정** |
| 재무제표 (사이클 위치, P/B 밴드, 일회성 손익) | Yahoo | Yahoo |
| PER·EPS·PBR·BPS·배당·52주 범위 | Yahoo | 네이버 (Yahoo 값이 비어 있음) |
| 올해·내년 EPS, 12개월 선행 EPS | Yahoo | WiseReport |
| 시나리오 EPS 최저·평균·최고, 추정치 방향, 실적 발표일, 서프라이즈 | Yahoo | Yahoo |
| 목표가 | Yahoo | Yahoo + 네이버(별도 열) |
| 시가총액 | Yahoo | 네이버(보통주) 표시, EV는 Yahoo |
| 투자자별 순매매 | — | 네이버 수량 × **거래소 종가(다음 금융)** |

## 점검 규칙

<a id="cross-source-5"></a>
### 출처 간 5% 규칙 (`cross_check`)

한국 종목의 올해·내년 EPS(WiseReport vs Yahoo, WiseReport vs 네이버), 평균 목표가(네이버 vs Yahoo), 시가총액(네이버 보통주 vs Yahoo)이 5% 넘게 다르면 경고합니다.

### 가격 이력 (KI-002, KI-006)

- 한국 종목은 다음 금융 일별 시세를 거래소 종가 기준으로 봅니다.
- 다음 금융 최근 100거래일 안에서 Yahoo에 없거나 빈 날은 채우고, 종가가 다른 날은 거래소 종가로 바꿉니다. 채운 날의 거래량은 다음 금융 값입니다(기준이 다를 수 있음).
- 코스피(`^KS11`)·코스닥(`^KQ11`) 지수 이력도 다음 금융 지수 종가(`/api/market_index/days`)로 같은 방식으로 보완합니다. 지수는 한국 종목 등락 계산의 거래일 달력이기도 합니다.

### 수급 금액 (KI-001)

- 네이버 순매수 수량 × 그날 거래소 종가로 계산합니다. 거래소 종가가 없는 날만 네이버 종가를 씁니다.

### 거래량 이상치 (KI-005)

- Yahoo 거래량이 직전 20일 중앙값(최소 10일)의 1% 미만이면 경고합니다. 값은 바꾸지 않습니다.

### 재무제표 반영 지연 (KI-003)

- 연간 표 최신 열이 `lastFiscalYearEnd`보다, 분기 표 최신 열이 `mostRecentQuarter`보다 7일 넘게 이르면 경고합니다.

### WiseReport 구조 (KI-004)

- 머리글 앞 6칸이 `재무년월, 매출액(억원, %), 영업이익(억원, %), 당기순이익(억원, %), EPS(원), PER(배)`가 아니거나, 행의 순이익(4번째 칸)과 EPS(5번째 칸) 부호가 다르면 WiseReport 값을 쓰지 않습니다.

## 새 데이터 문제를 발견했을 때

1. `check_data_sources.py`(또는 직접 대조)로 근거를 만들고 `raw/data-checks/`에 저장합니다.
2. 위키에 사건 문서 `wiki/known-issues/ki-NNN-*.md`를 만들고(ingest), `data_checks.KNOWN_ISSUES`에 번호를 추가합니다.
3. 감지·우회 코드를 넣고, 경고 앞에 `ki('KI-NNN', ...)`를 붙입니다.
4. `tests/test_data_checks.py`에 그 사례를 재현하는 테스트를 추가합니다.
5. 이 문서의 해당 규칙을 고칩니다.
