# STEP 13.6 Baseline AI 报告 — SS316LN Toroidal Tube Surrogate

日期: 2026-08-20
状态: **第一轮 baseline 完成。未做深度模型/大规模调参/数据修改。**
环境: `ml/.venv`（Python 3.10.5, sklearn 1.7.2, xgboost 3.2.0, seed=42）
证据: `ml/metrics/baseline_metrics.csv`、`ml/metrics/extrapolation_report.txt`、`ml/predictions/*.csv`、`ml/figures/*.png`

---

## 1. 数据与任务

- 300 case 数据集（STEP 12B），valid_for_AI=224 进入建模；train 104 / validation 46 / test 74（STEP 13.5 修复后划分）
- 特征 12：R_major, R_outer, wall_thickness, pressure, log1p(time), T_hot, Delta_T, E_GPa, σy(0填充), A_creep(0填充), n_creep(0填充), model_type_C
- Target：max_displacement（raw + log1p→expm1 双轨）、max_von_mises（raw）
- 模型：Dummy / Linear / Ridge / RF(300) / HistGB / XGBoost（保守参数，无搜索）

## 2. 主结果（MAE / RMSE / R²）

### max_von_mises (MPa)

| 模型 | Train R² | Val MAE | Val RMSE | Val R² | Test MAE | Test RMSE | Test R² |
|---|---|---|---|---|---|---|---|
| Dummy | 0.000 | 48.5 | 56.8 | -0.000 | 55.2 | 66.4 | -0.000 |
| Linear | 0.454 | 63.0 | 74.6 | -0.723 | 67.5 | 89.2 | -0.803 |
| Ridge | 0.357 | 69.4 | 80.7 | -1.018 | 68.8 | 86.9 | -0.712 |
| RF | 0.898 | 16.6 | 27.7 | 0.762 | 18.7 | 30.9 | 0.783 |
| HistGB | 0.513 | 40.2 | 48.5 | 0.271 | 40.7 | 51.2 | 0.407 |
| **XGB** | **0.999** | **14.8** | **18.3** | **0.896** | **16.0** | **25.2** | **0.856** |

→ **von Mises 最佳模型 = XGBoost**（validation 选择，test 一次性确认）。
（注: 2026-08-20 STEP 13.6A 已独立重算全部 54 组合指标，RMSE≥MAE 违规 0、与 csv 失配 0；本表早期版本曾以 "Train R² | Val MAE/RMSE/R² | Test MAE/RMSE/R²" 压缩展示，指标本身无 bug。详见 `docs/STEP13_BASELINE_AUDIT.md`）

### max_displacement (mm)

| 模型 | Train R² | Val R² | Test MAE/RMSE/R² |
|---|---|---|---|
| 全部 6 模型（raw 与 log1p） | 0.83–0.86 | −0.04 ~ −0.05 | 10.5–10.9 / 81.2 / **≈−0.017** |

→ **位移整体 R²≈−0.017 的表象已被 STEP 13.6A 分解（docs/STEP13_BASELINE_AUDIT.md）**：弹性域（PEEQ=0, n=68）位移预测实际优秀（MAE=0.090, R²=0.916）；失败完全由 6 个塑性 case（PEEQ>0）主导（MAE=128, R²=−0.252），其中 LHS241 单点 697 mm 主导 RMSE。本质 = **elastic→plastic regime transition + EPP 屈服后无硬化流动**，不是一般回归或变换问题（raw vs log1p 无实质差异；Rm150 子箱 raw 0.617 vs log1p 0.065）。

## 3. 外推评估（XGB-vm / Linear-disp，test 分箱）

| 外推轴 | 分箱 | von Mises R²（XGB） | displacement R²（linear） |
|---|---|---|---|
| 温度 | T≤700 (n=45) | 0.840 | 0.921 |
| | T=725 (n=2) | —（样本过少） | — |
| | **T=750 (n=27)** | **0.872 ✅** | −0.048 ❌ |
| 压力 | P≤20 (n=58) | 0.929 | −0.025 |
| | P=25 (n=6) | 0.453 | 0.948 |
| | **P≥30 (n=10)** | **−0.267 ❌（von Mises）** | **−0.111 ❌（displacement）** |

注（STEP 13.7 口径统一）：P≥30 的两个数字分属不同 target——−0.267 为 XGB-von Mises（MAE 44.4/RMSE 50.7 MPa），−0.111 为 linear-displacement（MAE 69.6/RMSE 219.7 mm）。报告 P≥30 一律标注 target。STEP 13.7 加入 physics 特征后 von Mises 的 P≥30 改善至 **+0.005**（见 `STEP13_7_PHYSICS_INFORMED_REPORT.md`）。
| 几何 | Rm≤120 (n=39) | 0.798 | −0.031 |
| | **Rm=150 (n=33)** | **0.890 ✅** | 0.617 |
| 蠕变时间 | t≤300 (n=56) | 0.841 | −0.023* |
| (MODEL_C) | **t=1000 (n=14)** | **0.813 ✅** | **0.939 ✅** |
| | **t=3000 (n=4)** | **0.999 ✅** | **0.808 ✅** |

*CT≤300 含非蠕变 case（t=0）→ 位移 R² 被 MODEL_B 污染；MODEL_C 单独看（下）。

**科学外推结论**：
- ✅ **T=750 外推成功**（vm R²=0.872；train 无 750）
- ✅ **Rm=150 外推成功**（vm R²=0.890；train 无 Rm150，本专项构造的外推区）
- ✅ **蠕变短时→长时外推成功**（MODEL_C 位移 train 0.878→test 0.960；t=1000/3000 R²=0.939/0.808）——**AI 能从短时蠕变行为外推长时**，这是本项目最有价值的科学结论之一
- ❌ **P≥30 外推失败**（vm R²=−0.267）——高压薄壁域进入 EPP 塑性流动，train 无此类样本

## 4. MODEL_B vs MODEL_C

| 分组 | von Mises test R² | displacement test R² |
|---|---|---|
| ALL | 0.856 | −0.017 |
| MODEL_B (n=54) | 0.832 | −0.024 |
| MODEL_C (n=20) | 0.902 | 0.960 |

- **von Mises：统一模型两型均良好**（0.832/0.902）→ 统一模型 + model_type 特征可行
- **displacement：MODEL_C 极好（0.960）而 MODEL_B 失败（−0.024）** → 位移目标必须分模型或排除 EPP 流动 case（报告不删除，仅分析）
- validation 无 MODEL_C（结构缺口，已在 STEP 13.5 记录）→ MODEL_C 的 val 指标 = unavailable，MODEL_C 结论以 test 时间外推为准

## 5. A+B vs A-only 敏感性（test）

| Target | A+B R² | A-only R² | 结论 |
|---|---|---|---|
| von_mises | 0.856 | **0.046** | **B 级数据（插值 σy/梯度/蠕变）是决定性帮助** |
| displacement | −0.017 | −0.017 | 均失败，无差异 |

→ 回答"B 级数据帮助还是偏差"：**A-only 训练在 test 上几乎失效（R² 0.05），A+B 大幅胜出**。B 级插值/derived 数据没有引入偏差，而是填补了参数空间（A-only train 仅 47 例，缺梯度覆盖）。A-only 仅作敏感性，主数据集保持 A+B。

## 6. PEEQ / CEEQ

- **max_PEEQ：train 非零仅 1 例（1.0%）→ insufficient positive training samples：不建立、不声称两段 PEEQ 模型**（严格按批准约束）
- **max_creep_strain：train 非零 15 例（14.4%）、validation 非零 0 例（0.0%）** → validation 无法独立验证 MODEL_C 蠕变；零值不能删除后声称完整预测；本轮仅 exploratory 统计，未训练 CEEQ 回归。MODEL_C 的蠕变结论以 test 时间外推为准（§3）

## 7. 过拟合检查

- XGB：train R²=0.999 vs val 0.896 vs test 0.856 —— **存在轻度过拟合**（train 近完美，外推下降 15%），但未崩坏；属可接受基线
- RF：0.898/0.762/0.783 —— 更稳健但精度低
- Linear/Ridge：train 低（0.36–0.45）且 val/test 负 → 欠拟合（强非线性）
- 结论：**如实标注 XGB 过拟合倾向**；未用 test 调参

## 8. 最严重失败 case

| case | 现象 | 根因 |
|---|---|---|
| LHS241 (750°C, P40, Rm100, **wall=2**) | 位移 697 mm，PEEQ=40.3 | **EPP 无硬化塑性流动**：vm=199=σy(750)，屈服后应变无约束增长。物理真实（EPP 模型内），工程上退化（真实 316LN 有硬化）。主导位移 test RMSE |
| LHS116 (750°C, P20, Rm80, **wall=2**) | 位移 74 mm，PEEQ=4.5 | 同上（vm=199=σy） |
| LHS064 (700°C, P20, Rm80, **wall=2**) | 位移 29 mm，PEEQ=1.9 | 同上（vm=212=σy(700)） |

规律：**薄壁 (wall=2) × 高压 → 触 σy → EPP 流动 → 大位移**。这些是数据集的物理特性（非错误、非可删），直接决定了位移外推的失败边界。von Mises 目标不受影响（饱和值 199/212 可预测）。

## 9. 文件产物

```
ml/models/  dummy|linear|ridge|rf|histgb|xgb × {displacement_raw, displacement_log1p, von_mises_raw} (18 个 .joblib)
ml/predictions/  predictions_*.csv (18 个，逐 case: case_id/y_true/y_pred/residual/abs_err/rel_err/split/model_type/T/P/Rm/time)
ml/metrics/  baseline_metrics.csv + baseline_config.json + extrapolation_report.txt + audit_dataset.json
ml/figures/  avp_×2, residual_dims_vm, model_comparison_test_r2, extrapolation_summary (5 张 PNG)
docs/STEP13_BASELINE_AI_REPORT.md（本报告）
```

## 10. 限制（如实）

1. displacement 外推失败：train 域外（EPP 流动）无样本可学 → 需要域扩展或物理约束模型
2. P≥30 高压区 vm 外推失败（n=10，含薄壁塑性）
3. PEEQ 无正样本（1/104）→ 不可建模；CEEQ val 无样本
4. XGB 轻度过拟合（train 0.999）
5. T=725、Rm=130/140 分箱样本过少（n=1–2）→ 未报告
6. 特征未做交互项/物理约束（如 vm∝P·Ro/wall 的先验）

## 11. 回答 12 个问题

1. 最佳 baseline：**XGBoost**（vm val 0.896/test 0.856）
2. raw vs log1p displacement：**无实质差异**（均失败）；Rm150 子箱 raw 更稳；位移问题在数据域不在变换
3. von Mises：**可可靠预测**（test R² 0.856，MAE 16 MPa）
4. Rm=150 外推：**成功**（vm 0.890）
5. T=750 外推：**成功**（vm 0.872）
6. P≥30 外推：**失败**（vm −0.267）
7. 蠕变 t≥1000 外推：**成功**（位移 0.939/0.808）——AI 可从短时外推长时蠕变
8. MODEL_B/C：**von Mises 统一模型可行**；**displacement 需分模型**（MODEL_C 0.960 vs MODEL_B −0.024）
9. A+B vs A-only：**A+B 显著更优**（0.856 vs 0.046），B 级数据无偏差引入
10. PEEQ：train 非零 1 例 → 不可建模；CEEQ：val 无 MODEL_C → 不可独立验证
11. 过拟合：XGB 轻度（train 0.999→val 0.896），如实记录
12. 下一步：见 §12

## 12. 下一步建议（STEP 13.6A 审计后更新，待 STEP 13.7 批准）

1. **特征**：加入物理无量纲 `P·Ro/(w·σy)`（与位移 r=0.593、与 PEEQ r=0.581，最高相关）与 `Ro/w`（exploratory 已验证，见 STEP13_BASELINE_AUDIT §7）
2. **位移专项（regime-aware）**：① P·Ro/(w·σy)≥1 判定塑性域 ② 弹性域回归（已验证 R²≈0.92 可行）③ 塑性域标记 EPP_post_yield_extreme、不声称预测（或需硬化本构数据）
3. **XGB 有限调参**（≤12 组，validation 驱动）：max_depth 3–6 / learning_rate 0.03–0.1 / n_estimators 200–500
4. **高压/薄壁数据缺口**（若 Abaqus 扩展获批）：补 650–750°C × P30–40 × w=2–3 弹性域样本
5. **CEEQ exploratory**：非零子集（15 例 train）log 回归，明确 exploratory-only
6. **SHAP 可解释性**：验证 vm 由 P·Ro/w、σy、T 驱动的物理合理性

---
*本报告全部数字来自固定 seed 42 的可复现训练；未使用 test 调参；未修改任何 Abaqus 数据/质量规则。*
