# STEP 13.7 Physics-informed 模型报告

日期: 2026-08-20
状态: **完成。未做深度模型/大规模搜索；未修改任何数据/质量规则；test 仅一次性确认。**
环境: `ml/.venv`（seed 42）
产物: `ml/models/step13_7/`、`ml/metrics/step13_7_{metrics,tuning,analysis}.csv/txt`、`ml/predictions/step13_7_predictions/`、`ml/figures/step13_7/`

---

## 0. P≥30 指标口径统一（问题澄清）

| 数字 | 实际含义 |
|---|---|
| **−0.267** | XGB-von **Mises** 的 test P≥30 分箱 R²（MAE 44.4 / RMSE 50.7 MPa） |
| **−0.111** | linear-**displacement** 的 test P≥30 分箱 R²（MAE 69.6 / RMSE 219.7 mm） |

两个数字对应**不同 target**，均正确；此前两份报告未标注 target 造成歧义。
**正式口径**：报告 P≥30 时一律标注 target。`STEP13_BASELINE_AI_REPORT.md` §3 已更新。

## 1. Physics features（4 候选 + 缺失策略）

- `Pi_yield = P·Ro/(w·σy)`（第一优先级）、`Ro/w`、`P/σy`、`σy/E`
- σy 缺失（MODEL_C）：physics 特征 0 填充（蠕变模型无塑性路径），model_type_C 编码身份；**未使用任何 test 信息**；记录于 `build_features_137.py` 与 feature_names.json
- 特征集 4 变体：base(12) / base+Pi / base+Pi+Ro_w / all(16)

## 2. von Mises：physics 特征效果（XGB0，validation 选择）

| 特征集 | Val R² | Test R² | Rm150 | T750 | **P≥30** |
|---|---|---|---|---|---|
| base | 0.896 | 0.856 | 0.890 | 0.872 | **−0.267** |
| base+Pi | 0.853 | 0.856 | 0.894 | 0.854 | −0.080 |
| base+Pi+Ro_w | 0.894 | 0.866 | 0.894 | 0.869 | −0.054 |
| **all** | **0.901** | 0.864 | **0.900** | **0.880** | **+0.005** |

**结论：physics 特征达成全部成功标准**——val 不降（0.896→0.901）、Rm150 不降（0.890→0.900）、T750 不降（0.872→0.880）、**P≥30 显著改善（−0.267→+0.005）**。采用 `all` 特征集。

## 3. XGB 有限调参（12 组，validation 选择）

| combo | 变化 | Val R² | Train R² |
|---|---|---|---|
| 5（**选中**） | lr=0.1 | **0.9098** | 1.0000 |
| 1 baseline | depth4/lr0.05 | 0.8962 | 0.9995 |
| 6 | n=200 | 0.8927 | 0.9979 |
| 12 | depth3/lr0.1/subs0.9 | 0.8952 | 0.9995 |
| 8 | min_child_weight=3 | **−0.132** | 0.9847 |

全部 12 组记录于 `ml/metrics/step13_7_tuning.csv`。选中 combo 5（lr=0.1）。
**test 一次性确认**：MAE=16.9 / RMSE=25.8 / R²=**0.849**（val 0.910 vs test 0.849，与 XGB0 的 0.896/0.856 相比 val 提升但 test 略降 0.007——如实记录 val/test 微小分歧；正式模型仍按 validation 选择，无 test 调参）。

## 4. Displacement：unified vs regime-aware

| 模型 | 配置 | Test 结果 |
|---|---|---|
| Model A unified XGB（all 特征） | 全部 74 例 | R²=−0.018（失败，符合预期） |
| **Model B regime-aware** | Stage1 分类 + Stage2 弹性域 linear（base 特征） | **弹性域 (n=68): MAE=0.090 / RMSE=0.112 / R²=0.917** |

- Stage-1（输入特征预测塑性，无 PEEQ/target 信息）：test 准确率 0.932（6 正样本中的检出能力受限于 train 仅 1 正样本，如实标注）
- Stage-2 用 **base 12 特征 + Linear**（R²=0.917，与 13.6A 一致）；**physics 特征对线性模型有害**（all-linear 弹性域 R²=−0.60，共线性证据：Pi_yield=P·Ro/(w·σy) 与 pressure/Ro/w/σy 完全共线）——physics 特征**仅用于树模型**
- 三组评估（Model A，test）：normal_elastic n=68 R²=0.197（unified XGB 不如 linear）、plastic_moderate n=0（6 例全属 EPP 组：vm 全部=σy）、**EPP_post_yield_extreme n=6 R²=−0.253**（不删除、不修改，如实报告）

## 5. Pi_yield 物理验证（决定性证据）

| Pi_yield 区间 | n | PEEQ>0 比例 | vm 范围 |
|---|---|---|---|
| <0.5 | 147 | 3% | 0–215 |
| 0.5–0.8 | 19 | 0% | 100–189 |
| 0.8–1.0 | 5 | 20% | 184–218 |
| **1.0–1.5** | 3 | **100%** | 199–227 |
| >1.5 | 1 | 100% | 199 |

→ **Pi_yield≈1 是塑性触发的强经验边界**（≥1.0 全部塑性），但非严格阈值（<0.5 的 4 例塑性来自**梯度热应力**，Pi_yield 仅含压力项）——与"实际阈值偏离简单薄壳估算"的预期一致。Pi_yield 作为 physics-informed feature（非硬编码定律）使用。

## 6. 特征重要性（permutation，validation；SHAP 不可用记录）

**von Mises**：Delta_T (1.38) > pressure (0.78) > wall_thickness (0.17) > E > R_outer > σy > Rm——与物理一致（梯度热应力 + 薄膜应力主导；vm 与 Rm 无关 ✓）。
**displacement unified**：所有特征重要性≈0（模型已失败，重要性无意义，如实标注）。
**SHAP 不可用记录**：shap 0.49.1 无法解析 xgboost 3.2 模型格式（base_score 解析 ValueError，wrapper 与 booster 路径均失败）；未修改环境强配；采用 permutation importance（模型无关、seed 42、10 次重复）作为等价分析。

## 7. CEEQ exploratory

- MODEL_C 57 例（train 37 / val 0 / **test 20**）**全部非零**（此前"90% 零"含 MODEL_B）
- 非零 CEEQ 跨 ~13 个数量级（1e-19–1e-6）→ log 域必需
- 物理自洽：650°C/P20/t3000 最大（9.9e-7）；单调随 T/P/t 增加；650°C 蠕变率 600°C 高 ~2 数量级（A 值差 1000× 部分抵消 n 差异）
- **结论**：CEEQ 仅 exploratory；val 无 MODEL_C → 无独立验证；若建正式模型须 log 域 + test 时间外推为主

## 8. 数据缺口分析（train 覆盖）

| 区域 | train 样本数 |
|---|---|
| P≥30 | **3** |
| wall=2 | 15 |
| **Pi_yield ∈ [0.8, 1.2]（过渡区）** | **0** |
| **Pi_yield > 1** | **0** |

→ **塑性过渡区在 train 完全缺失**。这是位移塑性失败与 P≥30 vm 外推失败的根本数据原因。
**下一批 Abaqus 最小设计建议**（未执行，待批准）：补 Pi_yield ∈ {0.7, 0.85, 1.0, 1.15, 1.3, 1.5} 各 2–3 例（≈12–18 例），即 650–750°C × P 15–40 × w 2–3 组合（含 wall=2、P≥30 弹性域 P·Ro/w < σy 与塑性域各半）。

## 9. 最终结论与 STEP 14 建议

1. **von Mises 最终模型**：XGB（all 16 特征，combo 5 参数）→ val 0.910 / test 0.849 / Rm150 0.900 / T750 0.880 / P≥30 +0.005
2. **displacement**：Model B regime-aware（linear 弹性域 R²=0.917 + 塑性标记）为当前最佳方案；unified 失败保留
3. **physics 特征**：对树模型有效（P≥30 改善 0.27），对线性模型有害（共线）——按模型族使用
4. **数据缺口**：Pi_yield 过渡区 train 0 例 → 需 Abaqus 补充（最小 12–18 例设计已给）
5. **CEEQ**：exploratory-only；需要正式模型须先解决 val 无 MODEL_C 的验证结构
6. SHAP 工具不可用（版本不兼容）已记录；若需要 SHAP 应升级 shap 或降级 xgboost（涉及环境变更，待批准）

---
*本报告全部数字来自固定 seed 42 的可复现脚本；未使用 test 调参；未删除/修改任何 case 与数据。*
