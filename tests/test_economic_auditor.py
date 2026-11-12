"""
Unit tests for economic_auditor.py:
Verifies EVA Spread, Implied ERP, Total Shareholder Yield, Cash Conversion,
Gatekeeper 1-Step Downgrade, and Joint De-rating calculations.
"""

import sys
import os
import pytest
import pandas as pd
import numpy as np

# Add scripts directory to path
script_dir = os.path.join(os.path.dirname(__file__), '..', 'skills', 'financial-analyst', 'scripts')
sys.path.insert(0, os.path.abspath(script_dir))

import economic_auditor as ea


def test_compute_eva_roic_wacc():
    # Healthy company: EBIT 50, Invested Capital 200 -> NOPAT = 50 * (1 - 0.22) = 39 -> ROIC = 19.5%
    # ke = 4.5 + 1.0 * 5.5 = 10.0%, Debt = 0 -> WACC = 10.0% -> EVA = +9.5%p (🟢)
    inc_df = pd.DataFrame({'2025-12-31': [50.0, 0.22]}, index=['EBIT', 'Tax Rate For Calcs'])
    bs_df = pd.DataFrame({'2025-12-31': [200.0]}, index=['Invested Capital'])
    info = {'marketCap': 500.0, 'totalDebt': 0.0, 'beta': 1.0}

    res = ea.compute_eva_roic_wacc(info, bs_df, inc_df, rf_rate=4.5)
    assert res['roic'] == 19.5
    assert res['wacc'] == 10.0
    assert res['eva_spread'] == 9.5
    assert res['signal'] == '🟢'

    # Value destroyer: EBIT 5, Invested Capital 200 -> NOPAT = 3.9 -> ROIC = 1.95% -> WACC = 10% -> EVA = -8.05%p (🔴)
    inc_bad = pd.DataFrame({'2025-12-31': [5.0, 0.22]}, index=['EBIT', 'Tax Rate For Calcs'])
    res_bad = ea.compute_eva_roic_wacc(info, bs_df, inc_bad, rf_rate=4.5)
    assert res_bad['eva_spread'] < 0
    assert res_bad['signal'] == '🔴'


def test_compute_implied_erp():
    # Forward PE 10x -> Earnings Yield 10.0% - Rf 4.5% = +5.5%p (🟢)
    res_good = ea.compute_implied_erp(10.0, rf_rate=4.5)
    assert res_good['earnings_yield'] == 10.0
    assert res_good['implied_erp'] == 5.5
    assert res_good['signal'] == '🟢'

    # Forward PE 40x -> Earnings Yield 2.5% - Rf 4.5% = -2.0%p (🔴)
    res_bad = ea.compute_implied_erp(40.0, rf_rate=4.5)
    assert res_bad['earnings_yield'] == 2.5
    assert res_bad['implied_erp'] == -2.0
    assert res_bad['signal'] == '🔴'


def test_compute_total_shareholder_yield():
    # Div 2.0% + Shares decreased 2.0% (buyback) -> TSY 4.0% (🟢)
    info = {'dividendYield': 2.0}
    bs_df = pd.DataFrame({
        '2025-12-31': [980.0],
        '2024-12-31': [1000.0]
    }, index=['Share Issued'])
    res = ea.compute_total_shareholder_yield(info, bs_df)
    assert res['dividend_yield'] == 2.0
    assert res['buyback_yield'] == 2.0
    assert res['total_shareholder_yield'] == 4.0
    assert res['signal'] == '🟢'

    # Div 0.5% + Shares increased 5.0% (dilution) -> TSY -4.5% (🔴)
    bs_diluted = pd.DataFrame({
        '2025-12-31': [1050.0],
        '2024-12-31': [1000.0]
    }, index=['Share Issued'])
    res_diluted = ea.compute_total_shareholder_yield({'dividendYield': 0.5}, bs_diluted)
    assert res_diluted['buyback_yield'] == -5.0
    assert res_diluted['total_shareholder_yield'] == -4.5
    assert res_diluted['signal'] == '🔴'


def test_compute_cash_conversion():
    # OCF 150, NI 100 -> CCR 1.5 (🟢)
    res_good = ea.compute_cash_conversion({'operatingCashflow': 150.0, 'netIncomeToCommon': 100.0})
    assert res_good['ccr'] == 1.5
    assert res_good['signal'] == '🟢'

    # OCF 50, NI 100 -> CCR 0.5 (🔴)
    res_bad = ea.compute_cash_conversion({'operatingCashflow': 50.0, 'netIncomeToCommon': 100.0})
    assert res_bad['ccr'] == 0.5
    assert res_bad['signal'] == '🔴'


def test_gatekeeper_1step_downgrade():
    audit_breached = {
        'gatekeeper_breached': True,
        'breach_summary': '자본 파괴 (EVA -3.50%p)',
    }
    audit_clean = {
        'gatekeeper_breached': False,
        'breach_summary': None,
    }

    # Case 1: 🟢 강력 매수 후보 + breached -> downgraded to 🟡 중립/관망 (⚠️ 밸류 트랩 경보)
    v1, r1 = ea.apply_gatekeeper_to_verdict("🟢 강력 매수 후보", audit_breached)
    assert "🟡 **중립/관망 (⚠️ 밸류 트랩 경보: 자본 파괴" in v1
    assert r1 is not None

    # Case 2: 🟢 강력 매수 후보 + clean -> remains 🟢
    v2, r2 = ea.apply_gatekeeper_to_verdict("🟢 강력 매수 후보", audit_clean)
    assert v2 == "🟢 강력 매수 후보"
    assert r2 is None

    # Case 3: 🔴 신중 접근 -> remains 🔴
    v3, r3 = ea.apply_gatekeeper_to_verdict("🔴 신중 접근 (주의 신호 2개 이상)", audit_breached)
    assert "🔴 신중 접근" in v3


def test_compute_joint_derating_floor():
    # Cyclical: current_bps 100,000, pb_min 0.8 -> Floor = 80,000
    f_cyc = ea.compute_joint_derating_floor(
        bear_eps=5000,
        current_bps=100000,
        pb_band={'min': 0.8},
        forward_pe=5.0,
        profile_type="CYCLICAL",
    )
    assert f_cyc == 80000.0

    # General: bear_eps 10, forward_pe 20.0 -> derated_pe = max(6.0, 20.0*0.55) = 11.0 -> Floor = 110.0
    f_gen = ea.compute_joint_derating_floor(
        bear_eps=10.0,
        current_bps=50.0,
        pb_band=None,
        forward_pe=20.0,
        profile_type="GENERAL",
    )
    assert f_gen == 110.0


def test_render_economic_audit_table_and_snap():
    recorded = {}

    def mock_snap(path, val):
        recorded[path] = val

    sample_results = {
        'TEST.KS': {
            'info': {'forwardPE': 12.0},
            '_economic_audit': {
                'eva': {'roic': 15.0, 'wacc': 8.0, 'eva_spread': 7.0, 'signal': '🟢'},
                'erp': {'implied_erp': 3.8, 'signal': '🟢'},
                'tsy': {'total_shareholder_yield': 4.5, 'signal': '🟢'},
                'ccr': {'ccr': 1.25, 'signal': '🟢'},
                'overall_status': '🟢 통과 (강력한 경제적 해자)',
                'gatekeeper_breached': False,
            }
        }
    }

    table_md = ea.render_economic_audit_table(sample_results, mock_snap)
    assert "### 5." in table_md or "### 6-1." in table_md
    assert "[경제학 감사] Moat & 밸류 트랩 필터" in table_md
    assert "TEST.KS" in table_md
    assert "15.0%" in table_md
    assert "8.0%" in table_md
    assert "+7.0%p 🟢" in table_md
    assert "+3.8%p 🟢" in table_md
    assert "+4.5% 🟢" in table_md
    assert "1.25 🟢" in table_md
    assert "TEST.KS.economic_audit.roic" in recorded
    assert recorded["TEST.KS.economic_audit.roic"] == 15.0
    assert recorded["TEST.KS.economic_audit.eva_spread"] == 7.0


def test_compute_cash_conversion_cycle():
    info = {
        'grossMargins': 0.425,
        'totalRevenue': 1000.0,
        'costOfRevenue': 600.0,
    }
    bs = pd.DataFrame({
        '2025-12-31': [100.0, 80.0, 50.0],
    }, index=['Inventory', 'Receivables', 'Payables'])
    inc = pd.DataFrame({
        '2025-12-31': [1000.0, 600.0],
    }, index=['Total Revenue', 'Cost Of Revenue'])

    res = ea.compute_cash_conversion_cycle(info, bs, inc)
    assert res['gpm'] == 42.5
    assert res['dio'] is not None
    assert res['dso'] is not None
    assert res['dpo'] is not None
    assert res['ccc'] is not None
    # DIO = 100 / 600 * 365 = 60.83
    # DSO = 80 / 1000 * 365 = 29.2
    # DPO = 50 / 600 * 365 = 30.42
    # CCC = 60.83 + 29.2 - 30.42 = 59.61
    assert abs(res['dio'] - 60.83) < 0.1
    assert abs(res['dso'] - 29.2) < 0.1
    assert abs(res['dpo'] - 30.42) < 0.1
    assert abs(res['ccc'] - 59.61) < 0.1

