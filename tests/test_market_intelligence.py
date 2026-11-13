"""
Unit tests for market-intelligence skill and dynamic event gatekeeper.
Tests zero-dictionary anomaly detection, 2-stage multi-hop query generation,
severity taxonomy (Level 1~5), conditional silence, and WATCH downgrade.
"""

import json
import os
import sys
import tempfile
import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MI_SCRIPTS = os.path.join(os.path.dirname(CURRENT_DIR), "skills", "market-intelligence", "scripts")
FA_SCRIPTS = os.path.join(os.path.dirname(CURRENT_DIR), "skills", "financial-analyst", "scripts")

for p in (MI_SCRIPTS, FA_SCRIPTS):
    if p not in sys.path:
        sys.path.insert(0, p)

import intelligence_collector as ic
import render_intelligence as ri
import economic_auditor as ea


# Mock headlines for testing
MOCK_NVDA_HEADLINES = [
    {"title": "Exclusive | Nvidia Is Preparing to Oust CEO Jensen Huang", "link": "https://wsj.com/1", "pubDate": "Wed, 12 Nov 2026 04:00:00 GMT"},
    {"title": "Nvidia board meeting to decide CEO Jensen Huang's fate stretches into evening", "link": "https://wsj.com/2", "pubDate": "Wed, 12 Nov 2026 05:00:00 GMT"},
    {"title": "Statement From NVIDIA Board of Directors: Independent Investigation by Wachtell", "link": "https://reuters.com/3", "pubDate": "Wed, 12 Nov 2026 06:00:00 GMT"},
    {"title": "House Committee issues subpoena over Alice Huang Chinese MSS allegations", "link": "https://nyt.com/4", "pubDate": "Wed, 12 Nov 2026 07:00:00 GMT"},
    {"title": "Nvidia CEO Jensen Huang admits second affair with VP Kimberly Powell", "link": "https://nyt.com/5", "pubDate": "Wed, 12 Nov 2026 08:00:00 GMT"},
]

MOCK_BENIGN_HEADLINES = [
    {"title": "Apple reports solid Q4 earnings beat driven by iPhone 18 sales", "link": "https://cnbc.com/1", "pubDate": "Wed, 12 Nov 2026 04:00:00 GMT"},
    {"title": "Apple introduces new M5 MacBook Pro with enhanced AI performance", "link": "https://theverge.com/2", "pubDate": "Wed, 12 Nov 2026 05:00:00 GMT"},
    {"title": "Analysts maintain Outperform rating on Apple ahead of holiday quarter", "link": "https://bloomberg.com/3", "pubDate": "Wed, 12 Nov 2026 06:00:00 GMT"},
]


def test_anomaly_spike_detection_nvda():
    """Verify that zero-dictionary token spike detection isolates ouster, affair, and CEO from NVDA headlines."""
    counts, crisis_hits = ic.extract_token_spikes(MOCK_NVDA_HEADLINES, "NVDA")
    
    # Must extract proper nouns & crisis verbs
    assert "Jensen" in counts or "Huang" in counts or "CEO" in counts
    assert len(crisis_hits) > 0
    
    crisis_terms = [h[0] for h in crisis_hits]
    assert any(t in crisis_terms for t in ["oust", "affair", "subpoena", "wachtell", "spy", "investigation"])


def test_severity_taxonomy_levels():
    """Verify severity classifier maps crisis terms to Level 5 and benign terms to Level 1."""
    # Test Level 5: Oust + affair + subpoena
    _, crisis_hits_nvda = ic.extract_token_spikes(MOCK_NVDA_HEADLINES, "NVDA")
    sev_nvda, primary_nvda, desc_nvda = ic.classify_severity(crisis_hits_nvda, len(MOCK_NVDA_HEADLINES))
    assert sev_nvda == 5
    assert "경영권 분쟁" in primary_nvda or "거버넌스" in primary_nvda or "사법" in primary_nvda

    # Test Level 1: Benign
    _, crisis_hits_benign = ic.extract_token_spikes(MOCK_BENIGN_HEADLINES, "AAPL")
    sev_benign, primary_benign, _ = ic.classify_severity(crisis_hits_benign, len(MOCK_BENIGN_HEADLINES))
    assert sev_benign == 1
    assert "정상" in primary_benign


def test_conditional_silence_rendering():
    """Verify that Level 1/2 returns empty string (conditional silence), while Level 5 renders alert box."""
    # Level 1 payload
    benign_payload = {
        "severity": {"level": 1, "is_crisis": False, "primary_crisis": "정상"},
        "evidence_headlines": ["Apple reports solid Q4"],
    }
    rendered_benign = ri.render_crisis_alert_box(benign_payload)
    assert rendered_benign == "", "Level 1 must remain 100% silent (no dead tables)"

    # Level 5 payload
    crisis_payload = {
        "severity": {
            "level": 5,
            "is_crisis": True,
            "primary_crisis": "경영권 분쟁 및 이사회 해임",
            "description": "최고경영자 거버넌스 붕괴 및 이사회 해임 논의",
        },
        "evidence_headlines": [
            "Exclusive | Nvidia Is Preparing to Oust CEO Jensen Huang",
            "Nvidia CEO admits second affair",
        ],
    }
    rendered_crisis = ri.render_crisis_alert_box(
        crisis_payload,
        peer_divergence_text="피어 AMD(+13.1%) 대비 -16.1%p 단독 폭락",
        multiple_c_floor_price=84.25,
        multiple_c_downside_pct=-0.515,
        drop_from_high_pct=28.6,
        currency="$"
    )
    assert "🚨 **[특수 이벤트 긴급 경보: Level 5" in rendered_crisis
    assert "Multiple C 결합 바닥가 = `$84.25`" in rendered_crisis
    assert "피어 AMD(+13.1%) 대비 -16.1%p 단독 폭락" in rendered_crisis
    assert "신규 매수 전면 동결(WATCH)" in rendered_crisis


def test_event_gatekeeper_downgrade():
    """Verify that apply_event_gatekeeper automatically downgrades 🟢 to 🟡 WATCH under Level 5 crisis."""
    preliminary_verdict = "🟢 **매수 고려**"

    # Under benign condition: no downgrade
    benign_intel = {"severity": {"level": 1, "is_crisis": False}}
    v_out, reason = ea.apply_event_gatekeeper(preliminary_verdict, benign_intel)
    assert v_out == preliminary_verdict
    assert reason is None

    # Under Level 5 crisis: must downgrade to 🟡 WATCH
    crisis_intel = {
        "severity": {
            "level": 5,
            "is_crisis": True,
            "primary_crisis": "CEO 사내 불륜 폭로 및 이사회 해임 논의",
        }
    }
    v_out, reason = ea.apply_event_gatekeeper(preliminary_verdict, crisis_intel)
    assert "🟡" in v_out
    assert "WATCH" in v_out
    assert "🚨 거버넌스 긴급 경보" in v_out
    assert reason == "CEO 사내 불륜 폭로 및 이사회 해임 논의"


def test_intelligence_snapshot_spec003(monkeypatch):
    """Verify that intelligence payload serializes and deserializes deterministically without loss."""
    with tempfile.TemporaryDirectory() as tmpdir:
        snap_path = os.path.join(tmpdir, "NVDA_intelligence.json")

        # Mock RSS fetch with static fixture
        monkeypatch.setattr(ic, "fetch_google_news_rss", lambda query, max_items=30: MOCK_NVDA_HEADLINES)

        data = ic.run_intelligence_collection("NVDA", output_path=snap_path)
        assert os.path.isfile(snap_path)

        with open(snap_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["meta"]["ticker"] == "NVDA"
        assert loaded["severity"]["level"] == 5
        assert loaded["severity"]["is_crisis"] is True
        assert len(loaded["evidence_headlines"]) > 0
        assert "Exclusive | Nvidia Is Preparing to Oust CEO Jensen Huang" in loaded["evidence_headlines"][0]


def test_official_disclosures_verification(monkeypatch):
    """Verify official disclosure check classifies unfiled 8-K as PENDING and filed 8-K as FILED."""
    # Test Level 1/2: returns None
    assert ic.fetch_official_disclosures("NVDA", 1) is None

    import mcp_client

    # Case 1: Unfiled (pending) 8-K (no recent 5.02 item)
    monkeypatch.setattr(
        mcp_client,
        "call_mcp",
        lambda server, tool, args: {
            "rows": [
                {"form": "8-K", "filing_date": "2026-10-15", "items": "8.01"}
            ]
        },
    )
    res_pending = ic.fetch_official_disclosures("NVDA", 5)
    assert res_pending is not None
    assert res_pending["authority"] == "SEC EDGAR"
    assert res_pending["status"] == "PENDING_OR_NOT_FILED"
    assert res_pending["governance_item_filed"] is False
    assert "8-K" in res_pending["status_label"]

    # Case 2: Filed 8-K with Item 5.02 within 14 days
    now_str = ic.datetime.datetime.now(ic.KST).strftime("%Y-%m-%d")
    monkeypatch.setattr(
        mcp_client,
        "call_mcp",
        lambda server, tool, args: {
            "rows": [
                {"form": "8-K", "filing_date": now_str, "items": "5.02,9.01"}
            ]
        },
    )
    res_filed = ic.fetch_official_disclosures("NVDA", 5)
    assert res_filed is not None
    assert res_filed["status"] == "FILED"
    assert res_filed["governance_item_filed"] is True
    assert "Item 5.02" in res_filed["status_label"]
