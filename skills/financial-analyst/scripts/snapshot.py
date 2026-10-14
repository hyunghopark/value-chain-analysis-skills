"""
Data snapshot module for value-chain-analysis reports.
Spec: specs/001-data-snapshot/
Rules: skills/financial-analyst/references/rules/data-snapshot.md
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Union

BASES = {
    'krx_regular_close',
    'flow_feed_price',
    'yahoo_close',
    'index_close',
    'quote',
    'statement',
    'consensus',
    'derived',
}

STATUSES = {
    'final',
    'provisional',
    'estimated',
    'corrected',
}

_UNSET = object()
_KI_PATTERN = re.compile(r'\[(KI-\d+)\]')


class Snapshot:
    """Manages collection and serialization of financial report data snapshot."""

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
        original: Any = _UNSET,
        inputs: Optional[List[str]] = None,
    ) -> None:
        """Record a single data point with traceability metadata."""
        if basis not in BASES:
            raise ValueError(f"Invalid basis '{basis}'. Must be one of: {sorted(BASES)}")

        if status not in STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {sorted(STATUSES)}")

        if status == 'corrected':
            if ki is None:
                raise ValueError(f"Field 'ki' is required when status is 'corrected' (path: {path})")
            if original is _UNSET:
                raise ValueError(f"Field 'original' is required when status is 'corrected' (path: {path})")

        record_item: Dict[str, Any] = {
            "value": value,
            "source": source,
            "basis": basis,
            "as_of": as_of,
            "status": status,
        }

        if note is not None:
            record_item["note"] = note
        if ki is not None:
            record_item["ki"] = ki
        if original is not _UNSET:
            record_item["original"] = original
        if inputs is not None:
            record_item["inputs"] = inputs

        self.values[path] = record_item

    def series(
        self,
        path: str,
        data: Union[Dict[str, Any], Any],
        *,
        source: str,
        basis: str,
        limit: int = 260,
    ) -> None:
        """Record time-series data (e.g. daily close, volume) limited to latest N days."""
        if basis not in BASES:
            raise ValueError(f"Invalid basis '{basis}'. Must be one of: {sorted(BASES)}")

        # Convert to dict if pandas Series or similar
        if hasattr(data, 'to_dict'):
            raw_dict = data.to_dict()
        elif isinstance(data, dict):
            raw_dict = data
        else:
            raise TypeError("Series data must be a dict or pandas Series-like object")

        # Sort dates ascending and take last `limit`
        sorted_keys = sorted(str(k) for k in raw_dict.keys())
        if limit > 0 and len(sorted_keys) > limit:
            selected_keys = sorted_keys[-limit:]
        else:
            selected_keys = sorted_keys

        trimmed_data = {k: raw_dict[k] for k in selected_keys}

        self.series_data[path] = {
            "source": source,
            "basis": basis,
            "data": trimmed_data,
        }

    def warning(self, msg: str) -> None:
        """Record a data quality warning, parsing [KI-xxx] tag if present."""
        clean_msg = msg.strip()
        # Remove leading '[Warn] ' if present
        if clean_msg.startswith('[Warn] '):
            clean_msg = clean_msg[len('[Warn] '):].strip()

        match = _KI_PATTERN.search(clean_msg)
        ki_id = match.group(1) if match else None

        self.warnings.append({
            "ki": ki_id,
            "msg": clean_msg,
        })

    def to_dict(self, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return snapshot representation as a dictionary."""
        return {
            "meta": meta or {},
            "values": self.values,
            "series": self.series_data,
            "warnings": self.warnings,
        }

    def dump(self, file_path: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Serialize snapshot to JSON file. Raises Exception on I/O error."""
        parent_dir = os.path.dirname(os.path.abspath(file_path))
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        payload = self.to_dict(meta=meta)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
