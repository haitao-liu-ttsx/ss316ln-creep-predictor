# STEP 14-A PRE-AUDIT（读取核实与现状确认）

日期: 2026-08-20
状态: 只读核实，无任何计算性改变

## 1. 文件确认（全部存在）

| 类别 | 文件 |
|---|---|
| STEP13 文档 | STEP13_FINAL_REPORT / MASTER_RESULTS / REPRODUCIBILITY_AUDIT / STEP14_GAP_ANALYSIS |
| 数据 | data/ai_ready_v4/{simulation_dataset_318,train,validation,test}.csv |
| 特征 | ml/features/v4/feature_names.json（16 特征） |
| CEEQ 模型 | ml/models/step13_10/ceeq_exploratory_xgb.joblib（exploratory） |
| CEEQ 指标 | ml/metrics/step13_10_ceeq.csv（log10 域 test R²=0.650） |
| 材料 | materials/SS316LN_N014/creep.csv（Norton 550/600/650） |
| 生成/求解/后处理 | abaqus/scripts/generate_cases_v2.py、run_batch_v3.py、postprocess/postprocess_v3.py |
| CEEQ 建模代码 | ml/analyze_1310.py（log10 非零域，无 epsilon） |
| 锁定产物 | ml/final/checksums.json；simulation/generated_cases_step13_8/ |

## 2. MODEL_C 基线核实（与 STEP14_GAP_ANALYSIS 一致 ✅）

| 指标 | 实测 | 预期 |
|---|---|---|
| train MODEL_C | **37**（t 1×9/10×9/100×13/300×6） | 37 ✅ |
| validation MODEL_C | **0** | 0 ✅ |
| test MODEL_C | **20**（t 100×2/1000×14/3000×4） | 20 ✅ |
| train 基准几何占比 | 34/37（100/20/4） | ~全部基准 ✅（confounding 确认） |
| t=3000 已求解 | 4 例（全基准几何） | ≈4 ✅ |
| t=1000 locked | 14 例（v1 基准 9 + v3 新几何 5） | 14 ✅（保持 locked） |
| 历史蠕变时间值 | {1, 10, 100, 300, 1000, 3000}；**t=500/750 = 0 例** | 新时间层可用 ✅ |

## 3. CEEQ target 定义确认

- STEP 13（analyze_1310.py）使用 **log10(CEEQ)**，仅非零域（`nz = CEEQ > 0` 后 `np.log10`），**无 epsilon、无 log1p**
- 现有 37 例 train CEEQ 全部 >0（最小 ~1.5e-18@550°C/t1h）→ 训练域无零值，**不需要 epsilon**；新增 t=500/750/3000 在 550–650°C 均预期非零（Norton 率>0）
- 本阶段沿用 log10 非零域定义，不更改

## 4. 材料参数确认（不修改）

- Norton：550 A=7.75e-32/n=9.51；600 A=3.56e-30/n=9.04；650 A=2.35e-25/n=7.57（MAT-05, AIR）
- E：蠕变 case 沿用 RCCMR 公式值（550=155.0/600=150.8）与 EXP@650（171.0 GPa）；σy 对 MODEL_C 不适用（无塑性卡）
- ν=0.30；热物性表 550–750°C 五点不变

## 5. 设计决策记录（与用户方案的一处必要调整）

用户 §六 A 指定 VAL 时间层 t={500, 1000}。核实发现：**t=1000 × 基准几何 × T{550,600,650} × P{5,10,20} 的 9 例已存在于 locked test**（v1 CR_*_T1000h，红线 §四[4] 要求保持 locked）→ 若执行 t={500,1000} 将与 locked test 直接冲突。
**调整：VAL 时间层改为 t={500, 750}**（仍在"validation 500–1000 h"区间内），保持 3T×3P×2t=18 结构；t=750 为全新时间值（历史 0 例）。TEST 层维持 t=3000 非基准几何（历史 t=3000 全为基准几何，零冲突）。
此调整为满足"locked test 不变"最高优先级的最小改动；其余设计（T/P/几何/数量/三层结构）与用户方案一致。

## 6. 结论

基线核实通过，设计前提成立。进入 STEP4-5：27 case 设计与 PRE-SOLVE AUDIT。
