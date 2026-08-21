# STEP 15-G.2 Abaqus 数据生成报告（50 例新增）

日期: 2026-08-20
状态: **数据生成 + QC 完成 — 未训练 v1.2、未修改 v1.1、LOCKED 未读**
目录: `simulation/generated_cases_step15g/`（50 例 .inp/.odb/.sta/.msg/.dat 全保留）+ `ml/data/step15g_snapshots/*.npz`（CEEQ 场 2304）

## 1. 执行摘要

- PRE-SOLVE：**50/50 PASS**（锁定设计 CSV、ID/参数唯一、历史/EXT27/locked 零重复、Norton 卡值核对、几何校验）
- 求解：**50/50 COMPLETED**（Abaqus 2024, cpus=4, ~23 min, 27–29s/case；0 失败、0 license 异常）
- ODB QC：50/50 可读；**拓扑全部 3072 节点/2304 单元一致**；CEEQ 提取 50/50（NaN=0/Inf=0/负=0）
- 场定义与 STEP15-B 完全一致（element centroid CEEQ, 2304 维, 最终帧）

## 2. 覆盖统计

| 指标 | 数值 |
|---|---|
| t=3000h | **48**（P1×36 + P1b×12） |
| t=1000h | 2（P2 桥接——50 截取后 1000h 块未满，如实记录） |
| 非基准几何 | **5 种**：120/25/3×14、80/15/2×12、90/18/3×9、110/22/4×9、150/20/4×6 |
| P≥25 | **12**（25/30 × 薄壁 3000h） |
| P·Ro/w | **25–250**（中低应力尺度密集；>250 高应力域未覆盖——设计集中所致） |
| T | 550/600/650（**0 例 700/750**，DATA_REQUIRED 遵守） |
| 重复 | 历史 0 / locked 0 / EXT27 0 |

## 3. 物理 QC

- 趋势检查（同几何 t=3000 组内 P 单调）：**0 违规**
- 物理警告：**0**
- 新数据无 NaN/Inf/负；CEEQ 幅度 1.3e-10..2.0e-5（含高应力薄壁放大，物理合理）

## 4. 数据保护

318 `20f21ebc67ea`、locked `fa573e330926`、v1.1 freeze manifest 均 unchanged；LOCKED 未读；v1.1 模型未动。

## 5. 遗留说明（如实）

- 1000h 桥接层新增仅 2 例（截取策略所致）——**现有 1000h 历史 14 例 + 新增 2 例仍偏少**；若 v1.2 需要更强桥接，建议 STEP 15-G.3 补充 1000h 块（约 10–15 例）
- P·Ro/w >250 高应力域未新增（设计优先级所致）——记录为次要缺口

## 6. 状态声明

STEP 15-G.2 COMPLETE ｜ NEW CASES = 50/50 ｜ ABAQUS SUCCESS = 50/50 ｜ ODB QC PASS = 50/50 ｜ CEEQ EXTRACTION PASS = 50/50 ｜ HISTORICAL DUPLICATE = 0 ｜ LOCKED DUPLICATE = 0 ｜ LOCKED TEST READ = **NO** ｜ 318 DATASET MODIFIED = **NO** ｜ V1.1 MODIFIED = **NO** ｜ V1.2 TRAINING = **NOT STARTED**

---
*产物：`step15_g_presolve.json`、`step15_g_solve_results.csv`（odb_qc 内）、`step15_g_odb_qc.csv`、`step15_g_field_statistics.csv`、`step15_g_geometry_coverage.csv`、`step15_g_time_coverage.csv`、`step15_g_physics_audit.json`、`step15_g_final_audit.json`。*
