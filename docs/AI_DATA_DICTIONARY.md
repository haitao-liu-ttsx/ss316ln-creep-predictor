# AI 数据字典 (AI_DATA_DICTIONARY)

日期: 2026-08-20
数据文件: data/ai_ready/simulation_dataset.csv (222 行), train.csv (73), validation.csv (23), test.csv (54)
单位体系: mm-N-MPa-s-°C (与 Abaqus 一致)

---

## 输入字段 (Inputs)

| 字段 | 单位 | 物理意义 | 来源 | 实验? | 插值? | 假设? | AI训练? |
|------|------|---------|------|-------|-------|-------|---------|
| case_id | — | 唯一案例标识 | 生成器 | — | — | — | — |
| model_type | — | MODEL_A/B/C (弹性/EPP/蠕变) | 配置 | — | — | — | 是 |
| material_id | — | 材料身份变体 | 材料库 | — | — | — | 是 |
| N_content | wt% | 氮含量 | 目标 0.14 (IGCAR) | 是 | — | — | 是 |
| environment | — | 环境 | AIR ONLY | — | — | — | 是 |
| R_major | mm | 环面主半径 80-150 | 参数 | — | — | — | 是 |
| R_outer | mm | 管外径 15-25 | 参数 | — | — | — | 是 |
| wall_thickness | mm | 壁厚 2-5 | 参数 | — | — | — | 是 |
| R_inner | mm | 内径 (=R_outer-wall) | 派生 | — | — | — | 是 |
| T_uniform | °C | 均匀温度 | 参数 | — | — | — | 是 |
| T_inner / T_outer | °C | 梯度边界温度 | 参数 | — | — | — | 是 |
| Delta_T | °C | 温度差 (内-外) | 派生 | — | — | — | 是 |
| pressure | MPa | 内压 0-40 | 参数 | — | — | — | 是 |
| time | h | 蠕变持时 1-1000 | 参数 | — | — | — | 是 |

## 材料字段

| 字段 | 单位 | 物理意义 | 来源 | 实验? | 插值? | 假设? | AI训练? |
|------|------|---------|------|-------|-------|-------|---------|
| E_GPa | GPa | 弹性模量 (温度相关) | MAT-02 实测 (A) / RCCMR 公式 (D) | 650-750 是; 550-600 否 | — | — | 是 |
| sigma_y_MPa | MPa | 屈服强度 (EPP) | MAT-02 实测 (A) | 650-750 是; 550-600 DATA_REQUIRED | — | — | 650-750 是 |
| A_creep | s⁻¹/MPaⁿ | Norton 蠕变系数 | MAT-05 实测 (A) | 550-650 是; 700-750 DATA_REQUIRED | — | — | 是 |
| n_creep | — | Norton 应力指数 | MAT-05 实测 (A) | 是 | — | — | 是 |
| rho_kgm3 | kg/m³ | 密度 (温度相关) | IAEA 316 (C) + 插值 (E) | 否 | 是 | — | 是 |
| k_WmK | W/(m·K) | 热导率 | IAEA 316 (C/E) | 否 | 是 | — | 是 |
| Cp_JkgK | J/(kg·K) | 比热容 | IAEA 316 (C/E) | 否 | 是 | — | 是 |
| CTE_1e6 | 1e-6/K | 线膨胀系数 (瞬时) | IAEA 316 (C/E) | 否 | 是 | — | 是 |

## 输出字段 (Outputs)

| 字段 | 单位 | 物理意义 | 计算方法 | AI训练? |
|------|------|---------|---------|---------|
| max_temperature | °C | 最高温度 | ODB NT11 max | 是 |
| max_heat_flux | W/m² | 最大热流 | ODB HFL | 是 |
| max_displacement | mm | 最大位移 | ODB U | 是 |
| max_von_mises | MPa | 最大等效应力 | ODB S | 是 |
| max_PEEQ | — | 最大等效塑性应变 | ODB PEEQ | 是 |
| max_thermal_strain | — | 最大热应变 | ODB EE | 是 |
| max_creep_strain | — | 最大蠕变应变 | ODB CEEQ | 是 |
| max_creep_rate | s⁻¹ | 最大蠕变率 | 未直接提取 (可由 CEEQ/time 推导) | 后续加 |

## 质量字段

| 字段 | 取值 | 意义 | AI训练? |
|------|------|------|---------|
| mesh_level | medium | 当前全部 medium (收敛验证用 fine/extra_fine) | — |
| converged | YES/NO | 网格收敛 | 决定 valid |
| quality_grade | A/B/C/D/E | 数据质量等级 (见下) | A/B 是; C 仅验证; D/E 否 |
| valid_for_AI | YES/NO | 是否允许 AI 训练 | — |
| valid_for_physics_reference | YES/NO | 是否可作物理参考 | — |
| solver_status | OK/FAILED/PENDING | 求解状态 | 非 OK 否 |
| notes | — | 分级原因 | — |

## 质量等级定义 (STEP 11.8)

| 等级 | 定义 | AI训练 |
|------|------|--------|
| A | EXPERIMENTAL mechanical + converged | ✅ 允许 |
| B | reference material + converged numerical | ✅ 允许 |
| C | numerical reference / sensitivity | 仅验证/敏感性, 不默认进核心集 |
| D | mesh-sensitive (梯度塑性) | ❌ 禁止 |
| E | DATA_REQUIRED (550/600 σy 缺失) | ❌ 禁止 |

## 防泄漏划分 (STEP 11.13)

- train (73): T≤700 uniform, ΔT≤150 梯度 (T_inner<750), P≤25, Rm≤120, 蠕变 t≤100h
- validation (23): T=700, 梯度 T_inner≈725, P=25, Rm=120
- test (54): T=750 uniform, 梯度 Rm≥150 或 T_inner=750, P≥30, 蠕变 t=1000h
- **外推测试保证**: Rm=150, T=750, P≥30, t=1000h 不出现在 train (0 重叠)
