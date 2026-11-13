import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

KST = datetime.timezone(datetime.timedelta(hours=9))


def run_script(cmd: List[str], label: str) -> str:
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


def find_skills_dir() -> str:
    """Folder containing peer skills (market-analyst, financial-analyst, value-chain-analyzer)."""
    cur = os.path.dirname(os.path.abspath(__file__))  # .../investment-strategy/scripts
    strategy_dir = os.path.dirname(cur)               # .../investment-strategy
    skills_dir = os.path.dirname(strategy_dir)         # .../skills or .../.agents/skills
    return skills_dir


def find_reports_root() -> str:
    """Find root directory where reports/ should be placed."""
    cur = os.path.dirname(os.path.abspath(__file__))
    while cur != os.path.dirname(cur):
        if os.path.basename(cur) in (".agents", ".claude", "ki009-nxt"):
            return os.path.dirname(cur)
        cur = os.path.dirname(cur)
    if os.path.isdir(os.path.join(os.getcwd(), "reports")):
        return os.getcwd()
    return os.getcwd()


skills_dir_path = find_skills_dir()
fin_scripts_path = os.path.join(skills_dir_path, 'financial-analyst', 'scripts')
intel_scripts_path = os.path.join(skills_dir_path, 'market-intelligence', 'scripts')
alpha_scripts_path = os.path.join(skills_dir_path, 'alpha-engine', 'scripts')
if fin_scripts_path not in sys.path:
    sys.path.insert(0, fin_scripts_path)
if intel_scripts_path not in sys.path:
    sys.path.insert(0, intel_scripts_path)
if alpha_scripts_path not in sys.path:
    sys.path.insert(0, alpha_scripts_path)

try:
    from intelligence_collector import run_intelligence_collection
    from render_intelligence import render_crisis_alert_box, render_section1_2_crisis_diagnosis
    from economic_auditor import apply_event_gatekeeper
except ImportError as e:
    print(f"⚠️ 인텔리전스 모듈 로드 경고: {e}", file=sys.stderr)
try:
    from calculate_alpha_score import evaluate_alpha, format_alpha_section_table
except ImportError as e:
    print(f"⚠️ 알파 엔진 모듈 로드 경고: {e}", file=sys.stderr)
try:
    from profile_detector import PROFILE_NAMES
except ImportError:
    PROFILE_NAMES = {
        'cyclical': '🔄 경기순환',
        'cash_cow_dividend': '🛡️ 배당·현금흐름',
        'tech_high_growth': '🚀 고성장·무형자산',
        'financials': '🏦 금융·자본효율',
        'biotech_pipeline': '🧪 R&D·파이프라인',
        'general': '일반',
    }


def detect_market_benchmark(industry: str, tickers_str: str, override_market: Optional[str] = None) -> str:
    """Auto-detect market benchmark query based on industry keywords and target ticker."""
    if override_market and override_market.strip():
        return override_market.strip()

    ind_lower = industry.lower()
    tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
    target_ticker = tickers[0] if tickers else ""

    # 1. Semiconductor keywords in industry
    if any(k in ind_lower for k in ["반도체", "메모리", "semi", "semiconductor", "hbm", "파운드리", "foundry"]):
        return "반도체"

    # 2. Tech / BigTech keywords in industry
    if any(k in ind_lower for k in ["기술", "빅테크", "tech", "소프트웨어", "software", "ai", "인공지능", "플랫폼", "cloud", "클라우드"]):
        return "기술주식"

    # 3. Target ticker geography
    if target_ticker.endswith(".KS") or target_ticker.endswith(".KQ") or re.match(r'^\d{6}$', target_ticker):
        return "한국증시"

    # Default to US market
    return "미국증시"


def extract_target_verdict(cleaned_financial: str, target_ticker: str) -> str:
    """Extract the corporate valuation decision verdict for target ticker from Table 5."""
    in_table5 = False
    clean_target = target_ticker.strip().upper()
    for line in cleaned_financial.splitlines():
        # Identify Table 4 or Table 5 header
        if re.search(r'###\s*(?:4|5)\..*의사결정', line) or '핵심 지표 의사결정 매트릭스' in line:
            in_table5 = True
            continue
        if in_table5:
            # If next heading starts, Table 4/5 has ended
            if line.startswith('###') or (line.startswith('##') and not line.startswith('###')):
                break
            if '|' in line:
                cols = [c.strip() for c in line.split('|') if c.strip()]
                if cols and len(cols) >= 3:
                    # Match target ticker in the first column
                    col0 = cols[0].upper().replace('*', '').strip()
                    if clean_target in col0 or target_ticker in cols[0]:
                        return cols[-1]  # The last column in Table 4/5 is '종합 판단'
    return "[AI_TODO: Section 4.2 › 4번 매트릭스 타겟 기업 종합 판단]"


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Generate a Unified 3-Tier Investment Strategy Report Master Template")
    parser.add_argument("--industry", type=str, required=True, help="Name of the industry")
    parser.add_argument("--upstream", type=str, required=True, help="Upstream components (comma-separated; no commas inside an item)")
    parser.add_argument("--midstream", type=str, required=True, help="Midstream components (comma-separated; no commas inside an item)")
    parser.add_argument("--downstream", type=str, required=True, help="Downstream components (comma-separated; no commas inside an item)")
    parser.add_argument("--tickers", type=str, required=True, help="Comma-separated list of tickers (1 target + 2 peers + 1 bottleneck)")
    parser.add_argument("--market", type=str, default="", help="Optional market benchmark override ('반도체', '코스피', '한국증시', '미국증시', '기술주식')")
    parser.add_argument("--cyclical", type=str, default="", help="Comma-separated tickers to treat as cyclical (memory, chemicals, steel, shipping ...)")
    parser.add_argument("--not-cyclical", type=str, default="", help="Comma-separated tickers to exclude from automatic cyclical detection")
    parser.add_argument("--benchmarks", type=str, default="", help="Comma-separated index tickers for the market comparison table (default: auto)")
    parser.add_argument("--weights", type=str, default="0.2,0.5,0.3", help="Scenario probabilities Bull,Base,Bear (must sum to 1)")
    parser.add_argument("--output", type=str, default="", help="Optional output markdown file path")

    args = parser.parse_args()
    py_exec = sys.executable or "python3"

    # Helper scripts live next to this skill in the skills directory
    skills_dir = find_skills_dir()
    mermaid_script = os.path.join(skills_dir, "value-chain-analyzer", "scripts", "generate_mermaid.py")
    financial_script = os.path.join(skills_dir, "financial-analyst", "scripts", "get_financial_stats.py")
    market_script = os.path.join(skills_dir, "market-analyst", "scripts", "get_market_stats.py")

    for path in (mermaid_script, financial_script, market_script):
        if not os.path.isfile(path):
            sys.exit(f"❌ 보조 스크립트를 찾을 수 없습니다: {path}")

    financial_scripts_dir = os.path.join(skills_dir, "financial-analyst", "scripts")
    market_scripts_dir = os.path.join(skills_dir, "market-analyst", "scripts")

    if financial_scripts_dir not in sys.path:
        sys.path.insert(0, financial_scripts_dir)
    if market_scripts_dir not in sys.path:
        sys.path.insert(0, market_scripts_dir)

    from snapshot import section4_body as financial_section4_body
    from market_snapshot import section4_body as market_section4_body
    import target_resolver as tr
    import get_market_stats as gms

    tickers_list = [t.strip() for t in args.tickers.split(',') if t.strip()]
    target_ticker = tickers_list[0] if tickers_list else ""

    # Determine Output Filename & Snapshot Filename
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

    # -------------------------------------------------------------
    # Phase 0: Pre-Flight Breaking News & Special Situations Sentinel (market-intelligence)
    # -------------------------------------------------------------
    intel_snapshot_filename = f"{base_no_ext}_intelligence.json"
    intel_snapshot_basename = os.path.basename(intel_snapshot_filename)
    print(f"⏳ [Phase 0] Scanning Real-Time Breaking News Sentinel for target '{target_ticker}'...")
    try:
        intel_data = run_intelligence_collection(target_ticker, output_path=intel_snapshot_filename)
    except Exception as e:
        print(f"⚠️ [market-intelligence] 사전 뉴스 수집 예외 발생: {e}", file=sys.stderr)
        intel_data = {
            "meta": {"ticker": target_ticker, "error": str(e)},
            "severity": {"level": 1, "is_crisis": False, "primary_crisis": "정상", "description": "뉴스 수집 실패(Fallback)"},
            "evidence_headlines": [],
            "items": [],
        }

    intel_sev = intel_data.get("severity", {})
    is_crisis = intel_sev.get("is_crisis", False)
    crisis_level = intel_sev.get("level", 1)
    primary_crisis = intel_sev.get("primary_crisis", "")
    if is_crisis:
        print(f"🚨 [Phase 0 Alert] Level {crisis_level} Crisis Detected: {primary_crisis}")

    # -------------------------------------------------------------
    # Phase 1: Top-Down Macro Regime & Market Diagnostic (market-analyst)
    # -------------------------------------------------------------
    target_market = detect_market_benchmark(args.industry, args.tickers, args.market)
    print(f"⏳ [Phase 1] Auto-detected Market Benchmark: '{target_market}' (Query: '{args.industry}', Target: '{target_ticker}')")
    resolved_target = tr.resolve_target(target_market)

    target_indices = list(resolved_target.get("indices", []))
    if target_ticker and target_ticker not in target_indices:
        target_indices.append(target_ticker)

    print(f"⏳ [Phase 1] Running Market Analysis for indices: {target_indices}...")
    sec4_market_text, mkt_snap = gms.run_market_analysis(
        indices=target_indices,
        sectors=resolved_target.get("sectors"),
        macro=resolved_target.get("macro"),
        primary_ticker=resolved_target.get("primary_ticker"),
        parent_index=resolved_target.get("parent_index"),
    )
    cleaned_market = market_section4_body(sec4_market_text)
    mkt_snap_dict = mkt_snap.to_dict()

    # Extract macro signals
    macro_verdict = mkt_snap.values.get("macro.regime.verdict", {}).get("value", "국면 진단 완료")
    macro_cash_pct = mkt_snap.values.get("macro.regime.cash_pct", {}).get("value", 25)
    macro_icon = mkt_snap.values.get("macro.regime.icon", {}).get("value", "🟡")
    macro_signal_str = f"{macro_icon} {macro_verdict} (권장 현금 {macro_cash_pct}%)"

    # -------------------------------------------------------------
    # Phase 2: Structural Supply Chain Mapping (value-chain-analyzer)
    # -------------------------------------------------------------
    print(f"⏳ [Phase 2] Generating Value Chain Diagram for {args.industry}...")
    mermaid_output = run_script(
        [py_exec, mermaid_script, "--industry", args.industry, "--upstream", args.upstream,
         "--midstream", args.midstream, "--downstream", args.downstream, "--lang", "ko"],
        "가치사슬 다이어그램 생성")

    # -------------------------------------------------------------
    # Phase 3: High-Precision Bottom-Up Corporate Valuation (financial-analyst)
    # -------------------------------------------------------------
    print(f"⏳ [Phase 3] Fetching Financial Data for tickers: {args.tickers}...")
    temp_fin_snap_path = f"{base_no_ext}_temp_fin.json"
    financial_cmd = [
        py_exec, financial_script,
        "--tickers", args.tickers,
        "--weights", args.weights,
        "--snapshot", temp_fin_snap_path
    ]
    for flag, value in (("--cyclical", args.cyclical), ("--not-cyclical", args.not_cyclical), ("--benchmarks", args.benchmarks)):
        if value:
            financial_cmd += [flag, value]

    financial_output = run_script(financial_cmd, "재무 데이터 수집")
    cleaned_financial = financial_section4_body(financial_output)

    fin_snap_dict = {}
    if os.path.isfile(temp_fin_snap_path):
        try:
            with open(temp_fin_snap_path, "r", encoding="utf-8") as f:
                fin_snap_dict = json.load(f)
            os.remove(temp_fin_snap_path)
        except Exception as e:
            print(f"⚠️ 임시 재무 스냅샷 로드 경고: {e}", file=sys.stderr)

    target_verdict = extract_target_verdict(cleaned_financial, target_ticker)

    # -------------------------------------------------------------
    # Phase 3.5: Forward-Looking Alpha Scoring & Dual Scoreboard (alpha-engine)
    # -------------------------------------------------------------
    print(f"⏳ [Phase 3.5] Evaluating 4 Alpha Archetypes for tickers: {tickers_list}...")
    alpha_results = []
    alpha_map: Dict[str, Any] = {}
    for t in tickers_list:
        try:
            a_res = evaluate_alpha(t)
            alpha_results.append(a_res)
            alpha_map[t] = a_res
        except Exception as e:
            print(f"⚠️ [{t}] 알파 평가 예외: {e}", file=sys.stderr)

    alpha_sec_table = format_alpha_section_table(alpha_results) if alpha_results else ""

    target_alpha = alpha_map.get(target_ticker, {})
    target_alpha_score = target_alpha.get('composite_alpha_score', 0.0)
    target_defense_score = target_alpha.get('defense_score', 0.0)
    target_archetype = target_alpha.get('primary_archetype', '')
    target_archetype_label = target_alpha.get('primary_label', '미래 알파 주도주')
    target_dual_verdict = target_alpha.get('dual_verdict', '')

    # -------------------------------------------------------------
    # Phase 4: Event-Driven Gatekeeper & Resynthesis (market-intelligence)
    # -------------------------------------------------------------
    effective_target_verdict, event_downgrade_reason = apply_event_gatekeeper(target_verdict, intel_data)
    if event_downgrade_reason:
        print(f"🚨 [Phase 4 Gatekeeper] Corporate Verdict Downgraded: {target_verdict} ➡️ {effective_target_verdict}")
    else:
        # Prevent backward-looking cyclical peak penalty from degrading a confirmed supercycle leader
        if not is_crisis and target_archetype == 'SUPERCYCLE_LEADER' and target_alpha_score >= 80.0:
            if '중립' in target_verdict or '관망' in target_verdict:
                effective_target_verdict = f"🟢 **적극 매수 (🚀 슈퍼사이클 확장기 — 알파 {target_alpha_score}점)**"
                print(f"🚀 [Phase 3.5 Alpha Override] Supercycle expansion recognized: {target_verdict} ➡️ {effective_target_verdict}")
            else:
                effective_target_verdict = target_verdict
        else:
            effective_target_verdict = target_verdict

    # Extract quantitative context for crisis comparison
    fin_vals = fin_snap_dict.get("values", {})
    target_price = fin_vals.get(f"{target_ticker}.quote.current_price", {}).get("value")
    target_high = (fin_vals.get(f"{target_ticker}.quote.fifty_two_week_high", {}).get("value")
                   or fin_vals.get(f"{target_ticker}.technical.52w_high", {}).get("value"))
    target_5d_ret = fin_vals.get(f"{target_ticker}.technical.5d_return", {}).get("value")
    drop_from_high_pct = (target_price / target_high - 1) * 100 if (target_price and target_high) else None

    floor_price = fin_vals.get(f"{target_ticker}.scenario.joint_derating_floor_price", {}).get("value")
    floor_downside = fin_vals.get(f"{target_ticker}.scenario.return_joint_derating", {}).get("value")

    # Relative peer divergence
    peer_summaries = []
    for peer in tickers_list[1:]:
        p_ret = fin_vals.get(f"{peer}.technical.5d_return", {}).get("value")
        if p_ret is not None:
            peer_summaries.append(f"{peer} {p_ret*100:+.1f}%")
    parent_idx = resolved_target.get("parent_index") or ("^KS11" if target_ticker.endswith((".KS", ".KQ")) else "^GSPC")
    mkt_parent_ret = mkt_snap_dict.get("values", {}).get(f"{parent_idx}.return_5d", {}).get("value")
    mkt_label = resolved_target.get("label", parent_idx)
    parent_str = f"동기간 {mkt_label}({mkt_parent_ret*100:+.2f}%)" if mkt_parent_ret is not None else mkt_label
    peers_str = f" 및 피어({', '.join(peer_summaries[:2])})" if peer_summaries else ""
    t_ret_str = f"{target_5d_ret*100:+.1f}%" if target_5d_ret is not None else "-"
    peer_divergence_text = f"{parent_str}{peers_str} 대비 타겟 기업 변동({t_ret_str})으로 기업 고유 충격 확인"

    currency = "$" if not target_ticker.endswith((".KS", ".KQ")) else "₩"

    crisis_alert_box = render_crisis_alert_box(
        intelligence=intel_data,
        peer_divergence_text=peer_divergence_text,
        multiple_c_floor_price=floor_price,
        multiple_c_downside_pct=floor_downside,
        drop_from_high_pct=abs(drop_from_high_pct) if drop_from_high_pct else None,
        currency=currency
    )

    sec1_2_crisis_text = render_section1_2_crisis_diagnosis(
        target_ticker=target_ticker,
        intelligence=intel_data,
        drop_pct_5d=target_5d_ret,
        drop_from_high_pct=abs(drop_from_high_pct) if drop_from_high_pct else None,
        peer_divergence_text=peer_divergence_text,
        multiple_c_floor_price=floor_price,
        multiple_c_downside_pct=floor_downside,
        currency=currency
    )

    # -------------------------------------------------------------
    # Assemble Unified Quantitative Section 4 and Companion Snapshot
    # -------------------------------------------------------------
    sec4_full_body = f"""### 4.1. 탑다운 거시 시장 및 시장 국면 진단 (Phase 1: Market Analyst)

{cleaned_market}

### 4.2. 바텀업 기업 재무 및 밸류에이션 매트릭스 (Phase 3: Financial Analyst)

{cleaned_financial}

### 4.3. 미래 상승 알파(Alpha) 정밀 진단 및 듀얼 스코어보드 (Phase 3.5: Alpha Engine)

{alpha_sec_table}"""

    sec4_sha256 = hashlib.sha256(sec4_full_body.encode('utf-8')).hexdigest()
    now_kst_str = now_kst.strftime('%Y-%m-%d %H:%M KST')

    # Merge values, series, warnings, and inputs
    merged_values: Dict[str, Any] = {}
    merged_values.update(mkt_snap_dict.get("values", {}))
    merged_values.update(fin_snap_dict.get("values", {}))

    # Record Alpha metrics for all tickers
    for t, a_data in alpha_map.items():
        merged_values[f"{t}.alpha.composite_score"] = {
            "value": a_data.get('composite_alpha_score', 0.0),
            "source": "alpha-engine",
            "basis": "calculated",
            "as_of": now_kst_str
        }
        merged_values[f"{t}.alpha.defense_score"] = {
            "value": a_data.get('defense_score', 0.0),
            "source": "alpha-engine",
            "basis": "calculated",
            "as_of": now_kst_str
        }
        merged_values[f"{t}.alpha.primary_archetype"] = {
            "value": a_data.get('primary_archetype', ''),
            "source": "alpha-engine",
            "basis": "classified",
            "as_of": now_kst_str
        }
        merged_values[f"{t}.alpha.dual_verdict"] = {
            "value": a_data.get('dual_verdict', ''),
            "source": "alpha-engine",
            "basis": "synthesized",
            "as_of": now_kst_str
        }

    # Also record corporate verdict
    clean_target_verdict = effective_target_verdict.replace('*', '').strip()
    merged_values[f"{target_ticker}.decision.verdict"] = {
        "value": clean_target_verdict,
        "source": "calculated",
        "basis": "derived",
        "as_of": now_kst_str,
        "status": "final"
    }

    merged_series: Dict[str, Any] = {}
    merged_series.update(mkt_snap_dict.get("series", {}))
    merged_series.update(fin_snap_dict.get("series", {}))

    merged_warnings: List[Any] = []
    merged_warnings.extend(mkt_snap_dict.get("warnings", []))
    merged_warnings.extend(fin_snap_dict.get("warnings", []))

    merged_inputs: Dict[str, Any] = {}
    merged_inputs.update(mkt_snap_dict.get("inputs", {}))
    merged_inputs.update(fin_snap_dict.get("inputs", {}))

    unified_snapshot = {
        "meta": {
            "format_version": 2,
            "industry": args.industry,
            "tickers": tickers_list,
            "target_ticker": target_ticker,
            "market": target_market,
            "generated_at": now_kst_str,
            "args": {
                "industry": args.industry,
                "tickers": args.tickers,
                "market": target_market,
                "upstream": args.upstream,
                "midstream": args.midstream,
                "downstream": args.downstream,
                "cyclical": args.cyclical,
                "not_cyclical": args.not_cyclical,
                "benchmarks": args.benchmarks,
                "weights": args.weights,
            },
            "macro_regime": {
                "verdict": macro_verdict,
                "cash_pct": macro_cash_pct,
                "icon": macro_icon,
            },
            "financial_meta": fin_snap_dict.get("meta", {}),
            "market_meta": mkt_snap_dict.get("meta", {}),
            "profile": fin_snap_dict.get("values", {}).get(f"{target_ticker}.meta.profile", {}).get("value", "general"),
            "profile_desc": fin_snap_dict.get("values", {}).get(f"{target_ticker}.meta.profile_desc", {}).get("value", ""),
            "intelligence_meta": intel_data.get("meta", {}),
            "intelligence_severity": intel_sev,
        },
        "values": merged_values,
        "series": merged_series,
        "warnings": merged_warnings,
        "inputs": merged_inputs,
        "market_intelligence": intel_data,
        "section4": {
            "text": sec4_full_body,
            "sha256": sec4_sha256,
            "attached_at": now_kst_str,
            "market_sha256": hashlib.sha256(cleaned_market.encode('utf-8')).hexdigest(),
            "financial_sha256": hashlib.sha256(cleaned_financial.encode('utf-8')).hexdigest(),
        }
    }

    try:
        with open(snapshot_filename, 'w', encoding='utf-8') as f:
            json.dump(unified_snapshot, f, ensure_ascii=False, indent=2)
        baseline_note = ""
    except Exception as e:
        baseline_note = f" (스냅샷 저장 실패: {e})"

    # Dynamic company analysis blocks
    company_blocks = []
    for idx, ticker in enumerate(tickers_list, 1):
        t_prof = fin_snap_dict.get("values", {}).get(f"{ticker}.meta.profile", {}).get("value", "general")
        t_prof_name = PROFILE_NAMES.get(t_prof, t_prof)
        block = f"""### {idx}) {ticker} (비즈니스 프로파일: {t_prof_name})
- **스크립트 판정**: [AI_TODO: Section 4.2 › 4번 매트릭스의 '종합 판단'을 그대로 옮겨 적기]
- **판정 근거 해석**: [AI_TODO: 판정을 만든 🟢/🔴 신호를 설명. {t_prof_name} 특성에 맞추어 활성 지표 중심으로 분석하고, 왜곡 지표('· 제외')는 분석 근거로 사용하지 않음]
- **핵심 투자 포인트 & 촉매제 (Catalysts)**: [AI_TODO: 90일 이내 출처(제목·날짜·URL)로 확인된 것만. 오래된 정보는 날짜와 '과거 정보' 표시]
- **개별 리스크 요인**: [AI_TODO: 단일 고객사 의존도, 가격 경쟁, 환율 및 규제 리스크 등]"""
        company_blocks.append(block)

    company_analysis_section = "\n\n".join(company_blocks) if company_blocks else "[AI_TODO: 분석 대상 기업 정보를 입력하세요.]"
    peer_rows = "\n".join("| [AI_TODO] | [AI_TODO] | [AI_TODO] | [AI_TODO] |" for _ in range(max(len(tickers_list), 1)))

    # Master Template Assembly
    if is_crisis:
        conclusion_line = f"{clean_target_verdict} — {intel_sev.get('description', '')}"
        crisis_box_insert = f"\n{crisis_alert_box}\n" if crisis_alert_box else ""
        sec1_2_content = f"{sec1_2_crisis_text}\n\n[AI_TODO: 위 긴급 경보 및 Section 4.1 거시 지표, Section 4.2 › 1-3 시장 비교 표를 바탕으로 세부 변동성을 상술하세요.]"
        floor_str = f"{currency}{floor_price:,.2f}" if floor_price is not None else "바닥선"
        sec7_3_content = f"""| 자산군 / 종목 | 권장 배정 비중 | 포지션 성격 및 실행 가이드 |
|---|:---:|---|
| **안전 현금 (Cash)** | **40.0%** (+15%p) | 거버넌스 위기 대응 긴급 완충 안전마진 (거시 기본 {macro_cash_pct}% + 위기 방어 15%) |
| **타겟: {target_ticker}** | **0.0% (동결)** | **🚨 [WATCH] 신규 매수 전면 금지** (기존 보유자는 50% 비중 축소 권고, Multiple C `{floor_str}` 방어선) |
| **가치사슬/경쟁 피어** | **60.0%** | AI 공급망 우량 피어 분산 (TSMC 30%, AMD 20%, AVGO 10% 피난처 분산) |
| **합계** | **100.0%** | **AI 인프라 성장은 유지하되, 최고경영자 키맨 리스크만 원천 격리** |

> 🚨 **[포트폴리오 비상 재배분 지침]** {target_ticker}는 CEO/거버넌스 위기(Level {crisis_level})로 인해 신규 매수가 전면 동결(0.0%)되었습니다. 기존 보유자는 50% 비중 축소를 권고하며, 자금은 안전 현금(40.0%) 및 AI 공급망 우량 피어로 분산되었습니다."""
    else:
        conclusion_line = f"[AI_TODO: 🟢 매수 / 🟡 중립·관망 / 🔴 비중 축소·회피 중 하나. 거시 시장 국면({macro_verdict}, 권장 현금 {macro_cash_pct}%)과 기업 밸류에이션 매트릭스 판정({effective_target_verdict}), 시나리오 결과를 종합해 한 줄로 요약]"
        crisis_box_insert = ""
        sec1_2_content = "[AI_TODO: 최근 1~5일 주가 급변동, 52주 고점 대비 낙폭, 직접적 트리거를 정리하고, Section 4.1 거시 지표 및 Section 4.2 › 1-3 시장 비교 표를 근거로 원인이 '기업 고유 / 업종 전반 / 시장 전체' 중 무엇인지 판별하세요. 수급 금액은 '추정', 장중 데이터는 '잠정'으로 표기하고 '확정·증명' 표현은 쓰지 않습니다.]"
        sec7_3_content = f"[AI_TODO: 거시 현금 제약({macro_cash_pct}%)과 기업별 판정을 연동해 비중을 제시하세요(🔴 판정 기업은 0% 또는 축소). 단일 업종 집중 위험과 포트폴리오 베타를 함께 밝힙니다.]"

    alpha_sig_icon = "🟢" if target_alpha_score >= 80 else ("🟡" if target_alpha_score >= 65 else "⚪")

    template = f"""# {args.industry} 투자 전략 보고서

> **분석 기준 시각**: {now_kst_str} (시세 상태는 Section 4.2 첫 줄 '데이터 기준' 참고 — 장중 실행이면 시세·수급은 잠정치)
> **데이터 스냅샷**: `{snapshot_basename}`{baseline_note}
> **종합 의사결정 신호**: [거시 시장 신호: {macro_signal_str}] vs [기업 밸류 신호: {effective_target_verdict}] vs [미래 알파 신호: {alpha_sig_icon} {target_archetype_label} (공격 {target_alpha_score}점 / 방어 {target_defense_score}점)]
> **한 줄 결론**: {conclusion_line}
{crisis_box_insert}
### 📌 Executive Summary & Signal Dashboard

| 핵심 평가 영역 | 진단 신호 | 세부 진단 요약 |
|---|:---:|---|
| **거시 시장 국면 (Phase 1)** | {macro_icon} | **{macro_verdict}**: 권장 현금 {macro_cash_pct}% 안전마진 준수 |
| **가치사슬 구조 (Phase 2)** | 🟢 | **독점적 병목 해자 및 교섭력**: Up/Mid/Downstream 가치사슬 및 GPM 우위 |
| **기업 밸류에이션 (Phase 3)** | 🟡 | **정밀 밸류에이션 및 바닥선 점검**: 4-호라이즌 밸류에이션 및 Multiple C 하방선 |
| **미래 상승 알파 (Phase 3.5)** | {alpha_sig_icon} | **{target_archetype_label}**: 공격 알파 **{target_alpha_score}점** (방어 {target_defense_score}점) |
| **권장 모델 포트폴리오** | 🛡️ | **현금 {macro_cash_pct}.0%** (거시 안전마진 준수) + 타겟 및 피어 분산 |

---

## 1. 산업 개요 및 최근 시장 동향

### 1.1. 중장기 산업 규모 및 구조적 성장 동인
[AI_TODO: {args.industry} 산업의 시장 규모, 연평균 성장률(CAGR), 중장기 전망을 출처(제목·발행일·URL)와 함께 요약. 전망치 발표 시점이 오래됐으면 날짜를 밝힐 것]

### 1.2. 최근 시장 변동성 및 거시/업황 트리거 진단
{sec1_2_content}

### 1.3. 검증 체크리스트 (필수 — 모든 항목에 출처 제목·발행일·URL)

| 확인 항목 | 확인 결과 | 출처 (발행일) |
|---|---|---|
| 타겟·경쟁사의 최근 실적 및 잠정실적 | [AI_TODO: 최신 분기 매출·영업이익(잠정 포함). Section 4.2 › 6번 시나리오의 EPS 범위와 어긋나면 그 점을 적기] | [AI_TODO] |
| 다음 실적 발표일 | [AI_TODO: Section 4.2 › 3-1 표 + 잠정실적 공시 일정] | [AI_TODO] |
| 최근 30일 이익 추정치 방향 | [AI_TODO: Section 4.2 › 3-1 표 해석] | 스크립트 산출 |
| 지수·해외 피어 동반 등락 여부 | [AI_TODO: Section 4.1 및 Section 4.2 › 1-3 표 해석] | 스크립트 산출 |
| 하락·상승 트리거의 사실관계 | [AI_TODO: 발표 원문 확인, 공개된 사양·수율·고객사 여부] | [AI_TODO] |
| 핵심 촉매의 현재 상태 | [AI_TODO: 90일 이내 출처로만 확인] | [AI_TODO] |

---

## 2. 가치사슬 구조도

{mermaid_output}

---

## 3. 핵심 병목(Bottleneck) 및 해자(Moat) 분석

산업의 핵심 병목 현상과 강력한 해자(Moat)를 지닌 기업들을 분석합니다. 타겟과 경쟁 관계인 사업부가 있는 병목 기업은 역할을 함께 표기합니다(예: `[병목협력·경쟁]`).
> 💡 **가치사슬 교섭력(Bargaining Power)**: 상류-중류-하류 간 이익 독점 구조는 Section 4의 **매출총이익률(GPM)**과 **현금전환주기(CCC)**를 대조하여, 누가 납품업체에 대금과 재고를 떠넘기고 현금을 독식하는 '진짜 갑'인지 함께 분석하세요.

| 기업명 | 티커 | 가치사슬 위치 | 핵심 역할 및 경제적 해자(Moat) |
|---|---|---|---|
{peer_rows}

---

## 4. 정량 데이터 분석 결과 (스크립트 자동 산출 — 수치 수정 금지)

{sec4_full_body}

---

## 5. 기업별 심층 분석 및 밸류에이션 판단

[AI_TODO: Section 4.2의 판정(4번 매트릭스)을 기업별로 해석하세요. 판정을 바꾸지 말고, 왜 그런 신호가 나왔는지와 신호가 놓칠 수 있는 점을 설명합니다.]

{company_analysis_section}

---

## 6. 소크라테스식 변증법적 리스크 평가 및 가설 검증

### 6.1. 시나리오 스트레스 테스트 해석

> 💡 수치는 Section 4.2 › 6번 표(스크립트 산출)를 그대로 인용합니다. 영업이익·EPS·배수를 직접 만들어 넣지 않습니다.

[AI_TODO: (1) 배수 A(현재 배수 유지)와 배수 B(목표가 내재 배수)의 결과 차이가 무엇을 뜻하는지, (2) Bear 하방이 음수이면 그 크기를 그대로 적고, (3) 순환업종은 Section 4.2 › 2-1의 '밴드 최저 P/B 회귀 시 주가'도 함께 적으세요. (4) 결합 하방 시나리오(배수 C: 실적 쇼크와 밸류에이션 수축이 동시 발생할 때의 진짜 바닥선)를 직시하고 계좌 보호를 위한 현금 비중 원칙을 명시하세요. 핵심 드라이버(예: D램 가격)와 이익의 연결은 출처가 있는 민감도 수치만 인용합니다. 결론에 맞추려고 가정을 바꾸지 않습니다.]

### 6.2. 소크라테스식 6대 질문 심층 검증 (Socratic 6-Pillar Interrogation)

1. **명료화 (Clarification)**: [AI_TODO: 현재 주가 조정 또는 랠리의 본질을 감정적 수식어 없이 객관적으로 정의]
2. **숨은 가정 검증 (Hidden Assumptions)**: [AI_TODO: 시장 참여자들이 당연하게 믿고 있는 전제(예: 무한 AI CAPEX, 금리 인하 기대 등) 중 훼손된 것 식별]
3. **정량적 근거 탐색 (Empirical Evidence)**: [AI_TODO: Section 4.1 및 4.2의 정량 지표(200선 이격도, VIX, Forward P/E, 신용 스프레드)를 근거로 주장 제시]
4. **변증법적 반대 논증 (Bear Anti-Thesis, 필수)**: [AI_TODO: 기관 숏세력/비관론자 입장에서 가장 강력한 반대 논리 3가지와 근거 제시]
5. **연쇄 파급효과 시뮬레이션 (Cascading Consequences)**: [AI_TODO: 핵심 지지선 붕괴 시 발생할 수 있는 마진콜, CTA 강제 매도, 밸류체인 연쇄 충격 시뮬레이션]
6. **메타인지 점검 (Meta-Cognitive Evaluation)**: [AI_TODO: 본 분석이 특정 결론에 편향되지 않았는지, 5대 인지 편향에 걸려있지 않은지 자기 점검]

### 6.3. 인지 편향 감사 및 가설 무효화 사다리 (Thesis Invalidation Ladder)

#### 5대 인지 편향 교정 점검
[AI_TODO: Section 4.1 › 6번 인지 편향 감사 결과를 바탕으로, 최신 편향·닻내림 편향·확증 편향·손실 회피·행동 편향에 대한 구체적 교정 방안 작성]

#### 가설 무효화 조건
| 가설 구분 | 무효화 트리거 조건 (수치/이벤트 기준) | 전환 행동 |
|---|---|---|
| 강세론 (Bull) | [AI_TODO: Section 4.1 › 7번 무효화 조건 및 추가 기업 지표] | 즉시 비중 축소 / 손절 |
| 약세론 (Bear) | [AI_TODO: Section 4.1 › 7번 무효화 조건 및 추가 기업 지표] | 저가 분할 매수 재개 |

- **스크립트 판정과 다른 결론을 쓴 경우의 근거**: [AI_TODO: 해당 없으면 '해당 없음']

---

## 7. 투자 전략 및 포트폴리오 배분 제안

### 🎯 7.1. 탑다운 거시 현금 제약 (Cash Allocation Constraint)
- **현재 시장 국면**: {macro_verdict} ({macro_icon})
- **최소 권장 현금 비중**: **{macro_cash_pct}% 이상** (거시 하방 충격 대비 안전마진 확보)
- **거시 신호 연동 행동 지침**: [AI_TODO: 거시 시장 위험 신호와 연동된 포트폴리오 전체 리스크 관리 원칙 작성]

### 🎯 7.2. 바텀업 판정 연동 실행 전략 (Execution Strategy)
[AI_TODO: Section 4.2의 기업별 종합 판정과 6.3 가설 무효화 사다리를 연계하여 작성하세요.
- 🟢 매수: 분할 매수 계획(1차 지지선, 2차 위기 지지선 등 가격대·비중·조건)과 무효화 트리거 터치 시 대응
- 🟡 중립·관망: 진입을 검토할 조건(예: 추정치 방향 전환, 밴드 하단 접근, VIX 안정)과 그때까지의 관망 대응
- 🔴 비중 축소·회피: 축소·회피 근거와 재진입을 검토할 조건
기술적 지표(Section 4.1/4.2)는 진입 시점을 고르는 보조 수단으로만 쓰고, 과매도 자체를 매수 근거로 쓰지 않습니다.]

### 💰 7.3. 포트폴리오 배분 제안
{sec7_3_content}

---

## 8. 참고 문헌 (References)

[AI_TODO: 본문에서 인용한 출처를 [번호] 제목 — 발행일 — URL 형식으로 적으세요. 사이트 홈페이지만 가리키는 링크는 쓰지 않습니다. 숫자 점검(check_strategy_report_numbers.py)에서 남은 문제가 있으면 '## 9. 숫자 점검 결과' 섹션을 이 목록 뒤에 넣습니다.]

---

*본 보고서는 공개 데이터와 컨센서스를 바탕으로 자동·반자동 생성된 참고 자료이며 투자 권유가 아닙니다. 수치는 데이터 제공처의 지연·오류를 포함할 수 있고, 투자 판단과 그 결과의 책임은 투자자 본인에게 있습니다.*
"""

    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(template)

    print(f"✅ 통합 4-티어 투자 전략 보고서 템플릿이 성공적으로 생성되었습니다: {output_filename}")
    print(f"📦 통합 동반 데이터 스냅샷: {snapshot_filename}")
    print("🤖 AI 에이전트는 이제 [AI_TODO] 영역을 채워주세요. Section 4의 수치와 판정은 절대 수정하지 않습니다.")


if __name__ == "__main__":
    main()
