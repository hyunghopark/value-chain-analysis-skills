"""
Market Intelligence Collector (실시간 특수 상황 및 뉴스 인텔리전스 수집기)
Zero-Dictionary 2-Stage Adaptive Multi-hop Discovery Engine.
Pure Python standard library with 100% Spec 003 snapshot determinism.
"""

import argparse
import collections
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set, Tuple

KST = datetime.timezone(datetime.timedelta(hours=9))

# Standard English financial stopwords (to isolate unusual proper nouns & verbs)
COMMON_STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
    "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more",
    "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
    "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they",
    "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't",
    "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom",
    "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've",
    "your", "yours", "yourself", "yourselves", "stock", "stocks", "shares", "market", "markets",
    "inc", "corp", "co", "ltd", "today", "week", "month", "year", "news", "report", "reports",
    "investor", "investors", "analyst", "analysts", "price", "target", "quarter", "q1", "q2", "q3", "q4",
    "fy24", "fy25", "fy26", "fy27", "earnings", "call", "results", "update", "updates", "say", "says",
    "said", "will", "may", "can", "new", "first", "last", "one", "two", "three", "see", "sees",
}

# Institutional Crisis Keywords with Severity Weighting
CRISIS_LEXICON: Dict[str, Tuple[int, str]] = {
    # Term: (Severity weight 1-5, Category)
    "affair": (5, "거버넌스 및 도덕적 해이"),
    "extramarital": (5, "거버넌스 및 도덕적 해이"),
    "mistress": (5, "거버넌스 및 도덕적 해이"),
    "scandal": (5, "거버넌스 위기"),
    "oust": (5, "경영권 분쟁 및 이사회 해임"),
    "ouster": (5, "경영권 분쟁 및 이사회 해임"),
    "remove": (4, "경영진 교체"),
    "subpoena": (5, "사법 및 의회 소환"),
    "subpoenas": (5, "사법 및 의회 소환"),
    "spy": (5, "국가 안보 및 스파이 연루"),
    "espionage": (5, "국가 안보 및 스파이 연루"),
    "mss": (5, "중국 정보기관 연루"),
    "wachtell": (5, "이사회 독립 조사 착수"),
    "fraud": (5, "분식회계 및 사기"),
    "indictment": (5, "형사 기소"),
    "resigns": (4, "임원 사임"),
    "resignation": (4, "임원 사임"),
    "auditor": (4, "외부 감사인 분쟁"),
    "probe": (4, "감독 당국 정식 조사"),
    "investigation": (4, "정식 조사 착수"),
    "sec": (3, "규제 당국 개입"),
    "doj": (4, "법무부 반독점/형사 조사"),
    "ftc": (3, "공정위 조사"),
    "antitrust": (4, "반독점 규제"),
    "bsod": (5, "대규모 시스템 마비"),
    "outage": (4, "서비스 중단"),
    "recall": (3, "제품 리콜"),
    "whistleblower": (4, "내부 고발"),
}


def fetch_google_news_rss(query: str, max_items: int = 30) -> List[Dict[str, str]]:
    """Fetch recent headlines from Google News RSS using pure standard library."""
    encoded_q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
    }
    req = urllib.request.Request(url, headers=headers)
    items: List[Dict[str, str]] = []

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        for item in root.findall(".//item")[:max_items]:
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            pub_date = item.findtext("pubDate") or ""
            source = item.findtext("source") or ""
            # Strip source from title if format is "Headline - Source"
            clean_title = re.sub(r'\s*-\s*[^-]+$', '', title).strip()
            if clean_title:
                items.append({
                    "title": clean_title,
                    "link": link,
                    "pubDate": pub_date,
                    "source": source or "Google News",
                })
    except Exception as e:
        print(f"⚠️ [market-intelligence] RSS fetch warning for '{query}': {e}", file=sys.stderr)

    return items


def extract_token_spikes(items: List[Dict[str, str]], ticker: str) -> Tuple[collections.Counter, List[Tuple[str, int, str]]]:
    """
    Extract high-frequency non-stopword tokens and identify crisis keyword hits.
    Returns:
        (token_counts, crisis_hits: List of (term, severity, category))
    """
    tokens: List[str] = []
    ticker_clean = ticker.upper().split('.')[0]
    extra_stops = {ticker.lower(), ticker_clean.lower(), "nvidia", "nvda", "tsmc", "tsm", "amd", "broadcom", "avgo", "samsung", "sk"}

    crisis_hits: List[Tuple[str, int, str]] = []
    seen_crisis_terms: Set[str] = set()

    for it in items:
        title = it.get("title", "")
        # Check crisis lexicon first
        title_lower = title.lower()
        for term, (sev, cat) in CRISIS_LEXICON.items():
            if re.search(r'\b' + re.escape(term) + r'\b', title_lower):
                if term not in seen_crisis_terms:
                    crisis_hits.append((term, sev, cat))
                    seen_crisis_terms.add(term)

        # Word token extraction
        words = re.findall(r'\b[A-Za-z][A-Za-z0-9_\-\']+\b', title)
        for w in words:
            w_lower = w.lower()
            if len(w) > 2 and w_lower not in COMMON_STOPWORDS and w_lower not in extra_stops:
                tokens.append(w)

    counts = collections.Counter(tokens)
    return counts, crisis_hits


def classify_severity(crisis_hits: List[Tuple[str, int, str]], items_count: int) -> Tuple[int, str, str]:
    """
    Classify crisis severity level (1-5) and provide diagnostic summary.
    Returns: (severity_level, primary_crisis, description)
    """
    if not crisis_hits or items_count == 0:
        return 1, "정상 (특이 동향 없음)", "특수 이벤트나 거버넌스 이상 징후가 감지되지 않았습니다."

    max_sev = max(hit[1] for hit in crisis_hits)
    categories = list(dict.fromkeys(hit[2] for hit in crisis_hits))
    terms = [hit[0] for hit in crisis_hits]

    # Level 5: Catastrophic governance crisis / board ouster / subpoena
    if max_sev >= 5 or any(t in terms for t in ["affair", "oust", "ouster", "subpoena", "spy", "wachtell", "bsod"]):
        terms_lower = [t.lower() for t in terms]
        terms_str = " ".join(terms_lower)
        primary = f"{categories[0]} (핵심 키워드: {', '.join(terms[:4])})"
        if any(k in terms_str or k in primary for k in ("oust", "ouster", "affair", "wachtell", "해임", "경영권")):
            desc = "최고경영자 거버넌스 붕괴, 이사회 해임 논의 등 중대 경영권 위기 국면입니다."
        elif any(k in terms_str or k in primary for k in ("antitrust", "반독점", "subpoena", "소환장", "doj", "ftc")):
            desc = "사법 당국의 반독점 소송 또는 중대 규제 시정조치 리스크가 부각된 위기 국면입니다."
        else:
            desc = f"{primary} 관련 중대 기업 고유 리스크가 감지된 상태입니다."
        return 5, primary, desc

    # Level 4: Severe operational or regulatory probe
    if max_sev == 4 or any(t in terms for t in ["probe", "investigation", "resigns", "resignation", "auditor", "doj"]):
        terms_lower = [t.lower() for t in terms]
        terms_str = " ".join(terms_lower)
        primary = f"{categories[0]} (핵심 키워드: {', '.join(terms[:3])})"
        if any(k in terms_str or k in primary for k in ("antitrust", "반독점")):
            desc = "사법 당국의 반독점 소송 또는 중대 규제 시정조치 리스크가 부각된 위기 국면입니다."
        elif any(k in terms_str or k in primary for k in ("resigns", "resignation", "auditor", "사임", "회계")):
            desc = "핵심 경영진 사임, 회계법인 분쟁 또는 사법 당국의 정식 조사가 착수된 심각한 위기 상태입니다."
        else:
            desc = f"{primary} 관련 중대 기업 고유 리스크가 감지된 상태입니다."
        return 4, primary, desc

    # Level 3: Moderate watch
    if max_sev == 3:
        primary = f"{categories[0]} (키워드: {', '.join(terms[:2])})"
        desc = "공급망 지연, 사소한 규제 조사 또는 리콜 이슈가 발생하여 면밀한 모니터링이 필요합니다."
        return 3, primary, desc

    return 2, "경미한 노이즈", "일상적인 시장 변동성 또는 경미한 분쟁 수준입니다."


def fetch_official_disclosures(ticker: str, severity_level: int, primary_crisis: str = "") -> Optional[Dict[str, Any]]:
    """
    Query official regulatory disclosures (SEC Form 8-K for US, DART for KR)
    when Level 4 or Level 5 crisis is detected.
    """
    if severity_level < 4:
        return None

    clean_ticker = ticker.upper().split(".")[0]
    now_date = datetime.datetime.now(KST).date()

    mcp = None
    try:
        from . import mcp_client
        mcp = mcp_client
    except (ImportError, ValueError):
        try:
            import mcp_client
            mcp = mcp_client
        except Exception:
            pass

    if not mcp:
        return {
            "authority": "SEC EDGAR" if not ticker.endswith((".KS", ".KQ")) else "DART",
            "status": "UNAVAILABLE",
            "status_label": "ℹ️ [공시 클라이언트 미연결]",
            "governance_item_filed": False,
            "latest_filing": None,
            "diagnosis": "공시 MCP 클라이언트를 로드할 수 없습니다.",
        }

    # --- US Ticker via SEC EDGAR ---
    if not ticker.endswith((".KS", ".KQ")):
        try:
            filings = mcp.call_mcp("edgar", "sec_filings", {"company": clean_ticker, "forms": "8-K,8-K/A", "limit": 10})
            if filings and "rows" in filings and len(filings["rows"]) > 0:
                latest = filings["rows"][0]
                has_recent_502 = False
                target_filing = latest
                for r in filings["rows"]:
                    items = str(r.get("items", ""))
                    f_date_str = r.get("filing_date", "")
                    try:
                        f_date = datetime.datetime.strptime(f_date_str, "%Y-%m-%d").date()
                        days_diff = (now_date - f_date).days
                    except Exception:
                        days_diff = 999

                    if "5.02" in items and days_diff <= 14:
                        has_recent_502 = True
                        target_filing = r
                        break

                crisis_label = primary_crisis if primary_crisis else "감지된 사안"
                if has_recent_502:
                    return {
                        "authority": "SEC EDGAR",
                        "status": "FILED",
                        "status_label": "🚨 [공식 8-K 접수 확인 (Item 5.02: 경영진/이사진 변동)]",
                        "governance_item_filed": True,
                        "latest_filing": target_filing,
                        "diagnosis": (
                            f"SEC 공식 Form 8-K (접수일: {target_filing.get('filing_date')}, Item: {target_filing.get('items')})에 "
                            f"경영진/이사진 변동 안건이 정식 접수되었습니다. 사실관계가 법적으로 확정되었습니다."
                        ),
                    }
                else:
                    return {
                        "authority": "SEC EDGAR",
                        "status": "PENDING_OR_NOT_FILED",
                        "status_label": "⏳ [공식 8-K 미접수 / 사안 심의 진행 중 (Pending)]",
                        "governance_item_filed": False,
                        "latest_filing": latest,
                        "diagnosis": (
                            f"최신 Form 8-K 접수일은 {latest.get('filing_date')} (Item {latest.get('items')})이며, "
                            f"감지된 사안({crisis_label})과 직접 관련된 신규 수시공시(8-K)는 아직 SEC EDGAR에 접수되지 않았습니다. "
                            f"(SEC 규정상 사건 발생 후 4영업일 이내 의무 제출 대상이며, 현재는 언론 특종 보도 및 내부 심의 단계입니다)."
                        ),
                    }
        except Exception as e:
            return {
                "authority": "SEC EDGAR",
                "status": "QUERY_ERROR",
                "status_label": "⚠️ [SEC EDGAR 조회 에러]",
                "governance_item_filed": False,
                "latest_filing": None,
                "diagnosis": f"SEC 공시 조회 중 오류 발생: {e}",
            }

    # --- KR Ticker via DART ---
    else:
        try:
            clean_code = ticker.split(".")[0]
            corp_res = mcp.call_mcp("dart", "dart_find_corp", {"query": clean_code})
            corp_code = None
            if corp_res and "results" in corp_res and len(corp_res["results"]) > 0:
                corp_code = corp_res["results"][0].get("corp_code")

            if corp_code:
                disclosures = mcp.call_mcp("dart", "dart_disclosures", {"corp": corp_code, "page_count": 5})
                if disclosures and "list" in disclosures and len(disclosures["list"]) > 0:
                    latest = disclosures["list"][0]
                    has_major = any(
                        "주요사항" in d.get("report_nm", "") or "임원" in d.get("report_nm", "")
                        for d in disclosures["list"]
                    )
                    return {
                        "authority": "DART",
                        "status": "FILED" if has_major else "PENDING_OR_NOT_FILED",
                        "status_label": "🚨 [DART 주요사항보고서 접수 확인]" if has_major else "⏳ [DART 거버넌스 수시공시 미접수 (Pending)]",
                        "governance_item_filed": has_major,
                        "latest_filing": latest,
                        "diagnosis": f"최신 DART 공시는 '{latest.get('report_nm')}' (접수일: {latest.get('rcept_dt')})입니다.",
                    }
        except Exception as e:
            return {
                "authority": "DART",
                "status": "QUERY_ERROR",
                "status_label": "⚠️ [DART 조회 에러]",
                "governance_item_filed": False,
                "latest_filing": None,
                "diagnosis": f"DART 공시 조회 중 오류 발생: {e}",
            }

    return None


def run_intelligence_collection(ticker: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute 2-stage adaptive intelligence discovery loop:
    1. Wide Scan: '{ticker} breaking news'
    2. Anomaly Spike Extraction & Multi-hop Triggering
    3. Deep Dive Follow-up (if crisis detected)
    4. Deterministic Snapshot Packaging
    """
    now_kst_str = datetime.datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')
    ticker_clean = ticker.upper().split('.')[0]

    # --- Stage 1: Wide Broad Scan ---
    query_stage1 = f"{ticker_clean} breaking news"
    items_stage1 = fetch_google_news_rss(query_stage1, max_items=30)
    token_counts, crisis_hits = extract_token_spikes(items_stage1, ticker_clean)
    severity_level, primary_crisis, crisis_desc = classify_severity(crisis_hits, len(items_stage1))

    # --- Stage 2: Adaptive Multi-hop Deep Dive ---
    items_stage2: List[Dict[str, str]] = []
    deep_queries: List[str] = []

    if severity_level >= 3:
        # Pick top spiking proper nouns / crisis terms not in ticker name
        top_spikes = [w for w, _ in token_counts.most_common(5) if len(w) > 3]
        critical_terms = [t for t, sev, _ in crisis_hits if sev >= 4]

        # Generate targeted follow-up query
        target_entity = critical_terms[0] if critical_terms else (top_spikes[0] if top_spikes else "investigation")
        q2 = f"{ticker_clean} {target_entity}"
        deep_queries.append(q2)
        items_stage2 = fetch_google_news_rss(q2, max_items=15)

    # Merge unique news items
    seen_links = set()
    merged_items: List[Dict[str, str]] = []
    for it in (items_stage1 + items_stage2):
        link = it.get("link")
        if link and link not in seen_links:
            seen_links.add(link)
            merged_items.append(it)

    # Compile Top 5 Key Evidence Headlines
    evidence_headlines = [it["title"] for it in merged_items[:5]]

    # --- Stage 3: Official Disclosure Cross-Verification (SEC Form 8-K / DART) ---
    official_disclosures = None
    if severity_level >= 4:
        official_disclosures = fetch_official_disclosures(ticker, severity_level, primary_crisis)

    intelligence_payload: Dict[str, Any] = {
        "meta": {
            "format_version": 1,
            "ticker": ticker_clean,
            "as_of": now_kst_str,
            "stage1_query": query_stage1,
            "stage2_queries": deep_queries,
            "total_items_scanned": len(merged_items),
        },
        "severity": {
            "level": severity_level,  # 1 to 5
            "is_crisis": severity_level >= 4,
            "primary_crisis": primary_crisis,
            "description": crisis_desc,
            "crisis_tokens": [hit[0] for hit in crisis_hits],
        },
        "official_disclosures": official_disclosures,
        "token_spikes": dict(token_counts.most_common(10)),
        "evidence_headlines": evidence_headlines,
        "items": merged_items[:30],
    }

    if output_path:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(intelligence_payload, f, ensure_ascii=False, indent=2)

    return intelligence_payload


def main():
    parser = argparse.ArgumentParser(description="Market Intelligence Autonomous Collector")
    parser.add_argument("--ticker", type=str, required=True, help="Target stock ticker (e.g. NVDA, 005930.KS)")
    parser.add_argument("--output", type=str, default="", help="Path to output snapshot JSON")
    args = parser.parse_args()

    result = run_intelligence_collection(args.ticker, args.output)
    sev = result["severity"]
    print(f"✅ [market-intelligence] Scanned {result['meta']['total_items_scanned']} items. "
          f"Severity: Level {sev['level']} ({sev['primary_crisis']})")
    if sev["is_crisis"]:
        print(f"🚨 [CRISIS ALERT TRIGGERED] {sev['description']}")
        for h in result["evidence_headlines"][:3]:
            print(f"   - {h}")


if __name__ == "__main__":
    main()
