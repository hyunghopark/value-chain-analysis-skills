# 001. 데이터 스냅샷과 출처 정보 — 작업 목록

- 상태: 구현 대기 — **T1부터 시작** (spec·plan 확정 2026-10-14)
- 설계: [plan.md](plan.md)

커밋 하나에 작업 하나. 각 작업은 테스트가 통과한 상태로 커밋한다.

## 준비
- [x] T0. spec 열린 질문과 plan '결정이 필요한 것' 확인 → spec·plan 상태를 '확정'으로
- [ ] T1. 회귀 기준 만들기: 현재 코드로 같은 티커의 Section 4를 저장 (판정·주요 수치 비교용)

## 기반
- [ ] T2. `references/rules/data-snapshot.md` 작성 (형식, basis·status 어휘, 경로 규칙)
- [ ] T3. `snapshot.py` + `tests/test_snapshot.py` (어휘 검증, 기록, series 260일 제한, 경고의 KI 파싱, 저장 실패 처리)

## 기록 지점 (get_financial_stats.py)
- [ ] T4. `warn()` → 스냅샷 경고 연결, `--snapshot` 인자와 저장, 메타(시각·인자·버전·커밋)
- [ ] T5. Yahoo info 원값과 한국 종목 덮어쓰기(네이버·WiseReport) 기록 — `original` 포함
- [ ] T6. ADR 보정(KI-008), 이력 보완·교정(KI-002·006, 종목·지수) 기록
- [ ] T7. 수급 표: 수량·수급 데이터 가격·정규장 종가·추정 금액 기록 (KI-001 기준 구분)
- [ ] T8. 컨센서스·추정치 방향, 사이클(연간 영업이익률·기간), P/B 밴드(시점별 BPS·P/B) 기록
- [ ] T9. 시장 비교·기술적 지표·시나리오의 계산 입력(`inputs`) 기록, 가격 이력 series 저장

## 연결
- [ ] T10. `generate_strategy_report.py`: 파일명 결정 → 스냅샷 경로 전달 → 보고서 상단 표시
- [ ] T11. 완료 기준 테스트: Section 4 표 값이 모두 스냅샷에 있는지 대조

## 마무리
- [ ] T12. 전체 실행 검증 (T1 회귀 기준과 판정·수치 비교, 스냅샷 크기 확인)
- [ ] T13. SKILL.md(스냅샷 안내, Clean-Slate에 스냅샷 포함)·README·ROADMAP 상태 갱신, 필요 시 결정 기록
