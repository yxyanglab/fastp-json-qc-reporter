# fastp JSON QC Reporter

A lightweight decision-support tool for bacterial RNA-seq quality control based on fastp JSON reports. It summarizes filtering rate, Q30 rate, GC content, and base composition across multiple samples, then generates `PASS/WARN/FAIL` decisions, diagnostic patterns, and follow-up suggestions.

This project is designed to complement fastp and MultiQC. Instead of replacing visual QC reports, it converts commonly used QC metrics into a concise screening report for downstream analysis decisions.

## 为什么做这个项目

在转录组或宏组学分析中，每个样本运行 fastp 后都会生成 HTML 和 JSON 报告。HTML 报告适合逐个查看细节，但样本数一多就很低效。MultiQC 可以汇总所有样本，不过它更偏向展示；我在日常分析中更需要的是一个明确判断：

> 这些样本质控是否合格，能不能进入后续分析？如果不合格，具体是哪几个样本、哪些指标有问题、下一步应该怎么处理？

因此这个项目只提取我最常用的 fastp 质控指标，并把细菌转录组初筛中的常见判断规则写成脚本和 Claude Code skill，减少重复打开报告和手动判断的时间。

## 项目功能

- 批量读取一个目录下的 `*.json` fastp 质控文件
- 输出多样本 `qc_summary.csv`
- 输出可读的 `qc_report.md`
- 给出 `PASS/WARN/FAIL` 三级决策
- 在 Claude Code skill 中直接回答“是否可以继续后续分析”
- 自动标记细菌 RNA-seq 常见异常模式：过滤损耗偏高、Q30 偏低、GC 异常、碱基组成偏差、组内 GC 系统性偏移
- 给出可能原因和后续复查建议
- 提供示例输入、示例输出和质控阈值说明

## 项目结构

```text
.
├── README.md
├── scripts/
│   └── analyze_fastp.py
├── examples/
│   ├── input/
│   │   ├── good_sample.fastp.json
│   │   └── problem_sample.fastp.json
│   └── output/
│       ├── qc_summary.csv
│       └── qc_report.md
├── claude-skill/
│   └── SKILL.md
└── docs/
    ├── qc_thresholds.md
    ├── diagnostic_rules.md
    ├── decision_examples.md
    └── microbiome_workflow.md
```

## 快速开始

不需要安装额外 Python 包，Python 3.9+ 即可。

```bash
python3 scripts/analyze_fastp.py examples/input \
  --csv examples/output/qc_summary.csv \
  --report examples/output/qc_report.md
```

分析自己的 fastp JSON 文件：

```bash
python3 scripts/analyze_fastp.py /path/to/fastp_json_dir \
  --csv qc_summary.csv \
  --report qc_report.md
```

也可以同时传入多个 JSON 文件：

```bash
python3 scripts/analyze_fastp.py sample1.fastp.json sample2.fastp.json
```

## 输出示例

脚本会输出结构化结果，Claude Code skill 会基于结果给出自然语言决策。

`qc_summary.csv` 包含以下列：

| 列名 | 含义 |
| --- | --- |
| `sample` | 样本名 |
| `decision` | `PASS`、`WARN` 或 `FAIL` |
| `before_reads` | 过滤前 reads 数 |
| `after_reads` | 过滤后 reads 数 |
| `filter_rate` | 过滤率 |
| `q30_rate` | 过滤后 Q30 rate |
| `gc_content` | 过滤后 GC 含量 |
| `A/T/C/G` | 平均碱基比例 |
| `at_diff` | `\|A-T\|` |
| `cg_diff` | `\|C-G\|` |
| `patterns` | 异常模式 |
| `cohort_notes` | 样本横向比较提示 |

文本报告示例：

```text
QC verdict: 1 FAIL, 0 WARN, 1 PASS.
Sample            Decision      Filter       Q30        GC     \|A-T\|   \|C-G\|
good_sample       PASS           6.00%    91.50%    51.20%     0.25%     0.25%
problem_sample    FAIL          24.00%    73.50%    70.20%    16.12%     4.12%
```

Claude Code skill 回答示例：

```text
有 1/2 个样本质控异常，暂不建议所有样本直接进入后续分析。

problem_sample 存在以下问题：
- 过滤率 24.00%，高于 15% 阈值，提示低质量 reads 或接头污染较多
- Q30 为 73.50%，低于 80% 阈值，提示过滤后整体测序质量偏低
- GC content 为 70.20%，高于 65% 阈值，需结合物种背景排查污染或建库偏差
- \|A-T\| 为 16.12%，高于 10% 阈值，需检查 read composition 或链特异性设置

建议先复查 problem_sample 的 fastp HTML/MultiQC 图，必要时重新运行 fastp 并增加前端/尾端修剪参数；good_sample 可以继续后续分析。
```

## 默认合格判断标准

| 指标 | WARN | FAIL |
| --- | --- | --- |
| 过滤率 | `>= 15%` | `>= 30%`，或与低 Q30 共同出现 |
| Q30 rate | `< 85%` | `< 80%` |
| GC content | 样本/组间系统性偏移 | `<35%` 或 `>65%` |
| `\|A-T\|` / `\|C-G\|` | `>5%` | `>10%` |

详细说明见 [docs/qc_thresholds.md](docs/qc_thresholds.md)，异常模式见 [docs/diagnostic_rules.md](docs/diagnostic_rules.md)。

## 自定义阈值

```bash
python3 scripts/analyze_fastp.py examples/input \
  --filter-rate-warn 0.20 \
  --filter-rate-fail 0.35 \
  --q30-warn 0.90 \
  --q30-fail 0.85 \
  --gc-min 0.30 \
  --gc-max 0.70 \
  --base-diff-warn 0.08 \
  --base-diff-fail 0.12
```


## 作为 Claude Code skill 使用

`claude-skill/SKILL.md` 保留了 skill 的说明文本。可以把本仓库的脚本路径配置到自己的 Claude skill 中，让 Claude Code 在检查 fastp JSON 时自动调用：

```bash
python3 scripts/analyze_fastp.py /path/to/fastp_json_dir
```

更多“脚本输出 + Claude Code 决策回答”的展示见 [docs/decision_examples.md](docs/decision_examples.md)。
