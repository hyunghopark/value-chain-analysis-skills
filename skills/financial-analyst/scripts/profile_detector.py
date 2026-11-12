"""
Profile detector for sector-adaptive valuation frameworks.
Identifies one of the 5 institutional business profiles automatically based on
GICS sector, industry, and balance sheet/cash flow characteristics.
"""

from typing import Any, Dict, Optional, Tuple

PROFILE_CYCLICAL = 'cyclical'
PROFILE_CASH_COW = 'cash_cow_dividend'
PROFILE_TECH_GROWTH = 'tech_high_growth'
PROFILE_FINANCIALS = 'financials'
PROFILE_BIOTECH = 'biotech_pipeline'
PROFILE_GENERAL = 'general'

PROFILE_NAMES = {
    PROFILE_CYCLICAL: '🔄 경기순환',
    PROFILE_CASH_COW: '🛡️ 배당·현금흐름',
    PROFILE_TECH_GROWTH: '🚀 고성장·무형자산',
    PROFILE_FINANCIALS: '🏦 금융·자본효율',
    PROFILE_BIOTECH: '🧪 R&D·파이프라인',
    PROFILE_GENERAL: '일반',
}


def detect_business_profile(info: Dict[str, Any], symbol: str = "") -> Tuple[str, str]:
    """
    Detects the corporate business profile.
    Returns:
        (profile_id, basis_description)
    """
    sym = (symbol or info.get('symbol') or "").upper()
    sector = str(info.get('sector') or "").lower().strip()
    industry = str(info.get('industry') or "").lower().strip()
    quote_type = str(info.get('quoteType') or "").lower().strip()

    # Manual user overrides passed via info
    if info.get('_manual_profile'):
        pid = info['_manual_profile']
        if pid in PROFILE_NAMES:
            return pid, f"사용자 지정({PROFILE_NAMES[pid]})"

    # Legacy flags support
    if info.get('_is_cyclical_manual_false'):
        # Excluded from cyclical manually
        pass
    elif info.get('_is_cyclical_manual_true'):
        return PROFILE_CYCLICAL, "사용자 지정(순환)"

    # Financial data points
    ebitda = info.get('ebitda')
    operating_cf = info.get('operatingCashflow')
    free_cf = info.get('freeCashflow')
    rev_growth = info.get('revenueGrowth') or 0.0
    div_yield = info.get('dividendYield') or 0.0
    rd_exp = info.get('researchAndDevelopment') or 0.0
    total_rev = info.get('totalRevenue') or 0.0
    net_income = info.get('netIncomeToCommon') or info.get('netIncome') or 0.0

    # 1. Financials: Banks, Insurance, Capital Markets, Asset Management
    financial_keywords = [
        'bank', 'insurance', 'capital markets', 'asset management', 'credit',
        'brokerage', 'financial', 'mortgage', 'savings', 'securities',
        '생명보험', '손해보험', '화재', '은행', '금융', '증권', '카드'
    ]
    if 'financial' in sector or any(k in industry for k in financial_keywords) or any(k in sym for k in ['KB', 'SHINHAN']):
        return PROFILE_FINANCIALS, f"GICS 금융 섹터/산업({sector or industry})"

    # 2. Biotech & Clinical Pipeline: Biotechnology, Drug Discovery, Clinical stage
    biotech_keywords = [
        'biotechnology', 'biotech', 'drug discovery', 'pharmaceutical', 'biopharmaceuticals',
        'clinical', '신약', '바이오'
    ]
    if any(k in industry for k in biotech_keywords) or ('healthcare' in sector and any(k in industry for k in ['biotechnology', 'drug'])):
        if ebitda is None or (isinstance(ebitda, (int, float)) and ebitda <= 0) or (total_rev > 0 and rd_exp / total_rev > 0.25):
            return PROFILE_BIOTECH, f"바이오텍/신약개발 R&D 특성({industry})"
        return PROFILE_BIOTECH, f"GICS 바이오/헬스케어({industry})"

    # 3. Cash Cow & Dividend Defense: Consumer Staples, Utilities, Telecom with stable FCF
    cash_cow_sectors = ['consumer defensive', 'utilities']
    cash_cow_industries = [
        'beverage', 'tobacco', 'household', 'food', 'electric utility', 'gas utility',
        'water utility', 'telecom', 'packaged foods', 'confectionery', 'soft drinks',
        '음료', '담배', '전력', '가스', '통신', '식품'
    ]
    if any(k in sector for k in cash_cow_sectors) or any(k in industry for k in cash_cow_industries):
        return PROFILE_CASH_COW, f"필수소비재/유틸리티/배당형 산업({sector or industry})"

    # 4. Cyclicals: Semiconductors, Chemicals, Steel, Energy, Shipping, Mining, Auto, Hardware
    cyclical_sectors = ['basic materials', 'energy']
    cyclical_industries = [
        'semiconductor', 'chemical', 'steel', 'metals', 'mining', 'oil & gas',
        'marine', 'shipping', 'freight', 'construction', 'auto manufacturers',
        'consumer electronics', 'electronic components', 'hardware', 'display',
        '반도체', '화학', '철강', '조선', '해운', '정유', '건설', '전자부품'
    ]
    is_cyc_sector = any(k in sector for k in cyclical_sectors) or any(k in industry for k in cyclical_industries)
    cyc_info = info.get('_cycle') or {}
    is_cyc_auto = bool(cyc_info.get('auto'))

    if is_cyc_sector or is_cyc_auto:
        basis = cyc_info.get('basis') or (f"GICS 산업({industry or sector})")
        return PROFILE_CYCLICAL, f"경기순환형 산업({industry or sector}) · {basis}"

    # 5. Tech & High Growth: Software, Platforms, SaaS, Cloud, AI
    tech_industries = [
        'software', 'internet', 'cloud', 'information technology services', 'cybersecurity',
        'interactive media', 'digital platforms', 'saas', '플랫폼', '소프트웨어'
    ]
    if 'technology' in sector or 'communication' in sector or any(k in industry for k in tech_industries):
        if rev_growth >= 0.15:
            return PROFILE_TECH_GROWTH, f"고성장 기술/플랫폼(매출성장 {rev_growth*100:.1f}%)"
        return PROFILE_TECH_GROWTH, f"소프트웨어/기술 산업({industry})"

    # Fallback to general
    return PROFILE_GENERAL, f"일반 산업({sector or industry})"
