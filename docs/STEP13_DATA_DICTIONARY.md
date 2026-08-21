# STEP 13 数据字典 — 318 Case 数据集（v4）

日期: 2026-08-20（STEP 13.9 更新）
数据源: `data/ai_ready_v4/simulation_dataset_318.csv`（318 行 × 38 列；300 行原样保留 + STEP 13.8A 18 例真实 Abaqus 输出）
早期版本: 300 行数据集字典见本文档原始章节（STEP 13.5，`data/ai_ready_v3/`）
审计证据: `ml/metrics/audit_dataset_318.json`（STEP 13.9 只读生成）＋ `ml/metrics/audit_dataset.json`（300 行版）

**STEP 13.9 变化**：新增 18 例（Grade A × 18、valid_for_AI=YES × 18、Pi_yield 0.698–1.508 含 3 例 onset 微屈服），字段 schema 与 300 行完全一致（38 列），无新字段、无缺失结构变化。train 120 / validation 48 / test 74（v1 150 例 split 零变化）。

---

## 1. 33 字段字典

| # | 字段 | 含义 | 单位 | 类型 | 来源 | 输入特征 | 目标 | 泄漏风险 |
|---|---|---|---|---|---|---|---|---|
| 1 | case_id | case 唯一标识（B/LHS/CR/U/G 前缀） | — | cat | metadata | ❌ | ❌ | — |
| 2 | model_type | MODEL_B=弹塑性 / MODEL_C=Norton 蠕变 | — | cat | metadata | ✅ | ❌ | 与目标强相关（CEEQ 仅 C 非零），**作为特征时需单独检验** |
| 3 | material_id | SS316LN_N014_EXP / RCCMR / CREEP | — | cat | derived | ⚠️ | ❌ | 与 model_type+T 冗余；CREEP 即 MODEL_C → 与 #2 共线 |
| 4 | N_content | 氮含量 | wt.% | num | experimental | ⚠️ | ❌ | 常数 0.14 → 无信息 |
| 5 | environment | 环境 | — | cat | metadata | ❌ | ❌ | 全为 AIR → 常数 |
| 6 | R_major | 环主半径 | mm | num | input | ✅ | ❌ | 无 |
| 7 | R_outer | 管外半径 | mm | num | input | ✅ | ❌ | 无 |
| 8 | wall_thickness | 壁厚 | mm | num | input | ✅ | ❌ | 无 |
| 9 | R_inner | 内半径 = R_outer − wall | mm | num | derived | ⚠️ | ❌ | 由 #7−#8 完全决定 → 共线（可作物理量，但冗余） |
| 10 | T_uniform | 均匀温度（仅均匀 case） | °C | num | input | ✅ | ❌ | 与 #11/#12 互斥缺失（结构缺失，见 §3） |
| 11 | T_inner | 梯度内壁温度（仅梯度 case） | °C | num | input | ✅ | ❌ | 同上；梯度时材料参数取 T_inner |
| 12 | T_outer | 梯度外壁温度 | °C | num | input | ✅ | ❌ | 与 #11 联合定义 ΔT |
| 13 | Delta_T | 梯度温差 = T_inner − T_outer（均匀=0） | °C | num | derived | ✅ | ❌ | 由 #11−#12 决定（冗余，可替代） |
| 14 | pressure | 内压 | MPa | num | input | ✅ | ❌ | 无 |
| 15 | time | 分析时长（蠕变；非蠕变=0） | h | num | input | ✅ | ❌ | 无（蠕变时间外推关键轴） |
| 16 | E_GPa | 弹性模量（EXP 实测/插值/RCCMR 公式） | GPa | num | material input | ✅ | ❌ | 由温度+模型决定；**不是 Abaqus 输出**，无泄漏 |
| 17 | sigma_y_MPa | 屈服强度（650/700/750 实验、675/725 插值、550/600 缺失） | MPa | num | material input | ✅ | ❌ | 550/600 缺失（DATA_REQUIRED，不进训练）；MODEL_C 无 σy → 结构缺失 |
| 18 | A_creep | Norton 系数（仅 MODEL_C，550/600/650） | s⁻¹/MPaⁿ | num | material input | ✅ | ❌ | 非蠕变 case 缺失（81%）→ 结构缺失 |
| 19 | n_creep | Norton 指数 | — | num | material input | ✅ | ❌ | 同上 |
| 20 | rho_kgm3 | 密度（IAEA 316 插值） | kg/m³ | num | material input | ⚠️ | ❌ | 温度 5 点查表 → 与温度共线，几乎无信息 |
| 21 | k_WmK | 导热系数 | W/(mK) | num | material input | ⚠️ | ❌ | 同上 |
| 22 | Cp_JkgK | 比热 | J/(kgK) | num | material input | ⚠️ | ❌ | 同上 |
| 23 | CTE_1e6 | 热膨胀系数 | ×10⁻⁶/K | num | material input | ⚠️ | ❌ | 同上（热应变直接由它驱动） |
| 24 | max_temperature | 求解最高温度 | °C | num | **simulation output** | ❌ | ⚠️ | **确定性 = 输入温度 → 作特征即泄漏；作 target 平凡** |
| 25 | max_heat_flux | 最大热流 | W/m² | num | simulation output | ❌ | ⚠️ | 数据集全 0（未实际输出）→ 无信息 |
| 26 | max_displacement | 最大位移 | mm | num | simulation output | ❌ | ✅ | 作特征即泄漏 |
| 27 | max_von_mises | 最大 von Mises 应力 | MPa | num | simulation output | ❌ | ✅ | 作特征即泄漏 |
| 28 | max_PEEQ | 最大等效塑性应变 | — | num | simulation output | ❌ | ✅ | 作特征即泄漏；80.7% 为 0 |
| 29 | max_thermal_strain | 最大热应变 | — | num | simulation output | ❌ | ✅ | 作特征即泄漏 |
| 30 | max_creep_strain | 最大蠕变应变（CEEQ） | — | num | simulation output | ❌ | ✅ | 作特征即泄漏；90% 为 0 |
| 31 | max_creep_rate | 最大蠕变率 | s⁻¹ | num | simulation output | ❌ | ⚠️ | **100% 缺失**（数据集未填充）→ 不可用 |
| 32 | mesh_level | 网格等级 | — | cat | metadata | ❌ | ❌ | 全 medium → 常数 |
| 33 | converged | 数值收敛标志 | — | cat | metadata | ❌ | ❌ | **目标派生标签，作特征=泄漏** |
| — | quality_grade | A/B/D/E 质量等级 | — | cat | metadata | ❌ | ❌ | **作特征=严重泄漏（直接编码有效性）** |
| — | valid_for_AI | 是否 AI 可用 | — | cat | metadata | ❌ | ❌ | **划分依据，作特征=泄漏** |
| — | valid_for_physics_reference | 物理参考标志 | — | cat | metadata | ❌ | ❌ | 同 quality_grade |
| — | solver_status | 求解状态 | — | cat | metadata | ❌ | ❌ | 全 OK → 常数 |
| — | notes | 质量备注 | — | cat | metadata | ❌ | ❌ | **含质量标签信息，作特征=泄漏** |

注: 33 列中末 4 个标志字段（quality_grade/valid_for_AI/valid_for_physics_reference/notes）为第 29–33 列，converged/solver_status 也在 33 列内。表格末尾 5 行（quality_grade 等）属同一 33 列集合，此处单独列出以强调其标签性质。

## 2. 目标变量候选（实测统计）

| target | 缺失 | 零比例 | min–max | 数量级跨度 | 回归适宜性 | log 处理 |
|---|---|---|---|---|---|---|
| max_displacement | 0% | 0% | 0.129–2306 mm | 4.3 阶 | ✅ 连续、全正 | log1p 候选（train 域仅 0.24–2.2，test 至 697 → 外推强） |
| max_von_mises | 0% | ~1% | 8e-12–810 MPa | 14 阶（含数值零） | ✅ 物理有界（≤σy+热应力） | 不建议 log（含 0 且物理有界）；标准化即可 |
| max_PEEQ | 0% | **80.7%** | 0–75.8 | ∞（含 0） | ⚠️ 严重零膨胀 | 两段模型（非零判定+量级）或仅非零子集；**train 仅 1 例非零** |
| max_thermal_strain | 0% | 1.3% | 7.6e-17–6.7e-3 | 14 阶 | ✅ 连续 | log1p 候选 |
| max_creep_strain | 0% | **90%** | 0–9.9e-7 | ∞（含 0）；非零域 ~8 阶 | ⚠️ 严重零膨胀 | **log 必需**（非零域跨 1e-15–1e-6） |
| max_creep_rate | **100%** | — | — | — | ❌ 不可用 | 需从 ODB 重提取后才可考虑 |
| max_temperature | 0% | 0% | 550–750 | 0.1 阶 | ⚠️ 由输入确定性决定 → 平凡 target | 不建议作 target |
| max_heat_flux | 0% | 100% | 全 0 | — | ❌ 无信息 | 需重提取 HFL 输出 |

## 3. 结构缺失说明（重要）

- `T_uniform`/`T_inner` 互斥缺失（均匀 vs 梯度）→ 特征工程需合成单一热负荷温度 `T_hot = T_uniform 或 T_inner`
- `sigma_y_MPa` 缺失 = MODEL_C 550/600 例（蠕变模型不承载 σy）→ 特征层按 model 分组或指示变量
- `A_creep`/`n_creep` 缺失 = MODEL_B 例 → 同上
- `max_creep_rate` 全缺失 → 不可用（除非后续从 ODB 重提取）

## 4. 输入特征（推荐，详见 STEP13_LEAKAGE_AUDIT.md）

连续: `R_major, R_outer, wall_thickness, pressure, time, T_hot(=T_uniform|T_inner), T_outer, E_GPa, sigma_y_MPa(条件), A_creep(条件), n_creep(条件)`
类别: `model_type`
可选（弱信息/共线）: `R_inner, Delta_T, material_id, rho/k/Cp/CTE`
禁用: 全部 `max_*` 输出、全部质量标签（grade/valid/notes/converged/solver）、`case_id, mesh_level, environment, N_content`（常数）
