# STEP 15 最终科研报告 — SS316LN 环状结构三维时空 CEEQ 场 Surrogate

日期: 2026-08-20
状态: **Production package 完成 — 限定有效域内的场 surrogate 交付；LOCKED 未读**
产物: `ml/production/step15_v1_2/`（PRODUCTION_MANIFEST.json + model/schema/runtime/tests/README）、`ml/final/step15_v1_2/`（冻结模型）、`ml/final/step15_v1_1/`、`ml/final/step15_v1/`（历史版本保留）

## 1. 科学目标

建立 SS316LN 环状/环形结构三维时空蠕变 CEEQ 场 surrogate：`[T,P,t,Rm,Ro,w] → CEEQ(x,y,z,t)`（2304 element-centroid 场），最终用于工程热点识别与蠕变场评估。

## 2–4. 数据与 Abaqus 模型

- 数据集：318 历史（STEP10–13，含 57 蠕变场 case）+ STEP14-A 27（独立 EXT）+ STEP15-G 新增 50（48×3000h + 2×1000h，非基准几何/高 P）→ **87 例可训练蠕变场 case（187 snapshots）**
- Abaqus 2024/Standard，MODEL_C Norton 蠕变（MAT-05 550/600/650°C 锁定参数）；318 ODB 全量审计（318/318 可读、拓扑统一 3072 节点/2304 单元、场输出全覆盖）

## 5–7. STEP14 标量基线 → STEP15 场表示

- STEP14：PhysB-quad scalar max-CEEQ 物理基线（TRAIN/VAL/TEST 闭环，EXT logMAE 1.22）——**物理参照物**
- STEP15：POD(log10 CEEQ, k=3) + 模态系数回归 → 场重构；**场内在维度≈2 的科学发现**（稳态蠕变=单空间模式×时间线性）

## 8–11. v1 → v1.1 → G.2 数据扩充 → v1.2

| 版本 | 结构 | EXT 27 overall logMAE |
|---|---|---|
| v1 | XGB + log1p(t)（树外推） | 1.166 |
| v1.1 | XGB + 解析 log10(t) + log10(P·Ro/w) | 0.591 |
| G.2 | +50 例真实 Abaqus（3000h×非基准几何×高 P） | — |
| **v1.2** | **Ridge-Poly2 + log10(P·Ro/w)（数据覆盖充分）** | **0.0314** |

## 12–17. 外部验证（EXT 27，冻结后一次性）

- **overall logMAE=0.0314 / logR²=0.9998 / relL2=0.148 / hotspot=27/27 / physics violations=0**
- 时间：500h 0.032（R² 0.9998）、750h 0.024（0.9999）、**3000h 0.038（0.9996）**
- 几何：基准 0.028、80/15/2 0.027、120/25/3 0.068、150/20/4 0.019
- 应力尺度：低 0.039 / 中 0.018 / 高（120–250）0.035；**geometry-dependent amplification 已学到**（P·Ro/w 特征生效）
- 热点：27/27（top5 0.33，如实记录）

## 18–19. 有效域与禁止外推区

**有效域**：T 550–650°C；P 2.5–30 MPa；t 1–3000h；Rm 80–150 / Ro 15–25 / w 2–5 mm；P·Ro/w ≤250。
**OUT_OF_DOMAIN（API 硬性守卫）**：T>650（DATA_REQUIRED）、t>3000、P>30、P·Ro/w>250。

## 20–21. Production 架构与限制

- `ml/production/step15_v1_2/`：predict_field / predict_time_series / get_hotspot API + domain/physics guard + 5 tests + PRODUCTION_MANIFEST（checksum ×6）
- **可复现性：与 G.4 保存预测零差异（max_abs_diff=0）**
- 限制：1000h 桥接层稀疏；P·Ro/w>250 未覆盖；700/750°C 无参数；EPP 塑性域（STEP13 遗留）与场 surrogate 无关

## 22–23. 未来数据扩展与可复现性

下一批建议：1000h×非基准几何（桥接）、高应力尺度（P·Ro/w>250）、t>3000h 验证层。全部流程 seed 42 确定性、脚本落盘、checksum 可追溯。

## 24. 最终科研结论

**"Within the validated domain, STEP15-v1.2 provides a three-dimensional spatiotemporal CEEQ field surrogate for SS316LN toroidal/annular structures."** —— 限定有效域内的场 surrogate，**不是万能 SS316LN 蠕变模型**；R²=0.9998 是场预测评价指标，不是工程百分比准确率。

**层级关系**：STEP14 = 标量 Norton 物理基线；**STEP15 = 三维空间场 surrogate（本项目最终 AI surrogate）**。

## 状态

PRODUCTION PACKAGE = **COMPLETE** ｜ INFERENCE API = COMPLETE ｜ REPRODUCIBILITY = **PASS（0 差异）** ｜ DOMAIN GUARD = **PASS** ｜ PHYSICS GUARD = **PASS** ｜ KNOWN CASE REGRESSION = **PASS（5/5 tests）** ｜ G.4 EXT VALIDATION = **PASS** ｜ LOCKED TEST = **NOT READ** ｜ 318 DATASET = **UNCHANGED** ｜ V1.1 = **UNCHANGED** ｜ V1.2 = **FROZEN**

---
*STEP 15 交付完成；数据链（318+27+50）、模型链（v1→v1.1→v1.2）、验证链（TRAIN/VAL/EXT/LOCKED）全部分层清晰、可复现、可审计。*
