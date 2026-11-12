"""
Report number verification script for market-analyst:
Validates that Section 4 hash matches the data snapshot baseline,
that no unpopulated placeholders remain, and that numbers mentioned
with [1] citations trace to the snapshot values.
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
from typing import Any, Dict, List, Set, Tuple

from market_snapshot import section4_body

EXIT_OK = 0
EXIT_ISSUES = 1
EXIT_CANNOT_RUN = 2

# Standard calendar numbers, dates, SMA windows, or common percentages exempt from snapshot lookup
IGNORED_NUMBERS = {
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 20, 22, 30, 50, 60, 64, 100, 200, 252,
    2024, 2025, 2026, 2027, 8, 5, 4, 19, 10,
}


def extract_numbers_from_text(text: str) -> List[Tuple[str, float]]:
    """Extract numeric values with percentages or plain numbers from text lines."""
    # Matches numbers with or without commas: e.g. 5800.0, 7,447.15, -3.54%, +1.69%, 22.91, 55000원, $220.50
    num_pattern = re.compile(r'([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)(%|배|pt|bps|원|\$)?')
    results = []
    for line in text.splitlines():
        # Skip table lines, comments, and timestamp lines
        stripped = line.strip()
        if stripped.startswith('|') or stripped.startswith('<!--') or stripped.startswith('> 산출 시점:'):
            continue
        # Strip citation markers like [1], [2]
        clean_line = re.sub(r'\[\d+\]', '', line)
        # Strip code ticker symbols inside backticks e.g. `005930.KS`, `066570.KS`
        clean_line = re.sub(r'`[^`]+`', '', clean_line)
        # Strip 6-digit stock codes e.g. 005930.KS
        clean_line = re.sub(r'\b\d{6}(?:\.KS|\.KQ)?\b', '', clean_line)
        # Strip Tier numbering e.g. Tier 1, Tier 2, Tier 3, 3단계
        clean_line = re.sub(r'\bTier\s*\d+\b', '', clean_line, flags=re.IGNORECASE)
        clean_line = re.sub(r'\b\d+단계\b', '', clean_line)
        # Strip dates like 2024-08-05, times like 02:23, and time window units like 60일, 52주, 3거래일
        clean_line = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '', clean_line)
        clean_line = re.sub(r'\b\d{1,2}:\d{2}\b', '', clean_line)
        clean_line = re.sub(r'\b\d+(?:일|거래일|주|개월|년)\b', '', clean_line)
        clean_line = re.sub(r'52주', '', clean_line)
        clean_line = re.sub(r'(?:S&P\s*|SP\s*)500\b', '', clean_line, flags=re.IGNORECASE)
        clean_line = re.sub(r'(?:Nasdaq\s*|나스닥\s*)100\b', '', clean_line, flags=re.IGNORECASE)
        clean_line = re.sub(r'(?:Russell\s*|러셀\s*)2000\b', '', clean_line, flags=re.IGNORECASE)
        clean_line = re.sub(r'(?:코스피|KOSPI)\s*200\b', '', clean_line, flags=re.IGNORECASE)

        for m in num_pattern.finditer(clean_line):
            raw_str = m.group(1).replace(',', '')
            try:
                val = float(raw_str)
                results.append((m.group(0), val))
            except ValueError:
                pass
    return results


def verify_report(report_path: str) -> int:
    """Verify market report against paired snapshot."""
    if not os.path.isfile(report_path):
        print(f"❌ Error: Report file not found: {report_path}", file=sys.stderr)
        return EXIT_CANNOT_RUN

    base_no_ext, _ = os.path.splitext(report_path)
    snapshot_path = f"{base_no_ext}_data.json"
    if not os.path.isfile(snapshot_path):
        print(f"❌ Error: Companion snapshot not found: {snapshot_path}", file=sys.stderr)
        return EXIT_CANNOT_RUN

    with open(report_path, 'r', encoding='utf-8') as f:
        report_text = f.read()

    with open(snapshot_path, 'r', encoding='utf-8') as f:
        snapshot_data = json.load(f)

    issues: List[str] = []

    # 1. Check Section 4 Hash
    sec4_text = section4_body(report_text)
    if not sec4_text:
        issues.append("❌ Section 4 body could not be located in report.")
    else:
        sec4_sha = hashlib.sha256(sec4_text.encode('utf-8')).hexdigest()
        baseline_sec4 = snapshot_data.get("section4", {})
        baseline_sha = baseline_sec4.get("sha256")
        if not baseline_sha:
            issues.append("⚠️ Warning: No Section 4 baseline hash attached to snapshot.")
        elif sec4_sha != baseline_sha:
            issues.append(f"❌ Section 4 hash mismatch! Expected: {baseline_sha[:8]}..., Got: {sec4_sha[:8]}... (Section 4 was manually modified)")

    # 2. Check for leftover placeholders
    placeholders = [
        (r'\[AI_TODO[^\]]*\]', "unpopulated [AI_TODO]"),
        (r'\[수치[^\]]*\]', "unpopulated [수치]"),
        (r'\[XX%\]', "unpopulated [XX%]"),
        (r'\[🟢/🟡/🔴\]', "unpopulated [🟢/🟡/🔴]"),
        (r'\[방어 유지[^\]]*\]', "unpopulated [방어 유지]"),
        (r'\[진단[^\]]*\]', "unpopulated [진단]"),
        (r'\[출처[^\]]*\]', "unpopulated [출처]"),
        (r'<!--\s*스크립트.*?-->', "unpopulated script template comment"),
        (r'\[\s*(?:YYYY|MM|DD)[^\]]*\]', "unpopulated date placeholder"),
    ]
    for pattern, desc in placeholders:
        matches = re.findall(pattern, report_text)
        if matches:
            issues.append(f"❌ Found {len(matches)} {desc} placeholders in report.")

    # 3. Check values coverage: Verify numbers cited with [1] trace to snapshot
    snapshot_values = snapshot_data.get("values", {})
    recorded_numbers: Set[float] = set()
    for item in snapshot_values.values():
        v = item.get("value")
        if isinstance(v, (int, float)):
            recorded_numbers.add(round(float(v), 2))
            recorded_numbers.add(round(float(v), 1))
            recorded_numbers.add(round(float(v), 0))
            recorded_numbers.add(abs(round(float(v), 2)))
            recorded_numbers.add(abs(round(float(v), 1)))

    untraced_count = 0
    for line_no, line in enumerate(report_text.splitlines(), start=1):
        if "[1]" in line and not line.strip().startswith("|") and not line.strip().startswith("* [1]"):
            nums = extract_numbers_from_text(line)
            for raw_m, val in nums:
                if val in IGNORED_NUMBERS or abs(val) in IGNORED_NUMBERS:
                    continue
                v_round2 = round(val, 2)
                v_round1 = round(val, 1)
                v_round0 = round(val, 0)
                v_abs2 = abs(v_round2)
                v_abs1 = abs(v_round1)
                if not ({v_round2, v_round1, v_round0, v_abs2, v_abs1} & recorded_numbers):
                    # Check if within 0.1 tolerance of any recorded number
                    if not any(abs(val - r) < 0.15 for r in recorded_numbers):
                        untraced_count += 1
                        if untraced_count <= 5:
                            issues.append(f"⚠️ Untraced [1] cited number '{raw_m}' on line {line_no}: {line.strip()[:60]}...")

    if untraced_count > 5:
        issues.append(f"⚠️ ... and {untraced_count - 5} additional untraced numbers cited with [1].")

    # Print summary
    print(f"📋 Market Report Number Check: {os.path.basename(report_path)}")
    print(f"   - Snapshot: {os.path.basename(snapshot_path)} ({len(snapshot_values)} values recorded)")
    if issues:
        print("\n❌ Issues identified:")
        for iss in issues:
            print(f"   {iss}")
        return EXIT_ISSUES

    print("\n✅ All checks passed! Section 4 hash matches and report has zero unpopulated placeholders.")
    return EXIT_OK


def main():
    parser = argparse.ArgumentParser(description="Check market report numbers against snapshot")
    parser.add_argument("report_file", type=str, help="Path to markdown report file")
    args = parser.parse_args()

    code = verify_report(args.report_file)
    sys.exit(code)


if __name__ == "__main__":
    main()
