# STEP 15-E v1.1 训练与内部验证报告

日期: 2026-08-20
状态: **v1.1 已训练（TRAIN/VAL 内部验证完成）— 未冻结、EXT 未重测、LOCKED 未读**
定位: v1.1 修复版场 surrogate（解析时间项 + 几何应力尺度特征）
产物: `ml/final/step15_v1_1/`（pod_basis_v11.npz）、`ml/metrics/step15_e_v11_*.json/csv`

## 1. 数据与 POD

- case-level split（31/6/27诊断/20锁定）；POD = **log10(CEEQ) 域、TRAIN-only 重拟合、k=3**（k=3/4/5 累计方差均 1.0，k=3 选为最简）
- 时间网格 1/3/10/30/100/300h（零外推）

## 2. 时间结构（核心修复）

- **解析时间项**：c_i = g_i(T,P,geom) + **d_i·log10(t)**；全局斜率 d=[32.56, −0.14, −0.22]（TRAIN pooled 拟合，与 D.1 证据一致）
- **外推诊断（300→500→750→1000h）**：VAL 全部 6 例预测最大 CEEQ 严格单调增长（如 3.00e-13→4.24e-13→5.59e-13→6.79e-13）——**v1 的树常数外推缺陷已修复**
- 注意：3000h 的**精度**未评估（EXT 未读）；单调性由结构保证，准确率待冻结后 EXT 验证

## 3. Geometry 特征

- 新增 **log10(P·Ro/w)**（D.2 证据 r=0.836）；Ablation 显示其对 VAL 域贡献边际（VAL 几何单一），对非基准几何的表达能力待 EXT 验证

## 4. Ablation（VAL，18 snapshots）

| 模型 | val_logMAE | field MAE | hotspot | top5 |
|---|---|---|---|---|
| A: v1 架构（XGB no-analytic） | 0.0119 | 1.4e-15 | 1.00 | 1.00 |
| B: +log10(P·Ro/w) | 0.0083 | 1.7e-15 | 1.00 | 1.00 |
| C: 解析时间、无 stress | 0.0119 | 1.4e-15 | 1.00 | 1.00 |
| **D: 解析时间 + stress（推荐）** | **0.0083** | 1.7e-15 | **1.00** | **1.00** |
| D-RF | 0.0439 | 7.4e-15 | 1.00 | 1.00 |
| D-RidgePoly | 0.0193 | 2.9e-15 | 1.00 | 1.00 |

**VAL 局限（如实）**：VAL 全在 t≤300h 插值层 → 所有候选近完美，VAL 无法区分时间外推；候选间差异极小 → 选择主要依据结构合理性（解析时间项必须存在）+ 简洁性 → **推荐 D（XGB + 解析时间 + log10(P·Ro/w)）**，但最终时间/几何外推能力必须由冻结后 EXT 判定。

## 5. 物理审计：0 violations（CEEQ≥0、finite）

## 6. 泄漏与数据保护

EXT 27 仅 C.2 诊断（未参与 v1.1 训练/特征/选择）；LOCKED 未读；scaler/POD TRAIN-only；318 `20f21ebc67ea`、locked `fa573e330926` unchanged；v1 完整保留。

## 7. 结论与推荐

v1.1（Candidate D）已在结构上修复 v1 的两个缺陷：解析时间外推（单调性诊断通过）与显式几何应力尺度特征。**v1.1 NOT FROZEN**——冻结与 EXT 一次性验证需 STEP 15-F 批准；3000h 外推的最终判定权在 EXT。

---
*声明：EXT target NOT READ（本阶段）；LOCKED TEST NOT READ；v1.1 NOT FROZEN；no new Abaqus cases；318 dataset unchanged。*
