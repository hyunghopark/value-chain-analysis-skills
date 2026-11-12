"""
Data snapshot module for market-analyst reports.
Rules: skills/market-analyst/references/rules/data-snapshot.md
"""

import datetime
import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Union

BASES = {
    'index_close',
    'quote',
    'moving_average',
    'drawdown',
    'support_check',
    'relative_strength',
    'spread',
    'macro_indicator',
    'regime_matrix',
    'socratic_rule',
    'derived',
}

STATUSES = {
    'final',
    'provisional',
    'estimated',
    'corrected',
}

FORMAT_VERSION = 2
MARKET_HEADER = "## 4. 📊 정량 지표 데이터 분석 결과 (스크립트 자동 산출)"


def current_versions() -> Dict[str, Optional[str]]:
    import platform
    from importlib import metadata
    out: Dict[str, Optional[str]] = {'python': platform.python_version(), 'skill': '1.0.0'}
    for pkg in ('yfinance', 'pandas', 'numpy'):
        try:
            out[pkg] = metadata.version(pkg)
        except Exception:
            out[pkg] = None
    return out


class MarketSnapshot:
    """Manages collection and serialization of market analysis report data snapshots."""

    def __init__(self):
        self.values: Dict[str, Dict[str, Any]] = {}
        self.series_data: Dict[str, Dict[str, Any]] = {}
        self.warnings: List[Dict[str, Any]] = []

    def record(
        self,
        path: str,
        value: Any,
        *,
        source: str,
        basis: str,
        as_of: Optional[str] = None,
        status: str = 'final',
        note: Optional[str] = None,
        ki: Optional[str] = None,
        original: Any = None,
        inputs: Optional[List[str]] = None,
    ) -> None:
        """Record a single data point with traceability metadata."""
        if basis not in BASES:
            raise ValueError(f"Invalid basis '{basis}'. Must be one of: {sorted(BASES)}")

        if status not in STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {sorted(STATUSES)}")

        record_item: Dict[str, Any] = {
            "value": value,
            "source": source,
            "basis": basis,
            "as_of": as_of,
            "status": status,
        }
        if note:
            record_item["note"] = note
        if ki:
            record_item["ki"] = ki
        if original is not None:
            record_item["original"] = original
        if inputs:
            record_item["inputs"] = inputs

        self.values[path] = record_item

    def record_series(
        self,
        path: str,
        series_dict: Dict[str, Any],
        *,
        source: str,
        basis: str,
        status: str = 'final',
        unit: Optional[str] = None,
    ) -> None:
        """Record a historical time series."""
        if basis not in BASES:
            raise ValueError(f"Invalid basis '{basis}'. Must be one of: {sorted(BASES)}")
        if status not in STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {sorted(STATUSES)}")

        item: Dict[str, Any] = {
            "source": source,
            "basis": basis,
            "status": status,
            "data": series_dict,
        }
        if unit:
            item["unit"] = unit
        self.series_data[path] = item

    def add_warning(
        self,
        code: str,
        message: str,
        *,
        severity: str = "warning",
        ticker: Optional[str] = None,
        source: Optional[str] = None,
    ) -> None:
        """Record a data quality warning."""
        warn: Dict[str, Any] = {
            "code": code,
            "message": message,
            "severity": severity,
        }
        if ticker:
            warn["ticker"] = ticker
        if source:
            warn["source"] = source
        self.warnings.append(warn)

    def to_dict(
        self,
        meta_args: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        generated_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert snapshot to formatted dictionary."""
        kst = datetime.timezone(datetime.timedelta(hours=9))
        now_str = generated_at or datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M KST")

        out: Dict[str, Any] = {
            "meta": {
                "format_version": FORMAT_VERSION,
                "generated_at": now_str,
                "args": meta_args or {},
                "versions": current_versions(),
            },
            "values": self.values,
            "series": self.series_data,
            "warnings": self.warnings,
        }
        if inputs is not None:
            out["inputs"] = inputs
        return out

    def save(
        self,
        filepath: str,
        meta_args: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        generated_at: Optional[str] = None,
    ) -> None:
        """Save snapshot to a JSON file."""
        data = self.to_dict(meta_args=meta_args, inputs=inputs, generated_at=generated_at)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def section4_body(text: str) -> str:
    """Extract Section 4 body text from report text or raw script output."""
    t = text.strip()
    if t.startswith(MARKET_HEADER):
        t = t[len(MARKET_HEADER):].strip()
    else:
        idx = t.find(MARKET_HEADER)
        if idx != -1:
            t = t[idx + len(MARKET_HEADER):].strip()
        else:
            m = re.search(r'^## 4\..*$', t, re.MULTILINE)
            if m:
                t = t[m.end():].strip()

    next_s = re.search(r'\n## [0-9]', t)
    if next_s:
        t = t[:next_s.start()]
    t = re.sub(r'\n+---+\s*$', '', t)
    return t.strip()


def attach_section4(report_text: str, snapshot_path: str, attached_at: Optional[str] = None) -> bool:
    """Read Section 4 from report text and attach section4 block to snapshot JSON."""
    if not os.path.isfile(snapshot_path):
        return False
    body = section4_body(report_text)
    if not body:
        return False
    sha = hashlib.sha256(body.encode('utf-8')).hexdigest()
    kst = datetime.timezone(datetime.timedelta(hours=9))
    now_str = attached_at or datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M KST")

    try:
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['section4'] = {
            'text': body,
            'sha256': sha,
            'attached_at': now_str,
        }
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
