#!/usr/bin/env python3
"""Summarize fastp JSON QC reports and flag samples that need attention."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_THRESHOLDS = {
    "filter_rate_max": 0.15,
    "q30_min": 0.80,
    "gc_min": 0.35,
    "gc_max": 0.65,
    "base_diff_max": 0.10,
}


SUGGESTIONS = {
    "filter_rate": "检查原始测序质量和接头污染；必要时调整 fastp 修剪参数或重新测序。",
    "q30": "检查测序平台、试剂批次和低质量循环；必要时加强前后端修剪。",
    "gc": "结合物种背景判断是否合理；若明显异常，排查污染、建库偏好或样本混淆。",
    "at_diff": "检查链特异性、随机引物偏好和 read composition；轻微偏差需在报告中说明。",
    "cg_diff": "检查链特异性、随机引物偏好和 read composition；轻微偏差需在报告中说明。",
}


def percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def mean_base(data: dict[str, Any], read_key: str, base: str) -> float:
    values = data[read_key]["content_curves"][base]
    return sum(values) / len(values)


def base_composition(data: dict[str, Any]) -> dict[str, float]:
    read_keys = [
        key
        for key in ("read1_before_filtering", "read2_before_filtering")
        if key in data
    ]
    if not read_keys:
        raise KeyError("fastp JSON lacks read*_before_filtering content_curves")

    composition = {}
    for base in "ATCG":
        composition[base] = sum(mean_base(data, key, base) for key in read_keys) / len(read_keys)
    return composition


def sample_name(path: Path) -> str:
    name = path.name
    for suffix in (".fastp.json", ".json"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def analyze_file(path: Path, thresholds: dict[str, float]) -> dict[str, Any]:
    data = read_json(path)
    summary = data["summary"]
    before_summary = summary["before_filtering"]
    after_summary = summary["after_filtering"]

    before_reads = before_summary["total_reads"]
    after_reads = after_summary["total_reads"]
    if before_reads == 0:
        raise ValueError(f"{path} has zero reads before filtering")

    filter_rate = (before_reads - after_reads) / before_reads
    q30_rate = after_summary["q30_rate"]
    gc_content = after_summary["gc_content"]

    bases = base_composition(data)
    at_diff = abs(bases["A"] - bases["T"])
    cg_diff = abs(bases["C"] - bases["G"])

    issues = []
    if filter_rate > thresholds["filter_rate_max"]:
        issues.append("filter_rate")
    if q30_rate < thresholds["q30_min"]:
        issues.append("q30")
    if gc_content < thresholds["gc_min"] or gc_content > thresholds["gc_max"]:
        issues.append("gc")
    if at_diff > thresholds["base_diff_max"]:
        issues.append("at_diff")
    if cg_diff > thresholds["base_diff_max"]:
        issues.append("cg_diff")

    return {
        "sample": sample_name(path),
        "file": str(path),
        "before_reads": before_reads,
        "after_reads": after_reads,
        "filter_rate": filter_rate,
        "q30_rate": q30_rate,
        "gc_content": gc_content,
        "A": bases["A"],
        "T": bases["T"],
        "C": bases["C"],
        "G": bases["G"],
        "at_diff": at_diff,
        "cg_diff": cg_diff,
        "status": "FAIL" if issues else "PASS",
        "issues": issues,
    }


def discover_json_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(sorted(path.glob("*.json")))
        elif path.is_file():
            files.append(path)
        else:
            print(f"Warning: {path} does not exist; skipped.", file=sys.stderr)
    return sorted(set(files))


def write_csv(results: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "sample",
        "status",
        "before_reads",
        "after_reads",
        "filter_rate",
        "q30_rate",
        "gc_content",
        "A",
        "T",
        "C",
        "G",
        "at_diff",
        "cg_diff",
        "issues",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow(
                {
                    **{field: row[field] for field in fields if field != "issues"},
                    "issues": ";".join(row["issues"]),
                }
            )


def render_report(results: list[dict[str, Any]], thresholds: dict[str, float]) -> str:
    bad = [row for row in results if row["status"] == "FAIL"]
    lines = []
    lines.append("=" * 72)
    if bad:
        lines.append(f"QC verdict: {len(bad)}/{len(results)} samples need attention.")
    else:
        lines.append(f"QC verdict: all {len(results)} samples passed.")
    lines.append("=" * 72)
    lines.append("")
    lines.append(
        f"{'Sample':<18}{'Status':<8}{'Filter':>10}{'Q30':>10}{'GC':>10}"
        f"{'|A-T|':>10}{'|C-G|':>10}"
    )
    lines.append("-" * 76)
    for row in results:
        lines.append(
            f"{row['sample']:<18}{row['status']:<8}"
            f"{percent(row['filter_rate']):>10}"
            f"{percent(row['q30_rate']):>10}"
            f"{percent(row['gc_content']):>10}"
            f"{percent(row['at_diff']):>10}"
            f"{percent(row['cg_diff']):>10}"
        )

    lines.append("")
    lines.append("Pass thresholds")
    lines.append(f"- Filtering rate <= {percent(thresholds['filter_rate_max'])}")
    lines.append(f"- Q30 rate >= {percent(thresholds['q30_min'])}")
    lines.append(
        f"- GC content between {percent(thresholds['gc_min'])} and {percent(thresholds['gc_max'])}"
    )
    lines.append(f"- |A-T| and |C-G| <= {percent(thresholds['base_diff_max'])}")

    if bad:
        lines.append("")
        lines.append("Failed samples")
        for row in bad:
            lines.append(f"- {row['sample']}: {', '.join(row['issues'])}")
            for issue in row["issues"]:
                lines.append(f"  Suggestion: {SUGGESTIONS[issue]}")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a multi-sample QC summary from fastp JSON files."
    )
    parser.add_argument("paths", nargs="+", help="fastp JSON files or directories containing JSON files")
    parser.add_argument("--csv", default="qc_summary.csv", help="CSV output path")
    parser.add_argument("--report", default="qc_report.txt", help="text report output path")
    parser.add_argument("--filter-rate-max", type=float, default=DEFAULT_THRESHOLDS["filter_rate_max"])
    parser.add_argument("--q30-min", type=float, default=DEFAULT_THRESHOLDS["q30_min"])
    parser.add_argument("--gc-min", type=float, default=DEFAULT_THRESHOLDS["gc_min"])
    parser.add_argument("--gc-max", type=float, default=DEFAULT_THRESHOLDS["gc_max"])
    parser.add_argument("--base-diff-max", type=float, default=DEFAULT_THRESHOLDS["base_diff_max"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    thresholds = {
        "filter_rate_max": args.filter_rate_max,
        "q30_min": args.q30_min,
        "gc_min": args.gc_min,
        "gc_max": args.gc_max,
        "base_diff_max": args.base_diff_max,
    }

    files = discover_json_files(args.paths)
    if not files:
        print("No JSON files found.", file=sys.stderr)
        return 1

    results = [analyze_file(path, thresholds) for path in files]
    results.sort(key=lambda row: row["sample"])

    csv_path = Path(args.csv)
    report_path = Path(args.report)
    write_csv(results, csv_path)
    report = render_report(results, thresholds)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    print(report)
    print(f"CSV written to: {csv_path}")
    print(f"Report written to: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
