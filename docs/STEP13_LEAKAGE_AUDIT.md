# STEP 13 数据泄漏审计

日期: 2026-08-20
范围: `data/ai_ready_v3/simulation_dataset_300.csv` + train/validation/test 划分
原则: 禁止把"未来才知道"的 Abaqus 输出、质量标签、划分信息用作输入特征。发现任何疑似泄漏**不静默处理**——本文件记录原因与建议。

---

## 1. 字段分类清单

### ✅ SAFE FEATURES（安全输入）

| 字段 | 原因 |
|---|---|
| R_major, R_outer, wall_thickness | 纯输入几何参数，Abaqus 求解前已知 |
| pressure | 纯输入载荷 |
| time | 纯输入（蠕变时长；非蠕变=0） |
| T_uniform / T_inner / T_outer / Delta_T | 纯输入温度边界（注意互斥缺失 → 特征工程合成 T_hot） |
| E_GPa, sigma_y_MPa, A_creep, n_creep | **材料输入参数**（实验/公式/插值），求解前已知，非求解输出。注意：E/σy 由温度与模型决定 → 与 T 共线，但作为输入材料属性无泄漏 |
| model_type | 模型选择（MODEL_B/C），求解前已知 |
| material_id | 与 model_type+T 冗余，可作类别输入（或省略） |
| R_inner | 由 R_outer−wall 派生，纯输入 |

### ❌ UNSAFE FEATURES（禁止作输入）

| 字段 | 泄漏路径 |
|---|---|
| max_von_mises | 目标之一；作特征=目标自泄漏 |
| max_displacement | 目标之一；同上 |
| max_PEEQ | 目标之一；同上 |
| max_thermal_strain | 目标之一；同上 |
| max_creep_strain | 目标之一；同上 |
| max_temperature | **确定性由输入温度决定**（≈T_hot 复制）→ 作特征即泄漏；作 target 亦平凡（仅可作求解保真度验证） |
| max_creep_rate / max_heat_flux | 输出字段（虽当前空/零，禁止作特征） |
| quality_grade | **直接编码数据有效性（A/B/D/E）** → 泄漏 |
| valid_for_AI / valid_for_physics_reference | 划分与标签依据 → 泄漏 |
| converged | 求解结果派生的有效性标签 → 泄漏 |
| solver_status | 有效性元数据 → 泄漏 |
| notes | 含质量信息（mesh_sensitive / DATA_REQUIRED / INTERPOLATED）→ 泄漏 |
| case_id | 唯一标识，无泛化意义（且含类型前缀信息） |

### ⚠️ UNCERTAIN / 待决策

| 字段 | 分析 |
|---|---|
| rho_kgm3 / k_WmK / Cp_JkgK / CTE_1e6 | 输入热物性（IAEA 插值），但仅 5 个离散值（随温度查表）→ 与温度完全共线、几乎零信息；**建议不入选**（保留 CTE 供物理可解释性实验可选） |
| N_content / environment / mesh_level | 常数（0.14 / AIR / medium）→ 零信息，排除 |
| Delta_T vs (T_inner,T_outer) | 冗余表示：二者选一。建议 (T_hot, Delta_T) 或 (T_inner, T_outer)；ΔT 方向（负值=反向梯度仅 1 例） |
| material_id | 与 model_type 高度共线（CREEP↔MODEL_C）；可选作备用 |
| σy/A_creep/n_creep 缺失值 | 结构缺失（MODEL_C 无 σy；MODEL_B 无蠕变参数）。处理选项：①按 model_type 分组特征 ②零填充+缺失指示器。**不删除 case** |

## 2. 划分级泄漏检查（已实测）

| 检查 | 结果 |
|---|---|
| 三集字段一致性 | ✅ 完全一致（33 列） |
| 三集内部重复 case_id | ✅ 无 |
| case_id 跨集重复 | ✅ 无（train∩val=∅, train∩test=∅, val∩test=∅） |
| 完全复制行（全字段） | ✅ 无 |
| test/val 中 train 的完全复制样本 | ✅ 无 |
| test/val 中 train 的**参数复制**（同 T/P/Rm/几何/时间，不同 case） | ⚠️ 存在 11 个 (T,ΔT,P,Rm) 同键组合 —— 全部为**时间外推**（短时 train vs 长时 test）与**模型类型**（MODEL_B vs MODEL_C）维度，与 STEP 11.13 时间外推设计一致，非参数泄漏（详见 STEP12B_FINAL_REPORT §4） |

## 3. 发现的问题（待批准修复，未静默改动）

### 问题 A：train 含 Rm=150 case（外推梯子破坏）—— ✅ 已修复（STEP 13.5 批准）

- 原状：v3 新规则中 `T_u==675 → train`、MODEL_C `t≤300 → train` 先于 `Rm>=150 → test` → 3 例 Rm150 进入 train（U_675_P5_Rm150、CR_600_P5_T100h_Rm150、CR_650_P5_T100h_Rm150）
- **修复（2026-08-20, coverage_split_v3.py）**：v1 case（B###/LHS###/旧 CR_*）走 v1 原规则（含 hard rules），逐 case 分类不变；v3 新 case 走修正规则（`Rm>=150 → test` 最高优先级）
- **修复后审计（ml/audit_split.py，7 项全过）**:
  1. v1 150 例分类变化 = **0**（train/validation/test 旧 73/23/54 逐 case 一致）
  2. 新划分 = **train 104 / validation 46 / test 74**（合计 224 = valid 总数；数量变化因 3 例 Rm150 由 train 移入 test + U_725_P10_Rm150 由 validation 移入 test，未人为凑数）
  3. Rm=150: train **0** 例 / validation 2 例（LHS114/LHS215，v1 历史原样保留）/ test 33 例
  4. 外推梯子：T train≤700→val 725/750→test 全；Rm train≤120→val 130/140→test 150；t train≤300→test≥1000；P 均匀 train≤20、均匀 P≥30 强制 test（v1 hard rule），train 中 P25+ 均为 v1 梯度规则原样（T_in<725 梯度无 P 上限，历史行为）
  5. train/test 同键组合仍为 11 个 = 10 蠕变时间外推（t≤300 vs ≥1000）+ 1 温度外推（梯度 T_in 650/700 vs 750，v1 原样）—— 无参数泄漏
  6. 无新异常：跨集重叠 0、总计数一致 224
- 相关文件更新：`coverage_split_v3.py`（修复）、`ml/audit_split.py`（审计）、`docs/STEP12B_FINAL_REPORT.md` §4（划分数字）

### 问题 B：validation 无 MODEL_C 样本（结构缺口，⚠️ 已确认非泄漏）

- val 47 例全为 MODEL_B；蠕变按时间规则仅进 train/test
- 后果：MODEL_C 无法在 val 上评估 → 三集评估对蠕变 target 退化为 train/test
- 非泄漏（划分规则一致），属设计事实；报告中如实说明，评估策略调整：MODEL_C 用 test 为主、train 内留出（hold-out）为辅

### 问题 C：max_temperature 作为 target 的平凡性

- max_temperature 与输入温度确定性相等 → 若建模须报告为平凡基线（R²≈1 无信息）；不建议作为主 target

### 问题 D：max_creep_rate / max_heat_flux 不可用

- max_creep_rate 100% 缺失；max_heat_flux 100% 为零（v1/v3 数据集均未实际填充）
- 结论：两者暂不可作 target；如需，须从 ODB 重提取（后处理 v4 扩展），不在本轮范围

## 4. 最终建议特征集（待 STEP 13.5 实施）

```
主特征 (13):
  R_major, R_outer, wall_thickness, pressure, time,
  T_hot (= T_uniform if set else T_inner), T_outer,
  E_GPa, sigma_y_MPa, A_creep, n_creep, model_type, Delta_T(可选,与T_outer冗余)
处理:
  - sigma_y/A_creep/n_creep 结构缺失 → 按 model_type 分组填充或 0+指示器（决策：采用指示器方案，见 STEP13_BASELINE_REPORT）
  - T_hot/T_outer 标准化; pressure 标准化; time 建议 log1p(小时) 或 0/非0 指示+log
  - model_type one-hot (2 类)
禁用:
  所有 max_* 输出、quality_grade、valid_for_AI、valid_for_physics_reference、
  converged、solver_status、notes、case_id、mesh_level、environment、N_content
```

## 5. 结论

- 核心字段层面：**输出与标签未混入特征**，设计安全
- 划分层面：**无 case 级泄漏**（无重复/跨集/复制）；11 个同键组合为时间/类型外推设计
- **发现 1 个划分规则缺陷（问题 A：Rm150 入 train）** —— 已记录原因与修复方案，等待批准
- 修复后须重跑：`coverage_split_v3.py` → 重新生成三集 → 重跑本审计确认
