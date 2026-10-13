# value-chain-analysis-skills 작업 규칙

투자 분석 스킬 3개(`skills/`)와 그 운영 지식(규칙·사실·결정)을 함께 관리하는 저장소입니다.

## 어디에 무엇이 있나

| 경로 | 내용 |
|---|---|
| `skills/` | 스킬 본체 (SKILL.md, 스크립트). `~/.claude/skills/`에 링크해서 씁니다. |
| `skills/financial-analyst/references/rules/` | **판정·데이터 규칙의 원본.** 기준값은 여기와 코드에만 둡니다. |
| `wiki/` | 데이터 출처 백과와 사건 기록(`known-issues/`). karpathy-llm-wiki 패턴, LLM이 관리합니다. |
| `raw/` | 위키의 근거 자료. 한 번 저장하면 수정하지 않습니다. |
| `ROADMAP.md` | 목표와 단계별 상태. |
| `specs/NNN-이름/` | 목표별 요구사항(`spec.md`) → 설계(`plan.md`) → 작업(`tasks.md`). 구현은 확정된 spec·plan을 따릅니다. |
| `docs/decisions/` | 왜 그렇게 정했는지(결정 기록). |
| `tests/` | `data_checks.py` 테스트. |
| `.claude/skills/karpathy-llm-wiki/` | 위키 스킬 (고정 커밋 복사본, 이 저장소에서만 작동). |

## 규칙

1. **기준값을 바꾸면** 규칙 문서·코드·테스트를 같은 커밋에서 고치고, `docs/decisions/`에 이유를 남깁니다.
2. **새 데이터 문제를 발견하면** `references/rules/data-quality.md`의 '새 데이터 문제를 발견했을 때' 절차를 따릅니다. 근거(`raw/`) → 사건 문서(`wiki/known-issues/`) → 코드 경고 `ki('KI-NNN', ...)` → 테스트 순서입니다.
3. **위키에는 방법론과 데이터 품질 사실만** 넣습니다. 기업별 분석 결론·판정·목표가는 넣지 않습니다(investment-strategy의 Clean-Slate 원칙).
4. 위키 숫자는 `raw/`에 글자 그대로 있어야 합니다. 커밋 전 근거 대조를 돌립니다.
5. **새 목표나 큰 변경은** `specs/`에 spec → plan → tasks 순으로 쓰고 확정한 뒤 구현합니다. 범위가 바뀌면 spec부터 고칩니다.
6. 비공식 출처(네이버·다음·WiseReport)는 언제든 바뀔 수 있으므로, 정기 점검 결과가 바뀌면 사건 문서의 상태를 갱신합니다(지우지 않고 Outdated 표시).

## 명령

```bash
# 테스트
uv run --no-project --with-requirements skills/financial-analyst/requirements.txt --with pytest pytest tests -q
# 출처 정기 점검 (결과를 raw/data-checks/YYYY-MM-DD-cross-source-check.md로 저장한 뒤 위키에 ingest)
uv run --no-project --with-requirements skills/financial-analyst/requirements.txt python skills/financial-analyst/scripts/check_data_sources.py --krx 005930,000660 --us MU
# 위키 근거 대조
python .claude/skills/karpathy-llm-wiki/scripts/check_evidence.py .
```
