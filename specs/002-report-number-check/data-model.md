# Data Model: 보고서 숫자 자동 대조

**Feature**: [spec.md](spec.md) · 조사 근거: [research.md](research.md)

## 1. 스냅샷 확장 (001 형식에 추가)

001 형식([data-snapshot.md](../../skills/financial-analyst/references/rules/data-snapshot.md))은 그대로 두고 아래만 더한다.

### 1-1. `section4` (최상위, 신규)

| 필드 | 타입 | 뜻 |
|---|---|---|
| `text` | string | 보고서에 넣은 Section 4 본문 그대로 (`## 4.` 제목 줄 제외) |
| `sha256` | string | `text`의 SHA-256 (빠른 동일성 확인용) |
| `attached_at` | string | 덧붙인 시각 (KST) |

- `generate_strategy_report.py`가 보고서 파일을 쓰기 직전에 덧붙인다. 스냅샷 파일이 없으면(저장 실패) 덧붙이지 않고, 점검 도구가 '기준본 없음'을 보고한다.
- **비교 범위**: 보고서의 `## 4.` 제목 다음 줄부터 다음 `---` 줄 또는 `## ` 제목 전까지를 `text`와 비교한다. 양쪽 모두 앞뒤 빈 줄을 지우고 줄 끝 공백은 무시한다.

### 1-2. `values` 경로 추가

[research.md R10](research.md#r10-section-4와-스냅샷-대응-fr-015)의 표대로 Section 4 누락 값을 기록한다. 판정 기준값은 `rules.` 접두사를 쓴다(종목과 무관).

| 경로 | basis | status | 예 |
|---|---|---|---|
| `rules.{rule}.{threshold}` | `derived` | `final` | `rules.revision_direction.up_ratio` = 0.3 |

`source`는 `rules`, `note`에 규칙 원본 파일 이름을 적는다.

## 2. 점검 도구 내부 엔터티

### 2-1. NumberMention (숫자 표기)

| 필드 | 타입 | 뜻 |
|---|---|---|
| `id` | string | `{섹션 해시 4자}-{raw}-{섹션 내 순번}` (R9) |
| `raw` | string | 원문 표기 (예: `-3조 9,334억 원`) |
| `value` | float | 해석한 값 (단위 적용 전 숫자, 예: -3.9334 with unit `조`) |
| `unit` | string | `%`, `%p`, `배`, `조`, `억`, `원`, `T`, `B`, `M`, `""` 등 |
| `decimals` | int | 표기된 소수 자릿수 |
| `explicit_sign` | `+`/`-`/null | 표기에 있는 부호 |
| `section` | string | 가장 가까운 `##`/`###` 제목 |
| `line` | int | 줄 번호 (표시용, ID에는 쓰지 않음) |
| `context` | string | 앞뒤 문맥 (약 40자) |
| `ticker_context` | string/null | 같은 줄의 종목 전부(쉼표로 연결), 없으면 상위 제목의 종목 |
| `scope_citations` | int[] | 같은 문장·표 행·목록 항목의 인용 번호 |
| `classification` | enum | `script` / `cited` / `unsupported` |
| `weak` | bool | 종목 문맥이 있는데 다른 종목 경로에서만 맞은 경우 — 일치로 치지 않고 참고로 `matched_path`만 남김 (규칙 §4-5) |
| `matched_path` | string/null | 일치한 스냅샷 경로 |
| `match_count` | int | 일치한 경로 수 |
| `snapshot_status` | string/null | 일치한 값의 `status` (`provisional` 등) |

**용어 대응**: spec의 '스크립트 값 일치' = `script`, '인용 출처 있음' = `cited`, '근거 없음' = `unsupported`, '대조 불가'(짝 스냅샷 없음) = `no_snapshot` 문제.

**분류 순서**: 제외 규칙 → 스냅샷 일치(`script`) → 범위 내 인용(`cited`) → 나머지(`unsupported`). 스크립트 일치와 인용이 둘 다 있으면 `script`로 두고 `scope_citations`도 남긴다.

### 2-2. ExcludedCount (제외 집계)

범주(`date`, `year`, `period_label`, `duration`, `numbering`, `citation`, `ticker_code`, `product_spec`, `diagram_style`)별 개수. 개별 목록은 `--verbose`일 때만 낸다.

### 2-3. Reference (참고문헌 항목)

| 필드 | 타입 | 뜻 |
|---|---|---|
| `number` | int | 번호 |
| `title` | string/null | 제목 |
| `date` | string/null | `YYYY-MM-DD` |
| `url` | string/null | 주소 |
| `cited` | bool | 본문에서 인용했는지 |
| `problems` | enum[] | `missing_title`, `missing_date`, `missing_url`, `homepage_url`, `unused` |
| `fetch` | object/null | 기사 대조 결과 (`--fetch-sources`일 때만): `status`(`found`/`not_found`/`unverifiable`), `checked`(대조한 숫자 ID 목록), `missing`(문서에 없던 숫자 ID), `reason` |

### 2-4. Section4Check

| 필드 | 타입 | 뜻 |
|---|---|---|
| `baseline` | `present`/`missing` | 스냅샷에 기준본이 있는지 |
| `changed_lines` | object[] | `{line, current, original}` — 현재 보고서와 기준본이 다른 줄 |
| `snapshot_missing` | object[] | 기준본 Section 4 숫자 중 스냅샷에 없는 것 (NumberMention 축약) |
| `warnings_missing` | string[] | 8번 경고 중 스냅샷 `warnings`에 없는 문장 |

### 2-5. Issue (문제)

점검 결과의 모든 문제를 한 목록으로 모은다.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `id` | string | NumberMention이면 그 ID, 그 밖에는 `{kind}-{대상}` (예: `ref-homepage-7`) |
| `kind` | enum | `unsupported_number`, `section4_changed`, `section4_not_in_snapshot`, `warning_not_in_snapshot`, `missing_citation_target`, `reference_format`, `unused_reference`(경고), `ai_todo_left`, `no_snapshot`, `no_baseline`, `check_section_missing`, `check_section_stale`, `source_not_found`, `source_unverifiable` |
| `severity` | `error`/`warning` | `unused_reference`만 `warning` |
| `location` | string | 섹션 제목·줄 번호 |
| `message` | string | 사람이 읽는 설명 |
| `documented` | bool | '숫자 점검 결과' 섹션에 사유와 함께 적혀 있는지 |

### 2-6. CheckResult (점검 결과)

| 필드 | 타입 | 뜻 |
|---|---|---|
| `report` | string | 보고서 경로 |
| `snapshot` | string/null | 짝 스냅샷 경로 |
| `checked_at` | string | KST 시각 |
| `counts` | object | `script`, `cited`, `unsupported`, `weak`(다른 종목 값과만 맞은 수, 분류와 별개), `excluded`(범주별) |
| `mentions` | NumberMention[] | 본문 숫자 전체 |
| `section4` | Section4Check | |
| `references` | Reference[] | |
| `ai_todo` | object[] | `{line, text}` |
| `issues` | Issue[] | |
| `exit_code` | 0/1/2 | [contracts/cli.md](contracts/cli.md) |

## 3. 보고서의 '숫자 점검 결과' 섹션

점검 도구가 출력하고 AI가 '## 8. 참고 문헌' 목록 뒤, 면책 문구 앞에 '## 9.'로 넣는다. 형식은 [contracts/cli.md](contracts/cli.md#보고서에-넣는-숫자-점검-결과-섹션).

**상태 전이 (보고서 마무리)**:

```
AI_TODO 채움 → 점검(1) ─문제 0건──────────────────────────────→ 섹션 붙임 → 점검 → exit 0 → 완료
                 └ 문제 있음 → 수정 → 점검(n) … ─남은 문제─→ 섹션 붙임·사유 작성 → 점검 → exit 0 → 완료
                                                          (섹션 없음·개수 다름·사유 없음 → exit 1 → 다시)
```

## 4. 검증 세트 `tests/fixtures/002/labels.json`

```json
{
  "report": "report.md",
  "snapshot": "report_data.json",
  "labels": [
    {"id": "a1f3-52.18%-1", "raw": "52.18%", "expected": "script", "note": ""},
    {"id": "a1f3-107.4조-1", "raw": "107.4조", "expected": "cited", "note": "[7]"}
  ]
}
```

`expected`는 `script`·`cited`·`unsupported`·`excluded`. 사람이 확정한다(R11).
