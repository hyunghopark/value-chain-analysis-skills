# Quickstart: 수집·정제·계산·출력 분리 검증

**Spec**: [spec.md](spec.md) | **CLI**: [contracts/cli.md](contracts/cli.md)

구현이 끝났을 때 아래 순서로 확인한다. 명령은 저장소 루트(`.agents/`)에서 실행한다. 표기 편의상 다음 별칭을 쓴다.

```bash
PY=(uv run --no-project --with-requirements skills/financial-analyst/requirements.txt python)
S=skills/financial-analyst/scripts
```

## 1. 오프라인 테스트 (CI와 같음)

```bash
uv run --no-project --with-requirements skills/financial-analyst/requirements.txt --with-requirements tests/requirements-pinned.txt --with pytest pytest tests -q -m "not network" -rs
```

기대 결과:
- 모두 통과하고, 003 테스트 중 건너뛴 것이 없어야 한다.
- 003 테스트에 포함되는 것:
  - 시험 스냅샷 재현 동일성(SC-001, SC-006)
  - 외부 접속·시각 차단 실행과 코드 검사(SC-002)
  - 계산값 변조·원자료 누락 감지(SC-003)
  - 기준값 하나를 바꿨을 때 영향 범위(SC-005)
  - 표 형식 왕복
  - 이전 형식 거부
  - 옵션 재계산
- 002 검증 세트도 그대로 통과해야 한다(SC-008).

## 2. 새 보고서의 Section 4를 다음 날 다시 만들기 (SC-001)

```bash
"${PY[@]}" $S/get_financial_stats.py --tickers "000660.KS,005930.KS,MU,TSM" --snapshot /tmp/q003/a_data.json > /tmp/q003/a.md
# (다음 날, 또는 장 마감 후) 네트워크 없이:
"${PY[@]}" $S/rebuild_section4.py /tmp/q003/a_data.json --json /tmp/q003/a_rebuild.json
```

기대 결과:
- 생성 직후와 다음 날 모두 종료 코드 0이고, Section 4·values·warnings가 모두 같다.
- `get_financial_stats.py`만 실행해서 기준본이 없으면 `section4.compared: false`가 나온다. 이때는 `--print` 출력을 `a.md`와 비교한다. `generate_strategy_report.py`로 만든 보고서라면 기준본과 직접 비교한다.
- 장중(15:40 이전) 수집본과 장 마감 후 수집본을 하나씩 만들어 두 번 확인한다. 장중 수집본은 다시 만들어도 수급 표에 '잠정' 표시가 그대로 나와야 한다.

## 3. 변조와 누락 감지 (SC-003)

스냅샷 복사본에서 `values`의 값 하나를 바꾸고, `inputs.<종목>.quarterly_balance_sheet` 항목 하나를 지운 뒤 각각 실행한다.

기대 결과:
- 값을 바꾼 경우: 종료 코드 1. 바꾼 경로, 저장값, 재계산값이 나온다.
- 항목을 지운 경우: 종료 코드 2. `missing_input`과 경로가 나온다.

## 4. 이전 형식 (FR-008)

```bash
"${PY[@]}" $S/rebuild_section4.py tests/fixtures/002/report_data.json; echo "exit $?"
"${PY[@]}" $S/check_report_numbers.py tests/fixtures/002/report.md --snapshot tests/fixtures/002/report_data.json; echo "exit $?"
```

기대 결과:
- 재현 도구: 이전 형식 안내와 종료 코드 2.
- 숫자 점검: 지금과 같은 결과.

## 5. 옵션 재계산 (US3)

```bash
"${PY[@]}" $S/rebuild_section4.py /tmp/q003/a_data.json --weights 0.1,0.5,0.4 --out /tmp/q003/a_w.md
diff /tmp/q003/a.md /tmp/q003/a_w.md
"${PY[@]}" $S/rebuild_section4.py /tmp/q003/a_data.json --weights 0.1,0.5,0.4 --out /tmp/q003/a_w.md; echo "exit $?"
```

기대 결과:
- 첫 실행은 종료 코드 0이다.
- `diff`로 보면 다른 곳이 다음뿐이다.
  - 재계산 머리 2줄
  - 7번 시나리오 표의 확률 설명과 확률가중 기대값 행
- 두 번째 실행은 `output_exists`, 종료 코드 2다.
- 원본 `a_data.json`의 수정 시각과 SHA-256이 그대로다.

## 6. 분리 전후 같음 (FR-014, SC-004)

```bash
git worktree add /tmp/q003/main main
"${PY[@]}" tests/tools/replay_main.py --main /tmp/q003/main --snapshot /tmp/q003/a_data.json --out /tmp/q003/main_replay.md
"${PY[@]}" $S/rebuild_section4.py /tmp/q003/a_data.json --print > /tmp/q003/new.md
diff /tmp/q003/main_replay.md /tmp/q003/new.md
```

기대 결과:
- 재생 비교에서 다른 줄은 0줄이어야 한다(R12).
- 차이가 나면 줄마다 원인을 PR에 적는다. 예를 들어 `meta.generated_at`의 뜻 변경 때문에 데이터 기준 블록 시각이 다를 수 있다.
- 같은 시각에 실제로 실행한 비교(002 T037 방식)에서도 판정 기호가 있는 행과 종합 판단이 100% 같아야 한다.

## 7. 크기와 시간 (SC-006, SC-007)

```bash
ls -l /tmp/q003/a_data.json
time "${PY[@]}" $S/rebuild_section4.py /tmp/q003/a_data.json
```

기대 결과:
- 스냅샷이 10MB 이하다. 예상은 약 2MB다(R2).
- 재현이 10초 안에 끝난다.

## 8. 보고서 생성 끝에서 끝까지

```bash
"${PY[@]}" skills/investment-strategy/scripts/generate_strategy_report.py --industry "검증" --upstream "" --midstream "" --downstream "" \
  --tickers "000660.KS,MU" --output /tmp/q003/r.md
"${PY[@]}" $S/rebuild_section4.py /tmp/q003/r_data.json; echo "exit $?"
"${PY[@]}" $S/check_report_numbers.py /tmp/q003/r.md; echo "exit $?"
```

기대 결과:
- 재현 확인은 종료 코드 0(기준본과 같음)이다.
- 숫자 점검은 [AI_TODO]만 남은 상태로 지금과 같은 결과를 낸다.
