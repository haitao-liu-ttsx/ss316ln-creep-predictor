# STEP A：温度数据恢复与可用性审计（700/750℃）

日期: 2026-08-20 | 性质: 只读审计——未训练、未修改 v1.2、未读 LOCKED、未新增 Abaqus case、未改 318
目标: 回答 "700/750℃ 是否有可用于 Abaqus / 材料模型 / AI surrogate 的合法数据"，区分 A–F 六类信息。

---

## 1. 六类信息分类结果（全项目实测）

### A. 论文中存在的 700/750℃ 实验数据 —— ✅ 存在（1 篇）

| 来源 | 温度 | 数据 | 材料 | 状态 |
|---|---|---|---|---|
| **Pan et al. 2024** (Nucl. Eng. Des. 424:113288, doi:10.1016/j.nucengdes.2024.113288) | **650/700/750℃** | Table 3: 空气蠕变断裂时间（700℃-225MPa→103.87h；750℃-145MPa→31.77h）；Fig.10: MCR（最小蠕变速率）vs 应力曲线；Table 2: E / Rp02 / UTS 实测 | MAT-02, **N=0.13%**, 20μm 细晶 | 论文 PDF 在 `D:\harness_work\316LN\1-s2.0-S0029549324003881-main.pdf` |
| GaneshKumar 2013 / Mathew 2015 | 仅 550/600/650 | — | MAT-05/04, N=0.14% | **无 700/750 数据** |
| Schirra 1999 / Ravi 2012 | 550/600 或已排除 | — | — | 不相关 |

> 注意：Pan 2024 的 700/750 蠕变数据材料为 **N=0.13% 细晶（20μm）**，与项目核心身份 MAT-05/04（N=0.14%，78μm，IGCAR NE316LN）**成分接近但非同一炉次**——使用须带 documented caveat。

### B. 已提取的数值参数（700/750）—— ✅ 部分存在，但**无 Norton 稳态蠕变参数**

已入 `materials/SS316LN_N014/` 数据库（来源全部标注）：

| 参数 | 700℃ | 750℃ | 来源 | 质量 |
|---|---|---|---|---|
| 蠕变断裂时间 t_rupt | 103.87 h @225MPa | 31.77 h @145MPa | Pan2024 Table 3 | A |
| E 弹性模量（实测） | 141000 MPa | 119000 MPa | Pan2024 Table 2（MAT-02） | A |
| σy / Rp02 / 硬化（9 行/温度） | ✅ | ✅ | plastic.csv（Pan2024） | A |
| **Norton C / n（稳态蠕变）** | **❌ 无** | **❌ 无** | — | — |

对照：550/600/650 的 Norton C/n（GaneshKumar2013 Table 2）已存在：
- 550: C=2.79e-27 %/h/MPaⁿ, n=9.51；600: 1.28e-24, 9.04；650: 8.46e-20, 7.57
- Abaqus 卡使用换算值：550: A=7.75e-32, n=9.51（G 系列 inp）

### C. 已写入 Abaqus 材料卡 / Norton law 的参数 —— ❌ 700/750 无 Norton

- **G 系列（v1.2 域）inp** `*Creep, law=STRAIN`：**仅 550/600/650 各一行**（单温度行，如 `7.75e-32, 9.51, 0., 550`）
- **B 系列（历史）inp**：无 *Creep 块（弹塑性：E=141000, σy=212）——E=141000 恰为 Pan2024 700℃ 实测值
- Density/Expansion 表：B 系列含 550-750 五温度行（来源未记录；metadata.yaml 明确热物性 `MISSING - not invented`，此表视为早期估计）
- **结论：700/750℃ 无法合法进入 Abaqus 蠕变材料模型——缺 Norton C/n。**

### D. 已运行 Abaqus 的 700/750℃ ODB —— ✅ 存在，但**全部无蠕变**

- 318 dataset（`data/ai_ready_v4/simulation_dataset_318.csv`，公开文件）：
  - T_uniform: 550×34, 600×30, 650×45, 675×10, **700×24**, 725×10, **750×25**
  - T_inner/T_outer（梯度行）: 700×25 / 750×57（含 B004-B006、LHS001-177 设计行）
- 但这些 case **全部 t=0（无蠕变步）**：弹塑性 / 热应力基准。inventory 确认 57 个 CEEQ case 的 T ∈ {550,600,650}，**700/750 的 ODB 无 CEEQ**（有完整 S 张量 + 均匀 TEMP）
- LHS 177 个梯度设计行：**无对应 ODB**（从未求解）

### E. 已进入 AI TRAIN/VAL 的 700/750℃ —— ❌ 零

- 57 个 CEEQ snapshot case：T = {550:19, 600:18, 650:20}
- v1.2 训练 87 例（TRAIN 68 / VAL 19）：T ∈ {550,600,650}
- EXT 27 例：T ∈ {550,600,650}
- production domain（predict_field.py）：T ∈ {550,600,650}，700/750 返回 OUT_OF_DOMAIN + DATA_REQUIRED

### F. 仅存在文献、尚未数字化 —— ✅ Pan2024 Fig.10 是唯一缺口

- **Pan2024 Fig.10：700/750℃ MCR（最小蠕变速率）vs 应力曲线——尚未数字化**。这是恢复 700/750℃ Norton C/n 的**唯一直接数据源**。
- Mathew2015 Fig.1/Fig.3、GaneshKumar 2013 stress-rupture 图：仅 550/600/650（与现有参数同源，未数字化无新增价值）

---

## 2. 关键判定

1. **700℃ 可靠蠕变数据？** 部分——有 1 个断裂时间点 + E/σy 实测 + Fig.10 MCR 曲线（未数字化）；**无 Norton C/n**。
2. **750℃ 同上**：1 个断裂时间点 + E/σy 实测 + Fig.10（未数字化）；**无 Norton C/n**。
3. **800℃ 及更高：无任何数据**（目标域 550-750 不涉及，无需讨论）。
4. **绝对禁止**：把 A/F 当 E——目前 700/750 从未进入任何 TRAIN/VAL/EXT。

## 3. 恢复路径（STEP B/C 建议，本次未执行）

1. **STEP B（文献提取，LITERATURE-DERIVED）**：
   - 数字化 Pan2024 Fig.10 的 700/750℃ MCR 曲线（~5-8 点/温度）
   - 拟合 Norton ε̇=A·σⁿ：700/750℃（单位统一：文献 %/h → Abaqus）
   - 用 650℃ 同时数字化 Pan 曲线 vs GaneshKumar 参数做交叉验证（N=0.13 vs 0.14 的炉次差异量化）
   - E/σy 直接用 Pan2024 Table 2 实测（700: 141000 / 750: 119000 MPa）
2. **STEP C（新 Abaqus creep cases，700/750）**：
   - 温度档：550/600/650/700/750（550-650 复用现有）
   - 700/750 新增：**~40-48 例建议**（2 温度 × 3-4 几何 × 3 P × 2 时间 t=1000/3000h + 少量 100h 桥接），满足 TRAIN/VAL case-level 分层 + EXT 预留
3. **v1.3 = Multi-Field + Expanded Temperature Domain**：POD×5 + Ridge-Poly2，2304 mesh，域 T=550-750（材料表 5 行）

## 4. 审计产物

- 本报告 + `ml/metrics/step19a_temperature_recovery.json`（机器可读分类）
- 证据文件（只读）：`materials/SS316LN_N014/{creep,elastic,plastic,derived_interpolation_675_725,metadata}.csv/yaml`、`data/ai_ready_v4/simulation_dataset_318.csv`、`ml/metrics/step15_odb_inventory.csv`、`ml/metrics/step19_odb_field_inventory.csv`、`D:\harness_work\316LN\SS316LN_CREEP_AIR_014N_550_750_{RAW,FIT_CANDIDATES}.csv`

## 5. STEP B 执行结果（Pan2024 PDF 直接提取，2026-08-20 追加）

PDF 权限标志已用 pypdf 剥离（`316LN/_pan2024_clean.pdf` 为工作副本），文本层完整提取：

**Table 2（力学性能实测）**：650: E=171GPa, Rp0.2=227, σb=432；**700: E=141, Rp0.2=212, σb=384；750: E=119, Rp0.2=199, σb=317**（MPa）

**Table 3（空气蠕变断裂）**：650℃-345MPa→36.98h；**700℃-225MPa→103.87h；750℃-145MPa→31.77h**（钠环境各行排除）

**Table 5（Norton A/n 拟合，钠环境）**：
- 650: A=5.62e-64, n=24.20（n 异常高 → 不可靠，见下）
- **700: A=3.89e-25, n=9.38**
- **750: A=1.23e-40, n=17.56**

**文本倍数**（同应力 MCR 比，钠/空气）：650→6.18、700→4.18、750→2.37

**→ 严格环境分类（用户裁定：只要空气环境）——`ml/metrics/step19a_pan2024_air_only.json`**：

| 数据 | 环境 | 状态 |
|---|---|---|
| Table 2 E/Rp0.2/σb（650/700/750） | 拉伸测试（非钠） | ✅ **AIR 可用**：E=171/141/119 GPa，σy=227/212/199 MPa |
| Table 3 空气断裂行 | **AIR** | ✅ 650℃-345MPa-36.98h；700℃-225MPa-103.87h；750℃-145MPa-31.77h |
| Table 5 Norton A/n（24.2/9.38/17.56） | **钠环境** | ❌ **排除**（论文明示 sodium environment 拟合） |
| Fig.10 MCR-stress 拟合线 | **钠环境** | ❌ 排除（Table 5 对应图） |
| Fig.9 应变率-时间曲线（含空气） | 空气+钠 | ⚠️ 空气曲线存在但每温度仅 1 条（1 应力），数字化需图例色识别+轴标定，标记 PENDING |

**空气 Norton 700/750 结论：DATA_REQUIRED**——Pan2024 每温度仅 1 个空气 MCR 点（1 应力），**无法独立拟合 A/n**。
- 此前生成的"钠 A ÷ 倍数(6.18/4.18/2.37) → 空气 C/n"（9.31e-26/9.38、5.19e-41/17.56）**撤回作为主来源**——本质是钠参数推导，非直接空气测量；如需作参考值已标注 REFERENCE-ONLY。
- 替代路径（需用户裁定）：a) 提供其他空气蠕变数据源；b) Fig.9 数字化 3 个空气 MCR 单点 + 假设 n（文献趋势 6-8，须显式标记模型假设）；c) 无外推规则禁止用 GaneshKumar 外推。
- 可合法进入 Abaqus 的空气参数：E（171/141/119 GPa 实测）+ σy（227/212/199 MPa 实测）；**蠕变 Norton 550-650 用 GaneshKumar（现有），700/750 = 缺口**。
- Fig.10 像素数字化（`step19a_pan2024_fig10_points.csv`）仅作为 Table 5 位置自洽验证保留。

## 5.1 其余 4 篇 PDF 全量扫描结果（`ml/metrics/step19a_papers_scan.json`）

| 论文 | 温度 | 结论 |
|---|---|---|
| **Ravi 2012** (JNM 427, `1-s2.0-S0022311512002152`) | 600℃ 流钠 | N=0.06% **排除**（成分不匹配）；无 700/750 |
| **Schirra 1999** (NED 188, `1-s2.0-S0029549399000461`) | 550/600℃ 低应力 | MCR 数据 n≈6.8（低应力域）；VALIDATION 级（N 未确认）；**引用文献中 700-750℃ 的 n 值 ~6-8**（NRIM/Nakazawa） |
| **Mathew 2015** (MHT 32(4), `MHT146-...pdf`) | 550/600/650℃ | 14N 炉次 MCR（Fig.1 @650）+ 设计曲线；n 14N≈7-8 与 GaneshKumar 650 n=7.57 **交叉一致**；无 700/750 |
| **GaneshKumar 2013** (NED 265, `NED-...pdf`) | 550/600/650℃ | Table 2（项目 creep.csv 的来源）、Table 3 St、Fig.6 MCR n=9.6/9.0/7.5（R²=0.99）**交叉确认项目参数**；无 700/750 |

**交叉验证结论**：
1. 项目现有 550/600/650 空气参数（GaneshKumar Table 2）得到 Mathew 2015（同 IGCAR 数据集）确认。
2. **Schirra 引用的 700-750℃ 文献 n 值 ~6-8** 与 Pan 750℃ 钠拟合 n=17.56 明显不符 → Pan 的 n 很可能被"每温度仅 3 个高应力点"拟合抬高；**750℃ 参数须保守使用并设计验证 case**。
3. **700/750℃ 数值参数唯一来源仍为 Pan 2024**（已完成提取，见 §5）。

## 6. 状态声明

STEP19A AUDIT = COMPLETE ｜ V1.2 = UNCHANGED ｜ LOCKED = NEVER READ ｜ 318 = UNCHANGED ｜ TRAINING = NOT STARTED ｜ NEW ABAQUS CASE = 0 ｜ WEBAPP = UNCHANGED ｜ 文献数字化 = **COMPLETE（Pan2024 全部表格 + 文本）** ｜ 像素数字化 = 初步验证完成 ｜ Norton 700/750 拟合 = LITERATURE-DERIVED 待裁定
