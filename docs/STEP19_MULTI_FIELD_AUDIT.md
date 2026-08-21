# STEP 19 多物理场输出升级前置审计报告

日期: 2026-08-20
状态: **STEP19 AUDIT = COMPLETE ｜ V1.2 = UNCHANGED ｜ LOCKED = NEVER READ ｜ TRAINING = NOT STARTED ｜ WEBAPP = UNCHANGED ｜ ABAQUS = NO NEW RUN**

## 0. 执行摘要（最重要结论先行）

1. **CEEQ 即等效蠕变应变**，v1.2 已实现，继续作为第 5 输出（无需重建）。
2. **464/464 个历史 ODB 全部可读；443 个含完整 S 张量**（S11/S22/S33/S12/S13/S23，INTEGRATION_POINT）。
3. **σr / σθ / σz / τ 全部 AVAILABLE**：可从已有 S 张量经圆柱坐标转换提取，**无需重新运行 Abaqus**。
4. **C3D8R 单积分点 = 单元质心** → 应力场可直接映射到 2304 element-centroid，与 CEEQ 同 mesh，IP→centroid 无需插值。
5. **575/625℃ 无任何数据**（TRAIN/VAL/EXT 只有 {550,600,650}）→ UI 只能作为"未验证插值点"出现。
6. **ΔTr（径向温差）：PARTIAL**——8 个 GRAD case（±200℃ 梯度，有 S+TEMP 无 CEEQ）存在但不在 v1.2 域内。
7. **ΔTz（轴向温差）：NOT_AVAILABLE**——零数据，必须新增 thermal-mechanical cases。
8. **推荐 v1.3 Multi-Field**（每输出独立 POD + Ridge-Poly2），不重跑 Abaqus，仅需新建应力提取管线 + 训练。
9. **颜色系统当前为相对色标**（per-case min/max），工况间不可比——需改绝对/相对双模式。

---

## 1. v1.2 真实输入 schema（`step19_input_feature_audit.json`）

- 模型特征（10）：`T, P, log1p_time, Rm, Ro, w, E, A_creep, n_creep, log10(P·Ro/w)`
- **用户输入（6）**：T, P, t, Rm, Ro, w；其余为派生：E/A_creep/n_creep 由**温度查表**（仅 {550,600,650} 三行），log10(P·Ro/w) 为应力尺度特征。
- **生产 API 实际只接受 T ∈ {550, 600, 650}**（`validate_input` 用 `E_T/CREEP` 精确查表，575/625 直接 OUT_OF_DOMAIN）。

## 2. 温度覆盖审计（`step19_temperature_audit.json`）

| 集合 | case 数 | T 唯一值 | 575/625 | P·Ro/w 范围 | P·Ro/w>250 |
|---|---|---|---|---|---|
| TRAIN | 68 | {550, 600, 650} | **无** | 25–250 | 0 |
| VAL | 19 | {550, 600, 650} | **无** | 25–250 | 0 |
| EXT27 | 27 | {550, 600, 650} | **无** | — | 0 |

- t 覆盖：v1.2 域内 1–3000h（3000h 由 48 个 G case 补足；**1000h 仍稀疏** ~16）
- 几何：10 种（Rm 80–150 × Ro 15–25 × w 2–5，含 90/18/3、80/15/2、110/22/4、150/20/4 等非基准）
- P：2.5–30；P≥25 有 12 例（G 设计）

**结论：575℃ / 625℃ = 零数据 → 只能标记「未验证插值（INTERPOLATION / DATA_REQUIRED）」，不可声称已验证。**

## 3. 温度输入 UI 建议

- 档位：**550 / 575 / 600 / 625 / 650（25℃ 步长）**——但这 5 档中仅 **550/600/650** 为真实训练温度（绿）；575/625 为插值档（黄，标注"未验证插值"）。
- 实现建议（STEP19 后阶段）：UI 提供 5 档下拉而非自由数字输入；575/625 提交时走 v1.2 会返回 OUT_OF_DOMAIN（当前行为安全）——**在 UI 明确显示"该温度未经验证"提示**。650–700 段：必须 DATA_REQUIRED（模型无材料表）。

## 4. ODB 场清单审计（`step19_odb_field_inventory.csv/.json`，464/464 可读）

| 场 | 数量 | position | 说明 |
|---|---|---|---|
| S（全 6 分量） | **443** | INTEGRATION_POINT | 全部 C3D8R 减缩积分 |
| CEEQ | 135 | INTEGRATION_POINT | 57 旧 + 50 G + 28 step14a |
| TEMP / NT11 | 464 / 464 | NODAL | 所有 case 均有温度输出 |
| E / EE / U / RF | 443 | — | 弹性应变/非弹性应变/位移/反力 |
| PEEQ | 300 | — | 等效塑性应变 |
| LE | 0 | — | 无对数应变输出（不需要） |

- **无 S 的 21 个 ODB**：thermal_mechanical 中的纯热传导 case（CONV_*_TH、S11*_TH、SENS_*_TH、TH-01/02）——本为热分析，无机械场。
- **v1.2 训练集 87 例全部有 S**（B 系列 318 全有；G 系列 INP 请求 `S,LE,EE,PEEQ,TEMP,CEEQ`）。

## 5. CEEQ 特别确认

- Abaqus 定义：CEEQ = Equivalent Creep Strain（*Creep, law=STRAIN 积分），无量纲、恒 ≥0。
- v1.2 production 输出即 CEEQ 场（log10 域 POD），**继续作为第 5 输出，不重建**。

## 6. 应力坐标系审计（详见 `docs/STEP19_STRESS_COORDINATE_DEFINITION.md` 与 `step19_stress_coordinate_audit.json`）

- 全局笛卡尔（无 *ORIENTATION）；torus 环轴 = Z；θ = atan2(y,x)。
- 转换（逐质心，θ=atan2(y,x)）：
  - σr = S11·cos²θ + S22·sin²θ + 2S12·sinθ·cosθ
  - σθ = S11·sin²θ + S22·cos²θ − 2S12·sinθ·cosθ
  - σz = S33
  - **τ（面内）= τrθ** = (S22−S11)sinθ·cosθ + S12(cos²θ−sin²θ)（τrz、τθz 亦可导出）
- **严禁直接取 S12 为"面内剪应力"**——S12 是全局 xy 分量，与管壁局部方位无关。
- 单位：mm–N–s–MPa（E=155020 实证）→ 应力 **MPa**；CEEQ 无量纲。拉正压负。

## 7. 2304 element-centroid 映射

- C3D8R 单积分点**精确位于单元质心** → S 的 IP 值可直接用作 centroid 值，**无需平均/外推**。
- 单元编号与 production `_mesh()`（48×16×3）确定性一致（STEP15-B 已验证 CEEQ snapshot 提取）。
- → **2304 × 5（σr, σθ, σz, τ, CEEQ）可同一 mesh 显示**；API 可返回 5 个 field 数组 + 共享 centroids。

## 8. 数据覆盖（五输出场，`step19_multifield_feasibility.json`）

| 场 | 状态 | case 数 | 备注 |
|---|---|---|---|
| CEEQ | AVAILABLE | 135 | v1.2 已生产化 |
| σr / σθ / σz / τ | AVAILABLE | 443 | 需应力提取管线（新代码，非新 Abaqus） |
| TEMP（等温） | AVAILABLE | 464 | v1.2 域内全部等温 |
| ΔTr 径向梯度 | **PARTIAL** | 8 | GRAD_550_750_P{0,5,10,20} + 反向：TH-01/02 稳态传导 550↔750（内/外壁），3072/2304，S+TEMP 全，**无蠕变步/无 CEEQ** |
| ΔTz 轴向梯度 | **NOT_AVAILABLE** | 0 | 所有温度 BC 均为径向面 INNER/OUTER → DATA_REQUIRED |

其他覆盖缺口：P·Ro/w > 250 = 0 例（域上限维持 250）；1000h 桥接稀疏（16 snapshot）。

## 9. 径向/轴向温差审计

- **ΔTr 有探索性数据**：8 例 GRAD（ΔTr = ±200℃，内 550/外 750 或反向），含完整 S 与温度场，网格统一 2304。
  但：梯度端点 550↔750 超出 v1.2 等温域；无蠕变（CEEQ）输出 → **不能直接并入 v1.2 训练**。
- **ΔTz 无任何数据** → 必须设计新轴向梯度 thermal-mechanical cases（提案见 §12）。
- **不伪造**：ΔTr/ΔTz 在实现前不进 Web UI。

## 10. 架构判断：v1.3 Multi-Field（情况 A 成立）

- **情况 A 判定**：现有 ODB 已有完整 S + CEEQ，且 v1.2 域内 87 例全有 S → **v1.3 Multi-Field 可行，无需新 Abaqus case**。
- 架构：
  - 5 个独立 POD（POD_CEEQ / POD_σr / POD_σθ / POD_σz / POD_τ），每输出 TRAIN-only basis
  - 每模态 Ridge-Poly2（沿用 v1.2 配方：10 特征、log1p(t)、log10(P·Ro/w)、seed 42、case-level split）
  - 共享 2304 centroid mesh；一次推理输出 5 个 field
  - 应力提取管线（新）：读 ODB → S(2304×6) → θ 逐质心 → 圆柱转换 → 5 场 snapshot 矩阵
- 情况 B（Multi-output 联合 POD）不必要：各场 POD 方差近 1.0，独立建模更简单、与 v1.2 一致。
- **不训练**（本次仅审计；训练属 STEP20）。

## 11. 若需新增数据：最少 cases 估算（提案，不执行）

| 目标 | 最少新增 | 设计 |
|---|---|---|
| 仅应力场（v1.3 核心） | **0** | 直接用现有 87 例 ODB 提取 S |
| ΔTr 并入 550–650 域 | ~12 | 2 方向 × 3 幅度（±50/±100/±200℃）× 2 P，T=600 基 |
| ΔTz 并入 550–650 域 | ~12–16 | 2 方向 × 2–3 幅度 × 2–3 P × 1–2 T |
| ΔTr+ΔTz 联合 | ~24–30 | 上两者并集（共享热-力步） |
| 1000h 桥接 | ~10–15 | t=1000h × 非基准几何（G.3 遗留） |
| P·Ro/w>250 | 按需 | P 40 × 薄壁（域外扩展决策） |

## 12. 网页最终目标架构（STEP20 设计稿）

```
输入：T | P | t | Rm | Ro | w | （ΔTr、ΔTz —— 待模型就绪后加入，禁止先放后训）
输出选择：○σr  ○σθ  ○σz  ○τ  ●CEEQ（任意单选，多选后续）
3D：同一 2304 mesh 显示所选场；max/mean/P95/热点 element/热点 xyz/单位/Physics status
单位：应力 MPa（实证单位体系）；CEEQ 无量纲
```

## 13. 颜色系统审计（网页现状与建议）

**现状**：`App.tsx` 中 `colorRange` 按当前场自身 min/max 归一化 → **相对色标**。
→ 工况改变（如 T 550→650）后 CEEQ 值域变化数倍，但颜色分布几乎不变——正是"颜色变化不明显"的根因。

**建议（STEP20 实施）**：
1. **双模式切换**：
   - **绝对色标**（默认）：全局固定数值范围（跨工况可比，如 CEEQ log10 全局域 [−10, −4]）
   - **相对色标**：per-case min/max（观察内部空间分布）
   - UI 按钮：`[绝对色标] [相对色标]`，色标轴显示实际数值
2. **CEEQ 默认 log10 映射**（现状已如此，保持）。
3. **应力 diverging 色标**：应力有正有负，禁用 0→max 线性色标；采用 **压(蓝) ← 0(白) → 拉(红)** 居中发散色标，midpoint=0 锚定。
4. 绝对模式的固定范围来源：v1.3 训练场的全局 min/max（生成配置随模型冻结）。

## 14. 审计产物清单

- `ml/metrics/step19_odb_field_inventory.csv` / `.json`（464 ODB 场清单，含分量/position/values）
- `ml/metrics/step19_temperature_audit.json`（TRAIN/VAL/EXT 温度覆盖）
- `ml/metrics/step19_input_feature_audit.json`（v1.2 feature schema）
- `ml/metrics/step19_stress_coordinate_audit.json`（坐标系/转换/单位/符号）
- `ml/metrics/step19_multifield_feasibility.json`（五场可用性/缺口/架构建议）
- `docs/STEP19_STRESS_COORDINATE_DEFINITION.md`（应力定义文档）
- 审计脚本：`postprocess/step19_odb_inventory.py`、`step19_temperature_audit.py`、`step19_report_build.py`

## 15. 15 问最终回答

1. CEEQ 是否即等效蠕变应变？ **是**（Abaqus CEEQ = Equivalent Creep Strain，v1.2 已实现）。
2. 现有 ODB 是否有完整 S 张量？ **是**（443/464，全 6 分量）。
3. 可否提取 σr？ **可以**（圆柱转换，AVAILABLE）。
4. 可否提取 σθ？ **可以**（AVAILABLE）。
5. 可否提取 σz？ **可以**（S33 直接，AVAILABLE）。
6. 可否提取 τ？ **可以**（τrθ 为主，τrz/τθz 亦可，AVAILABLE）。
7. 哪些可直接从已有 ODB 获得？ **σr、σθ、σz、τ、CEEQ、TEMP（等温）——全部**（需新提取代码，不需新 Abaqus）。
8. 哪些需要重新运行 Abaqus？ **ΔTr 域内蠕变梯度 case、ΔTz（新设计）**；五场本体不需要。
9. 哪些需要重新训练 AI？ **五场 surrogate（v1.3）需要新训练**；v1.2 保持冻结不重训。
10. ΔTr 是否已有数据？ **探索性有**（8 例 GRAD ±200℃，无蠕变，550–750 梯度）。
11. ΔTz 是否已有数据？ **无**（DATA_REQUIRED）。
12. 是否需要新增 thermal-mechanical cases？ **需要**（ΔTz 必须；ΔTr 域内蠕变梯度建议；详见 §11）。
13. v1.3 还是 v2 更合适？ **v1.3 Multi-Field（情况 A）**：数据已具备，沿用 POD+Poly2 配方，风险最低。
14. 最少新增 cases？ **0（五场本体）**；ΔTr/ΔTz 扩展 ~12–30（见 §11 表）。
15. 五输出推荐架构？ **独立 POD×5 + 每模态 Ridge-Poly2 + 共享 2304 mesh**，一次推理 5 场，绝对/相对双色标，CEEQ log10、应力 diverging。

## 16. 状态声明

STEP19 AUDIT = **COMPLETE** ｜ V1.2 = **UNCHANGED** ｜ LOCKED = **NEVER READ** ｜ TRAINING = **NOT STARTED** ｜ WEBAPP = **UNCHANGED** ｜ NEW ABAQUS CASE = **0** ｜ 318 DATASET = **UNCHANGED**
