# Claude Code 决策回答示例

这个项目的核心不是单纯生成表格，而是把 fastp 质控结果转换成“能不能继续分析”的判断。脚本负责提取和汇总指标，Claude Code skill 负责把结构化结果解释成自然语言决策。

## 场景 1：没有 FAIL，但存在 WARN

用户输入：

```text
/fastp-check 分析 /Users/yeye/Desktop/fastp_demo 里的数据
```

脚本输出摘要：

```text
QC verdict: no FAIL samples; 4 samples need attention.
B-5/B-6/B-7/B-8: WARN - 样本间 GC 存在系统性偏移
```

Claude Code skill 应回答：

```text
没有 FAIL 样本，12 个样本整体可以进入后续分析；其中 B-5 到 B-8 为 WARN，需要在报告中备注并结合后续结果复查。

- 过滤率 0.01%-0.02%，数据损耗很小
- % > Q30 为 94.92%-98.03%，整体测序质量很好
- GC content 为 41.4%-50.7%，均未超出 35%-65% 默认范围
- \|A-T\| 和 \|C-G\| 均未达到失败阈值

B-5 到 B-8 的 GC content 约为 42%，明显低于其他样本。该模式不能直接判定为污染或建库失败，建议结合样本分组、建库批次、mapping rate、rRNA 比例和后续 PCA/聚类结果判断。如果 B-5 到 B-8 属于同一处理组，也可能反映真实生物差异。
```

## 场景 2：存在异常样本

脚本输出摘要：

```text
QC verdict: 1 FAIL, 0 WARN, 1 PASS.
problem_sample    FAIL    Filter 24.00%    Q30 73.50%    GC 70.20%    \|A-T\| 16.12%
```

Claude Code skill 应回答：

```text
有 1/2 个样本质控异常，暂不建议所有样本直接进入后续分析。

problem_sample 存在以下问题：
- 低质量 reads 与过滤损耗同时偏高：过滤率 24.00%，Q30 为 73.50%，提示需要复查 per-base quality、adapter content 和过滤后 reads 数
- GC content 为 70.20%，超出默认 35%-65% 范围，需结合参考基因组或近缘菌 GC 背景判断
- \|A-T\| 为 16.12%，高于 10% 失败阈值，需检查 read composition、链特异性建库、随机引物偏好或污染可能

建议先复查 problem_sample 的 fastp HTML/FastQC/MultiQC 图。如果低质量区域集中在 reads 前端或尾端，可以重新运行 fastp 并增加 `--cut_front`、`--cut_tail` 或调整质量阈值；如果 GC 和碱基组成异常仍存在，应进一步检查 mapping rate、rRNA 比例、样本污染、建库批次或样本混淆。good_sample 可以继续后续分析。
```

## 展示重点

GitHub 中的表格展示“工具能提取什么指标”，决策回答展示“工具怎样帮助分析人员做判断”。这两部分一起体现项目价值：

- 减少逐个打开 fastp HTML 的人工检查
- 补足 MultiQC 偏展示、缺少直接判读结论的问题
- 把细菌 RNA-seq 初筛经验整理成可复用规则
- 用 Claude Code 将规则解释为面向后续分析的建议
