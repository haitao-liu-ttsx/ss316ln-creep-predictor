# STEP 14-B.2/3 CEEQ 基线与物理参照报告

日期: 2026-08-20
状态: **B.2 审计 15/15、B.3 基线审计 12/12 PASS — 模型选择/冻结/TEST 评估未执行**
证据: `ml/metrics/step14b_feature_target_audit.json`、`step14b_cv_results.csv`、`step14b_baseline_comparison.csv`、`step14b_trend_check.json`、`step14b_baseline_audit.json`

## 1. Feature 定义（锁定）

9 特征（顺序固定）：`["T_hot", "pressure", "log1p_time", "Rm", "Ro", "w", "E", "A_creep", "n_creep"]`；时间变换 = **log1p(time)**（STEP13 定义，非 log10）。MODEL_C 中 Delta_T/σy/model_type_C/Pi_yield/P_over_sy/sy_over_E 为常数/零，排除。泄漏审计：A_creep/n_creep/E 均为求解前材料输入（MAT-05 表/公式），非 target 派生 ✓。

## 2. Target 定义（锁定）

log10(CEEQ)——最终帧、元素场 max、非零域、无 epsilon；train 37/37、val 18/18、test 9/9 全正。**TEST target 在 B.2/B.3 完全未读取**（quarantine）。

## 3. 物理幂律基线（解析式，n free vs n fixed）

log10 CEEQ = a + b₁T (+b₂T²) + n·log10 P + log10 t

| 模型 | 拟合 n | Train MAE/RMSE/R² | **Val MAE/RMSE/R²** |
|---|---|---|---|
| **PhysA-quad（n free）** | 8.57 | 0.240/0.345/0.985 | **0.181/0.217/0.993** |
| **PhysB-quad（n 固定 n(T)）** | 9.51/9.04/7.57 | 0.143/0.298/0.989 | **0.079/0.112/0.998** |
| PhysA-lin | 8.53 | 0.419/0.518/0.966 | 0.352/0.406/0.974 |
| PhysB-lin | 固定 | 0.591/0.698/0.938 | 0.516/0.590/0.946 |

**Norton 指数检查**：拟合 n=8.57 vs Norton 9.51（P×2 → log10 ratio 理论 2.86，拟合 2.58，偏差 ~10%——因训练集 P 网格粗（5/10/20 仅 3 档）与几何/应力系数未显式建模所致；如实报告）。**PhysB-quad 以固定 n(T) 为最优物理基线（val R²=0.998）**。

## 4. ML 基线（5-fold CV, seed 42, Pipeline 内预处理）+ Validation 独立评估

| 模型 | CV MAE/RMSE/R² | Val MAE/RMSE/R² | Val max_err |
|---|---|---|---|
| Linear | 0.619/0.807/0.916 | 0.417/0.534/0.956 | 0.89 |
| Poly-2 | 0.180/0.245/0.992 | 0.744/0.773/0.907 | 1.11 |
| Poly-3 | 0.234/0.999/0.872 | 5.76/5.87/**−4.35** | 6.92 |
| RF | 0.717/0.907/0.895 | 1.07/1.10/0.811 | 1.63 |
| HistGB | 2.34/2.82/−0.02 | 2.67/3.13/−0.52 | 6.03 |
| XGB | 0.395/0.576/0.957 | 1.37/1.46/0.671 | 2.03 |

- Poly-3/HistGB 严重过拟合（train 37 样本不足）；Poly-2 CV 好但 val 退化
- **最佳 ML = Linear（val R²=0.956）**，仍低于 PhysB-quad（0.998）

## 5. 核心科学回答（B.3 阶段结论）

**"ML 相对已知物理幂律模型是否提供额外预测能力？"——目前答案：不。**
PhysB-quad（固定 Norton n(T) + T² 温度项 + log10 P + log10 t）在独立 validation 上 R²=0.998 / MAE=0.079（log10 域），**优于全部 6 个 ML 模型**（最佳 Linear 0.956）。这符合预期：Norton 蠕变本质是幂律，物理形式先验 > 数据驱动拟合（n=37 小样本）。

## 6. 物理趋势检查（validation 预测）

- linear/rf/xgb/poly3：无违规（t 750>500、P 单调）✓
- **poly2：8/9 的 t 对违反**（预测 750<500）——记录 physics_trend_violation=true
- **histgb：3 个温度下 P 非单调**——记录
- 违规模型自动失去物理合理性加分（不修改）

## 7. 下一步（B.4-B.6，待批准）

模型选择将按规则（VAL RMSE 优先 + 简单性/物理合理性）：当前候选 = **PhysB-quad（物理基线）vs Linear（最佳 ML）**；B.5 将构建完整 MODEL_SELECTION_TABLE 并冻结。若选择物理基线，则 CEEQ production 为"物理幂律 + 可选 ML 残差校正"结构——B.6 冻结时决定。
