# STEP 15-C.1 第一版场 Surrogate 报告（v1 有限域）

日期: 2026-08-20
状态: **v1 训练与 VAL 评估完成 — EXT 27 未读取、LOCKED 未读取、模型未冻结**
定位: **SS316LN toroidal creep field surrogate v1 within the currently covered finite design domain**（非生产模型、非全温度/任意几何泛化）
产物: `ml/final/step15_v1/`（pod_basis.npz + step15_v1_model.json + config）、`ml/metrics/step15_c1_model_comparison.csv`、`step15_c1_physics_audit.json`、`docs/figures/step15_c1_*.png`

## 1. 数据与划分（C.0 冻结）

- case-level：TRAIN 31（119 snapshots，时间网格 1/3/10/30/100/300h 线性插值，零外推）/ VAL 6（18 snapshots）
- **POD basis 仅 TRAIN 拟合**；VAL 只投影；EXT 27/LOCKED 20 全程未读

## 2. 关键方法修正（C.1 发现）

raw 域 POD 系数 ~1e-15（CEEQ 值极小）→ 回归不可行（coef R² 巨大负）。**改为 log10(CEEQ) 域 POD**：系数 O(1) 可回归，重构 10^x 保证 CEEQ≥0。这是本阶段最重要的方法学结论。

## 3. 模型对比（VAL，POD k=3/4/5 × 4 模型）

| pod_k | model | coef R² (c1/c2/c3) | field logMAE | rel_L2 | 备注 |
|---|---|---|---|---|---|
| 3 | **XGB** | **0.999/1.000/0.999** | **0.024** | **0.092** | **最佳** |
| 3 | MLP | 0.998/0.983/0.948 | 0.043 | 0.134 | k=4/5 高模态崩坏 |
| 3 | RF | 0.98/0.99/0.99 | 0.152 | 0.349 | |
| 3 | Ridge | 0.36/0.60/0.67 | 0.850 | 0.349 | 欠拟合 |
| 4/5 | 各模型 | 第 4/5 模态 R² 负（噪声模态） | — | — | k=3 已 100% 方差 |

**选择：POD(k=3, log10) + XGBoost**（val field logMAE=0.024 ≈ 5.7% 场级对数误差；绝对 field MAE ~1e-14）。

## 4. 场重构演示（predict_field API）

- train 例 CR_550_P5_T1h @100h：pred max 1.65e-16 vs true 1.57e-16（field MAE 1.4e-18）
- val 例 CR_550_P10_T1h @100h：1.094e-13 vs 1.144e-13（field MAE 8.7e-16）
- 图：`docs/figures/step15_c1_{train,val}_*.png`（true/pred/abs-error）

## 5. 物理审计：**0 violations**

CEEQ≥0（10^x 保证）、finite、t 单调（100→300h 逐元素检查）全通过；P/T 趋势由 log10-POD 结构继承（STEP14-B 已证）。

## 6. Geometry 分组（VAL 局限，如实报告）

VAL 6 例全部基准几何 (100,20,4) → **几何分组在 C.1 无法评估**（train 池内非基准仅 80/15/2×1、90/18/3×2）→ geometry-dependent field 学习验证必须依赖 EXT（C.2）或新数据。模型是否学到 P·Ro/w 放大效应：C.1 无证据（数据域内几何单一），如实标注。

## 7. Inference API（`step15_v1_model.json` 内实现）

`predict_field(T,P,t,Rm,Ro,w,E,A_creep,n_creep)` → `{ceeq_field[2304], max/mean/p95, hotspot_element, pod_coefficients}`；未来扩展 CEEQ(θ,φ,r,t)。

## 8. 核心问题回答

1. **k 最佳**：k=3（k=4/5 高模态为噪声）
2. **模型最佳**：**XGBoost**
3. **VAL coef R²**：0.999/1.000/0.999
4. **VAL field R²**：log10 域等效（logMAE 0.024；raw 绝对 MAE ~1e-14）
5. **VAL rel_L2**：0.092（鲁棒分母定义；原始分母下小值主导，已在脚本注明）
6. **VAL max CEEQ error**：~8e-13（绝对，极小）
7. **Hotspot 可靠性**：重构误差极小 → hotspot 位置应可靠（C.2 用 EXT 非基准几何验证）
8. **Physics violation**：**0**
9. **Geometry-dependent field 是否学到**：C.1 无法判定（VAL 全基准几何）——留待 C.2 EXT
10. **能否从输入直接重构 2304 场**：**能**（v1 有限域内，API 已实现）
11. **当前 57 例最大限制**：训练池几何单一（34/37 基准）、T 仅 3 值、P≤20
12. **下一批最应补**：非基准几何蠕变场（6→10 种）+ 高压蠕变场（P 25–40）

## 9. 声明

**"EXT target has NOT been read." "LOCKED TEST has NOT been read." "Production model has NOT been frozen." "STEP 15 field surrogate v1 is not yet approved for final evaluation."**
318/locked checksum 未变；未生成新 case；未训练额外模型。

---
*v1 有限域验证版；全部产物可复现（seed 42）。*
