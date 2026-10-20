# CLI Contract: 수집·정제·계산·출력 분리

**Spec**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

## 1. `get_financial_stats.py` (변경: 내부만)

```bash
uv run --no-project --with-requirements skills/financial-analyst/requirements.txt \
  python skills/financial-analyst/scripts/get_financial_stats.py \
  --tickers "000660.KS,005930.KS,MU,TSM" [--cyclical ...] [--not-cyclical ...] [--benchmarks ...] [--weights 0.2,0.5,0.3] [--snapshot X_data.json]
```

| 항목 | 계약 |
|---|---|
| 인자 | 바뀌지 않는다(FR-009) |
| 표준 출력 | Section 4 마크다운. 형식 그대로이고, 원자료에서 만든다(R7) |
| 표준 오류 | `Fetching data for …` 진행 표시와 `[Warn]` 경고. 경고는 이제 정제·계산 단계에서 나온다 |
| `--snapshot` | 형식 2로 저장한다([data-model §1](../data-model.md#1-스냅샷-형식-2-최상위)). 저장에 실패하면 지금처럼 경고하고 보고서는 계속 만든다 |
| 종료 코드 | 그대로. 데이터를 하나도 못 받으면 1 |
| 네트워크·시각 | 수집 모듈만 쓴다 |

## 2. `rebuild_section4.py` (신규)

```bash
# 재현 확인: 저장된 Section 4·values·warnings와 비교
uv run --no-project --with-requirements skills/financial-analyst/requirements.txt \
  python skills/financial-analyst/scripts/rebuild_section4.py reports/X_data.json [--json result.json] [--print] [--verbose]

# 옵션 재계산 (확률·순환업종만, 별도 파일로)
... rebuild_section4.py reports/X_data.json --weights 0.1,0.5,0.4 [--cyclical 005930.KS] [--not-cyclical MU] --out reports/X_recompute.md
```

| 인자 | 뜻 |
|---|---|
| `SNAPSHOT` | 형식 2 스냅샷 하나. 다른 파일은 읽지 않는다(FR-010) |
| `--json PATH` | [재현 결과](../data-model.md#5-재현-결과-reproduction-result)를 JSON으로 저장 |
| `--print` | 다시 만든 Section 4를 표준 출력에 낸다 |
| `--verbose` | 차이를 모두 보여 준다(기본: 앞쪽 20개) |
| `--weights`, `--cyclical`, `--not-cyclical` | 옵션 재계산 모드. `--out` 필수 |
| `--out PATH` | 재계산 결과 마크다운. 이미 있으면 `output_exists` |
| 그 밖의 옵션(`--tickers`, `--benchmarks` 등) | 받지 않는다(`option_rejected`) |

### 종료 코드

| 코드 | 확인 모드 | 재계산 모드 |
|---|---|---|
| 0 | Section 4(기준본이 있을 때)·values·warnings가 모두 같음 | 계산 완료, 파일 저장 |
| 1 | 하나 이상 다름 | (쓰지 않음) |
| 2 | 다시 만들 수 없음: `legacy_format`, `missing_input`, `invalid_input`, `unreadable` | 같은 오류와 `option_needs_data`, `output_exists` |

### 표준 출력 요약 (확인 모드)

```text
재현 확인: reports/X_data.json (형식 2, 수집 2026-10-20 14:05 KST)
버전: 같음  (다르면: pandas 3.0.3 → 3.0.5 — 결과가 다르면 아래에 나타납니다)
Section 4: 같음 (기준본 412줄)            | 다름: 3줄 — 41행 "..." → "..."
계산 결과(values): 같음 (2,871개)          | 다름: 바뀜 2 · 새로 생김 0 · 없어짐 0 — MU.metrics.forward_pe 9.81 → 9.83
데이터 품질 경고: 같음 (14개)
결과: 같음 (종료 코드 0)
```

- 이전 형식이면 다음을 출력한다. `이 스냅샷은 원자료가 없는 이전 형식(001·002)이라 다시 만들 수 없습니다. 숫자 점검(check_report_numbers.py)은 그대로 쓸 수 있습니다.` 종료 코드는 2다.
- 원자료가 빠졌으면 다음을 출력한다. `원자료 없음: inputs.MU.quarterly_balance_sheet — 스냅샷이 손상됐거나 다른 도구로 만든 파일입니다.` 종료 코드는 2다.

### 재계산 결과 파일 머리

```markdown
> 🔁 **재계산 결과 — 보고서가 아닙니다.** 원본 스냅샷: `X_data.json` (sha256 1a2b…), 수집 2026-10-20 14:05 KST.
> 바꾼 옵션: weights 0.2,0.5,0.3 → 0.1,0.5,0.4. 데이터는 다시 받지 않았습니다.
```

그 아래에 다시 만든 Section 4를 붙인다. 원본 스냅샷과 보고서는 바꾸지 않는다.

## 3. `generate_strategy_report.py` (변경 없음)

명령과 출력 파일은 그대로다. `section4` 기준본은 지금처럼 덧붙인다. 기준본은 이제 원자료에서 만든 Section 4이므로, 생성 직후 재현 확인은 종료 코드 0이어야 한다(SC-001).

## 4. `check_report_numbers.py` (변경 없음)

형식 1과 형식 2 스냅샷을 모두 읽는다. 새 최상위 키(`inputs`)는 쓰지 않는다.

## 5. `investment-strategy` 연동 (SKILL.md)

Phase 3의 숫자 점검(002) 앞에 선택 단계를 넣지 않는다. 재현 확인은 검토자와 개발자가 쓰는 도구다. `financial-analyst/SKILL.md`의 Resources에 `rebuild_section4.py`를 추가하고, `--snapshot` 설명을 바로잡는다. 지금 설명은 "all raw inputs"라고 되어 있지만 실제로는 원자료가 저장되지 않았다. 003 이후에는 그 설명이 사실이 된다.
