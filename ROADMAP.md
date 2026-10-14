# 로드맵

**최종 목표:** 보고서의 모든 숫자를 출처·기준·시점까지 추적할 수 있고, 사람이 아니라 스크립트가 먼저 검증하게 만든다.

## 단계

| 단계 | 목표 | 완료 기준 | 상태 | 스펙 |
|---|---|---|---|---|
| 0 | 데이터 품질 관리 기반 | 출처 교차 점검, 사건 기록(KI), 규칙 원본, 결정 기록 | ✅ 완료 (2026-10-14, 브랜치 `claude/data-quality-wiki`) | — |
| 1 | 데이터 스냅샷과 출처 정보 | 보고서마다 수집 데이터 파일이 남고, 각 값에 출처·기준·시점·잠정 여부가 붙는다 | ✅ 완료 (2026-10-14, spec 001) | [001](specs/001-data-snapshot/spec.md) |
| 2 | 보고서 숫자 자동 대조 | 보고서 본문의 숫자가 스냅샷이나 인용 출처에 있는지 스크립트가 점검한다 | 📝 스펙·plan 작성 (2026-10-14, tasks 대기) | [002](specs/002-report-number-check/spec.md) |
| 3 | 수집·정제·계산·출력 분리 | 계산·표 생성이 스냅샷만 읽는다. 같은 스냅샷이면 같은 보고서가 나온다 | ⏳ 대기 (1단계 필요) | 003 (예정) |
| 4 | 공식 출처 전환 | 한국 재무제표는 DART, 미국은 SEC EDGAR. 가능하면 KRX 공식 시세 | ⏳ 대기 (API 키·계정 필요) | 004 (예정) |
| — | 사이클 위치 판정 개선 | 10년 이상 연간 자료·컨센서스 이익률 전망 반영 | 💤 보류 (4단계 필요, [결정 0003](docs/decisions/0003-cycle-position-semantics.md)) | — |

상태: 📝 스펙 작성 · 🔨 구현 중 · ✅ 완료 · ⏳ 대기 · 💤 보류

## 운영 방법

- [Spec Kit](https://github.com/github/spec-kit)을 씁니다(v1.1.3, [결정 0004](docs/decisions/0004-adopt-spec-kit.md)). 원칙은 [헌법](.specify/memory/constitution.md)에 있습니다.
- 목표 하나에 `specs/NNN-이름/` 폴더 하나를 둡니다.
  - `spec.md`: 무엇을, 왜, 완료 기준 (요구사항)
  - `plan.md`: 어떻게 (설계, 바꿀 파일, 위험)
  - `tasks.md`: 작업 목록 (체크박스, 커밋 단위)
- 순서: `/speckit-specify` → (`/speckit-clarify`) → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`. 구현 중 범위가 바뀌면 `spec.md`부터 고칩니다.
- 설계 중 중요한 선택은 `docs/decisions/`에 결정 기록으로 남깁니다.
- 데이터 출처의 사실은 `wiki/known-issues/`, 해야 할 작업은 GitHub Issues에 둡니다. 스펙·이슈·KI 문서는 서로 링크합니다.
- 단계가 끝나면 이 표의 상태를 바꾸고 README 변경 이력에 적습니다.
