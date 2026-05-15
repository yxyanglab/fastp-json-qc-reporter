---
name: fastp-check
description: Analyze fastp JSON output files from sequencing QC. Shows filtering rate, Q30 rate, GC content, and A/T/C/G base proportions. Automatically flags problematic samples and writes a CSV summary plus a text report.
---

# fastp-check

Use this skill when the user wants to inspect fastp JSON reports, summarize multi-sample sequencing QC, or decide whether samples can enter downstream analysis.

The purpose of this skill is not only to print a QC table. It should turn fastp metrics into a practical decision: whether the samples can proceed to downstream analysis, which samples need attention, and what the user should do next.

## Usage

From this GitHub project:

```bash
python3 scripts/analyze_fastp.py /path/to/fastp_json_dir \
  --csv qc_summary.csv \
  --report qc_report.txt
```

For example data:

```bash
python3 scripts/analyze_fastp.py examples/input \
  --csv examples/output/qc_summary.csv \
  --report examples/output/qc_report.txt
```

## What It Reports

1. Overall pass/fail verdict for all samples.
2. Multi-sample table with filtering rate, Q30 rate, GC content, A/T/C/G proportions, `|A-T|`, and `|C-G|`.
3. `qc_summary.csv` for downstream spreadsheet use.
4. `qc_report.txt` for direct reading or project notes.
5. Failed sample details with actionable suggestions.
6. A final natural-language answer: whether downstream analysis can continue.

## Response Style

After running the script, summarize the result in plain language:

- If all samples pass, say they can enter downstream analysis.
- Mention useful borderline patterns, such as GC being within threshold but noticeably different between groups.
- If any sample fails, list the sample name, failed metric, observed value, threshold, and suggested action.
- Keep the answer focused on decision-making rather than repeating every table value.

## QC Thresholds

| Metric | Pass condition | Flag if |
| --- | --- | --- |
| Filtering rate | `<= 15%` reads filtered | `> 15%` |
| Q30 rate after filtering | `>= 80%` | `< 80%` |
| GC content after filtering | `35%-65%` | outside range |
| `|A-T|` | `<= 10%` | `> 10%` |
| `|C-G|` | `<= 10%` | `> 10%` |

## Notes

- Treat this as an initial screening tool, not a replacement for biological interpretation.
- For unusual species or communities, adjust GC thresholds according to expected biology.
- For microbiome and metatranscriptome projects, combine this result with host contamination rate, mapping rate, taxonomic profile, and project metadata.
