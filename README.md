# Value Chain Analysis & Investment Strategy Agents

Antigravity 에이전트를 위한 산업 밸류체인 분석, 정밀 기업 재무 평가 및 통합 투자 전략 스킬 저장소입니다.

---

## 📂 저장소 디렉토리 구조

```
.agents/
├── .gitignore
├── README.md
└── skills/
    ├── financial-analyst/
    │   ├── SKILL.md
    │   ├── references/rules/        # 판정·데이터 규칙 원본
    │   ├── scripts/
    │   │   ├── get_financial_stats.py
    │   │   ├── data_checks.py       # 출처 교차 점검
    │   │   └── check_data_sources.py # 정기 점검 도구
    │   └── templates/
    │       └── financial_report_template.md
    ├── value-chain-analyzer/
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   └── generate_mermaid.py
    │   └── templates/
    │       └── report_template.md
    └── investment-strategy/
        ├── SKILL.md
        └── scripts/
            └── generate_strategy_report.py
```

운영 지식은 스킬과 함께 저장소 루트에서 관리합니다(스킬 설치에는 필요 없음).

```
CLAUDE.md                 # 이 저장소 작업 규칙
wiki/                     # 데이터 출처 백과·사건 기록(KI-xxx) — karpathy-llm-wiki 패턴
raw/                      # 위키 근거 자료 (수정 금지)
docs/decisions/           # 결정 기록
tests/                    # data_checks 테스트
.claude/skills/karpathy-llm-wiki/  # 위키 스킬 (고정 커밋 복사본, MIT)
```

---

## 📦 설치

세 스킬은 같은 `skills` 폴더에 나란히 있어야 합니다(`investment-strategy`가 나머지 둘의 스크립트를 실행).

### Antigravity
이 저장소를 프로젝트의 `.agents` 폴더로 내려받고, 프로젝트 가상환경에 패키지를 설치합니다.
```bash
git clone https://github.com/hyunghopark/value-chain-analysis-skills.git .agents
python -m venv venv
venv/bin/pip install -r .agents/skills/financial-analyst/requirements.txt   # Windows: venv\Scripts\pip.exe
```

### Claude Code
저장소를 아무 곳에나 내려받고, 세 스킬 폴더를 `~/.claude/skills`(모든 프로젝트) 또는 `<프로젝트>/.claude/skills`(해당 프로젝트)에 링크합니다. SKILL.md 안의 `${CLAUDE_SKILL_DIR}`가 스킬 폴더 경로로 바뀌어 스크립트를 찾습니다.

macOS / Linux:
```bash
git clone https://github.com/hyunghopark/value-chain-analysis-skills.git ~/value-chain-analysis-skills
mkdir -p ~/.claude/skills
for s in investment-strategy financial-analyst value-chain-analyzer; do ln -s ~/value-chain-analysis-skills/skills/$s ~/.claude/skills/$s; done
```

Windows (PowerShell, 관리자 권한 불필요):
```powershell
git clone https://github.com/hyunghopark/value-chain-analysis-skills.git "$HOME\value-chain-analysis-skills"
foreach ($s in 'investment-strategy','financial-analyst','value-chain-analyzer') { New-Item -ItemType Junction -Path "$HOME\.claude\skills\$s" -Target "$HOME\value-chain-analysis-skills\skills\$s" }
```

Python 패키지는 [uv](https://docs.astral.sh/uv/)가 있으면 SKILL.md의 `uv run --with-requirements ...` 명령이 알아서 설치합니다. uv가 없으면 가상환경에 `requirements.txt`를 설치하고 그 Python으로 실행하세요. 새 Claude Code 세션부터 `/investment-strategy`, `/financial-analyst`, `/value-chain-analyzer`로 쓸 수 있습니다.

> **claude.ai 업로드**는 지원 범위 밖입니다. claude.ai는 SKILL.md 앞머리에 지원하지 않는 항목(예: Antigravity 전용 `allowed-skills`)이 있으면 업로드를 거부하고, 실행 환경에서 금융 사이트 접속이 막혀 있을 수 있습니다.

### 보고서 저장 위치
`reports/` 폴더는 스킬을 프로젝트 안(`<프로젝트>/.agents/skills`, `<프로젝트>/.claude/skills`)에 설치했으면 그 프로젝트에, 개인 설치(`~/.claude/skills` 등)면 현재 작업 폴더에 만들어집니다. `--output`으로 직접 지정할 수도 있습니다.

---

## 🛠️ 포함된 스킬 (Skills)

### 1. `value-chain-analyzer` (v1.3.0)
- **개요**: 산업 및 기술 생태계의 전방(Upstream), 중방(Midstream), 후방(Downstream) 구조 분석
- **핵심 기능**:
  - 핵심 소재, 부품, 장비 및 주요 과점 벤더 식별
  - 병목(Bottleneck) 및 핵심 밸류체인 노드 도출
  - Mermaid 다이어그램 자동 생성 및 시각화 (역할 태그, 이중 역할 `[병목협력·경쟁]` 지원)

### 2. `financial-analyst` (v3.1.0)
- **개요**: 상장 기업의 정량 재무 지표 및 밸류에이션(Valuation) 정밀 평가
- **핵심 기능**:
  - PER, PBR, EV/EBITDA, ROE, 부채비율 등 핵심 지표와 4-Horizon PER·EPS(TTM·FY0·FY1·NTM)
  - **[경기순환 판정]**: 순환업종 자동 감지(연간 순이익 50% 이상 감소 이력) + `--cyclical` 지정, 사이클 위치(이익률)와 같은 방식으로 계산한 과거 P/B 밴드로 판정
  - **[추정치·실적]**: 최근 30일 EPS 추정치 상향/하향, 다음 실적 발표일, 최근 4분기 EPS 서프라이즈
  - **[시나리오]**: 내년 컨센서스 EPS 최저·평균·최고 × 현재 배수/목표가 내재 배수, 확률가중 기대값
  - **[회계 감사]**: 일회성 손익 감지 및 같은 분모로 다시 계산한 명목·정규화 ROE/EPS
  - **[수급·시장 비교]**: 최근 5거래일 투자자별 순매매 추정(장중 행은 '잠정' 표시), 지수·해외 피어 동반 등락
  - **[데이터 품질 경고]**: 출처 간 5% 이상 차이, ADR 통화 보정, 가격 이력 누락 등을 보고서에 자동 표기. 경고마다 사건 번호 `[KI-xxx]`
  - **[출처 교차 점검]**: 한국 종목 Yahoo 가격 이력을 거래소 종가(다음 금융)로 보완·교정, 수급 금액을 거래소 종가로 계산, WiseReport 표 구조 검증, 재무제표 반영 지연·거래량 이상치 감지

### 3. `investment-strategy` (v2.0.0)
- **개요**: `value-chain-analyzer`와 `financial-analyst` 스킬을 결합한 통합 투자 전략 수립 파이프라인
- **핵심 기능**:
  - **Phase 1**: 밸류체인 맵핑 및 '1+2+1 Framework'(타겟 1 + 직접경쟁 2 + 핵심병목 1)에 기반한 비교 분석 대상 4개사 선정, 검증 체크리스트
  - **Phase 2**: 4개사 정밀 재무 밸류에이션, 경기순환 판정, 회계 감사, 시나리오 스트레스 테스트
  - **Phase 3**: 8단계 투자 전략 보고서 도출 (판정 연동 실행 전략, 반대 논리·판단 무효화 조건, 면책 문구)
  - **객관성 원칙**: 결론을 먼저 정하지 않고, 스크립트 판정과 일치시키며, 출처·기준 시각·추정/잠정 여부를 명시

---

## 🧰 유지보수

- **규칙**: 판정 기준의 원본은 `skills/financial-analyst/references/rules/`입니다. 기준을 바꾸면 규칙 문서·코드·테스트를 한 커밋에서 고치고 `docs/decisions/`에 이유를 남깁니다.
- **데이터 사건**: 보고서 경고의 `[KI-xxx]`는 `wiki/known-issues/` 문서 번호입니다. 새 문제는 `references/rules/data-quality.md`의 절차(근거 → 사건 문서 → 코드 경고 → 테스트)를 따릅니다.
- **정기 점검**: `check_data_sources.py` 결과를 `raw/data-checks/`에 저장하고 위키에 반영합니다. 명령은 `CLAUDE.md`에 있습니다.

## 📝 변경 이력

### 2026-10-14 — 데이터 품질 관리 체계
- **출처 교차 점검 추가**: 한국 종목 가격을 거래소 종가(다음 금융) 기준으로 대조해 Yahoo의 누락·오류를 보완하고, 수급 금액을 거래소 종가로 계산합니다(네이버 종가 필드가 2026-09-14부터 거래소 종가와 달라짐).
- **조용한 오류 방지**: WiseReport 표 구조 검증, 재무제표 반영 지연·거래량 이상치 경고, 모든 데이터 경고에 사건 번호.
- **지식 관리**: 규칙 원본 문서, LLM 위키(출처 백과·사건 기록 8건, 근거 자동 대조), 결정 기록 3건, 저장소 작업 규칙(CLAUDE.md), 테스트 추가.

### 2026-10 — 객관성·경기순환 대응 개편
- **결론 선행 지시 제거**: "안전마진을 증명하라" 등 매수 결론을 전제한 지시를 "검증하라"로 바꾸고, 결론·매매 전략을 판정(🟢/🟡/🔴)에 연동했습니다.
- **스트레스 테스트를 스크립트가 계산**: AI가 영업이익·배수를 지어내던 표를 없애고, 컨센서스 EPS 범위와 두 가지 배수로 스크립트가 계산합니다.
- **경기순환 업종 판정 추가**: 이익 정점에서 PER·PEG가 낮아 보이는 문제를 막기 위해 P/B 밴드·사이클 위치·추정치 방향으로 판정합니다.
- **판정 문구 정리**: '조건부 매수(중립)' 대신 '중립/관망', 데이터 부족 시 '판단 보류'를 냅니다.
- **검증 단계 추가**: 최근 실적·잠정실적, 추정치 방향, 지수·피어 동반 등락, 촉매 최신성(90일)을 체크리스트로 확인합니다.
- **데이터 정확성**: 키옥시아 고정 문구 삭제, 정규화 ROE 분모 통일, 장중 수급 '확정' 오표기 수정, 출처 혼합(목표가·시가총액) 정리, WiseReport 실패 시 라벨 표시, RSI 와일더 방식, 가격 이력 누락 보정.
- **안정성**: 보조 스크립트가 실패하면 보고서를 만들지 않고 종료, `shell=True` 제거, Windows UTF-8 출력 처리.
- **Claude Code 호환**: SKILL.md 실행 명령을 `${CLAUDE_SKILL_DIR}` 기준(Claude Code)과 `.agents` 기준(Antigravity)으로 함께 표기, 도구 이름 병기, 스킬별 `requirements.txt` 추가, 개인 설치 시 보고서를 홈 폴더가 아닌 현재 작업 폴더에 저장.
