# STEP 19B — 700/750°C 空气蠕变参数最终溯源审计

日期: 2026-08-20 | 性质: 论文原文只读审计（Pan2024 原始 PDF + 其余三篇）
结论: **C = AIR_NORTON_DATA_REQUIRED**（700°C 与 750°C 空气 Norton 均不可由现有文献直接支持）

## 1. Table 5 环境判定 — SODIUM（铁证两条）

- **EV-1（PDF p.6, Discussion）**：`"the creep behavior of the specimens in the high temperature sodium environment also follows the power law creep relationship and the parameters A and n at each temperature are given in Table 5."`
- **EV-7（PDF p.9, Conclusions）**：`"The creep behavior of 316LN in sodium at 650°C, 700°C and 750°C is in accordance with the creep power law, the stress index n is 24.20, 9.38 and 17.56, respectively."`

→ **Table 5 的 A/n（650: 5.62e-64/24.20；700: 3.89e-25/9.38；750: 1.23e-40/17.56）= 钠环境拟合参数**（论文两处原文明确）。

## 2. Fig.10 环境判定 — SODIUM

- Caption（EV-6, p.7）中性："Correlation between ε̇c and stress at each temperature"
- 但正文（EV-3, p.6）在同一句链中把 Fig.10 与"high temperature sodium environment ... parameters A and n ... Table 5"绑定 → **Fig.10 = 钠环境 MCR-σ 拟合图**（与 Table 5 对应）。依据上下文而非颜色。

## 3. Fig.9 空气数据审计 — DATA_INSUFFICIENT

- Caption（EV-5, p.6）："(a) 650°C; (b) 700°C; (c) 750°C" 应变率-时间曲线
- 正文（EV-4, p.5）："The creep strain rates of the specimens in **air and sodium** ... are shown in Fig. 9" → 含空气曲线
- **但每温度空气曲线仅 1 条**（对应 Table 3 空气行唯一应力：650-345、700-225、750-145 MPa）
- **1 个应力点/温度 → 无法独立拟合 Norton C/n → DATA_INSUFFICIENT**

## 4. Table 3 空气/钠严格区分

| 温度 | AIR（σ, t_rupt） | SODIUM（σ, t_rupt） |
|---|---|---|
| 650 | 345 MPa, 36.98 h | 345→13.52h; 330→40.09h; 315→52.61h |
| 700 | 225 MPa, 103.87 h | 225→33.31h; 210→78.04h; 195→106.22h |
| 750 | 145 MPa, 31.77 h | 145→19.04h; 140→29.39h; 135→48.81h |

## 5. 四个数字溯源（9.31e-26 / 9.38 / 5.19e-41 / 17.56）

| 数字 | 类别 | 说明 |
|---|---|---|
| 700°C n=9.38 | **B**（论文钠参数） | Table 5 钠 n，原文直接给出 |
| 700°C C=9.31e-26 | **D**（钠倍率换算） | = 3.89e-25 ÷ 4.18（EV-4 比率），非空气测量 |
| 750°C n=17.56 | **B**（论文钠参数） | Table 5 钠 n |
| 750°C C=5.19e-41 | **D**（钠倍率换算） | = 1.23e-40 ÷ 2.37（EV-4 比率），非空气测量 |

**四个数字全部非空气直接实测。** 已修正 `step19a_pan2024_derived_params.json` 中误导性键名 `literature_derived_air` → `sodium_ratio_derived_reference_NOT_air_measured`；`step19a_pan2024_air_only.json` 已正确标注 DATA_REQUIRED。

## 6. 其余三篇对 700/750 空气 Norton 的支持 — 均不支持

- GaneshKumar 2013（NED 265）：550/600/650 实测（Table 2）——无 700/750
- Mathew 2015（MHT 32）：550/600/650（Fig.1 @650）——无 700/750
- Schirra 1999（NED 188）：550/600 实测；700-750°C n≈6-8 仅为**引用**（NRIM/Nakazawa）——非本项目实测空气参数，不得作为 SS316LN 空气 Norton

## 7. 最终结论与冻结

**结论 = C（AIR_NORTON_DATA_REQUIRED）**

- 700°C 空气 Norton：**DATA_REQUIRED**
- 750°C 空气 Norton：**DATA_REQUIRED**
- 禁止：生成 700/750 Abaqus creep case ｜ 修改 v1.2 ｜ 训练 v1.3 ｜ 放开网页 700/750 输入
- 保留可用空气数据（非 Norton）：E=171/141/119 GPa、σy=227/212/199 MPa（Table 2）、断裂 3 点（Table 3 air 行）

## 8. 状态声明

**STEP19B = COMPLETE ｜ V1.2 = UNCHANGED ｜ V1.3 TRAINING = NOT STARTED ｜ NEW ABAQUS CASES = 0 ｜ WEBAPP = UNCHANGED ｜ LOCKED = NEVER READ ｜ 318 DATASET = UNCHANGED**
