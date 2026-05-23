---
name: fastp-check
description: Analyze bacterial RNA-seq fastp JSON output files. Shows filtering rate, Q30 rate, GC content, and base composition, then gives PASS/WARN/FAIL decisions, pattern-level review notes, a CSV summary, and a Markdown report.
---

# fastp-check

Use this skill when the user wants to inspect fastp JSON reports, summarize multi-sample sequencing QC, or decide whether samples can enter downstream analysis.

The purpose of this skill is not only to print a QC table. It should turn fastp metrics into a practical screening decision for bacterial RNA-seq: whether the samples can proceed to downstream analysis, which samples need attention, and what the user should check next.

## Usage

From this GitHub project:

```bash
python3 scripts/analyze_fastp.py /path/to/fastp_json_dir \
  --csv qc_summary.csv \
  --report qc_report.md
```

For example data:

```bash
python3 scripts/analyze_fastp.py examples/input \
  --csv examples/output/qc_summary.csv \
  --report examples/output/qc_report.md
```

## What It Reports

1. Overall PASS/WARN/FAIL verdict for all samples.
2. Multi-sample table with filtering rate, Q30 rate, GC content, A/T/C/G proportions, `\|A-T\|`, and `\|C-G\|`.
3. `qc_summary.csv` for downstream spreadsheet use.
4. `qc_report.md` for direct reading or project notes.
5. Pattern-level review notes with possible reasons and suggested checks.
6. A final natural-language answer: whether downstream analysis can continue.

## Response Style

After running the script, summarize the result in plain language:

- If all samples pass, say they can enter downstream analysis.
- If samples are WARN, say they can usually continue but need notes or follow-up checks.
- Mention useful borderline patterns, such as GC being within threshold but noticeably different between groups.
- If any sample fails, list the sample name, pattern, observed value, threshold, and suggested check.
- Keep the answer focused on decision-making rather than repeating every table value.

## QC Thresholds

| Metric | WARN | FAIL |
| --- | --- | --- |
| Filtering rate | `>= 15%` | `>= 30%`, or with Q30 failure |
| Q30 rate after filtering | `< 85%` | `< 80%` |
| GC content after filtering | cohort/group-level shift | outside `35%-65%` |
| `\|A-T\|` / `\|C-G\|` | `> 5%` | `> 10%` |

## Notes

- Treat this as an initial screening tool, not a replacement for biological interpretation.
- Pattern notes are possible causes and suggested checks, not definitive root-cause diagnoses.
- For unusual bacterial species, adjust GC thresholds according to reference genome or close relatives.
- Combine this result with FastQC/MultiQC curves, mapping rate, rRNA ratio, reference genome GC background, and project metadata.
