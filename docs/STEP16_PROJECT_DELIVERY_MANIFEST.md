# STEP 16-H 项目交付清单

日期: 2026-08-20 ｜ 状态: **PROJECT DELIVERY READY**（16-A 资产审计 11/11 PASS、16-B API 验收全 PASS）

## DATA
| path | purpose | status |
|---|---|---|
| `data/ai_ready_v4/simulation_dataset_318.csv` | 主数据集（318 行，锁定） | UNCHANGED（`20f21ebc67ea`） |
| `data/ai_ready_v4/{train,validation,test}.csv` | STEP13 split（120/48/74） | UNCHANGED |
| `data/ai_ready_v4/test.csv` | LOCKED TEST（含 20 MODEL_C） | NEVER READ（`fa573e330926`） |
| `ml/data/step15_ceeq_snapshots/*.npz` | 57 例历史蠕变场 | OK |
| `ml/data/step15g_snapshots/*.npz` | 50 例新增蠕变场（G.2 QC 全过） | OK |

## ABAQUS
| path | purpose | status |
|---|---|---|
| `simulation/generated_cases/`、`generated_cases_v2/`、`generated_cases_step13_8/`、`generated_cases_step14a_ceeq/`、`generated_cases_step15g/` | 全部 INP/ODB/STA/MSG/DAT 证据 | COMPLETE（未覆盖） |

## POD
| path | purpose | status |
|---|---|---|
| `ml/final/step15_v1/pod_basis.npz`（v1） | 历史版本 | UNCHANGED |
| `ml/final/step15_v1_1/pod_basis_v11_frozen.npz` | v1.1 | UNCHANGED |
| `ml/final/step15_v1_2/pod_basis_v12_frozen.npz` | **v1.2 生产 basis（k=3, log10, TRAIN-only）** | FROZEN |

## MODELS
| path | purpose | status |
|---|---|---|
| `ml/final/step14b_refit_model.json` | STEP14 scalar（PhysB-quad） | UNCHANGED |
| `ml/final/step15_v1/`、`step15_v1_1/` | 历史场模型 | UNCHANGED |
| `ml/final/step15_v1_2/`（frozen_poly_mode{1,2,3}.joblib + config + freeze manifest） | **v1.2 生产模型** | FROZEN |
| `ml/production/step15_v1_2/model/` | production 副本（+ scaler） | COMPLETE |

## VALIDATION
| path | purpose | status |
|---|---|---|
| `ml/metrics/step15_g4_ext_*.csv/json` | EXT 27 一次性验证（logMAE 0.0314） | PASS |
| `ml/metrics/step15_f_v11_comparison_v1_vs_v11.csv` | 三代演进证据 | PASS |
| `ml/metrics/step16_api_acceptance.json` | API 14 项验收 | PASS |

## API / VISUALIZATION
| path | purpose | status |
|---|---|---|
| `ml/production/step15_v1_2/runtime/predict_field.py` | 生产推理 API（域守卫+物理守卫） | VALIDATED |
| `ml/production/step15_v1_2/tests/` | 5 测试（checksum/输入/物理/回归/重构） | PASS |
| `docs/figures/final/` | 12 张最终图（3D 场/θ-φ-r/时间演化/几何与应力对比/true-vs-pred） | COMPLETE |

## REPORTS / AUDIT
| path | purpose | status |
|---|---|---|
| `docs/STEP13_*`（14 份） | STEP13 数据-模型审计系列 | COMPLETE |
| `docs/STEP14*`（6 份）+ `STEP15*`（13 份） | STEP14/15 科研系列 | COMPLETE |
| `docs/STEP16_*`（5 份） | 最终交付（资产/API/有效域/结论/清单） | COMPLETE |
| `ml/metrics/step16_final_asset_audit.json` | 11 资产 checksum | 11/11 OK |
| `ml/metrics/step16_final_metrics.csv` | 论文级指标表 | COMPLETE |

## 完整性状态
318 `20f21ebc67ea` ✅ ｜ LOCKED `fa573e330926` ✅ ｜ STEP14/v1/v1.1/v1.2 全部未改 ✅ ｜ STEP16 新增文件仅写入独立目录 ✅
