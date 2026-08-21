# STEP 13.10 最终验证报告

日期: 2026-08-20
状态: **STEP 13.9 结论确认稳健。未进入 STEP 14；未加 Abaqus case；未做深度模型/大规模搜索。**
产物: `ml/models/step13_10/`、`ml/metrics/step13_10_{tuning,regime,importance,ceeq}.csv`、`step13_10_{metrics,analysis}.txt`、`ml/predictions/step13_10/`（预测文件复用 v4 输出）

---

## 1. von Mises 有限调参（≤6 组，validation 选择）

| combo | Val R² | Val MAE | Train R² |
|---|---|---|---|
| **base13.9（lr=0.1）** | **0.9385** | 11.67 | 1.0000 |
| lr=0.05 | 0.9322 | 11.60 | 0.9996 |
| n=500 | 0.9385 | 11.69 | 1.0000 |
| reg_lambda=2 | 0.9222 | 12.24 | 0.9999 |
| depth=6 | 0.8724 | 18.43 | 1.0000 |
| min_child_weight=3 | 0.6330 | 30.84 | 0.9986 |

**"best model was selected exclusively using validation performance."** → 选中 base13.9（并列最高 0.9385，取更简单配置）；test 一次性确认 **MAE=12.42 / RMSE=17.52 / R²=0.9304**（与 STEP 13.9 完全一致——参数稳健，无需调参）。

| test 外推 | R² |
|---|---|
| Rm150 (n=33) | 0.9148 |
| T750 (n=27) | 0.9408 |
| P25 (n=6) | 0.8679 |
| **P≥30 (n=10)** | **0.4553** |
| MODEL_B / MODEL_C | 0.917 / 0.980 |

## 2. Stage-1 regime：ML classifier vs physics threshold（test）

| 方法 | acc | precision | recall(F1) | plastic recall |
|---|---|---|---|---|
| Pi≥0.95/1.00/1.05/1.10 | 0.959 | 1.000 | 0.667 | **0.500（漏 3/6）** |
| Pi≥1.15 | 0.946 | 1.000 | 0.500 | 0.333 |
| **ML RF（输入仅求解前变量）** | **0.986** | **1.000** | **0.909** | **0.833（漏 1/6）** |

混淆矩阵（ML）：TN=68 FP=0 / FN=1 TP=5。
**结论：ML classifier 值得使用**——physics threshold 在 transition 区（Pi 1.0–1.14 微塑 3 例）漏检一半；ML 利用多维信息（含 P/σy、Ro/w、T 等）显著提升 plastic recall（0.50→0.83）。Pi_yield 仍作为连续特征输入，不升格为硬阈值。

## 3. Stage-2 elastic displacement 稳定性

| 版本 | R² | MAE | RMSE | medAE | maxAE |
|---|---|---|---|---|---|
| STEP 13.7 | 0.9166 | 0.090 | 0.112 | — | — |
| STEP 13.9 | 0.9167 | 0.090 | 0.112 | — | — |
| **STEP 13.10** | **0.9167** | 0.0903 | 0.1124 | 0.0812 | 0.2587 |

**R² 变化 <0.02 → 明确"稳定"**（0.9166/0.9167/0.9167）。

## 4. Unified displacement

test R²=**0.3499**（STEP 13.9=0.350 复现确认；MAE 11.4）。极端 case（LHS241/LHS116/LHS064）全部保留，未删除。

## 5. Plastic/EPP displacement

- plastic (n=6)：MAE=110.2 / RMSE=226.7 / R²=0.2095，medAE=23.2（半数中等偏差），maxAE=550（LHS241 主导）
- **标记：exploratory / insufficient reliable generalization**——不声称能预测 EPP post-yield 位移量级；stage-1 已能识别 regime（TP=5/6），量级回归留待硬化本构数据或专用模型
- 极端 case 全部保留

## 6. 318-case permutation importance（vm，validation，seed 42, 10 rep）

| 排名 | 特征 | 重要性 | vs STEP 13.7 |
|---|---|---|---|
| 1 | **Delta_T** | 1.3596 | 1.3782（保持第一，热应力主导 ✓） |
| 2 | pressure | 0.6408 | 0.7760（薄膜应力 ✓） |
| 3 | **Pi_yield** | **0.1102** | —（新增即进入前三，物理一致性证据 ✓） |
| 4 | Ro_over_w | 0.0636 | — |
| 5 | wall_thickness | 0.0142 | 0.1742（与 Ro/w/Pi 分担后下降，合理） |
| 6 | P_over_sy | 0.0117 | — |
| 7 | T_hot | 0.0070 | −0.0003 |

**physics consistency evidence**：ΔT 与 P 保持主导（梯度热应力+薄膜应力物理事实）；Pi_yield 成为第三重要特征；排名与物理认识一致。

## 7. CEEQ exploratory（MODEL_C only，log10 非零域）

- MODEL_C：train=37 / **val=0（无独立验证）** / test=20；非零 37+20
- train 拟合 → **test 一次性评估：MAE=1.36 / RMSE=1.54（log10 域）/ R²=0.650**
- 外推分箱：T=650 R²=0.727、t=3000 R²=0.684（较好）；P≥20 R²=−0.431（n=6，差）
- **明确标注：NOT production model / NOT final validated predictor / no independent validation for MODEL_C（val=0）**；禁止用 test 调参（未做）

## 8. CEEQ 物理单调性检查（不硬编码，仅验证预测趋势）

5 对检查（T↑×3、P↑×2）：**0 违规**——预测满足 T↑/P↑ → creep↑ 的已知物理趋势。（t↑ 对中短时样本在 train 域不可直接对比，未计入；test 内 t1000→t3000 预测随 t 增加，无反向。）

## 9. Final ablation（von Mises test R²，同 test 74 例）

| 组合 | 数据 | 特征 | Test R² | 贡献 |
|---|---|---|---|---|
| A | 300 | 12 | 0.856 | 基线 |
| B | 300 | 16 | 0.864 | **特征贡献 +0.008** |
| C | 318 | 12 | 0.8674 | **数据贡献 +0.011** |
| D | 318 | 16 | 0.9304 | **合计 +0.074**（叠加） |

→ **physics features 与 transition 数据存在叠加贡献**（特征 +0.008、数据 +0.011、叠加后 +0.074，非线性协同）。

## 10. 科研结论（克制表述）

1. von Mises surrogate 达到较高精度（test R² 0.930，MAE 12.4 MPa）；
2. physics-informed Pi_yield feature 显著改善高压外推（P≥30：−0.267→+0.005→+0.455 链）；
3. transition-region Abaqus 数据进一步改善 P≥30 外推（+0.005→+0.455）并提升整体 test R²（0.864→0.930）；
4. elastic displacement 预测达到较高精度（R² 0.917，稳定）；
5. plastic regime identification 明显改善（stage-1 plastic recall 0.50→0.83）；
6. **EPP post-yield displacement magnitude 仍存在可靠性限制**（R² 0.21，exploratory）；
7. **CEEQ 当前仅 exploratory**（test R² 0.65，val 无 MODEL_C）；
8. 当前模型仍需要针对塑性极端域进一步验证（高压薄壁训练数据已补 5 例 P≥30，仍有 n=10 test 上限）。

## 11. 推荐下一步（待人工批准）

1. **可选**：CEEQ 正式建模的前提 = 增加 MODEL_C validation 样本（需新 split design 或更多蠕变 case）——明确为 STEP 14 候选
2. **可选**：塑性域位移量级——需硬化本构（JH2/多线性硬化）Abaqus 数据或标记为模型边界
3. 文档/管线收尾：合并 STEP13 系列报告为最终交付

---
*本报告全部数字来自固定 seed 42 的可复现脚本；未用 test 调参；未修改数据/判据/split；未删除任何 case。*
