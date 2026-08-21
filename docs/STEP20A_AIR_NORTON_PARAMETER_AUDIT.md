# STEP 20-A — 700/750°C AIR Norton 蠕变参数正式恢复与可用性审计

日期: 2026-08-20 | 性质: 文献原始数据恢复 + 拟合 + 审计（未运行 Abaqus、未训练、未修改任何模型/数据）
核心文献: **FZKA 7065** — Rieth, M. et al., "Creep of the Austenitic Steel AISI 316 L(N) – Experiments and Models", FZK Karlsruhe 2004, 76 p.
PDF: 官方 KIT 来源下载成功（5.94 MB，84 页，`316LN/_step19a/FZKA7065.pdf`）

---

## 1. 原始证据（逐项核验）

| 项 | 证据 | 位置 |
|---|---|---|
| 实验环境 = **AIR** | "Loading took place in **normal atmosphere (air)** via lever arms (1:15) using weights." | PDF p.11（§2.2 Equipment） |
| 材料/炉次 | AISI 316 L(N)（DIN 1.4909，V4A 家族）；**heat no. 11477 from Creusot-Marell**；40mm 热轧板，1100°C 固溶 + 水淬，δ-铁素体 <1% | PDF p.10（§2.1 Material） |
| 化学成分（Table 1） | C 0.02 / Si 0.32 / Mn 1.80 / P 0.02 / S 0.006 / Cr 17.34 / Ni 12.50 / Mo 2.40 / Cu 0.12 / **N 0.08** / Al 0.018 / B 0.0014 (wt%) | PDF p.11 Table 1 |
| 晶粒度（Table 3） | d ≈ **100 µm**（实测） | PDF p.56 Table 3 |
| 数据类型 | **minimum creep rate**（minε̇，稳态蠕变率），单位 **10⁻⁶/h**（表头明确） | PDF p.58 Table 7 |
| 试样 | M5×30 mm（Table 7）、M8×200 mm（Table 8 长期低应力） | PDF p.58-59 |

**Table 7 原始数据（与待核验数字逐一吻合）**：

| Test | T (°C) | σ (MPa) | tm (h) | minε̇ (10⁻⁶/h) |
|---|---|---|---|---|
| ZSV1943 | **700** | 170 | 59 | **3680** |
| ZSV1917 | 700 | 150 | 125 | **1653** |
| ZSV1925 | 700 | 120 | 626 | **293** |
| ZSV1919 | 700 | 100 | 1383 | **102** |
| ZSV1960 | 700 | 80 | 4208 | **19** |
| ZSV2085 | 700 | 60 | aborted | 2.6（未计入主拟合） |
| ZSV1939 | **750** | 100 | 152 | **1760** |
| ZSV1940 | 750 | 80 | 440 | **318** |
| ZSV1921 | 750 | 60 | 2650 | **60** |
| ZSV1913 | 750 | 40 | 15692 | **10** |

> 用户提供的待核验数据与 Table 7 原文**完全一致**（700: 170/150/120/100/80 → 3680/1653/293/102/19；750: 100/80/60/40 → 1760/318/60/10；单位 10⁻⁶/h）。

## 2. Norton 拟合结果（log-log OLS：lnε̇ = lnC + n·lnσ）

**700°C**（5 点，80–170 MPa）：

| 指标 | 值 |
|---|---|
| n | **6.97** |
| C（1/h/MPaⁿ） | **1.05e-18** |
| C（Abaqus s⁻¹/MPaⁿ = C/3600） | **2.92e-22** |
| R² | 0.9985 |
| RMSE(log) / MAE(log) | 0.074 / 0.063 |
| 灵敏度 | 去最高点 n=7.00；去最低点 n=6.90；中间点 n=6.90；含 aborted 点 n=6.98 → **±1.5%，极稳健** |
| 逐点残差 | 见 `ml/metrics/step20a_fit_raw.json`（max rel err ~15%） |

**750°C**（4 点，40–100 MPa）：

| 指标 | 值 |
|---|---|
| n | **5.56** |
| C（1/h/MPaⁿ） | **9.99e-15** |
| C（Abaqus s⁻¹/MPaⁿ = C/3600） | **2.78e-18** |
| R² | 0.985 |
| RMSE(log) / MAE(log) | 0.236 / 0.233 |
| 灵敏度 | 去最高点 n=4.95；去最低点 n=6.58；中间点 n=5.80 → **4 点数据灵敏度偏高，如实记录** |

## 3. 单位核对（与项目 Abaqus 体系）

- 项目现有 Abaqus 卡（G 系列 inp `*Creep, law=STRAIN`）：`A(T), n, m=0, T`；STEP4 规则 `A_abq(s⁻¹/MPaⁿ) = C(%/h/MPaⁿ)/100/3600`（GaneshKumar 的 C 为 %/h 体系）
- FZKA Table 7 的 minε̇ 为**绝对应变速率**（10⁻⁶/h，即 1/h 体系）→ 换算到 Abaqus 只需 **÷3600**（h→s），**无 % 因子**（与 GaneshKumar 的 %/h 体系不同，勿混用）
- 已验证：650°C @200MPa Rieth 实测 1.24e-3 1/h vs GK 预测 2.22e-4 1/h（比值 5.6x，物理上 = N 0.08 vs 0.14 的蠕变强度差）

## 4. 与 Rieth 完整稳态模型对照

- 模型 = **Eq.(57)**：ε̇s = ε̇C + ε̇PL（+ε̇PLBD 当 σ>86 MPa），σ≤86 MPa 时 ε̇C + ε̇P
- 参数（Tables 4-6）：D0L=37.5e-6 m²/s, QL=280 kJ/mol；D0B=6e-6, QB=200；c3=2e20, D0C=10e-6, QC=520, **n=5**, α′=800；QP=460 kJ/mol, ∆F=1.04e-18 J, l=40nm, γ̇0=1e6
- 报告自评：模型对 600°C（含扩散域）拟合完美，600/650/700 验证良好；**550°C 低应力数据高于模型**（试验过早中止的误差讨论，P.49-50）
- **full-model 数值复算受限**：PDF 数学排版非机器可读，公式重建不可靠 → 本审计以 Table 7 原始数据简单 Norton 拟合为主（用户要求），full-model 对比标记 LIMITED
- 注：700/750°C 拟合的 n（6.97/5.56）与模型 n=5 的量级关系一致（高温/中应力接近幂律域）

## 5. 材料匹配评估

| 项 | Rieth CRM 11477 | 项目（GaneshKumar MAT-05） |
|---|---|---|
| 牌号 | AISI 316L(N) DIN 1.4909 | 316LN (NE316LN) IGCAR |
| **N (wt%)** | **0.08** | **0.14** |
| 晶粒度 | ~100 µm | ~78 µm |
| 处理 | 1100°C 固溶 + 水淬（40mm 板） | AIM+ESR 双熔 → 固溶 >1323K 水淬 |
| 环境 | AIR ✓ | AIR ✓ |

**材料匹配等级 = C**（同材料体系、成分接近，但 N 含量差 1.75 倍 → 蠕变率差 ~5.6 倍）。**影响**：Rieth 参数预测蠕变**偏快**（N 低）→ 对寿命预测偏保守方向；但不可直接等同于 N=0.14 材料。

## 6. 与现有 550–650°C 数据交叉验证

| T | Rieth (FZKA) n | GK (项目) n | 说明 |
|---|---|---|---|
| 550 | 11.58 | 9.51 | 应力域不同（Table 7 高应力 vs GK 140-350） |
| 600 | 11.10 | 9.04 | 同上 |
| 650 | 8.41 | 7.57 | 200MPa 点预测差 5.6x（N 效应） |
| **700** | **6.97** | — | 本项目新增 |
| **750** | **5.56** | — | 本项目新增 |

n(T) 单调下降（11.58→5.56），物理一致。**不做 n 平均**（不同材料/应力域）。

## 7. 与 Pan 2024 严格区分

| T | Pan AIR（断裂寿命） | Pan SODIUM（Table 5） | **Rieth AIR（本审计）** |
|---|---|---|---|
| 700 | 225MPa→103.87h（仅断裂，非 MCR） | A=3.89e-25, n=9.38 **SODIUM — DO NOT USE AS AIR** | **C=1.05e-18 1/h, n=6.97** |
| 750 | 145MPa→31.77h（仅断裂） | A=1.23e-40, n=17.56 **SODIUM — DO NOT USE AS AIR** | **C=9.99e-15 1/h, n=5.56** |

- Pan AIR 断裂点仅作 rupture-life validation 锚（**不是**稳态蠕变率，不拟合 Norton）
- 零 sodium→air 数学转换（严格执行）

## 8. Abaqus 可用性判定

| 温度 | 判定 |
|---|---|
| **700°C** | **USABLE WITH LITERATURE-DERIVED FLAG**（AIR ✓ 多应力点 ✓ 单位明确 ✓ 拟合稳健 ✓ 材料 C 级） |
| **750°C** | **USABLE WITH LITERATURE-DERIVED FLAG**（同上；4 点拟合灵敏度偏高 → 建议验证 case 于 60–80 MPa） |

判定依据：AIR 环境（P.11 原文）｜ 316L(N) 材料体系（C 级匹配）｜ minimum creep rate = 稳态（Table 7 定义）｜ 多应力点（5/4 点）｜ 单位明确（10⁻⁶/h）｜ C/n 可拟合（R²≥0.985）。

## 9. 产物

- `ml/metrics/step20a_air_norton_candidates.json`（候选参数全字段）
- `ml/metrics/step20a_fit_raw.json`（逐点预测/残差/灵敏度）
- 证据 PDF：`316LN/_step19a/FZKA7065.pdf`（官方 KIT 下载）+ 全文文本 `_fzka7065_text.txt`

## 10. 状态声明

**STEP20-A = COMPLETE ｜ V1.2 = UNCHANGED ｜ V1.3 TRAINING = NOT STARTED ｜ NEW ABAQUS CASES = 0 ｜ WEBAPP = UNCHANGED ｜ LOCKED = NEVER READ ｜ 318 DATASET = UNCHANGED ｜ ABAQUS MATERIAL CARD = UNCHANGED**
