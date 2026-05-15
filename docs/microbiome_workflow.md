# 微生物组数据分析流程说明

本文档用于展示从 FASTQ 原始数据出发，可以完成哪些微生物相关生信分析结果。可作为 GitHub 项目说明、简历作品集补充材料或面试讲解提纲。

## 1. 原始数据质控

输入：双端或单端 FASTQ 文件。

常见任务：

- 使用 fastp 去除低质量 reads、接头序列和过短 reads
- 汇总 reads 数量、过滤率、Q20/Q30、GC content 和碱基组成
- 使用 MultiQC 或本项目脚本汇总多样本质控结果

输出：

- 过滤后的 FASTQ
- fastp HTML/JSON 报告
- 多样本 `qc_summary.csv`
- 样本是否适合进入后续分析的质控结论

## 2. 物种组成分析

适用数据：16S、宏基因组、宏转录组。

常见任务：

- 去除宿主污染 reads
- 使用 Kraken2、MetaPhlAn、Centrifuge 等工具进行物种注释
- 生成门、纲、目、科、属、种不同分类水平的丰度表
- 比较不同组之间的群落组成差异

输出：

- taxonomy abundance table
- 物种组成柱状图
- heatmap
- alpha diversity 和 beta diversity 结果
- PCoA/NMDS 等降维可视化

## 3. 功能注释分析

适用数据：宏基因组、宏转录组、纯菌基因组。

常见任务：

- 宏基因组组装或 reads-based 功能注释
- 使用 HUMAnN、eggNOG-mapper、KEGG、COG、CAZy、CARD 等数据库进行功能分析
- 统计通路、基因家族、抗性基因或碳水化合物活性酶丰度

输出：

- gene family abundance table
- pathway abundance table
- KEGG/COG/CAZy/CARD 注释表
- 功能组成柱状图、热图和差异功能结果

## 4. 差异分析

适用数据：转录组、宏转录组、宏基因组丰度表。

常见任务：

- 构建样本分组信息表
- 对物种、功能或基因表达矩阵进行标准化
- 使用 DESeq2、edgeR、LEfSe、ANCOM-BC 或 MaAsLin2 等方法寻找差异特征
- 结合实验设计解释差异物种、差异通路或差异表达基因

输出：

- 差异物种表
- 差异功能表
- 差异表达基因表
- volcano plot、MA plot、boxplot、heatmap

## 5. 可视化与报告

常见任务：

- 使用 R 或 Python 绘制质量控制、物种组成、功能组成和差异分析图
- 整理可复现的分析命令、参数和软件版本
- 将关键结果写入 Markdown、HTML 或 PPT 报告

输出：

- 项目分析报告
- 论文或组会可用图表
- 可复现的流程记录

## 简历表达示例

可在简历中写为：

> 熟悉微生物相关多组学数据分析流程，能够在 Linux 公共服务器上完成 FASTQ 质控、物种组成分析、功能注释、差异分析和结果可视化；使用 Python/Claude Code 构建 fastp JSON 多样本质控汇总工具，实现质控指标自动提取、阈值判断和 CSV 报告输出。
