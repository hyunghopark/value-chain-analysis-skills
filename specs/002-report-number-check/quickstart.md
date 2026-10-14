# Quickstart: 보고서 숫자 자동 대조 검증

002가 동작하는지 끝에서 끝까지 확인하는 절차다. 명령 형식은 [contracts/cli.md](contracts/cli.md), 결과 구조는 [data-model.md](data-model.md)를 따른다.

## 준비

- 저장소 루트(`value-chain-analysis-skills`)에서 실행한다. `uv`가 있으면 따로 설치할 것은 없다.
- 단계 1~4는 네트워크가 필요 없다. 단계 5·6만 네트워크를 쓴다(로컬 전용).

```bash
UVR="uv run --no-project --with-requirements skills/financial-analyst/requirements.txt"
CHECK="$UVR python skills/financial-analyst/scripts/check_report_numbers.py"
```

## 1. 테스트 전체 (CI와 같음)

```bash
$UVR --with pytest pytest tests -q
```

기대: 모두 통과. 이 안에 아래가 들어 있다.
- 검증 세트(`tests/fixtures/002/`): 분류 일치율 95% 이상, `unsupported`를 다른 분류로 통과시킨 것 0건(SC-001), 근거 없음 비율 25% 이하(SC-002), 제외 대상의 오탐 5% 이하(SC-003)
- Section 4 숫자·판정 변경 주입 → 100% 감지(SC-004)
- 홈페이지 주소 참고문헌 17건 지적(SC-005)
- 기사 대조는 응답을 흉내 낸 테스트로만 확인

## 2. 검증 세트 보고서 점검

```bash
$CHECK tests/fixtures/002/report.md --snapshot tests/fixtures/002/report_data.json
echo "exit=$?"
```

기대: `exit=1`(기록되지 않은 문제가 있음). 요약 표에 분류별 개수, 문제 목록에 홈페이지 주소 참고문헌 17건과 근거 없는 숫자(위치·문맥 포함)가 나온다. 이 자료에는 Section 4 기준본이 없으므로 `no_baseline` 문제도 나온다. 실행 시간 10초 이내(SC-006).

## 3. 섹션 기록 흐름

```bash
cp tests/fixtures/002/report.md /tmp/r.md && cp tests/fixtures/002/report_data.json /tmp/r_data.json
$CHECK /tmp/r.md --snapshot /tmp/r_data.json --section   # 붙일 블록 출력
```

블록을 `/tmp/r.md`의 참고문헌 목록 뒤에 붙인 상태에서 다시 점검하면 `check_section_missing`은 사라지고, 사유가 `[AI_TODO]`인 문제는 계속 '기록 안 됨'으로 남는다(`exit=1`). 사유를 모두 채우면 `exit=0`.

## 4. 새 보고서의 Section 4 기준본 (로컬, 네트워크 필요)

```bash
$UVR python skills/investment-strategy/scripts/generate_strategy_report.py --industry "검증" \
  --upstream "A" --midstream "B" --downstream "C" --tickers "005930.KS,000660.KS,MU,TSM" \
  --output /tmp/v/report.md
python3 -c "import json;d=json.load(open('/tmp/v/report_data.json',encoding='utf-8'));print(d['section4']['sha256'][:12], len(d['section4']['text']))"
$CHECK /tmp/v/report.md --json /tmp/v/check.json; echo "exit=$?"
```

기대:
- 스냅샷에 `section4`가 있다.
- 점검 결과에서 `section4.changed_lines`가 0건, `section4.snapshot_missing`이 0건이다(SC-004, FR-015).
- `[AI_TODO]`가 남아 있으므로 `ai_todo_left` 문제로 `exit=1`이다.
- Section 4 표의 숫자 하나를 고치고 다시 점검하면 그 줄이 `section4_changed`로 나온다.

## 5. 기사 대조 (로컬 선택)

```bash
$CHECK /tmp/v/report.md --fetch-sources --json /tmp/v/check_fetch.json
```

기대: 참고문헌마다 `found`·`not_found`·`unverifiable` 중 하나가 붙는다. 홈페이지 주소나 접속 실패는 `unverifiable`이고 통과로 치지 않는다.

## 6. 판정 불변 (헌법 V)

단계 4의 보고서 Section 4를 001의 회귀 기준([baseline-section4.md](../001-data-snapshot/baseline-section4.md))과 같은 종목으로 비교한다. 002는 스냅샷 기록 경로만 추가하고 계산은 바꾸지 않는다. 더 확실한 비교는 같은 시각에 수정 전 코드(`git stash` 또는 `main`)와 수정 후 코드로 Section 4를 각각 만들어 판정(🟢🟡🔴)·종합 판단이 같은지 보는 것이다. 판정이 다르면 원인(코드 vs 데이터 변화)을 확인해 PR에 적는다.
