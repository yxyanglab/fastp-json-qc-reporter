#!/usr/bin/env python3
"""Summarize fastp JSON reports for bacterial RNA-seq QC decisions."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Any


DEFAULT_THRESHOLDS = {
    "filter_rate_warn": 0.15,
    "filter_rate_fail": 0.30,
    "q30_warn": 0.85,
    "q30_fail": 0.80,
    "gc_min": 0.35,
    "gc_max": 0.65,
    "base_diff_warn": 0.05,
    "base_diff_fail": 0.10,
    "gc_shift_warn": 0.06,
}


DECISION_RANK = {"PASS": 0, "WARN": 1, "FAIL": 2}


PATTERN_LIBRARY = {
    "low_quality_heavy_filtering": {
        "title": "低质量 reads 与过滤损耗同时偏高",
        "possible_reason": "测序质量偏低、接头/低质量尾端较多，或样本建库质量不稳定。",
        "check": "复查 fastp per-base quality、adapter content、过滤前后 reads 数和后续比对率；必要时调整 --cut_front/--cut_tail 或与测序服务商确认。",
    },
    "low_q30_after_filtering": {
        "title": "过滤后 Q30 仍偏低",
        "possible_reason": "过滤后整体碱基质量仍不足，可能影响细菌转录组比对、定量和差异分析稳定性。",
        "check": "查看 read 末端质量下降是否明显；若低质量集中在末端，可增加尾端修剪；若全程偏低，建议结合测序批次评估。",
    },
    "heavy_filtering_only": {
        "title": "过滤率偏高但 Q30 尚可",
        "possible_reason": "fastp 去除了较多低质量或过短 reads，但保留下来的 reads 质量尚可。",
        "check": "确认过滤后 reads 数是否满足转录组分析深度；复查 adapter trimming、too short reads 和 duplication 情况。",
    },
    "gc_out_of_range": {
        "title": "GC content 超出默认范围",
        "possible_reason": "可能与菌株自身 GC 背景、rRNA/污染序列、样本混淆或建库偏好有关。",
        "check": "先与参考基因组/近缘菌 GC 背景比较，再结合 mapping rate、rRNA 比例和物种注释结果判断。",
    },
    "gc_group_shift": {
        "title": "样本间 GC 存在系统性偏移",
        "possible_reason": "若偏移集中在同一处理组或同一批次，可能是真实生物差异，也可能是批次、污染或样本处理差异。",
        "check": "结合样本分组、建库批次、mapping rate 和后续 PCA/聚类结果判断；若只发生在单个样本，优先排查样本异常。",
    },
    "base_composition_bias": {
        "title": "A/T 或 C/G 碱基组成偏差较大",
        "possible_reason": "细菌 RNA-seq 中可能由随机引物偏好、链特异性建库、read composition 偏差或污染导致。",
        "check": "复查 fastp base content 曲线、FastQC per base sequence content、rRNA 去除效果和建库类型；轻微偏差可记录后继续分析。",
    },
    "mild_base_bias": {
        "title": "碱基组成存在轻微偏差",
        "possible_reason": "偏差未达到失败阈值，可能与细菌转录本组成或建库偏好有关。",
        "check": "可继续后续分析，但建议在 MultiQC/FastQC 中确认偏差是否集中在 reads 前端。",
    },
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


def infer_group(sample: str) -> str:
    for sep in ("-", "_", "."):
        if sep in sample:
            head = sample.split(sep)[0]
            if head:
                return head
    return "all"


def add_pattern(row: dict[str, Any], code: str, level: str) -> None:
    row["patterns"].append(code)
    if DECISION_RANK[level] > DECISION_RANK[row["decision"]]:
        row["decision"] = level


def evaluate_sample(row: dict[str, Any], thresholds: dict[str, float]) -> None:
    filter_rate = row["filter_rate"]
    q30_rate = row["q30_rate"]
    gc_content = row["gc_content"]
    at_diff = row["at_diff"]
    cg_diff = row["cg_diff"]

    if filter_rate >= thresholds["filter_rate_warn"] and q30_rate < thresholds["q30_fail"]:
        add_pattern(row, "low_quality_heavy_filtering", "FAIL")
    elif q30_rate < thresholds["q30_fail"]:
        add_pattern(row, "low_q30_after_filtering", "FAIL")
    elif filter_rate >= thresholds["filter_rate_fail"]:
        add_pattern(row, "heavy_filtering_only", "FAIL")
    elif filter_rate >= thresholds["filter_rate_warn"]:
        add_pattern(row, "heavy_filtering_only", "WARN")

    if q30_rate < thresholds["q30_warn"] and q30_rate >= thresholds["q30_fail"]:
        add_pattern(row, "low_q30_after_filtering", "WARN")

    if gc_content < thresholds["gc_min"] or gc_content > thresholds["gc_max"]:
        add_pattern(row, "gc_out_of_range", "FAIL")

    if at_diff > thresholds["base_diff_fail"] or cg_diff > thresholds["base_diff_fail"]:
        add_pattern(row, "base_composition_bias", "FAIL")
    elif at_diff > thresholds["base_diff_warn"] or cg_diff > thresholds["base_diff_warn"]:
        add_pattern(row, "mild_base_bias", "WARN")


def analyze_file(path: Path, thresholds: dict[str, float]) -> dict[str, Any]:
    data = read_json(path)
    summary = data["summary"]
    before_summary = summary["before_filtering"]
    after_summary = summary["after_filtering"]

    before_reads = before_summary["total_reads"]
    after_reads = after_summary["total_reads"]
    if before_reads == 0:
        raise ValueError(f"{path} has zero reads before filtering")

    bases = base_composition(data)
    sample = sample_name(path)
    row = {
        "sample": sample,
        "group": infer_group(sample),
        "file": str(path),
        "before_reads": before_reads,
        "after_reads": after_reads,
        "filter_rate": (before_reads - after_reads) / before_reads,
        "q30_rate": after_summary["q30_rate"],
        "gc_content": after_summary["gc_content"],
        "A": bases["A"],
        "T": bases["T"],
        "C": bases["C"],
        "G": bases["G"],
        "at_diff": abs(bases["A"] - bases["T"]),
        "cg_diff": abs(bases["C"] - bases["G"]),
        "decision": "PASS",
        "patterns": [],
        "cohort_notes": [],
    }
    evaluate_sample(row, thresholds)
    return row


def add_cohort_gc_notes(results: list[dict[str, Any]], thresholds: dict[str, float]) -> None:
    if len(results) < 3:
        return

    cohort_gc = [row["gc_content"] for row in results]
    cohort_median = statistics.median(cohort_gc)

    groups: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        groups.setdefault(row["group"], []).append(row)

    for row in results:
        gc_delta = row["gc_content"] - cohort_median
        if abs(gc_delta) >= thresholds["gc_shift_warn"]:
            row["cohort_notes"].append(
                f"GC differs from cohort median by {percent(abs(gc_delta))}"
            )
            if "gc_group_shift" not in row["patterns"]:
                add_pattern(row, "gc_group_shift", "WARN")

    for group, rows in groups.items():
        if len(rows) < 2 or len(groups) == 1:
            continue
        group_median = statistics.median(row["gc_content"] for row in rows)
        delta = group_median - cohort_median
        if abs(delta) >= thresholds["gc_shift_warn"]:
            for row in rows:
                row["cohort_notes"].append(
                    f"group {group} median GC differs from cohort median by {percent(abs(delta))}"
                )
                if "gc_group_shift" not in row["patterns"]:
                    add_pattern(row, "gc_group_shift", "WARN")


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
        "group",
        "decision",
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
        "patterns",
        "cohort_notes",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow(
                {
                    **{field: row[field] for field in fields if field not in {"patterns", "cohort_notes"}},
                    "patterns": ";".join(row["patterns"]),
                    "cohort_notes": ";".join(row["cohort_notes"]),
                }
            )


def decision_summary(results: list[dict[str, Any]]) -> dict[str, int]:
    return {decision: sum(1 for row in results if row["decision"] == decision) for decision in DECISION_RANK}


def render_console_report(results: list[dict[str, Any]], thresholds: dict[str, float]) -> str:
    counts = decision_summary(results)
    lines = []
    lines.append("=" * 76)
    if counts["FAIL"]:
        lines.append(f"QC verdict: {counts['FAIL']} FAIL, {counts['WARN']} WARN, {counts['PASS']} PASS.")
    elif counts["WARN"]:
        lines.append(f"QC verdict: no FAIL samples; {counts['WARN']} samples need attention.")
    else:
        lines.append(f"QC verdict: all {len(results)} samples passed.")
    lines.append("=" * 76)
    lines.append("")
    lines.append(
        f"{'Sample':<18}{'Decision':<10}{'Filter':>10}{'Q30':>10}{'GC':>10}"
        f"{'|A-T|':>10}{'|C-G|':>10}"
    )
    lines.append("-" * 78)
    for row in results:
        lines.append(
            f"{row['sample']:<18}{row['decision']:<10}"
            f"{percent(row['filter_rate']):>10}"
            f"{percent(row['q30_rate']):>10}"
            f"{percent(row['gc_content']):>10}"
            f"{percent(row['at_diff']):>10}"
            f"{percent(row['cg_diff']):>10}"
        )

    flagged = [row for row in results if row["decision"] != "PASS"]
    if flagged:
        lines.append("")
        lines.append("Flagged samples")
        for row in flagged:
            titles = [PATTERN_LIBRARY[code]["title"] for code in row["patterns"]]
            lines.append(f"- {row['sample']} [{row['decision']}]: {'; '.join(titles)}")
    lines.append("")
    lines.append(f"Rules: filter WARN >= {percent(thresholds['filter_rate_warn'])}, "
                 f"filter FAIL >= {percent(thresholds['filter_rate_fail'])}, "
                 f"Q30 WARN < {percent(thresholds['q30_warn'])}, "
                 f"Q30 FAIL < {percent(thresholds['q30_fail'])}.")
    return "\n".join(lines) + "\n"


def render_markdown_report(results: list[dict[str, Any]], thresholds: dict[str, float]) -> str:
    counts = decision_summary(results)
    lines = ["# fastp QC Decision Report", ""]
    lines.append("## Overall Decision")
    if counts["FAIL"]:
        lines.append(
            f"- **Decision:** {counts['FAIL']} samples should be reviewed before downstream analysis."
        )
    elif counts["WARN"]:
        lines.append(
            f"- **Decision:** no failed samples, but {counts['WARN']} samples have warning-level patterns."
        )
    else:
        lines.append("- **Decision:** all samples pass the current bacterial RNA-seq QC rules.")
    lines.append(f"- **Samples:** {len(results)} total; {counts['PASS']} PASS, {counts['WARN']} WARN, {counts['FAIL']} FAIL.")
    lines.append("")

    lines.append("## Sample Summary")
    lines.append("| Sample | Decision | Filter rate | Q30 rate | GC content | A | T | C | G | A-T diff | C-G diff | Patterns |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for row in results:
        pattern_text = "<br>".join(PATTERN_LIBRARY[code]["title"] for code in row["patterns"]) or "-"
        lines.append(
            f"| {row['sample']} | {row['decision']} | {percent(row['filter_rate'])} | "
            f"{percent(row['q30_rate'])} | {percent(row['gc_content'])} | "
            f"{percent(row['A'])} | {percent(row['T'])} | {percent(row['C'])} | {percent(row['G'])} | "
            f"{percent(row['at_diff'])} | {percent(row['cg_diff'])} | {pattern_text} |"
        )
    lines.append("")

    flagged = [row for row in results if row["decision"] != "PASS"]
    if flagged:
        lines.append("## Review Notes")
        for row in flagged:
            lines.append(f"### {row['sample']} - {row['decision']}")
            for code in row["patterns"]:
                rule = PATTERN_LIBRARY[code]
                lines.append(f"- **Pattern:** {rule['title']}")
                lines.append(f"  - Possible reason: {rule['possible_reason']}")
                lines.append(f"  - Suggested check: {rule['check']}")
            for note in row["cohort_notes"]:
                lines.append(f"  - Cohort note: {note}")
            lines.append("")

    lines.append("## Rule Thresholds")
    lines.append(f"- Filtering rate WARN: `>= {percent(thresholds['filter_rate_warn'])}`")
    lines.append(f"- Filtering rate FAIL: `>= {percent(thresholds['filter_rate_fail'])}`")
    lines.append(f"- Q30 WARN: `< {percent(thresholds['q30_warn'])}`")
    lines.append(f"- Q30 FAIL: `< {percent(thresholds['q30_fail'])}`")
    lines.append(f"- GC default range: `{percent(thresholds['gc_min'])}-{percent(thresholds['gc_max'])}`")
    lines.append(f"- Base composition WARN: `\\|A-T\\|` or `\\|C-G\\|` `> {percent(thresholds['base_diff_warn'])}`")
    lines.append(f"- Base composition FAIL: `\\|A-T\\|` or `\\|C-G\\|` `> {percent(thresholds['base_diff_fail'])}`")
    lines.append("")
    lines.append("## Interpretation Limits")
    lines.append(
        "These rules provide screening-level decision support for bacterial RNA-seq QC. "
        "They suggest possible causes and follow-up checks, but do not replace inspection of "
        "fastp/FastQC/MultiQC reports, mapping rate, rRNA ratio, reference genome GC background, "
        "or experimental metadata."
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate bacterial RNA-seq QC decisions from fastp JSON files."
    )
    parser.add_argument("paths", nargs="+", help="fastp JSON files or directories containing JSON files")
    parser.add_argument("--csv", default="qc_summary.csv", help="CSV output path")
    parser.add_argument("--report", default="qc_report.md", help="Markdown report output path")
    parser.add_argument("--filter-rate-warn", type=float, default=DEFAULT_THRESHOLDS["filter_rate_warn"])
    parser.add_argument("--filter-rate-fail", type=float, default=DEFAULT_THRESHOLDS["filter_rate_fail"])
    parser.add_argument("--q30-warn", type=float, default=DEFAULT_THRESHOLDS["q30_warn"])
    parser.add_argument("--q30-fail", type=float, default=DEFAULT_THRESHOLDS["q30_fail"])
    parser.add_argument("--gc-min", type=float, default=DEFAULT_THRESHOLDS["gc_min"])
    parser.add_argument("--gc-max", type=float, default=DEFAULT_THRESHOLDS["gc_max"])
    parser.add_argument("--base-diff-warn", type=float, default=DEFAULT_THRESHOLDS["base_diff_warn"])
    parser.add_argument("--base-diff-fail", type=float, default=DEFAULT_THRESHOLDS["base_diff_fail"])
    parser.add_argument("--gc-shift-warn", type=float, default=DEFAULT_THRESHOLDS["gc_shift_warn"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    thresholds = {
        "filter_rate_warn": args.filter_rate_warn,
        "filter_rate_fail": args.filter_rate_fail,
        "q30_warn": args.q30_warn,
        "q30_fail": args.q30_fail,
        "gc_min": args.gc_min,
        "gc_max": args.gc_max,
        "base_diff_warn": args.base_diff_warn,
        "base_diff_fail": args.base_diff_fail,
        "gc_shift_warn": args.gc_shift_warn,
    }

    files = discover_json_files(args.paths)
    if not files:
        print("No JSON files found.", file=sys.stderr)
        return 1

    results = [analyze_file(path, thresholds) for path in files]
    results.sort(key=lambda row: row["sample"])
    add_cohort_gc_notes(results, thresholds)

    csv_path = Path(args.csv)
    report_path = Path(args.report)
    write_csv(results, csv_path)
    markdown_report = render_markdown_report(results, thresholds)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown_report, encoding="utf-8")

    print(render_console_report(results, thresholds))
    print(f"CSV written to: {csv_path}")
    print(f"Markdown report written to: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
