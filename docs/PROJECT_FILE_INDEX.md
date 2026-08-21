# 项目文件索引 (PROJECT_FILE_INDEX)

日期: 2026-08-20
范围: SS316LN_N014 环形圆管 550-750°C 热-力耦合项目重要文件

---

## 1. 配置与几何

| 文件 | 用途 |
|------|------|
| `geometry/geometry.yaml` | 基准几何 + 网格等级 (coarse/medium/fine/extra_fine/G4/G5/G6) |
| `loads/pressure.yaml` | 基准压力 P_test=5 MPa |
| `simulation/case_matrix.yaml` | STEP 10 参数化 case 矩阵 (benchmark + LHS 轴) |

## 2. 材料定义

| 文件 | 用途 |
|------|------|
| `materials/SS316LN_N014/metadata.yaml` | 核心材料身份 (N=0.14, 成分, 热处理) |
| `materials/SS316LN_N014/database.csv` | 全材料数据表 |
| `materials/SS316LN_N014/elastic.csv` | E(T), ν |
| `materials/SS316LN_N014/plastic.csv` | σy, UTS |
| `materials/SS316LN_N014/creep.csv` | Norton 蠕变 C/n/A |
| `materials/SS316LN_N014/thermal.csv` | 热物性 (空—见 thermal_properties) |
| `materials/SS316LN_N014/coverage_report.md` | 材料数据覆盖 |
| `materials/SS316LN_N014/abaqus_ready.md` | Abaqus 就绪参数 (STEP 4) |
| `materials/SS316LN_N014/thermal_properties.yaml` | 热物性 YAML (rho/Cp/k/CTE) |
| `materials/SS316LN_N014/SS316LN_N014_EXP/*.csv` | EXP 模型 (MAT-02 实测 E) 全套 |
| `materials/SS316LN_N014/SS316LN_N014_RCCMR/*.csv` | RCCMR 模型 (公式 E) 全套 |
| `materials/SS316LN_N014/SS316LN_N014_EXP/excluded_sodium.csv` | 排除的钠数据记录 |

## 3. 热物性数据库

| 文件 | 用途 |
|------|------|
| `data/thermal_properties/thermal_properties_raw.csv` | 原始数据 (ATI/IAEA/Alleima/GeorgiaTech) |
| `data/thermal_properties/thermal_properties_reference.csv` | 参考汇总 |
| `data/thermal_properties/thermal_properties_SS316LN_N014.csv` | 目标材料热物性 (550-750°C) |
| `data/thermal_properties/thermal_property_sources.md` | 来源文档 |
| `data/thermal_properties/thermal_property_assumptions.md` | 假设 (CTE 定义等) |

## 4. 数据与 AI 就绪

| 文件 | 用途 |
|------|------|
| `data/ai_ready/simulation_dataset.csv` | AI 数据集 (222 行 × 33 列, v1) |
| `data/ai_ready/train.csv` | 训练集 (73) |
| `data/ai_ready/validation.csv` | 验证集 (23) |
| `data/ai_ready/test.csv` | 测试集 (54) |
| `data/ai_ready/coverage_report.csv/md` | 参数覆盖 |
| `data/ai_ready/ai_ready_schema.md` | 数据 schema + 防泄漏规则 |
| `data/raw/SS316LN_structured_database.md` | 941 行原始文献数据库 (副本) |

## 5. Abaqus 输入

| 文件 | 用途 |
|------|------|
| `abaqus/input/CASE-650-EXP-P0.inp` 等 | STEP 5/6 基准 case (30 个) |
| `simulation/thermal_mechanical/cases/TH_*.inp` | STEP 9 均匀温度 case |
| `simulation/thermal_mechanical/cases/GRAD_*.inp` | STEP 9 梯度 case |
| `simulation/thermal_mechanical/cases/TH-01/02.inp` | 热传导验证 case |
| `simulation/generated_cases/*.inp` | STEP 10 批量生成 case (222 个) |
| `simulation/generated_cases/manifest.csv` | case 清单 (参数) |
| `simulation/generated_cases/results.csv` | 后处理结果 (222 行) |

## 6. 脚本

| 文件 | 用途 |
|------|------|
| `abaqus/scripts/build_geometry.py` | 几何 + STEP 5/6 INP 生成 |
| `abaqus/scripts/build_thermal.py` | STEP 9 热-力耦合 INP 生成 |
| `abaqus/scripts/generate_cases.py` | STEP 10 参数化批量生成器 |
| `abaqus/scripts/build_material_db.py` | 材料库构建 |
| `abaqus/scripts/rebuild_models.py` | 双模型 (EXP/RCCMR) 重建 |
| `abaqus/scripts/run_batch.py` | 批量求解 |
| `abaqus/scripts/run_missing.py` | 补跑缺失 case |
| `abaqus/scripts/mesh_convergence_grad.py` | 梯度网格收敛 |
| `abaqus/scripts/step11_convergence.py` | STEP 11 收敛系列 |
| `abaqus/scripts/sensitivity_thermal.py` | 热物性敏感性 |
| `postprocess/postprocess.py` | ODB 自动提取 |
| `postprocess/extract_step9.py` | STEP 9 结果提取 |
| `postprocess/build_sim_dataset.py` | AI 数据接口 (STEP 9.23) |
| `postprocess/build_ai_ready.py` | AI 数据集组装 v1 |
| `postprocess/rebuild_ai_ready.py` | AI 数据集重建 (STEP 11 分级) |
| `postprocess/coverage_split.py` | train/val/test 划分 |
| `postprocess/gen_step6_csvs.py` | STEP 6 汇总 CSV |

## 7. 验证与报告

| 文件 | 用途 |
|------|------|
| `validation/pre_run_check.py` | 运行前 10 项检查 |
| `validation/sym_bc_rank.py` | 对称 BC 秩验证 |
| `validation/expansion_bc_analysis.py` | 热膨胀 BC 相容性分析 |
| `validation/mesh_convergence.md` | 网格收敛 (STEP 6.1) |
| `validation/gradient_convergence_report.md` | 梯度收敛 (STEP 10) |
| `validation/step11_gradient_convergence.csv` | STEP 11 收敛数据 |
| `validation/STEP11_gradient_convergence.md` | STEP 11 收敛报告 |
| `validation/constraint_check.md` | 约束检查 |
| `validation/analytical_sanity_check.md` | 解析合理性 |
| `validation/EXP_vs_RCCMR.md` | 双模型对比 |
| `validation/pressure_response_650C.md` | 650°C 压力响应 |
| `validation/temperature_response.md` | 温度响应 |
| `validation/constraint_reaction_summary.csv` | 反力汇总 |
| `docs/boundary_condition_definition.md` | 边界条件定义 |
| `docs/material_model_matrix.md` | 材料状态矩阵 |
| `docs/material_final_definition.md` | 最终材料定义 |
| `docs/thermal_properties_report.md` | 热物性报告 |
| `docs/STEP9_thermal_mechanical_validation.md` | STEP 9 报告 |
| `docs/STEP10_data_generation_report.md` | STEP 10 报告 |
| `docs/STEP11_report.md` | STEP 11 报告 |
| `docs/AI_DATA_DICTIONARY.md` | AI 数据字典 |
| `docs/PROJECT_STATE_STEP11.md` | 项目状态快照 (本文档) |

## 8. ODB 结果

| 位置 | 内容 |
|------|------|
| `abaqus/input/*.odb` | STEP 5/6 基准结果 |
| `simulation/thermal_mechanical/cases/*.odb` | STEP 9 热-力结果 |
| `simulation/generated_cases/*.odb` | STEP 10 批量结果 (222) |
| `simulation/thermal_mechanical/sensitivity/*.csv` | 敏感性结果 |

---

## 索引后状态
此索引基于文件系统实况生成; 生成后未运行 Abaqus、未修改任何文件。
