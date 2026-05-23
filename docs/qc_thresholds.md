# fastp JSON 质控分级判断标准

本项目默认用于细菌 RNA-seq fastp JSON 初筛。阈值不是绝对生物学结论，而是帮助快速发现需要人工复核的样本，并将结果分为 `PASS`、`WARN` 和 `FAIL`。

| 指标 | PASS | WARN | FAIL |
| --- | --- | --- | --- |
| 过滤率 | `<15%` | `>=15%` | `>=30%`，或与 Q30 failure 共同出现 |
| Q30 rate | `>=85%` | `80%-85%` | `<80%` |
| GC content | `35%-65%` 且无明显横向偏移 | 样本/组间系统性偏移 | `<35%` 或 `>65%` |
| `\|A-T\|` / `\|C-G\|` | `<=5%` | `>5%` | `>10%` |

## 指标来源

- 过滤率：`(summary.before_filtering.total_reads - summary.after_filtering.total_reads) / summary.before_filtering.total_reads`
- Q30 rate：`summary.after_filtering.q30_rate`
- GC content：`summary.after_filtering.gc_content`
- 碱基比例：`read1_before_filtering` 和 `read2_before_filtering` 中 `content_curves` 的平均值

## 使用建议

1. 细菌基因组 GC 差异很大，GC 阈值必须结合参考基因组或近缘菌背景解释。
2. `WARN` 通常表示可以继续分析，但需要在报告中记录或结合后续比对率、rRNA 比例、PCA/聚类结果复查。
3. `FAIL` 表示不建议无复核直接进入后续分析，但仍需要结合 fastp/FastQC/MultiQC 图、测序深度和实验设计综合判断。
4. 如果某个项目整体 Q30 偏低或过滤率偏高，应优先排查测序批次和建库批次，而不是只删除单个样本。
