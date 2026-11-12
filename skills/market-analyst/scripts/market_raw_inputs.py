"""
Raw inputs serialization and management for market-analyst snapshots.
"""

import datetime
import json
import math
from typing import Any, Dict, List, Optional
import pandas as pd


def _plain(v):
    """A JSON-safe cell: NaN/NaT -> None, inf -> 'Infinity', timestamps -> ISO text."""
    if v is None or v is pd.NaT:
        return None
    if isinstance(v, (pd.Timestamp, datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return str(v)
    return v


def frame_to_dict(df: pd.DataFrame) -> Dict[str, Any]:
    """Serialize a pandas DataFrame into a structured dictionary preserving index and columns."""
    if df is None or df.empty:
        return {"index": [], "columns": [], "dtypes": {}, "data": []}

    idx = [_plain(i) for i in df.index]
    cols = [str(c) for c in df.columns]
    dtypes = {str(c): str(t) for c, t in df.dtypes.items()}
    data = [[_plain(val) for val in row] for row in df.itertuples(index=False)]

    return {
        "index": idx,
        "columns": cols,
        "dtypes": dtypes,
        "data": data,
    }


def dict_to_frame(d: Dict[str, Any]) -> pd.DataFrame:
    """Deserialize a structured dictionary back to a pandas DataFrame."""
    if not d or not d.get("columns"):
        return pd.DataFrame()

    df = pd.DataFrame(data=d.get("data", []), columns=d.get("columns", []))
    idx = d.get("index")
    if idx:
        try:
            df.index = pd.to_datetime(idx)
        except Exception:
            df.index = pd.Index(idx)

    for col, dt in (d.get("dtypes") or {}).items():
        if col in df.columns:
            try:
                df[col] = df[col].astype(dt)
            except Exception:
                pass
    return df


def make_item(
    source: str,
    fetched_at: str,
    status: str,
    kind: str = "json",
    data: Any = None,
    error: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a raw input item."""
    item: Dict[str, Any] = {
        "source": source,
        "fetched_at": fetched_at,
        "status": status,
        "kind": kind,
    }
    if kind == "frame" and isinstance(data, pd.DataFrame):
        item["data"] = frame_to_dict(data)
    elif data is not None:
        item["data"] = data
    if error:
        item["error"] = error
    if note:
        item["note"] = note
    return item
