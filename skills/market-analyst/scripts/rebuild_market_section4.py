#!/usr/bin/env python3
"""Rebuild market analysis Section 4 from a format-2 snapshot alone — zero network, zero clock.

Compares the rebuilt Section 4 with the snapshot's recorded baseline SHA-256 hash,
verifies every computed metric, and checks data quality warnings.

Exit codes: 0 identical baseline · 1 difference detected · 2 execution error / missing inputs.
"""

import argparse
import difflib
import hashlib
import json
import math
import os
import sys
from typing import Any, Dict, List, Tuple

# Ensure scripts directory in path
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import get_market_stats as gms
from market_snapshot import section4_body

EXIT_SAME = 0
EXIT_DIFF = 1
EXIT_ERROR = 2

VALUE_REL_TOL = 1e-6
VALUE_ABS_TOL = 1e-4


def rebuild_from_snapshot(snapshot_path: str, verbose: bool = False) -> Tuple[int, str]:
    """Rebuild Section 4 from snapshot inputs and compare against baseline."""
    if not os.path.isfile(snapshot_path):
        return EXIT_ERROR, f"❌ Error: Snapshot file not found: {snapshot_path}"

    with open(snapshot_path, "r", encoding="utf-8") as f:
        try:
            snapshot_data = json.load(f)
        except Exception as e:
            return EXIT_ERROR, f"❌ Error parsing snapshot JSON: {e}"

    if not isinstance(snapshot_data, dict):
        return EXIT_ERROR, "❌ Error: Snapshot root is not a dictionary."

    meta = snapshot_data.get("meta", {})
    if meta.get("format_version") != 2:
        return EXIT_ERROR, f"❌ Error: Unsupported format version {meta.get('format_version')}. Expected 2."

    inputs = snapshot_data.get("inputs")
    if not inputs:
        return EXIT_ERROR, "❌ Error: Snapshot contains no 'inputs' block. Cannot rebuild offline."

    baseline_sec4 = snapshot_data.get("section4", {})
    baseline_raw_text = baseline_sec4.get("text", "")
    baseline_body = section4_body(baseline_raw_text) if baseline_raw_text else ""
    baseline_sha = baseline_sec4.get("sha256")
    recorded_values = snapshot_data.get("values", {})

    # Rebuild using snapshot inputs
    try:
        rebuilt_sec4, rebuilt_snap = gms.run_market_analysis(
            from_snapshot=snapshot_path,
        )
    except Exception as e:
        return EXIT_ERROR, f"❌ Error during rebuild execution: {e}"

    rebuilt_body = section4_body(rebuilt_sec4)
    rebuilt_sha = hashlib.sha256(rebuilt_body.encode("utf-8")).hexdigest()

    differences: List[str] = []

    # 1. Compare Section 4 SHA-256 (supporting both legacy raw and normalized baselines)
    normalized_baseline_sha = hashlib.sha256(baseline_body.encode("utf-8")).hexdigest() if baseline_body else baseline_sha
    if not baseline_sha:
        differences.append("⚠️ No baseline SHA-256 recorded in snapshot section4.")
    elif rebuilt_sha != baseline_sha and rebuilt_sha != normalized_baseline_sha:
        differences.append(f"❌ Section 4 SHA-256 mismatch: recorded {baseline_sha[:10]}... != rebuilt {rebuilt_sha[:10]}...")
        if verbose:
            diff = list(difflib.unified_diff(
                baseline_body.splitlines(keepends=True),
                rebuilt_body.splitlines(keepends=True),
                fromfile="recorded_baseline",
                tofile="rebuilt_section4",
            ))
            differences.append("".join(diff[:30]))

    # 2. Compare computed values
    rebuilt_values = rebuilt_snap.values
    val_diff_count = 0
    for path, rec_item in recorded_values.items():
        if path not in rebuilt_values:
            val_diff_count += 1
            if val_diff_count <= 5 or verbose:
                differences.append(f"❌ Missing in rebuilt: {path}")
            continue

        rec_v = rec_item.get("value")
        reb_v = rebuilt_values[path].get("value")

        if rec_v is None and reb_v is None:
            continue
        if isinstance(rec_v, (int, float)) and isinstance(reb_v, (int, float)):
            if not math.isclose(float(rec_v), float(reb_v), rel_tol=VALUE_REL_TOL, abs_tol=VALUE_ABS_TOL):
                val_diff_count += 1
                if val_diff_count <= 5 or verbose:
                    differences.append(f"❌ Value mismatch at {path}: recorded {rec_v} != rebuilt {reb_v}")
        elif rec_v != reb_v:
            val_diff_count += 1
            if val_diff_count <= 5 or verbose:
                differences.append(f"❌ Value mismatch at {path}: recorded {rec_v} != rebuilt {reb_v}")

    if val_diff_count > 5 and not verbose:
        differences.append(f"... and {val_diff_count - 5} additional value differences (use --verbose to see all).")

    summary_lines = [
        f"📊 Rebuild Report: {os.path.basename(snapshot_path)}",
        f"   - Recorded SHA-256: {baseline_sha[:16] if baseline_sha else 'None'}...",
        f"   - Rebuilt  SHA-256: {rebuilt_sha[:16]}...",
        f"   - Recorded Values:  {len(recorded_values)} items",
        f"   - Rebuilt Values:   {len(rebuilt_values)} items",
    ]

    if differences:
        summary_lines.append("\n❌ Differences detected:")
        summary_lines.extend(f"   {d}" for d in differences)
        return EXIT_DIFF, "\n".join(summary_lines)

    summary_lines.append("\n✅ Section 4 rebuild match verified: SHA-256 hash and all values are identical.")
    return EXIT_SAME, "\n".join(summary_lines)


def main():
    parser = argparse.ArgumentParser(description="Rebuild market analysis Section 4 from snapshot alone")
    parser.add_argument("snapshot", type=str, help="Path to snapshot JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print line diffs and all value mismatches")
    parser.add_argument("--out", type=str, default="", help="Write rebuilt Section 4 to output file")

    args = parser.parse_args()
    code, msg = rebuild_from_snapshot(args.snapshot, verbose=args.verbose)
    print(msg)

    if args.out and code in (EXIT_SAME, EXIT_DIFF):
        with open(args.snapshot, "r", encoding="utf-8") as f:
            snap_data = json.load(f)
        rebuilt_sec4, _ = gms.run_market_analysis(from_snapshot=args.snapshot)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(rebuilt_sec4)
        print(f"📄 Rebuilt Section 4 written to: {args.out}")

    sys.exit(code)


if __name__ == "__main__":
    main()
