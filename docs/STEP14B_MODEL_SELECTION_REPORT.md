# STEP 14-B.4-6 模型选择与冻结报告

日期: 2026-08-20
状态: **模型已冻结 — TEST target 未读取；TRAIN+VAL refit 未执行；最终 TEST 评估未执行**
证据: `ml/metrics/step14b_model_selection.csv/json`、`step14b_model_trend_audit.json`、`step14b_final_audit.json`（15/15）、`ml/final/step14b_frozen_config.json`、`physb_quad_model.json`、`ml_benchmark_models.json`、`MODEL_REGISTRY.json`

## 1. MODEL SELECTION TABLE（10 候选，值来自 B.3 产物文件）

| model | family | CV R² | Val MAE | **Val RMSE** | Val R² | 趋势违规 | 选择 |
|---|---|---|---|---|---|---|---|
| **PhysB-quad** | physics (n 固定 n(T), T²) | — | 0.079 | **0.112** | **0.998** | NONE | **PRIMARY** |
| PhysA-quad | physics (n free) | — | 0.181 | 0.217 | 0.993 | NONE | |
| PhysA-lin | physics (n free) | — | 0.352 | 0.406 | 0.974 | NONE | |
| PhysB-lin | physics (n 固定) | — | 0.516 | 0.590 | 0.946 | NONE | |
| Linear | ML | 0.916 | 0.417 | 0.534 | 0.956 | NONE | benchmark |
| Poly-2 | ML | 0.992 | 0.744 | 0.773 | 0.907 | **8/9 t 对违反** | |
| Poly-3 | ML | 0.872 | 5.76 | 5.87 | **−4.35** | NONE | overfit |
| RF | ML | 0.895 | 1.07 | 1.10 | 0.811 | NONE | |
| HistGB | ML | −0.02 | 2.67 | 3.13 | −0.52 | **P 非单调** | |
| XGB | ML | 0.957 | 1.37 | 1.46 | 0.671 | NONE | |

## 2. 最终选择：**PhysB-quad（primary production model）**

**选择依据**（严格按规则）：
1. **第一优先（Val RMSE）**：0.112，全表最低（最佳 ML Linear 0.534，低 4.8 倍）
2. **第二优先（物理合理性）**：Norton 幂律结构 + 固定 n(T)（9.51/9.04/7.57），与 318 数据集蠕变物理一致
3. **第三优先（复杂度）**：3 参数解析式，全表最简
4. **第四优先（CV 稳定性）**：解析拟合无随机性；无趋势违规

**明确记录**：*Physics baseline outperforms ML baseline; ML does not demonstrate additional predictive capability beyond the known Norton power-law structure in the present dataset.* —— 这是科研结果，不是失败。

## 3. 冻结内容（`ml/final/step14b_frozen_config.json`）

- train 37 / validation 18 / test 9 / locked 20；dataset checksum `20f21ebc67ea`
- 特征 9（顺序锁定）、target log10(CEEQ)（定义锁定）、time=log1p(time)、scaler=train-fold only、seed 42
- **模型公式**：log10(CEEQ) = a + b₁T + b₂T² + n(T)·log10 P + log10 t；n(T)={550→9.51, 600→9.04, 650→7.57}（Norton 锁定，未修改）
- 系数（TRAIN-only 拟合）：a、b₁、b₂ 存于 `physb_quad_model.json`（val R²=0.998）

## 4. 趋势审计（`step14b_model_trend_audit.json`）

Poly-2（8/9 t 对）与 HistGB（P 非单调）标记 physics_trend_violation=true；未修改输出。

## 5. 15/15 FINAL AUDIT PASS

TRAIN/VAL/TEST/LOCKED 数量、四集无重复、locked 未入训练、**TEST target 未读取（y_test.npy 不存在）**、locked target 未读取、318 checksum unchanged、split unchanged、特征/目标/scaler 锁定、选择冻结、生产模型与 freeze 一致。

---
*TEST 完全隔离；所有选择基于 TRAIN CV + VALIDATION 指标。*
