# STEP 13.9 重训报告 — 318 例数据集 + Transition 数据效果

日期: 2026-08-20
状态: **重训完成。v1 150 例 split 严格不变；未修改任何旧数据/质量判据。**
产物: `data/ai_ready_v4/`（318 数据集 + split）、`ml/features/v4/`、`ml/models/step13_9/`、`ml/metrics/step13_9_metrics.csv`、`ml/metrics/audit_dataset_318.json`

## 1. 数据合并（318 行）

- 300 行（v1 222 + v3 78）**逐值原样保留**（零修改/零删除/零重算）
- 新增 18 例（STEP 13.8A 真实 Abaqus 输出，38 列 schema 一致）
- 质量判据 v1 原样执行：**18/18 = Grade A、valid_for_AI = YES**（均匀 650–750 + solver OK；无放宽）
- 最终：**total 318、valid 242、A=132/B=110/D=49/E=27、physics_reference=76**
- 审计：`ml/metrics/audit_dataset_318.json`（38 字段、缺失、唯一值、target 统计、分级）

## 2. 重新 split（318）

| 集合 | 数量 | 构成 |
|---|---|---|
| train | **120** | v1 73（原样）+ v3 31 + **新 18 例中 16 例**（transition 主体） |
| validation | **48** | v1 23（原样）+ v3 23 + **新 2 例**（U_650_P34_Rm120_Ro20_w3 近屈服 650°C、U_750_P24_Rm120_Ro25_w2 强塑 750°C，独立验证） |
| test | **74** | 原样（v1 54 + v3 20；Rm150/T750/P≥30/蠕变 t≥1000 外推区完整保留） |

- **v1 150 例 case-by-case diff = 0（硬断言通过）**
- 新 18 例：16 train / 2 validation / **0 test**（test 不外扩，保持外推纯净）
- 新增 case 的 Rm 80–120 属 train 域，不触碰 Rm150 test 区

## 3. 特征重建（v4，16 特征）

`ml/features/v4/`：base 12 + Pi_yield + Ro_over_w + P_over_sy + sy_over_E；σy 缺失 0 填充策略不变；train 120 / val 48 / test 74。

## 4. 重训结果

### 4.1 von Mises（XGB all-features，3 变体 validation 选择 variant 1: lr=0.1）

| 指标 | STEP 13.7 | **STEP 13.9** |
|---|---|---|
| Train R² | 1.000 | 1.000 |
| **Val R²** | 0.901 | **0.9385** |
| **Test R²** | 0.864 | **0.9304** |
| Test MAE/RMSE | 16.4/24.5 | **12.4/17.5 MPa** |
| Rm150 | 0.900 | **0.9148** |
| T750 | 0.880 | **0.9408** |
| P25 | 0.453 | **0.8679** |
| **P≥30** | +0.005 | **+0.4553** |
| MODEL_B / MODEL_C | 0.83/0.90 | **0.917 / 0.980** |

**P≥30 外推对照链（同一 test 集）**：STEP 13.6 base=−0.267 → STEP 13.7 all-features=+0.005 → **STEP 13.9 +transition 数据=+0.455**。物理特征与过渡区数据共同作用，高压外推从负值转正且显著。

### 4.2 Displacement

| 模型 | STEP 13.7 | **STEP 13.9** |
|---|---|---|
| stage-1 正样本 (train) | 1 | **11**（含 10 例新塑性） |
| stage-1 acc (test) | 0.932 | **0.986** |
| stage-2 弹性域 R² (test, n=68) | 0.917 | **0.917**（保持） |
| unified XGB R² (test) | −0.018 | **+0.350**（训练含塑性样本后统一模型也改善） |

- 弹性域位移预测保持优秀（MAE 0.09 mm）；塑性域由 stage-1 识别（test 6 例全命中），EPP 极端区仍标记不预测
- 位移的 regime-aware 方案成立：stage-1 首次拥有 11 个真实正样本

## 5. 外推梯子保持

test 74 例（T=750 n=27、Rm150 n=33、P≥30 n=10、蠕变 t≥1000 n=18）全部原样保留——本次数据的目标是修补训练域，未人为制造新 test；STEP 13.6/13.7 的全部 baseline 对照数字仍可逐项比较。

## 6. 结论

1. **transition 数据（18 例）确实修补了训练域**：von Mises test R² 0.864→0.930；P≥30 从 −0.267→+0.455；unified displacement 从 −0.018→+0.350
2. **Pi_yield 作为连续 physics feature 持续有效**（STEP 13.7 特征贡献 + STEP 13.9 数据贡献叠加）
3. v1 150 例 split 严格不变、test 外推设计完整保留、质量判据未动
4. 仍存在的局限：P≥30 MAE 30 MPa（n=10，含薄壁 EPP 饱和 case）；位移塑性域仍不预测（EPP 流动无物理上界）；CEEQ 未建模（val 无 MODEL_C 结构未变）

## 7. 下一步建议（待批准）

- STEP 13.10 候选：① von Mises 有限调参确认（≤6 组）② 位移 stage-1 阈值校准（Pi_yield 边界 vs 分类器）③ SHAP/permutation 重要性复核（318 数据）④ CEEQ exploratory 建模（test 时间外推框架）
- 深度模型/大规模搜索仍不在本轮

---
*本报告全部数字来自固定 seed 42 的可复现重训；未修改旧数据/质量判据/split 规则。*
