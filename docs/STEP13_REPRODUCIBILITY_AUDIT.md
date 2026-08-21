# STEP 13 可复现性审计（Reproducibility Audit）

日期: 2026-08-20
结论: **全部要素可追溯。固定 seed=42 的确定性管线，模型/预测/指标/图均可复现。**

## 1. 环境

| 项 | 值 |
|---|---|
| OS | Windows 11 (win32) |
| Python | 3.10.5（`ml/.venv`，独立 venv） |
| numpy / scipy | 2.2.6 / 1.15.3 |
| pandas / scikit-learn | 2.3.3 / 1.7.2 |
| matplotlib / joblib | 3.10.9 / 1.5.3 |
| xgboost / shap | 3.2.0 / 0.49.1（SHAP 因 xgboost 3.x 解析不兼容未用，见 §9） |
| random seed | **42**（全部脚本 `random_state=42` / `np.random.seed(42)`） |

## 2. 数据校验和（`ml/final/checksums.json`，SHA-256 前缀）

| 文件 | checksum |
|---|---|
| simulation_dataset_318.csv | 20f21ebc67ea… |
| features/v4/X_train.npy | 009fef2c7ccb… |
| features/v4/feature_names.json | 22738bcc12f4… |
| final_vm_model.joblib | 882ccf69c646… |
| case_ids_{train,validation,test}.json | f3287361503b… / da0f34bba80f… / 0f97f10aa3fa… |

## 3. 数据与划分

- 318 行数据集: `data/ai_ready_v4/simulation_dataset_318.csv`（300 行原样 + 18 例 STEP 13.8A 真实 Abaqus）
- 划分: `data/ai_ready_v4/{train,validation,test}.csv` = 120/48/74；**v1 150 例逐 case 与 v1 原文件一致（diff=0，硬断言）**
- case ID 全量可枚举（case_ids_*.json）

## 4. 特征

16 特征（顺序锁定于 `feature_schema.json`）：R_major, R_outer, wall_thickness, pressure, log1p_time, T_hot, Delta_T, E_GPa, sigma_y_MPa, A_creep, n_creep, model_type_C, Pi_yield, Ro_over_w, P_over_sy, sy_over_E。
缺失策略：σy/A_creep/n_creep 0 填充 + model_type_C 编码（记录于 build_features_v4.py）。

## 5. 最终模型参数（`ml/final/model_config.json`）

- **FINAL VM**：XGBoost n_estimators=300, max_depth=4, learning_rate=0.1, subsample=0.8, colsample_bytree=0.8, seed=42；validation-only 选择（val R²=0.9385）；test 一次性 0.9304
- Stage-1：RandomForest n=300, balanced, seed=42
- Stage-2：LinearRegression（弹性域）
- Stage-3：exploratory only

## 6. 模型与预测文件

- 最终模型: `ml/final/{final_vm_model,final_regime_classifier,final_elastic_displacement_model}.joblib` + `ml/models/step13_final/`（锁定副本）
- 历史模型: `ml/models/step13_7/`、`step13_9/`、`step13_10/`（保留）
- 预测: `ml/predictions/`（18 个 baseline 文件）、`ml/predictions/step13_7_predictions/`、`step13_9` 指标、`step13_10` 指标
- 指标: `ml/metrics/`（baseline_metrics.csv, step13_7_*, step13_8a_*, step13_9_metrics.csv, step13_10_*, audit_dataset*.json, checksums.json）

## 7. 源脚本（全部落盘、可重跑）

| 阶段 | 脚本 |
|---|---|
| 数据审计 | `ml/audit_dataset.py`, `ml/audit_split.py`, `ml/audit_metrics.py` |
| 特征 | `ml/build_features.py`(v3), `ml/build_features_137.py`, `ml/build_features_v4.py`(318) |
| 训练 | `ml/train_baselines.py`, `ml/train_137.py`, `ml/train_139.py`, `ml/train_1310.py` |
| 分析 | `ml/evaluate_extrapolation.py`, `ml/analyze_137.py`, `ml/analyze_1310.py`, `ml/combine_138.py`, `ml/design_138.py`, `ml/check_138.py`, `ml/gen_run_138.py`, `ml/postprocess_138.py` |
| 绘图 | `ml/plots.py`, `ml/finalize_13.py` |
| Abaqus | `abaqus/scripts/generate_cases_v2.py`, `run_batch_v3.py`, `postprocess/postprocess_v3.py`, `build_sim_dataset_v4.py`, `coverage_split_v4.py` |

## 8. 图

`ml/figures/`（baseline 5 张）、`step13_7/`（2 张）、`step13_8a/`（2 张）、`step13_final/`（综合 1 张）。

## 9. 已知不可复现项（如实记录）

1. **SHAP**：shap 0.49.1 无法解析 xgboost 3.2 模型（base_score 解析错误）→ 采用 permutation importance（seed 42, 10 重复）替代；如需 SHAP 需升级 shap 或降级 xgboost（环境变更待批准）
2. **Abaqus 求解**：18 例（STEP 13.8A）由 Abaqus 2024 求解，.inp/.odb/.sta/.msg/.dat 全部保留于 `simulation/generated_cases_step13_8/`，可复核；Abaqus 输出不可被脚本确定性重放（求解器行为），但输入与后处理提取规则完全确定
3. `ml/metrics/_tmp_*.py` 为一次性诊断脚本（保留供追溯）

## 10. 结论

管线为**单一路径确定性执行**（无随机划分、无 test 调参、固定 seed）：从 318 行 CSV 到最终模型与指标，任何步骤可由上述脚本与配置重跑得到一致结果。
