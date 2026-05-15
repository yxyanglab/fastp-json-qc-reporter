# fastp JSON 质控合格判断标准

本项目默认用于 RNA-seq、纯菌测序和宏组学数据的 fastp JSON 初筛。阈值不是绝对生物学结论，而是帮助快速发现需要人工复核的样本。

| 指标 | 默认合格标准 | 标记异常的含义 |
| --- | --- | --- |
| 过滤率 | `<= 15%` | 被 fastp 去除的 reads 过多，可能存在低质量、接头污染或建库问题 |
| Q30 rate | `>= 80%` | 过滤后高质量碱基比例偏低，可能影响后续比对、组装或定量 |
| GC content | `35%-65%` | GC 明显偏离常见范围，需要结合物种背景判断污染或样本异常 |
| `|A-T|` | `<= 10%` | A/T 碱基比例偏差较大，可能与链特异性、随机引物偏好或污染有关 |
| `|C-G|` | `<= 10%` | C/G 碱基比例偏差较大，可能与链特异性、随机引物偏好或污染有关 |

## 指标来源

- 过滤率：`(summary.before_filtering.total_reads - summary.after_filtering.total_reads) / summary.before_filtering.total_reads`
- Q30 rate：`summary.after_filtering.q30_rate`
- GC content：`summary.after_filtering.gc_content`
- 碱基比例：`read1_before_filtering` 和 `read2_before_filtering` 中 `content_curves` 的平均值

## 使用建议

1. 对于不同物种或样本类型，GC 阈值可以根据参考基因组或预期群落组成调整。
2. 对于宏基因组和宏转录组，单个阈值只能做初筛，异常样本应结合 MultiQC、测序量、宿主污染率和后续比对率判断。
3. 如果某个项目整体 Q30 偏低或过滤率偏高，应优先排查测序批次和建库批次，而不是只删除单个样本。
