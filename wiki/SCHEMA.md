# LLM Wiki Schema — 금융 가치평가 및 GICS 산업 분류 체계

> **아키텍처 표준**: Andrej Karpathy's 3-Layer LLM Wiki Pattern (v2.1.0)
> **목적**: 글로벌 11대 GICS 섹터(163개 세부 산업)와 기관급 5대 비즈니스 프로파일 가치평가 체계를 상호 연결된 마크다운 지식 베이스로 영구 관리합니다.

---

## 1. 디렉토리 구조 (Three Layers)

```
wiki/
├── SCHEMA.md           # 위키 규칙, 도메인 설정, 태그 분류 체계 (Layer 3)
├── index.md            # 전체 위키 문서 카탈로그 및 한 줄 요약 (Layer 2)
├── log.md              # 시계열 생성 및 갱신 이력 로그 (Layer 2)
├── raw/                # 원본 자료 보관소 — 불변 (Layer 1)
│   ├── articles/       # 리서치 아티클 및 공시 원문
│   ├── papers/         # 금융공학 백서 및 방법론 문서
│   ├── transcripts/    # 어닝콜 및 인터뷰 기록
│   └── assets/         # 다이어그램 및 차트 이미지
├── concepts/           # 핵심 이론 및 프레임워크 문서 (Layer 2)
├── entities/           # GICS 11대 섹터 및 163개 세부 산업 심층 페이지 (Layer 2)
├── comparisons/        # 섹터 및 기업 간 비교 분석 (Layer 2)
└── queries/            # 주요 리서치 질의 및 분석 결과 아카이브 (Layer 2)
```

---

## 2. 문서 작성 규칙 (Conventions)

1. **YAML Frontmatter 필수**:
   모든 위키 문서는 상단에 아래와 같은 YAML 메타데이터를 포함합니다.
   ```yaml
   ---
   title: "문서 제목"
   category: "concept | entity | comparison | query"
   gics_code: "해당 시 GICS 코드 (예: 45, 45301020)"
   profile: "cyclical | cash_cow_dividend | tech_high_growth | financials | biotech_pipeline | general"
   tags: [gics, valuation, kpi, ...]
   updated: "YYYY-MM-DD"
   ---
   ```
2. **상호 링크 (Interlinking)**:
   - 관련 개념 및 섹터 문서는 상대 경로 마크다운 링크(예: `[5대 비즈니스 프로파일](../concepts/5대-비즈니스-프로파일-평가체계.md)`)로 연결합니다.
3. **5대 메타 프로파일 표준 기호**:
   - `🔄 경기순환형 (cyclical)`: 장치산업, 원자재, 하드웨어 사이클 업종
   - `🛡️ 배당·현금흐름형 (cash_cow_dividend)`: 필수소비재, 유틸리티, 통신, 인프라 배당 업종
   - `🚀 고성장·무형자산형 (tech_high_growth)`: 소프트웨어, 클라우드 SaaS, 플랫폼, AI
   - `🏦 금융·자본효율형 (financials)`: 은행, 보험, 증권, 여신, 결제 네트워크
   - `🧪 R&D·파이프라인형 (biotech_pipeline)`: 신약개발 바이오텍, 임상 단계 딥테크
4. **지표 표기 원칙**:
   - 각 세부 산업은 **Tier 1 (공통 재무 매트릭스 4대 기둥)**과 **Tier 2 (세부 산업 특화 현장 KPI)**로 구분하여 기술합니다.
   - 해당 산업에서 회계적 착시를 유발하는 지표는 반드시 **`🚫 왜곡 제외 지표 ('· 제외')`**로 명시합니다.
