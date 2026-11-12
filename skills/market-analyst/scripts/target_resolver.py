"""
Target resolver and query classifier for market-analyst:
Classifies user queries into institutional profiles (KR_INDEX, KR_MARKET, SECTOR_SEMI,
SECTOR_TECH, SINGLE_STOCK, US_MARKET) and resolves appropriate indices, macro tickers,
crisis benchmarks, and financial-analyst bridge configurations.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

PROFILE_KR_INDEX = "KR_INDEX"
PROFILE_KR_MARKET = "KR_MARKET"
PROFILE_SECTOR_SEMI = "SECTOR_SEMI"
PROFILE_SECTOR_TECH = "SECTOR_TECH"
PROFILE_SINGLE_STOCK = "SINGLE_STOCK"
PROFILE_US_MARKET = "US_MARKET"

# Well-known stock dictionary for auto-resolution
KNOWN_STOCKS: Dict[str, Dict[str, Any]] = {
    # Korean major stocks
    "삼성전자": {
        "ticker": "005930.KS",
        "name": "삼성전자 (Samsung Electronics)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "^SOX",
        "cyclical": True,
        "description": "글로벌 메모리 반도체 및 스마트폰 선도 기업 (코스피 시가총액 1위)",
    },
    "005930.KS": {
        "ticker": "005930.KS",
        "name": "삼성전자 (Samsung Electronics)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "^SOX",
        "cyclical": True,
        "description": "글로벌 메모리 반도체 및 스마트폰 선도 기업 (코스피 시가총액 1위)",
    },
    "005930": {
        "ticker": "005930.KS",
        "name": "삼성전자 (Samsung Electronics)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "^SOX",
        "cyclical": True,
        "description": "글로벌 메모리 반도체 및 스마트폰 선도 기업 (코스피 시가총액 1위)",
    },
    "LG전자": {
        "ticker": "066570.KS",
        "name": "LG전자 (LG Electronics)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLI",
        "cyclical": False,
        "description": "글로벌 가전 및 전장(VS) 솔루션 선도 기업",
    },
    "066570.KS": {
        "ticker": "066570.KS",
        "name": "LG전자 (LG Electronics)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLI",
        "cyclical": False,
        "description": "글로벌 가전 및 전장(VS) 솔루션 선도 기업",
    },
    "066570": {
        "ticker": "066570.KS",
        "name": "LG전자 (LG Electronics)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLI",
        "cyclical": False,
        "description": "글로벌 가전 및 전장(VS) 솔루션 선도 기업",
    },
    "SK하이닉스": {
        "ticker": "000660.KS",
        "name": "SK하이닉스 (SK Hynix)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "^SOX",
        "cyclical": True,
        "description": "HBM(고대역폭메모리) 독점적 리더 및 글로벌 메모리 반도체 기업",
    },
    "000660.KS": {
        "ticker": "000660.KS",
        "name": "SK하이닉스 (SK Hynix)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "^SOX",
        "cyclical": True,
        "description": "HBM(고대역폭메모리) 독점적 리더 및 글로벌 메모리 반도체 기업",
    },
    "000660": {
        "ticker": "000660.KS",
        "name": "SK하이닉스 (SK Hynix)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "^SOX",
        "cyclical": True,
        "description": "HBM(고대역폭메모리) 독점적 리더 및 글로벌 메모리 반도체 기업",
    },
    # US major stocks
    "테슬라": {
        "ticker": "TSLA",
        "name": "테슬라 (Tesla)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "XLY",
        "cyclical": False,
        "description": "글로벌 EV 및 자율주행·AI 로보틱스 선도 기업",
    },
    "TSLA": {
        "ticker": "TSLA",
        "name": "테슬라 (Tesla)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "XLY",
        "cyclical": False,
        "description": "글로벌 EV 및 자율주행·AI 로보틱스 선도 기업",
    },
    "엔비디아": {
        "ticker": "NVDA",
        "name": "엔비디아 (NVIDIA)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "^SOX",
        "cyclical": False,
        "description": "AI 가속기 및 GPU 컴퓨팅 글로벌 독점 선도 기업",
    },
    "NVDA": {
        "ticker": "NVDA",
        "name": "엔비디아 (NVIDIA)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "^SOX",
        "cyclical": False,
        "description": "AI 가속기 및 GPU 컴퓨팅 글로벌 독점 선도 기업",
    },
    "애플": {
        "ticker": "AAPL",
        "name": "애플 (Apple)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "XLK",
        "cyclical": False,
        "description": "글로벌 프리미엄 디바이스 및 온디바이스 AI 생태계 기업",
    },
    "AAPL": {
        "ticker": "AAPL",
        "name": "애플 (Apple)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "XLK",
        "cyclical": False,
        "description": "글로벌 프리미엄 디바이스 및 온디바이스 AI 생태계 기업",
    },
    # Major US tech & semi stocks
    "마이크로소프트": {
        "ticker": "MSFT",
        "name": "마이크로소프트 (Microsoft)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "XLK",
        "cyclical": False,
        "description": "글로벌 클라우드 및 생성형 AI 엔터프라이즈 선도 기업",
    },
    "MSFT": {
        "ticker": "MSFT",
        "name": "마이크로소프트 (Microsoft)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "XLK",
        "cyclical": False,
        "description": "글로벌 클라우드 및 생성형 AI 엔터프라이즈 선도 기업",
    },
    "구글": {
        "ticker": "GOOGL",
        "name": "알파벳 (Alphabet)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "XLC",
        "cyclical": False,
        "description": "글로벌 검색 엔진 및 클라우드·AI 연구 선도 기업",
    },
    "알파벳": {
        "ticker": "GOOGL",
        "name": "알파벳 (Alphabet)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "XLC",
        "cyclical": False,
        "description": "글로벌 검색 엔진 및 클라우드·AI 연구 선도 기업",
    },
    "GOOGL": {
        "ticker": "GOOGL",
        "name": "알파벳 (Alphabet)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "XLC",
        "cyclical": False,
        "description": "글로벌 검색 엔진 및 클라우드·AI 연구 선도 기업",
    },
    "아마존": {
        "ticker": "AMZN",
        "name": "아마존 (Amazon)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "XLY",
        "cyclical": False,
        "description": "글로벌 e커머스 및 AWS 클라우드 인프라 선도 기업",
    },
    "AMZN": {
        "ticker": "AMZN",
        "name": "아마존 (Amazon)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "XLY",
        "cyclical": False,
        "description": "글로벌 e커머스 및 AWS 클라우드 인프라 선도 기업",
    },
    "메타": {
        "ticker": "META",
        "name": "메타 (Meta Platforms)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "XLC",
        "cyclical": False,
        "description": "글로벌 소셜 플랫폼 및 오픈소스 AI(Llama) 선도 기업",
    },
    "META": {
        "ticker": "META",
        "name": "메타 (Meta Platforms)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "XLC",
        "cyclical": False,
        "description": "글로벌 소셜 플랫폼 및 오픈소스 AI(Llama) 선도 기업",
    },
    "AMD": {
        "ticker": "AMD",
        "name": "AMD (Advanced Micro Devices)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^NDX",
        "sector": "^SOX",
        "cyclical": True,
        "description": "글로벌 x86 CPU 및 데이터센터 AI 가속기(MI300) 기업",
    },
    "TSMC": {
        "ticker": "TSM",
        "name": "TSMC (TSM)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^SOX",
        "sector": "^SOX",
        "cyclical": True,
        "description": "글로벌 첨단 파운드리 독점 선도 기업",
    },
    "TSM": {
        "ticker": "TSM",
        "name": "TSMC (TSM)",
        "country": "US",
        "currency": "USD",
        "parent_index": "^SOX",
        "sector": "^SOX",
        "cyclical": True,
        "description": "글로벌 첨단 파운드리 독점 선도 기업",
    },
    # Additional Korean major stocks
    "현대차": {
        "ticker": "005380.KS",
        "name": "현대차 (Hyundai Motor)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLI",
        "cyclical": True,
        "description": "글로벌 완성차 및 친환경차·하이브리드 선도 기업",
    },
    "현대자동차": {
        "ticker": "005380.KS",
        "name": "현대차 (Hyundai Motor)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLI",
        "cyclical": True,
        "description": "글로벌 완성차 및 친환경차·하이브리드 선도 기업",
    },
    "005380.KS": {
        "ticker": "005380.KS",
        "name": "현대차 (Hyundai Motor)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLI",
        "cyclical": True,
        "description": "글로벌 완성차 및 친환경차·하이브리드 선도 기업",
    },
    "005380": {
        "ticker": "005380.KS",
        "name": "현대차 (Hyundai Motor)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLI",
        "cyclical": True,
        "description": "글로벌 완성차 및 친환경차·하이브리드 선도 기업",
    },
    "기아": {
        "ticker": "000270.KS",
        "name": "기아 (Kia)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLI",
        "cyclical": True,
        "description": "글로벌 고수익 SUV 및 EV 완성차 기업",
    },
    "000270.KS": {
        "ticker": "000270.KS",
        "name": "기아 (Kia)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLI",
        "cyclical": True,
        "description": "글로벌 고수익 SUV 및 EV 완성차 기업",
    },
    "000270": {
        "ticker": "000270.KS",
        "name": "기아 (Kia)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLI",
        "cyclical": True,
        "description": "글로벌 고수익 SUV 및 EV 완성차 기업",
    },
    "네이버": {
        "ticker": "035420.KS",
        "name": "NAVER (Naver)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLC",
        "cyclical": False,
        "description": "국내 1위 포털 검색 및 AI·커머스 플랫폼 기업",
    },
    "NAVER": {
        "ticker": "035420.KS",
        "name": "NAVER (Naver)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLC",
        "cyclical": False,
        "description": "국내 1위 포털 검색 및 AI·커머스 플랫폼 기업",
    },
    "035420.KS": {
        "ticker": "035420.KS",
        "name": "NAVER (Naver)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLC",
        "cyclical": False,
        "description": "국내 1위 포털 검색 및 AI·커머스 플랫폼 기업",
    },
    "035420": {
        "ticker": "035420.KS",
        "name": "NAVER (Naver)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLC",
        "cyclical": False,
        "description": "국내 1위 포털 검색 및 AI·커머스 플랫폼 기업",
    },
    "카카오": {
        "ticker": "035720.KS",
        "name": "카카오 (Kakao)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLC",
        "cyclical": False,
        "description": "국내 최대 모바일 메신저 및 콘텐츠 플랫폼 기업",
    },
    "035720.KS": {
        "ticker": "035720.KS",
        "name": "카카오 (Kakao)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLC",
        "cyclical": False,
        "description": "국내 최대 모바일 메신저 및 콘텐츠 플랫폼 기업",
    },
    "035720": {
        "ticker": "035720.KS",
        "name": "카카오 (Kakao)",
        "country": "KR",
        "currency": "KRW",
        "parent_index": "^KS11",
        "sector": "XLC",
        "cyclical": False,
        "description": "국내 최대 모바일 메신저 및 콘텐츠 플랫폼 기업",
    },
}


def resolve_target(
    market_query: str,
    custom_indices: Optional[List[str]] = None,
    custom_macro: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Classify user input into an institutional query profile and return resolved configurations.
    """
    q = (market_query or "").strip()
    q_lower = q.lower()
    q_norm = re.sub(r'[\s_\-]+', '', q_lower)

    # 1. Single Stock Check
    if q in KNOWN_STOCKS or q.upper() in KNOWN_STOCKS:
        stock_info = KNOWN_STOCKS.get(q) or KNOWN_STOCKS.get(q.upper())
        ticker = stock_info["ticker"]
        parent = stock_info["parent_index"]
        is_kr = stock_info["country"] == "KR"

        resolved_indices = custom_indices or (
            [ticker, "^KS11", "^KQ11", "^SOX", "^GSPC"] if is_kr else [ticker, "^NDX", "^GSPC", "^SOX"]
        )
        resolved_macro = custom_macro or (
            ["USDKRW=X", "^VIX", "^TNX", "^IRX", "DX-Y.NYB", "CL=F", "GC=F", "HYG", "LQD"] if is_kr else
            ["^VIX", "^TNX", "^IRX", "DX-Y.NYB", "CL=F", "GC=F", "HYG", "LQD"]
        )

        return {
            "profile": PROFILE_SINGLE_STOCK,
            "target_query": q,
            "primary_ticker": ticker,
            "primary_name": stock_info["name"],
            "parent_index": parent,
            "indices": resolved_indices,
            "macro": resolved_macro,
            "is_single_stock": True,
            "is_korean": is_kr,
            "stock_info": stock_info,
            "theme_default": f"{stock_info['name']} 탑다운 매크로 민감도 및 기술적 지지선 진단",
        }

    # Check generic ticker patterns (e.g. 6-digit KRX stock)
    if re.match(r'^\d{6}\.(KS|KQ)$', q, re.IGNORECASE) or (re.match(r'^\d{6}$', q) and not q.startswith("^")):
        ticker = q.upper() if "." in q else f"{q}.KS"
        is_kr = True
        stock_info = {
            "ticker": ticker,
            "name": f"국내 상장사 ({ticker})",
            "country": "KR",
            "currency": "KRW",
            "parent_index": "^KS11",
            "sector": "XLI",
            "cyclical": False,
            "description": "국내 증권시장 상장 기업",
        }
        return {
            "profile": PROFILE_SINGLE_STOCK,
            "target_query": q,
            "primary_ticker": ticker,
            "primary_name": stock_info["name"],
            "parent_index": "^KS11",
            "indices": custom_indices or [ticker, "^KS11", "^KQ11", "^SOX", "^GSPC"],
            "macro": custom_macro or ["USDKRW=X", "^VIX", "^TNX", "^IRX", "DX-Y.NYB", "CL=F", "GC=F", "HYG", "LQD"],
            "is_single_stock": True,
            "is_korean": is_kr,
            "stock_info": stock_info,
            "theme_default": f"{ticker} 탑다운 매크로 환경 및 지지선 진단",
        }

    # 2. Korean Index (코스피 / 코스닥)
    if any(k in q_norm for k in ["코스피", "kospi", "ks11", "^ks11"]):
        return {
            "profile": PROFILE_KR_INDEX,
            "target_query": q,
            "primary_ticker": "^KS11",
            "primary_name": "코스피 (KOSPI)",
            "parent_index": "^KS11",
            "indices": custom_indices or ["^KS11", "^KQ11", "^GSPC", "^SOX"],
            "macro": custom_macro or ["USDKRW=X", "^VIX", "^TNX", "^IRX", "DX-Y.NYB", "CL=F", "GC=F", "HYG", "LQD"],
            "is_single_stock": False,
            "is_korean": True,
            "stock_info": None,
            "theme_default": "코스피 탑다운 국면 및 환율·200일선 진단",
        }

    # 3. Korean Market (한국증시 / 국내증시 / 국장)
    if any(k in q_norm for k in ["한국증시", "국내증시", "한국시장", "국장", "koreanmarket", "koreastock"]):
        return {
            "profile": PROFILE_KR_MARKET,
            "target_query": q,
            "primary_ticker": "^KS11",
            "primary_name": "한국 증시 (KOSPI / KOSDAQ)",
            "parent_index": "^KS11",
            "indices": custom_indices or ["^KS11", "^KQ11", "^GSPC", "^SOX"],
            "macro": custom_macro or ["USDKRW=X", "^VIX", "^TNX", "^IRX", "DX-Y.NYB", "CL=F", "GC=F", "HYG", "LQD"],
            "is_single_stock": False,
            "is_korean": True,
            "stock_info": None,
            "theme_default": "한국 시장 매크로 국면 및 외국인 수급·환율 진단",
        }

    # 4. Semiconductor Sector (반도체 / 반도체섹터 / SOX / SMH)
    if any(k in q_norm for k in ["반도체", "semi", "sox", "^sox", "smh"]):
        return {
            "profile": PROFILE_SECTOR_SEMI,
            "target_query": q,
            "primary_ticker": "^SOX",
            "primary_name": "필라델피아 반도체 (^SOX)",
            "parent_index": "^GSPC",
            "indices": custom_indices or ["^SOX", "SMH", "^NDX", "^GSPC", "005930.KS", "000660.KS", "NVDA"],
            "macro": custom_macro or ["^VIX", "^TNX", "^IRX", "DX-Y.NYB", "CL=F", "GC=F", "HYG", "LQD"],
            "is_single_stock": False,
            "is_korean": False,
            "stock_info": None,
            "theme_default": "글로벌 반도체 사이클 및 필라델피아 반도체 지수 진단",
        }

    # 5. Tech Stocks (기술주식 / 기술주 / 빅테크 / Tech)
    if any(k in q_norm for k in ["기술주식", "기술주", "빅테크", "tech", "technology", "나스닥100"]):
        return {
            "profile": PROFILE_SECTOR_TECH,
            "target_query": q,
            "primary_ticker": "^NDX",
            "primary_name": "나스닥 100 (^NDX)",
            "parent_index": "^NDX",
            "indices": custom_indices or ["^NDX", "XLK", "^SOX", "^GSPC"],
            "macro": custom_macro or ["^VIX", "^TNX", "^IRX", "DX-Y.NYB", "CL=F", "GC=F", "HYG", "LQD"],
            "is_single_stock": False,
            "is_korean": False,
            "stock_info": None,
            "theme_default": "빅테크 밸류에이션 압축 및 나스닥 100 국면 진단",
        }

    # 6. Generic US Stock Ticker Check (e.g. INTC, PLTR, AVGO, COIN, CRM)
    if re.match(r'^[A-Za-z]{1,5}$', q) and q.upper() not in ["US", "SPX", "GSPC", "MARKET", "INDEX", "ALL", "GLOBAL", "DJI", "NDX", "RUT", "SOX", "SMH", "TECH", "SEMI", "KR", "KOSPI", "KOSDAQ"]:
        ticker = q.upper()
        parent = "^NDX" if ticker in ("QQQ", "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA", "AMD", "AVGO", "COST", "NFLX", "PLTR", "CRM", "INTC") else "^GSPC"
        stock_info = {
            "ticker": ticker,
            "name": f"미국 상장사 ({ticker})",
            "country": "US",
            "currency": "USD",
            "parent_index": parent,
            "sector": "XLK",
            "cyclical": False,
            "description": f"미국 증권시장 상장 기업 ({ticker})",
        }
        return {
            "profile": PROFILE_SINGLE_STOCK,
            "target_query": q,
            "primary_ticker": ticker,
            "primary_name": stock_info["name"],
            "parent_index": parent,
            "indices": custom_indices or [ticker, parent, "^GSPC", "^SOX"],
            "macro": custom_macro or ["^VIX", "^TNX", "^IRX", "DX-Y.NYB", "CL=F", "GC=F", "HYG", "LQD"],
            "is_single_stock": True,
            "is_korean": False,
            "stock_info": stock_info,
            "theme_default": f"{ticker} 탑다운 매크로 환경 및 지지선 진단",
        }

    # 7. Default: US Market (미국증시 / 미국지수 / US Market)
    return {
        "profile": PROFILE_US_MARKET,
        "target_query": q or "미국증시",
        "primary_ticker": "^GSPC",
        "primary_name": "S&P 500 (^GSPC)",
        "parent_index": "^GSPC",
        "indices": custom_indices or ["^GSPC", "^NDX", "^DJI", "^RUT", "^SOX"],
        "macro": custom_macro or ["^VIX", "^TNX", "^IRX", "DX-Y.NYB", "CL=F", "GC=F", "HYG", "LQD"],
        "is_single_stock": False,
        "is_korean": False,
        "stock_info": None,
        "theme_default": "미국 주요 지수 및 탑다운 거시 국면 진단",
    }
