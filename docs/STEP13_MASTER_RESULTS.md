# STEP 13 总体结果表（Master Results）

日期: 2026-08-20
范围: STEP 13.1–13.10 完整整合（数据 → 审计 → 基线 → physics-informed → transition 数据 → 最终验证）
最终产物: `ml/final/`（模型+配置+校验和）、`docs/STEP13_FINAL_REPORT.md`

---

## A. 数据集演化

| 版本 | 内容 | total | valid_for_AI | 质量分级 (A/B/D/E) | physics_ref |
|---|---|---|---|---|---|
| STEP 12B (v3) | v1 222 + v3 78 | **300** | **224** | 114/110/49/27 | 76 |
| STEP 13.8A | +18 physics-transition Abaqus case | **318** | **242** | 132/110/49/27 | 76 |
| 变化 | 18 例全部真实求解、Grade A | +18 | +18 | +18 A | 0 |

数据来源链: 222（STEP 10/11 批量 + 基准）→ 78（STEP 12B 精选，675/725 插值 σy 等空洞填补）→ 18（STEP 13.8 设计，Pi_yield 0.7–1.5 过渡区）。

## B. Valid 演化

| 阶段 | valid_for_AI | 说明 |
|---|---|---|
| v1 (222) | 150 | 67.6% |
| v3 (300) | 224 | 74.7%（78 例中 74 valid，4 例 550/600 DATA_REQUIRED） |
| v4 (318) | **242** | 76.1%（18 例全 A） |

## C. Split 演化

| 版本 | train | validation | test | 规则 |
|---|---|---|---|---|
| STEP 12B | 107 | 47 | 70 | 修复前（含 Rm150 入 train 缺陷） |
| STEP 13.5 | 104 | 46 | 74 | 问题 A 修复（v1 150 例 0 变化） |
| **STEP 13.9 (318)** | **120** | **48** | **74** | v1 150 例逐 case 不变 + 新 18 例 16/2/0 |

test 74 例外推区恒常：T750 n=27、Rm150 n=33、P≥30 n=10、蠕变 t≥1000 n=18——全阶段对照可比。

## D. 特征演化

| 版本 | 特征 | 内容 |
|---|---|---|
| STEP 13.5 | 12 | R_major, R_outer, wall, pressure, log1p(time), T_hot, ΔT, E, σy, A_creep, n_creep, model_type_C |
| STEP 13.7+ | **16** | + Pi_yield (P·Ro/(w·σy)), Ro/w, P/σy, σy/E（physics-informed，σy 缺失 0 填充+model_type 编码） |

## E. 模型演化（max_von_mises，同一 test 74 例）

| 版本 | 模型 | 数据/特征 | Val R² | Test R² | P≥30 R² |
|---|---|---|---|---|---|
| STEP 13.6 | XGB0 | 300/12 | 0.896 | 0.856 | **−0.267** |
| STEP 13.7 | XGB(all) | 300/16 | 0.901 | 0.864 | +0.005 |
| STEP 13.9 | XGB(all) | 318/16 | 0.9385 | 0.9304 | +0.4553 |
| **STEP 13.10（最终锁定）** | XGB(all, base 参数) | 318/16 | **0.9385** | **0.9304** | **+0.4553** |

## F. 位移模型演化

| 版本 | 方案 | 结果 |
|---|---|---|
| STEP 13.6 | unified（全部模型） | test R²≈−0.018（失败） |
| STEP 13.6A | 分解诊断 | elastic R²=0.916 / plastic 失败（EPP 主导） |
| STEP 13.7 | regime-aware（stage-1 + stage-2 linear） | elastic R²=0.917；stage-1 正样本 1 |
| STEP 13.9 | 318 数据重训 | stage-1 正样本 11、test acc 0.986；elastic 0.917 稳定；unified 0.350 |
| **STEP 13.10（最终定义）** | 三阶段（见 STEP13_FINAL_REPORT §4） | stage-1 acc 0.986/pl-recall 0.833；stage-2 R²=0.9167；stage-3 exploratory |

## G. 关键证据链

1. **Pi_yield transition（18 例 Abaqus）**：Pi<1 全弹性 → 1.00–1.14 onset（700/750°C 微屈服 @1.002/1.005；650°C 弹性 @0.999）→ >1.14 塑性饱和
2. **ML vs 物理阈值**：plastic recall 0.833（ML）vs 0.50（Pi≥1）→ classifier 胜出，Pi_yield 保持连续特征
3. **Ablation**：A=0.856 → B=0.864（特征 +0.008）→ C=0.8674（数据 +0.011）→ D=0.9304（叠加 +0.074）
4. **重要性**：ΔT > P > Pi_yield > Ro/w（物理一致）

---
*本表全部数字来自固定 seed 42 可复现脚本；历史 STEP13.x 结果全部保留未动。*
