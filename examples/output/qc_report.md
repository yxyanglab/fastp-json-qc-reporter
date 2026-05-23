# fastp QC Decision Report

## Overall Decision
- **Decision:** 1 samples should be reviewed before downstream analysis.
- **Samples:** 2 total; 1 PASS, 0 WARN, 1 FAIL.

## Sample Summary
| Sample | Decision | Filter rate | Q30 rate | GC content | A | T | C | G | A-T diff | C-G diff | Patterns |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| good_sample | PASS | 6.00% | 91.50% | 51.20% | 25.12% | 24.88% | 24.88% | 25.12% | 0.25% | 0.25% | - |
| problem_sample | FAIL | 24.00% | 73.50% | 70.20% | 35.00% | 18.88% | 21.00% | 25.12% | 16.12% | 4.12% | 低质量 reads 与过滤损耗同时偏高<br>GC content 超出默认范围<br>A/T 或 C/G 碱基组成偏差较大 |

## Review Notes
### problem_sample - FAIL
- **Pattern:** 低质量 reads 与过滤损耗同时偏高
  - Possible reason: 测序质量偏低、接头/低质量尾端较多，或样本建库质量不稳定。
  - Suggested check: 复查 fastp per-base quality、adapter content、过滤前后 reads 数和后续比对率；必要时调整 --cut_front/--cut_tail 或与测序服务商确认。
- **Pattern:** GC content 超出默认范围
  - Possible reason: 可能与菌株自身 GC 背景、rRNA/污染序列、样本混淆或建库偏好有关。
  - Suggested check: 先与参考基因组/近缘菌 GC 背景比较，再结合 mapping rate、rRNA 比例和物种注释结果判断。
- **Pattern:** A/T 或 C/G 碱基组成偏差较大
  - Possible reason: 细菌 RNA-seq 中可能由随机引物偏好、链特异性建库、read composition 偏差或污染导致。
  - Suggested check: 复查 fastp base content 曲线、FastQC per base sequence content、rRNA 去除效果和建库类型；轻微偏差可记录后继续分析。

## Rule Thresholds
- Filtering rate WARN: `>= 15.00%`
- Filtering rate FAIL: `>= 30.00%`
- Q30 WARN: `< 85.00%`
- Q30 FAIL: `< 80.00%`
- GC default range: `35.00%-65.00%`
- Base composition WARN: `\|A-T\|` or `\|C-G\|` `> 5.00%`
- Base composition FAIL: `\|A-T\|` or `\|C-G\|` `> 10.00%`

## Interpretation Limits
These rules provide screening-level decision support for bacterial RNA-seq QC. They suggest possible causes and follow-up checks, but do not replace inspection of fastp/FastQC/MultiQC reports, mapping rate, rRNA ratio, reference genome GC background, or experimental metadata.
