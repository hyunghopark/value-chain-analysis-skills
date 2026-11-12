# 판정 매트릭스 규칙 (원본)

이 문서가 판정 기준의 원본입니다. 기준을 바꿀 때는 이 문서, `scripts/get_financial_stats.py`의 해당 함수, 보고서 범례 문구를 **같은 커밋**에서 고치고, 이유를 저장소 `docs/decisions/`에 남깁니다.

## 신호 기둥

| 기둥 | 키 | 🟢 | 🟡 | 🔴 | 코드 |
|---|---|---|---|---|---|
| Forward P/E (12M) | `fpe` | < 18 | < 30 | 그 외 | `build_signals` |
| PEG | `peg` | < 1 | < 2 | 그 외 | `build_signals` |
| 매출 성장률 (YoY) | `rg` | > 20% | > 5% | 그 외 | `build_signals` |
| EV/EBITDA | `ev` | < 12 | < 20 | 그 외 | `build_signals` |
| ROE (일회성 감지 시 정규화 ROE) | `roe` | > 20% | > 10% | 그 외 | `build_signals` |
| 부채비율 (D/E) | `de` | < 50% | < 100% | 그 외 | `build_signals` |
| 추정치 방향 (30일) | `rev` | 아래 참고 | | | `revision_summary` |
| P/B 밴드 위치 | `band` | 아래 참고 | | | `compute_pb_band` |
| 사이클 위치 | `cycle` | [cycle-position.md](cycle-position.md) | | | `analyze_cycle` |

값이 없거나 0 이하(배수)면 ⚪(데이터 없음)입니다.

- **일반 기업 (`GENERAL`, Type 1)**: `fpe, peg, rg, ev, roe, de, rev` 7개
- **순환업종 (`CYCLICAL`, Type 2)**: `band, cycle, rev, de` 4개 — 이익 정점에서 좋아 보이는 PER·PEG·매출성장·EV/EBITDA·ROE는 '제외'로 표시하고 쓰지 않습니다.
- **플랫폼/SaaS (`PLATFORM_SAAS`, Type 3)**: `rg, fcf_margin, rule_of_40, ev_sales, peg, rev` 6개 — 무형자산 및 고성장 재투자 구조를 반영하여 전통적 PBR 및 단순 PER·D/E는 제외합니다.
- **금융/리츠/인프라 (`FINANCIAL_REIT`, Type 4)**: `band, roe, div_yield, fpe, rev` 5개 — 원재료가 '자본/차입금'이므로 일반 기업의 부채비율(`de`), `ev`(EV/EBITDA), `peg`는 제외합니다.
- **바이오텍/R&D (`BIOTECH_RD`, Type 5)**: `runway, net_cash_mcap, rd_intensity, rev, de` 5개 — 임상 및 선행 R&D 단계의 계획된 적자 특성을 반영하여 전통적 수익성 배수(`fpe, peg, ev, roe`)는 제외합니다.
- **순환업종 및 프로파일 자동 지정**: `scripts/profile_detector.py`가 GICS 섹터/산업 분류, 재무제표 구조, 연간 순이익 최대 감소율(-50% 이하 시 순환업종)을 종합하여 5대 프로파일을 자동 분류하며, `--cyclical` / `--not-cyclical`로 사람이 덮어씁니다. 상세 분류 기준은 [`../taxonomy/business-profiles.md`](../taxonomy/business-profiles.md) 및 [`../taxonomy/gics-163-subindustries.md`](../taxonomy/gics-163-subindustries.md)를 따릅니다.

<a id="estimate-revisions"></a>
## 추정치 방향 (30일)

1. 올해(FY0)와 내년(FY1)의 최근 30일 상향·하향 건수(Yahoo `eps_revisions`)를 더합니다.
2. 합계가 3건 이상이면 `(상향 - 하향) / 합계`가 +0.3 이상 🟢, -0.3 이하 🔴, 그 사이 🟡.
3. 3건 미만이면 내년 평균 EPS의 30일 변화(Yahoo `eps_trend`)가 +1% 초과 🟢, -1% 미만 🔴, 그 사이 🟡.
4. 둘 다 없으면 ⚪.

<a id="pb-band"></a>
## P/B 밴드

1. Yahoo 연간·분기 재무상태표의 자본(Common Stock Equity 또는 Stockholders Equity) ÷ 주식수로 시점별 BPS를 만듭니다.
2. 주식수가 중앙값과 8% 넘게 다르면 중앙값으로 바꿉니다 (KI-007).
3. 각 시점의 종가(그날 또는 직전 거래일) ÷ BPS로 과거 P/B 목록을 만들고, 현재 P/B는 현재가 ÷ 최신 BPS로 같은 방식으로 계산합니다.
4. 현재 P/B가 과거 최고 초과 🔴, 중앙값 초과 🟡, 중앙값 이하 🟢.
5. 시세 통화와 재무 통화가 다르면(ADR, KI-008) 계산하지 않습니다. 맞출 수 있는 시점이 3개 미만이어도 계산하지 않습니다.

알려진 한계: 일회성 평가이익이 자본에 들어 있으면 BPS가 커져 밴드 위치가 실제보다 낮게(싸게) 보입니다.

<a id="aggregation"></a>
## 종합 판정 (`decision_verdict`)

위에서부터 처음 맞는 규칙을 씁니다.

| 순서 | 조건 | 판정 |
|---|---|---|
| 1 | 🔴 2개 이상 | 🔴 신중 접근 |
| 2 | 유효 신호(⚪ 아닌 것) 4개 미만 | ⚪ 판단 보류 |
| 3 | 🟢 4개 이상, 🔴 0개 | 🟢 강력 매수 후보 |
| 4 | 🟢 3개 이상, 🔴 1개 이하 | 🟢 매수 고려 |
| 5 | 그 외 | 🟡 중립/관망 (🔴 1개면 '주의 신호 1개' 표시) |

순환업종은 기둥이 4개뿐이라 하나라도 ⚪이면 판단 보류가 됩니다.

<a id="economic-gatekeeper"></a>
## 경제학 Moat & 밸류 트랩 게이트키퍼 (`economic_auditor.py`, v4.0)

1차 신호등 집계로 🟢(강력 매수 후보 또는 매수 고려) 판정이 나오더라도, `Table 6-1 [경제학 감사]`에서 아래 결함(🔴)이 감지되면 최종 판정을 **1단계 자동 강등(Downgrade)**합니다:
1. **자본 파괴 (Value Destruction)**: 초과이윤 스프레드 $\text{EVA} = \text{ROIC} - \text{WACC} < 0.0\%p$ 🔴
2. **이익 현금전환율 불량 (Earnings Quality Alert)**: $\text{CCR} = \text{OCF} / \text{Net Income} < 0.7$ 🔴
3. **주주가치 지분 희석 (Dilution)**: 총주주환원율 중 순자사주 증감률 $\le -2.0\%$ 🔴

- **강등 결과**: `🟡 **중립/관망 (⚠️ 밸류 트랩 경보: [사유])**`
- **효과**: 🟢 판정은 기술적·재무적 신호등과 경제학적 자본비용/현금흐름 검증을 모두 무결하게 통과한 진짜 초우량 기업에게만 부여됩니다.
