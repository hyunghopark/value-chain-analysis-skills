import argparse
import datetime
import os
import subprocess
import sys

KST = datetime.timezone(datetime.timedelta(hours=9))
FINANCIAL_HEADER = "## 📊 정량 데이터 분석 결과 (스크립트 자동 산출)"


def run_script(cmd, label):
    """Run a helper script and return its stdout. Abort the whole report if it fails, so the
    agent never ends up filling empty data sections by hand."""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    except OSError as e:
        sys.exit(f"❌ {label} 실행 실패: {e}")
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0 or not result.stdout.strip():
        sys.exit(f"❌ {label} 실패 (exit code {result.returncode}). 보고서를 만들지 않았습니다. "
                 "위 오류를 해결한 뒤 다시 실행하세요. 표를 직접 채워 넣지 마세요.")
    return result.stdout.strip()


def find_reports_root():
    """Folder that gets reports/: the project holding a project-level .agents/.claude skills install,
    otherwise the current working directory (personal installs such as ~/.claude/skills live under home)."""
    home = os.path.normcase(os.path.realpath(os.path.expanduser("~")))
    cur = os.path.dirname(os.path.abspath(__file__))
    while cur != os.path.dirname(cur):
        if os.path.basename(cur) in (".agents", ".claude"):
            root = os.path.dirname(cur)
            if os.path.normcase(os.path.realpath(root)) != home:
                return root
            break
        cur = os.path.dirname(cur)
    return os.getcwd()


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Generate an Investment Strategy Report Master Template")
    parser.add_argument("--industry", type=str, required=True, help="Name of the industry")
    parser.add_argument("--upstream", type=str, required=True, help="Upstream components (comma-separated; no commas inside an item)")
    parser.add_argument("--midstream", type=str, required=True, help="Midstream components (comma-separated; no commas inside an item)")
    parser.add_argument("--downstream", type=str, required=True, help="Downstream components (comma-separated; no commas inside an item)")
    parser.add_argument("--tickers", type=str, required=True, help="Comma-separated list of tickers (1 target + 2 peers + 1 bottleneck)")
    parser.add_argument("--cyclical", type=str, default="", help="Comma-separated tickers to treat as cyclical (memory, chemicals, steel, shipping ...)")
    parser.add_argument("--not-cyclical", type=str, default="", help="Comma-separated tickers to exclude from automatic cyclical detection")
    parser.add_argument("--benchmarks", type=str, default="", help="Comma-separated index tickers for the market comparison table (default: auto)")
    parser.add_argument("--weights", type=str, default="0.2,0.5,0.3", help="Scenario probabilities Bull,Base,Bear (must sum to 1)")
    parser.add_argument("--output", type=str, default="", help="Optional output markdown file path")

    args = parser.parse_args()
    py_exec = sys.executable or "python3"

    # Helper scripts live next to this skill, wherever the skills folder is installed (.agents, .claude, ...)
    skills_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    mermaid_script = os.path.join(skills_dir, "value-chain-analyzer", "scripts", "generate_mermaid.py")
    financial_script = os.path.join(skills_dir, "financial-analyst", "scripts", "get_financial_stats.py")
    for path in (mermaid_script, financial_script):
        if not os.path.isfile(path):
            sys.exit(f"❌ 보조 스크립트를 찾을 수 없습니다: {path}")

    # 1. Determine Output Filename & Snapshot Filename first
    now_kst = datetime.datetime.now(KST)
    safe_industry_name = args.industry.replace(' ', '_').replace('/', '_')
    today_str = now_kst.strftime("%Y%m%d")

    if args.output:
        output_filename = args.output
    else:
        reports_dir = os.path.join(find_reports_root(), "reports")
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

    base_no_ext, _ = os.path.splitext(output_filename)
    snapshot_filename = f"{base_no_ext}_data.json"
    snapshot_basename = os.path.basename(snapshot_filename)

    print(f"⏳ Generating Value Chain Diagram for {args.industry}...")
    mermaid_output = run_script(
        [py_exec, mermaid_script, "--industry", args.industry, "--upstream", args.upstream,
         "--midstream", args.midstream, "--downstream", args.downstream, "--lang", "ko"],
        "가치사슬 다이어그램 생성")

    print(f"⏳ Fetching Financial Data for tickers: {args.tickers}...")
    financial_cmd = [py_exec, financial_script, "--tickers", args.tickers, "--weights", args.weights, "--snapshot", snapshot_filename]
    for flag, value in (("--cyclical", args.cyclical), ("--not-cyclical", args.not_cyclical), ("--benchmarks", args.benchmarks)):
        if value:
            financial_cmd += [flag, value]
    financial_output = run_script(financial_cmd, "재무 데이터 수집")

    cleaned_financial = financial_output
    if cleaned_financial.startswith(FINANCIAL_HEADER):
        cleaned_financial = cleaned_financial[len(FINANCIAL_HEADER):].strip()

    # Keep Section 4 as written in the snapshot, so check_report_numbers.py can detect later edits (spec 002).
    baseline_note = ""
    if os.path.isfile(snapshot_filename):
        sys.path.insert(0, os.path.dirname(financial_script))
        try:
            from snapshot import attach_section4
            attach_section4(snapshot_filename, cleaned_financial)
        except Exception as e:
            baseline_note = f" (Section 4 기준본 저장 실패: {e})"
    else:
        baseline_note = " (스냅샷 파일이 없어 Section 4 기준본을 저장하지 못함)"

    # Parse tickers and build dynamic company analysis blocks
    tickers_list = [t.strip() for t in args.tickers.split(',') if t.strip()]
    company_blocks = []
    for idx, ticker in enumerate(tickers_list, 1):
        block = f"""### {idx}) {ticker}
- **스크립트 판정**: [AI_TODO: Section 4 › 5번 매트릭스의 '종합 판단'을 그대로 옮겨 적기]
- **판정 근거 해석**: [AI_TODO: 판정을 만든 🟢/🔴 신호를 설명. 순환업종이면 P/B 밴드·사이클 위치·추정치 방향 기준으로 설명하고, 낮은 PER을 저평가 근거로 쓰지 않음]
- **핵심 투자 포인트 & 촉매제 (Catalysts)**: [AI_TODO: 90일 이내 출처(제목·날짜·URL)로 확인된 것만. 오래된 정보는 날짜와 '과거 정보' 표시]
- **개별 리스크 요인**: [AI_TODO: 단일 고객사 의존도, 가격 경쟁, 환율 및 규제 리스크 등]"""
        company_blocks.append(block)

    company_analysis_section = "\n\n".join(company_blocks) if company_blocks else "[AI_TODO: 분석 대상 기업 정보를 입력하세요.]"

    # 3. Assemble the Master Template
    formatted_time = now_kst.strftime("%Y-%m-%d %H:%M KST")
    peer_rows = "\n".join("| [AI_TODO] | [AI_TODO] | [AI_TODO] | [AI_TODO] |" for _ in range(max(len(tickers_list), 1)))

    template = f"""# {args.industry} 투자 전략 보고서

> **분석 기준 시각**: {formatted_time} (시세 상태는 Section 4 첫 줄 '데이터 기준' 참고 — 장중 실행이면 시세·수급은 잠정치)
> **데이터 스냅샷**: `{snapshot_basename}`{baseline_note}
> **한 줄 결론**: [AI_TODO: 🟢 매수 / 🟡 중립·관망 / 🔴 비중 축소·회피 중 하나. Section 4 › 5번 매트릭스 판정과 Section 6.1 시나리오 결과(하방 포함)를 그대로 반영하고, 핵심 논쟁(예: 피크아웃)을 한 줄로 요약. 판정과 다른 결론을 쓰려면 Section 6.2에 근거를 밝힐 것]

---

## 1. 산업 개요 및 최근 시장 동향

### 1.1. 중장기 산업 규모 및 구조적 성장 동인
[AI_TODO: {args.industry} 산업의 시장 규모, 연평균 성장률(CAGR), 중장기 전망을 출처(제목·발행일·URL)와 함께 요약. 전망치 발표 시점이 오래됐으면 날짜를 밝힐 것]

### 1.2. 최근 시장 변동성 및 핵심 현안 진단
[AI_TODO: 최근 1~5일 주가 급변동, 52주 고점 대비 낙폭, 직접적 트리거를 정리하고, Section 4 › 1-3 시장 비교 표를 근거로 원인이 '기업 고유 / 업종 전반 / 시장 전체' 중 무엇인지 판별하세요. 근거가 부족하면 '판단 보류'라고 씁니다. 수급 금액은 '추정', 장중 데이터는 '잠정'으로 표기하고 '확정·증명' 표현은 쓰지 않습니다.]

### 1.3. 검증 체크리스트 (필수 — 모든 항목에 출처 제목·발행일·URL)

| 확인 항목 | 확인 결과 | 출처 (발행일) |
|---|---|---|
| 타겟·경쟁사의 최근 실적 및 잠정실적 | [AI_TODO: 최신 분기 매출·영업이익(잠정 포함). Section 4 › 7번 시나리오의 EPS 범위와 어긋나면 그 점을 적기] | [AI_TODO] |
| 다음 실적 발표일 | [AI_TODO: Section 4 › 3-1 표 + 잠정실적 공시 일정] | [AI_TODO] |
| 최근 30일 이익 추정치 방향 | [AI_TODO: Section 4 › 3-1 표 해석] | 스크립트 산출 |
| 지수·해외 피어 동반 등락 여부 | [AI_TODO: Section 4 › 1-3 표 해석] | 스크립트 산출 |
| 하락·상승 트리거의 사실관계 | [AI_TODO: 발표 원문 확인, 공개된 사양·수율·고객사 여부] | [AI_TODO] |
| 핵심 촉매의 현재 상태 | [AI_TODO: 90일 이내 출처로만 확인] | [AI_TODO] |

---

## 2. 가치사슬 구조도

{mermaid_output}

---

## 3. 핵심 병목(Bottleneck) 및 해자(Moat) 분석

산업의 핵심 병목 현상과 강력한 해자(Moat)를 지닌 기업들을 분석합니다. 타겟과 경쟁 관계인 사업부가 있는 병목 기업은 역할을 함께 표기합니다(예: `[병목협력·경쟁]`).

| 기업명 | 티커 | 가치사슬 위치 | 핵심 역할 및 경제적 해자(Moat) |
|---|---|---|---|
{peer_rows}

---

## 4. 정량 재무 지표 및 투자 시그널 매트릭스 (스크립트 자동 산출 — 수치 수정 금지)

{cleaned_financial}

---

## 5. 기업별 심층 분석 및 밸류에이션 판단

[AI_TODO: Section 4의 판정(5번 매트릭스)을 기업별로 해석하세요. 판정을 바꾸지 말고, 왜 그런 신호가 나왔는지와 신호가 놓칠 수 있는 점을 설명합니다.]

{company_analysis_section}

---

## 6. 핵심 리스크 평가 (필수)

| 리스크 요인 | 영향도 (H/M/L) | 상세 설명 및 모니터링 포인트 |
|---|---|---|
| [AI_TODO: 리스크 1] | High/Medium | [AI_TODO: 설명] |
| [AI_TODO: 리스크 2] | High/Medium | [AI_TODO: 설명] |
| [AI_TODO: 리스크 3] | High/Medium/Low | [AI_TODO: 설명] |

### 6.1. 시나리오 스트레스 테스트 해석

> 💡 수치는 Section 4 › 7번 표(스크립트 산출)를 그대로 인용합니다. 영업이익·EPS·배수를 직접 만들어 넣지 않습니다.

[AI_TODO: (1) 배수 A(현재 배수 유지)와 배수 B(목표가 내재 배수)의 결과 차이가 무엇을 뜻하는지, (2) Bear 하방이 음수이면 그 크기를 그대로 적고, (3) 순환업종은 Section 4 › 2-2의 '밴드 최저 P/B 회귀 시 주가'도 함께 적으세요. 핵심 드라이버(예: D램 가격)와 이익의 연결은 출처가 있는 민감도 수치만 인용합니다. 결론에 맞추려고 가정을 바꾸지 않습니다.]

### 6.2. 반대 논리 (Bear Thesis) 및 판단 무효화 조건 (필수)

| 이 판단이 틀릴 수 있는 이유 | 근거 (출처·발행일) | 이 논리가 맞다면 영향 |
|---|---|---|
| [AI_TODO: 반대 논리 1] | [AI_TODO] | [AI_TODO] |
| [AI_TODO: 반대 논리 2] | [AI_TODO] | [AI_TODO] |
| [AI_TODO: 반대 논리 3] | [AI_TODO] | [AI_TODO] |

- **판단 무효화 조건**: [AI_TODO: 어떤 데이터(실적·추정치 방향·가격·이벤트)가 나오면 결론을 바꿀지 구체적으로]
- **스크립트 판정과 다른 결론을 쓴 경우의 근거**: [AI_TODO: 해당 없으면 '해당 없음']

---

## 7. 투자 전략 및 포트폴리오 배분 제안

### 🎯 7.1. 판정별 실행 전략
[AI_TODO: 종합 판정에 따라 작성하세요.
- 🟢 매수: 분할 매수 계획(가격대·비중·조건)과 손절·재평가 기준
- 🟡 중립·관망: 진입을 검토할 조건(예: 추정치 방향 전환, 밴드 하단 접근)과 그때까지의 대응
- 🔴 비중 축소·회피: 축소·회피 근거와 재진입을 검토할 조건
기술적 지표(Section 4 › 1-2)는 진입 시점을 고르는 보조 수단으로만 쓰고, 과매도 자체를 매수 근거로 쓰지 않습니다.]

### 💰 7.2. 포트폴리오 배분 제안
[AI_TODO: 판정과 연동해 비중을 제시하세요(🔴 판정 기업은 0% 또는 축소). 현금 비중을 포함할 수 있고, 단일 업종 집중 위험과 베타를 함께 밝힙니다.]

---

## 8. 참고 문헌 (References)

[AI_TODO: 본문에서 인용한 출처를 [번호] 제목 — 발행일 — URL 형식으로 적으세요. 사이트 홈페이지만 가리키는 링크는 쓰지 않습니다. 숫자 점검(SKILL.md Phase 3 5~7단계)에서 남은 문제가 있으면 '## 9. 숫자 점검 결과' 섹션을 이 목록 뒤에 넣습니다.]

---

*본 보고서는 공개 데이터와 컨센서스를 바탕으로 자동·반자동 생성된 참고 자료이며 투자 권유가 아닙니다. 수치는 데이터 제공처의 지연·오류를 포함할 수 있고, 투자 판단과 그 결과의 책임은 투자자 본인에게 있습니다.*
"""

    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(template)

    print(f"✅ 보고서 템플릿이 성공적으로 생성되었습니다: {output_filename}")
    print("🤖 AI 에이전트는 이제 [AI_TODO] 영역을 채워주세요. Section 4의 수치와 판정은 수정하지 않습니다.")


if __name__ == "__main__":
    main()
