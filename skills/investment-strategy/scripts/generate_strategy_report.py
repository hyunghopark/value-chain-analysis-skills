import argparse
import subprocess
import os
import sys

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True, check=True)
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        if e.stdout:
            print(e.stdout, file=sys.stderr)
        return ""

def find_repo_root():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cur = script_dir
    while cur != os.path.dirname(cur):
        if os.path.basename(cur) == ".agents":
            return os.path.dirname(cur)
        cur = os.path.dirname(cur)
    return os.path.abspath(os.path.join(script_dir, "../../../../"))

def main():
    parser = argparse.ArgumentParser(description="Generate an Investment Strategy Report Master Template")
    parser.add_argument("--industry", type=str, required=True, help="Name of the industry")
    parser.add_argument("--upstream", type=str, required=True, help="Upstream components")
    parser.add_argument("--midstream", type=str, required=True, help="Midstream components")
    parser.add_argument("--downstream", type=str, required=True, help="Downstream components")
    parser.add_argument("--tickers", type=str, required=True, help="Comma-separated list of tickers")
    parser.add_argument("--output", type=str, default="", help="Optional output markdown file path")
    
    args = parser.parse_args()
    py_exec = sys.executable or "python3"
    
    # Robust absolute paths to helper scripts based on repo root
    repo_root = find_repo_root()
    mermaid_script = os.path.join(repo_root, ".agents/skills/value-chain-analyzer/scripts/generate_mermaid.py")
    financial_script = os.path.join(repo_root, ".agents/skills/financial-analyst/scripts/get_financial_stats.py")
    
    print(f"⏳ Generating Value Chain Diagram for {args.industry}...")
    # 1. Generate Mermaid Diagram
    mermaid_cmd = f"\"{py_exec}\" \"{mermaid_script}\" --industry \"{args.industry}\" --upstream \"{args.upstream}\" --midstream \"{args.midstream}\" --downstream \"{args.downstream}\" --lang ko"
    mermaid_output = run_command(mermaid_cmd)
    
    print(f"⏳ Fetching Financial Data for tickers: {args.tickers}...")
    # 2. Get Financial Stats
    financial_cmd = f"\"{py_exec}\" \"{financial_script}\" --tickers \"{args.tickers}\""
    financial_output = run_command(financial_cmd)
    
    # Strip duplicate top-level H2 header from financial output if present
    cleaned_financial = financial_output
    prefix_header = "## 📊 Yahoo Finance API 실시간 데이터 분석 결과"
    if cleaned_financial.startswith(prefix_header):
        cleaned_financial = cleaned_financial[len(prefix_header):].strip()
    
    # Parse tickers and build dynamic company analysis blocks
    tickers_list = [t.strip() for t in args.tickers.split(',') if t.strip()]
    company_blocks = []
    for idx, ticker in enumerate(tickers_list, 1):
        block = f"""### {idx}) {ticker}
- **밸류에이션 판정**: [AI_TODO: 🟢 저평가(매수) / 🟡 적정(중립) / 🔴 고평가(신중) 판정]
- **핵심 투자 포인트 & 촉매제 (Catalysts)**: [AI_TODO: 실적 턴어라운드, 신규 수주, 제품 사이클, 마진 개선 등]
- **개별 리스크 요인**: [AI_TODO: 단일 고객사 의존도, 가격 경쟁, 환율 및 규제 리스크 등]"""
        company_blocks.append(block)
    
    company_analysis_section = "\n\n".join(company_blocks) if company_blocks else "[AI_TODO: 분석 대상 기업 정보를 입력하세요.]"
    
    # 3. Assemble the Master Template
    from datetime import datetime
    safe_industry_name = args.industry.replace(' ', '_').replace('/', '_')
    today_str = datetime.now().strftime("%Y%m%d")
    
    if args.output:
        output_filename = args.output
    else:
        reports_dir = os.path.join(repo_root, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        base_name = f"{safe_industry_name}_{today_str}_Investment_Strategy_Report"
        output_filename = os.path.join(reports_dir, f"{base_name}.md")
        # Ensure we never overwrite an existing report (auto-increment version)
        counter = 2
        while os.path.exists(output_filename):
            output_filename = os.path.join(reports_dir, f"{base_name}_v{counter}.md")
            counter += 1
            
    output_parent = os.path.dirname(os.path.abspath(output_filename))
    if output_parent:
        os.makedirs(output_parent, exist_ok=True)
    
    formatted_date = f"{today_str[:4]}-{today_str[4:6]}-{today_str[6:]}"
    
    template = f"""# {args.industry} 투자 전략 보고서

> **분석 기준일**: {formatted_date} (실시간 시장 데이터 기준)  
> **한 줄 결론**: [AI_TODO: 🟢/🟡/🔴 현재 주가 국면(급락/조정/상승), 핵심 시장 논쟁(피크아웃 등), 실전 매매 스탠스(공격적 분할 매수 / 신중 관망)]

---

## 1. 산업 개요 및 최근 시장 동향

### 1.1. 중장기 산업 규모 및 구조적 성장 동인
[AI_TODO: {args.industry} 산업의 시장 규모, 연평균 성장률(CAGR), 구조적 슈퍼사이클 등 중장기 전망을 요약하여 작성하세요.]

### 1.2. 최근 시장 변동성 및 핵심 현안 진단 (급락/급등 원인 분석)
[AI_TODO: 최근 1~5일간 주가 급변동(급락/급등) 및 52주 고점 대비 낙폭(Drawdown), 시장을 흔든 직접적 트리거(경쟁사 기술 발표, 실적 피크아웃 논쟁, 규제, 수급 등)를 분석하고, 이것이 '일시적 과민반응(노이즈)'인지 '구조적 펀더멘털 훼손'인지 판별하세요.]

---

## 2. 가치사슬 구조도

{mermaid_output}

---

## 3. 핵심 병목(Bottleneck) 및 해자(Moat) 분석

산업의 핵심 병목 현상과 강력한 해자(Moat)를 지닌 기업들을 분석합니다.

| 기업명 | 티커 | 가치사슬 위치 | 핵심 역할 및 경제적 해자(Moat) |
|---|---|---|---|
| [AI_TODO] | [AI_TODO] | [AI_TODO] | [AI_TODO] |
| [AI_TODO] | [AI_TODO] | [AI_TODO] | [AI_TODO] |
| [AI_TODO] | [AI_TODO] | [AI_TODO] | [AI_TODO] |

---

## 4. 실시간 정량 재무 지표 및 투자 시그널 매트릭스

{cleaned_financial}

---

## 5. 기업별 심층 분석 및 밸류에이션 판단

[AI_TODO: 위 4번 정량 재무 지표 및 시그널 매트릭스를 기반으로 개별 기업의 밸류에이션 매력도와 투자 판단을 서술하세요.]

{company_analysis_section}

---

## 6. 핵심 리스크 평가 (필수)

| 리스크 요인 | 영향도 (H/M/L) | 상세 설명 및 모니터링 포인트 |
|---|---|---|
| [AI_TODO: 리스크 1] | High/Medium | [AI_TODO: 설명] |
| [AI_TODO: 리스크 2] | High/Medium | [AI_TODO: 설명] |
| [AI_TODO: 리스크 3] | High/Medium/Low | [AI_TODO: 설명] |

### 6.1. 핵심 가치 드라이버(Key Driver) 시나리오별 실적 민감도 분석 (스트레스 테스트)

> 💡 **범용 가치 평가 스트레스 테스트**: 산업별 핵심 변수(반도체는 D램 ASP, 2차전지는 메탈가, 자동차는 환율/출하량 등) 변동 시나리오에 따른 영업이익, EPS, 이론적 내재가치 및 하방 안전마진(Margin of Safety)을 정량 산출합니다.

| 시나리오 구분 | 핵심 드라이버 가정 | 연간 영업이익 추정 | 12M Forward EPS | 적용 Target P/E | 시나리오별 적정주가 | 현재가 대비 상승여력 |
|---|---|---|---|---|---|---|
| **Bull Case (낙관)** | [AI_TODO: 드라이버 +15%] | [AI_TODO] | [AI_TODO] | [AI_TODO] | [AI_TODO] | [AI_TODO] |
| **Base Case (기준)** | [AI_TODO: 현 컨센서스] | [AI_TODO] | [AI_TODO] | [AI_TODO] | [AI_TODO] | [AI_TODO] |
| **Bear Case (비관)** | [AI_TODO: 드라이버 -15%] | [AI_TODO] | [AI_TODO] | [AI_TODO] | [AI_TODO] | [AI_TODO] |
| **확률가중 기대 적정주가** | **E[P] = 20%(Bull) + 50%(Base) + 30%(Bear)** | - | - | - | **[AI_TODO: 기대 주가]** | **[AI_TODO: 기대 상승여력]** |

> **안전마진 검증 결론 및 비대칭 손익비**: [AI_TODO: 최악의 침체(Bear Case) 시나리오에서도 현재가가 저평가되어 있는지 정량 증명하고, 비관 시나리오 30%를 가중하더라도 기대수익률이 양(+)으로 유지되는 비대칭 손익비(Asymmetric Risk/Reward) 분석]

---

## 7. 투자 전략 및 포트폴리오 배분 제안

### 🎯 7.1. 시장 변동성 국면 실전 매매 전략 (분할 매수 가이드)
[AI_TODO: Section 6.1의 Bear Case 적정가를 인용하여 하방 안전마진을 증명하고, Section 1-2 퀀트 기술적 모멘텀 지표(14일 RSI 과매도 및 20일 볼린저밴드 하단 이탈도)를 매매 트리거로 결합한 3단계 분할 매수 밴드(Tranches) 및 손절/리스크 관리 원칙을 제시하세요.]

### 💰 7.2. 포트폴리오 배분 제안
[AI_TODO: 핵심 병목 기업들을 중심으로 추천 투자 비중(%)을 제시하세요.]

---

## 8. 참고 문헌 (References)

[AI_TODO: 웹 리서치 및 데이터 수집 과정에서 참고한 핵심 출처 링크를 기재하세요. (예: [1] [출처 제목](URL))]
"""

    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(template)
        
    print(f"✅ 보고서 템플릿이 성공적으로 생성되었습니다: {output_filename}")
    print("🤖 AI 에이전트는 이제 replace_file_content 도구를 사용하여 [AI_TODO] 영역을 채워주세요.")

if __name__ == "__main__":
    main()
