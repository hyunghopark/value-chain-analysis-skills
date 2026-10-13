# Value Chain Analysis & Investment Strategy Agents

Antigravity 에이전트를 위한 산업 밸류체인 분석, 정밀 기업 재무 평가 및 통합 투자 전략 워크플로우 저장소입니다.

---

## 📂 저장소 디렉토리 구조

```
.agents/
├── .gitignore
├── README.md
├── skills/
│   ├── financial-analyst/
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   └── get_financial_stats.py
│   │   └── templates/
│   │       └── financial_report_template.md
│   └── value-chain-analyzer/
│       ├── SKILL.md
│       ├── scripts/
│       │   └── generate_mermaid.py
│       └── templates/
│           └── report_template.md
└── workflows/
    ├── investment-strategy.md
    └── scripts/
        └── generate_strategy_report.py
```

---

## 🛠️ 포함된 스킬 (Skills)

### 1. `value-chain-analyzer` (v1.1.0)
- **개요**: 산업 및 기술 생태계의 전방(Upstream), 중방(Midstream), 후방(Downstream) 구조 분석
- **핵심 기능**:
  - 핵심 소재, 부품, 장비 및 주요 과점 벤더 식별
  - 병목(Bottleneck) 및 핵심 밸류체인 노드 도출
  - Mermaid 다이어그램 자동 생성 및 시각화

### 2. `financial-analyst` (v2.0.0)
- **개요**: 상장 기업의 실시간 정량 재무 지표 및 밸류에이션(Valuation) 정밀 평가
- **핵심 기능**:
  - PER, PBR, EV/EBITDA, ROE, 부채비율 등 6대 핵심 지표 분석
  - 최근 분기 실적 및 어닝 서프라이즈 추적
  - **[회계 감사 기능]**: 일회성 비경상 손익(Unusual Items) 감지 및 본업 기준 정규화(Normalized) 지표 대조 산출

---

## ⚡ 포함된 워크플로우 (Workflows)

### 1. `investment-strategy`
- **개요**: `value-chain-analyzer`와 `financial-analyst` 스킬을 결합한 통합 투자 전략 수립 파이프라인
- **프로세스**:
  - **Phase 1**: 밸류체인 맵핑 및 '1+2+1 Framework'(타겟 1 + 직접경쟁 2 + 핵심병목 1)에 기반한 비교 분석 대상 4개사 선정
  - **Phase 2**: 4개사 정밀 재무 밸류에이션 및 회계 감사 수행
  - **Phase 3**: 밸류체인 구조적 해자(Moat)와 밸류에이션 지표를 융합한 기관 수준의 투자 전략 보고서 도출
