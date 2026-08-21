# STEP 14-B.8 TEST 一次性评估报告

日期: 2026-08-20
状态: **TEST 首次且唯一一次读取完成 — 模型未动；LOCKED TEST 未读；等待批准 B.9**
证据: `ml/metrics/step14b_test_results.csv`、`step14b_test_evaluation.json`、`step14b_test_audit.json`（11/11 PASS）

## 0. 定位声明

**STEP 14-B.8 evaluates the frozen scalar max-CEEQ surrogate on the untouched 9-case TEST set.**
**PhysB-quad is the primary model for the STEP 14 scalar max-CEEQ task only.**
（不是最终三维场 AI 模型；三维时空蠕变 surrogate 属 STEP 15 规划。）

## 1. TEST 数据与模型

- TEST：STEP14-A.9 的 9 例（t=3000h、非基准几何拉丁方）；target 本步骤首次读取
- 模型：PhysB-quad（TRAIN+VAL refit55，`ml/final/step14b_refit_model.json`）；benchmark：Linear（train-fit）
- 训练/选择/refit 均未触碰 TEST

## 2. 逐 case 结果（log10 域）

| case | T | P | 几何 | y_true | y_pred | abs_err |
|---|---|---|---|---|---|---|
| CEEQ14A_T550_P10_…Rm120_Ro25_w3 | 550 | 10 | 120/25/3 | −9.288 | −11.337 | 2.048 |
| CEEQ14A_T550_P20_…Rm150_Ro20_w4 | 550 | 20 | 150/20/4 | −8.828 | −8.474 | 0.355 |
| CEEQ14A_T550_P5_…Rm80_Ro15_w2 | 550 | 5 | 80/15/2 | −12.660 | −14.199 | 1.540 |
| CEEQ14A_T600_P10_…Rm150_Ro20_w4 | 600 | 10 | 150/20/4 | −10.817 | −10.602 | 0.215 |
| CEEQ14A_T600_P20_…Rm80_Ro15_w2 | 600 | 20 | 80/15/2 | −6.295 | −7.881 | 1.586 |
| CEEQ14A_T600_P5_…Rm120_Ro25_w3 | 600 | 5 | 120/25/3 | −11.254 | −13.323 | 2.070 |
| CEEQ14A_T650_P10_…Rm80_Ro15_w2 | 650 | 10 | 80/15/2 | −6.954 | −8.248 | 1.294 |
| CEEQ14A_T650_P20_…Rm120_Ro25_w3 | 650 | 20 | 120/25/3 | −4.302 | −5.969 | 1.667 |
| CEEQ14A_T650_P5_…Rm150_Ro20_w4 | 650 | 5 | 150/20/4 | −10.740 | −10.526 | 0.214 |

## 3. Overall 指标（log10 域）

| 模型 | MAE | RMSE | R² | max_err | median_err |
|---|---|---|---|---|---|
| **PhysB-quad (refit55)** | **1.221** | **1.415** | **0.692** | 2.070 | 1.294 |
| Linear (benchmark) | 1.518 | 1.892 | 0.449 | 2.91 | 1.52 |

物理基线在 TEST 上仍优于 ML benchmark（R² 0.69 vs 0.45）——ML 未提供额外能力（延续 B.3 结论）。

## 4. 分组误差

| 分组 | n | MAE | RMSE | R² |
|---|---|---|---|---|
| T=550 / 600 / 650 | 3/3/3 | 1.31/1.29/1.06 | 1.49/1.51/1.22 | 0.24/0.55/0.79 |
| P=5 / 10 / 20 | 3/3/3 | 1.27/1.19/1.20 | 1.49/1.40/1.34 | −2.39/0.22/0.47 |
| **geo (150,20,4)** | 3 | **0.261** | 0.269 | **0.914** |
| geo (120,25,3) | 3 | 1.928 | 1.937 | 0.562 |
| geo (80,15,2) | 3 | 1.473 | 1.479 | 0.732 |

## 5. 时间外推（t=3000h，train 1–300/val 500–750）

TEST R²=0.692 vs VAL R²=0.998：时间外推导致明显性能降级（MAE 0.079→1.22，~15×）。Norton 幂律的 ∝t 项本身外推正确（无系统性时间漂移证据），主要误差来自几何项缺失与 P 幂律在非基准应力水平下的偏差。

## 6. Geometry domain shift（核心局限，如实记录）

- 已知 ×50 几何效应（T650/P20: 基准 9.9e-7 vs (120,25,3) 4.99e-5）
- **PhysB-quad 预测 1.07e-6 vs 真实 4.99e-5——低估 ~47×**；几何分组显示 (150,20,4)（最接近基准应力比 7.5）误差最小（MAE 0.26）、(120,25,3)（应力比 8.33）误差最大（1.93）
- **结论（明确记录）**：*"当前 PhysB-quad 只包含 T、P、t 的 Norton 结构及全局几何固定条件下的标量基线，因此不能充分表达 geometry-dependent spatial/mechanical effects。"* 这不是程序错误，而是模型结构（无几何应力项）的预期局限——指向 STEP 15 场级模型与几何显式建模的必要性。

## 7. 物理合理性检查

- CEEQ>0 ✓、finite ✓、无 NaN/Inf ✓
- 预测范围 6.3e-15..1.1e-6 与 train/val 域（~1e-19..2.5e-7）可比，无爆炸外推
- **1 项 mild violation 记录**：按 P·Ro/w 排序的预测单调性轻微违反（模型无几何项所致）→ physics_trend_violation 如实记录，未修改输出

## 8. Leakage audit：11/11 PASS

TEST target 仅 B.8 读取一次；LOCKED TEST 未读；TEST 未用于训练/refit/调参/选择；refit 与冻结选择未变；318 checksum `20f21ebc67ea` 与 split checksum `fa573e330926` unchanged。

## 9. 科研结论

1. 冻结的 PhysB-quad 在**从未触碰的 TEST**（双重外推：3000h + 非基准几何）上 R²=0.692（log10 域），量级正确但几何域 shift 未被表达（(120,25,3) 低估 ~47×）
2. 物理基线持续优于 ML benchmark（TEST R² 0.69 vs 0.45）——**无证据表明 ML 对已知 Norton 幂律提供额外预测能力**（本数据范围）
3. 当前模型为标量 max-CEEQ 基线；**三维场预测不属于本阶段**（STEP 15）

---
*TEST 为最终一次性评估；无任何模型修改/重选；LOCKED 20 例保持隔离。*
