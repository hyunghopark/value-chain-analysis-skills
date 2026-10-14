# Contract: `check_report_numbers.py`

**위치**: `skills/financial-analyst/scripts/check_report_numbers.py` · 규칙 원본: `skills/financial-analyst/references/rules/report-number-check.md`

## 실행

```bash
# Claude Code (investment-strategy SKILL.md에서): 형제 스킬 폴더의 스크립트를 부른다
uv run --no-project --with-requirements "${CLAUDE_SKILL_DIR}/../financial-analyst/requirements.txt" \
  python "${CLAUDE_SKILL_DIR}/../financial-analyst/scripts/check_report_numbers.py" REPORT.md [옵션]

# Antigravity
venv/bin/python3 .agents/skills/financial-analyst/scripts/check_report_numbers.py REPORT.md [옵션]
```

| 인자·옵션 | 기본값 | 뜻 |
|---|---|---|
| `REPORT` (필수) | — | 점검할 보고서 `.md` |
| `--snapshot PATH` | 보고서 머리의 `**데이터 스냅샷**:` 줄에 적힌 파일(보고서와 같은 폴더) | 짝 스냅샷을 직접 지정 |
| `--json PATH` | 없음 | 구조화 결과를 파일로 저장 ([data-model.md](../data-model.md) §2-6 CheckResult) |
| `--section` | 꺼짐 | 보고서에 넣을 '숫자 점검 결과' 블록만 표준 출력에 낸다 |
| `--fetch-sources` | 꺼짐 | 참고문헌 기사를 내려받아 인용 숫자를 대조 (네트워크, 로컬 전용) |
| `--verbose` | 꺼짐 | 일치·제외한 숫자 목록까지 출력 |

- 보고서·스냅샷을 **읽기만** 한다(FR-014). 짝 스냅샷 외의 스냅샷·보고서를 찾거나 읽지 않는다(헌법 VI).
- 네트워크는 `--fetch-sources`일 때만 쓴다.

## 종료 코드

| 코드 | 뜻 |
|---|---|
| `0` | 기록되지 않은 `error` 문제 없음 (문제 0건, 또는 남은 문제가 모두 '숫자 점검 결과' 섹션에 사유와 함께 기록됨) |
| `1` | 기록되지 않은 `error` 문제 있음 |
| `2` | 실행 불가 (보고서 없음, 읽기 실패, 인자 오류) |

`warning`(미사용 참고문헌)은 종료 코드에 영향을 주지 않는다. 짝 스냅샷이 없으면 `no_snapshot` 문제가 생기므로, `0`이 나오려면 그 사실이 섹션에 기록돼야 한다(조용히 통과하지 않음).

## 표준 출력 (기본)

```markdown
## 숫자 점검 — AI_메모리_반도체_20261014_Investment_Strategy_Report.md
점검 시각: 2026-10-14 15:20 KST · 스냅샷: AI_..._data.json

| 분류 | 개수 |
|---|---|
| 스크립트 값 일치 | 131 (약한 일치 6) |
| 인용 출처 있음 | 24 |
| 근거 없음 | 12 |
| 제외(수량 아님) | 86 |

### 문제 (기록 안 됨 9 / 기록됨 3)
- [unsupported_number] 1.2 최근 시장 변동성 › 줄 25 › "-3조 9,334억 원" — …외국인 투자자는 삼성전자 주식을 누적 약 -3조 9,334억 원(추정)…
- [reference_format] 참고문헌 [7] — 홈페이지 주소(https://www.yna.co.kr)
- [section4_changed] Section 4 › 줄 141 — 현재 "₩238,250" / 기준본 "₩237,500"
…
### 약한 일치 (검토 권장)
- 5) 005930.KS › "62%" → 005930.KS.pb_band.percentile (0.62)
```

(위 숫자는 형식 예시다.)

## 보고서에 넣는 '숫자 점검 결과' 섹션

`--section` 출력. AI가 '## 8. 참고 문헌 (References)' 목록 **뒤**, 면책 문구 앞에 붙이고 `[AI_TODO]` 사유를 채운다.

```markdown
## 9. 숫자 점검 결과 (스크립트 자동 점검)

> 점검 시각: 2026-10-14 15:20 KST · 스크립트 값 일치 131 · 인용 24 · 근거 없음 2 · 제외 86 · Section 4 변경 0 · 참고문헌 문제 0

| ID | 위치 | 숫자 | 문제 | 사유 |
|---|---|---|---|---|
| 9c2e-+86.8%-1 | 6.1 시나리오 해석 | +86.8% | 근거 없음 | [AI_TODO: 남긴 이유] |
```

- 남은 문제가 없으면 표 대신 "남은 문제 없음" 한 줄을 낸다.
- 다시 점검할 때 이 섹션은 대조 대상에서 빼고, 머리 줄의 개수와 표의 ID·사유를 현재 결과와 비교한다([research.md](../research.md) R9). 개수가 다르면 `check_section_stale`이고, 표에 없거나 사유가 `[AI_TODO]`인 문제는 `documented: false`로 남는다.
- 참고문헌 파싱은 '## 9.' 제목에서 끝난다.

## JSON 결과 (`--json`)

[data-model.md](../data-model.md) §2-6 `CheckResult`를 그대로 직렬화한다. 최상위 키: `report`, `snapshot`, `checked_at`, `counts`, `mentions`, `section4`, `references`, `ai_todo`, `issues`, `exit_code`. 002 단계에서는 하위 호환을 약속하지 않으며, 형식을 바꾸면 규칙 원본에 적는다.

## investment-strategy 연동 (SKILL.md Phase 3에 추가)

5. `[AI_TODO]`를 모두 채운 뒤 점검 도구를 실행한다.
6. 문제가 나오면 고친다: 근거 없는 숫자는 Section 4·스냅샷 값을 그대로 인용하거나 출처를 붙이거나 지운다. 직접 계산한 숫자는 쓰지 않는다(FR-012). Section 4 변경은 되돌린다. 참고문헌은 기사 주소와 발행일로 고친다. 다시 점검한다.
7. 더 고칠 수 없으면 `--section` 출력을 붙이고 남은 문제마다 사유를 적는다. 종료 코드 `0`이 나올 때까지 반복한 뒤 마무리한다.
8. (선택, 로컬) `--fetch-sources`로 인용 숫자를 기사와 대조하고, `not_found`·`unverifiable`도 같은 방식으로 고치거나 기록한다.
