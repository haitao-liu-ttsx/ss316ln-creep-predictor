# STEP 14-A.6 首例 CEEQ 求解与提取验证

日期: 2026-08-20
状态: **PASS — 链路 INP→Abaqus/Standard→ODB→CEEQ extraction→log10 target→sanity check 全部验证通过**
机器可读证据: `ml/metrics/step14a_first_case_validation.json`、`simulation/generated_cases_step14a_ceeq/first_case_extract.json`

## 1. 执行对象（仅此 1 例）

`CEEQ14A_T550_P5_t500h_Rm100_Ro20_w4`：T=550°C、P=5 MPa、t=500 h、Rm=100/Ro=20/w=4（基准几何）

## 2. Preflight（执行前核对）

manifest / generation_metadata / INP 三方一致：Norton `7.75e-32, 9.51, 0., 550`、`*Visco 0.01, 500, 1e-06, 500`、`ALLN, 550.00`、`SINNER, P, 5`、E=155020 MPa（RCCMR@550）、medium 网格 3072 节点。

## 3. Abaqus 求解

- Abaqus 2024 / Standard；`cpus=4`；29 s（16:26:22→16:26:51）；return 0
- license 正常检出；`.sta` 末行 `THE ANALYSIS HAS COMPLETED SUCCESSFULLY`（20 个增量帧，末帧 500 h）
- `.msg` 汇总：**0 ERROR MESSAGES**；警告仅 3 条输入处理（显式积分稳定性限制，*Visco 预期行为）+ 1 条分析警告；0 数值问题/0 负特征值

## 4. ODB 与 CEEQ 提取

- ODB 存在、可读；step TM、最终 frame time = **500.0000 h** ✓
- **实际输出变量**（从 ODB 实测，非假设）：`CEEQ, E, EE, NT11, RF, S, TEMP, U`（8 个 field，与 STEP13 MODEL_C 模板一致）
- CEEQ 为元素场（2304 单元）：**max=7.847e-16、mean=1.332e-16、min=4.592e-18**（全正）
- **log10(CEEQ_max) = −15.1053**（非零域、无 epsilon，与 STEP13 定义一致）
- 提取方法：最终帧、元素场 max（与 v1/v3 postprocess 的 CEEQ_max 定义逐字相同）

## 5. Sanity check（逐项 PASS）

| 项 | 结果 |
|---|---|
| CEEQ ≥ 0 | PASS（min 4.6e-18） |
| CEEQ 有限 / 无 NaN/Inf | PASS |
| 温度 | PASS（NT11=TEMP=550） |
| vm 一致性 | PASS（25.07 MPa = 5.01×P，与 318 集标定一致） |
| 最终时间 | PASS（500 h） |
| **Norton 数量级交叉检查** | **PASS**：v1 `CR_550_P5_T1000h` CEEQ=1.569e-15（同 T/P/几何）→ 500h 期望 ≈7.8e-16；实测 **7.85e-16**（CEEQ∝t 线性，与锁定 Norton 本构数量级与趋势完全相容） |
| 异常尖峰/异常 0 | 无 |

## 6. 历史数据保护（求解后复验）

- 318 dataset checksum `20F21EBC67EA` — **unchanged** ✓
- locked test checksum `FA573E330926` — **unchanged** ✓
- `ml/final/` 模型 mtime 未变 — **unchanged** ✓
- split/材料/报告均未触碰 ✓

## 7. 结论

链路验证完整通过：INP → Abaqus/Standard → ODB → CEEQ extraction → log10 target → sanity check → 历史保护。首例 CEEQ 输出与锁定 Norton 本构相容（CEEQ∝t 精确成立）。

---
*仅求解 1 例；其余 26 例未执行；未训练模型；未修改任何历史数据。*
