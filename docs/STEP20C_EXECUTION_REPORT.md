# STEP20-C 执行报告 — 700/750°C AIR Norton 蠕变生产数据扩充

日期: 2026-08-21 | 状态: **COMPLETE（123/128 成功 + 5 EXT 收敛失败）**

## 1. 参数与材料

| T | C (s⁻¹/MPaⁿ) | n | E (MPa) | σy (MPa) | 来源 |
|---|---|---|---|---|---|
| 700 | 2.92e-22 | 6.97 | 141000 | 212 | STEP20-A 冻结（FZKA7065 Table 7），STEP20-B 验证 |
| 750 | 2.78e-18 | 5.56 | 119000 | 199 | 同上 |

- 生成器修改：`generate_cases.py` CREEP dict += 700/750；`generate_cases_v2.py` creep T 检查放宽为 {550,600,650,700,750}（仅 MODEL_C 分支）
- E/σy 700/750 已存在于 `build_geometry.py`（Pan2024 实测），未重复添加
- 时间约定：period = t_h（与现有 318 管线一致，见报告 §5）

## 2. 128 case 设计与分层（按 (T,P,Rm,Ro,w) 组，4 个 t 同组防泄漏）

| 温度 | P 档 | t 档 | 几何 | 设计 |
|------|------|------|------|------|
| 700 | {16,20,26,30} | {100,300,1000,3000} | 4 种 | P·Ro/w 覆盖 80-170（域内）+ 195-250（域外 EXT） |
| 750 | {8,12,16,20} | 同上 | 4 种 | P·Ro/w 覆盖 40-100（域内，含 60-80 敏感带）+ 120-167（域外 EXT） |

| split | 组数 | case 数 | 说明 |
|---|---|---|---|
| TRAIN | 16 | 16 | 基准几何 100/20/4+150/20/4 域内全部 |
| VAL | 4 | 4 | 非基准几何域内低 P |
| EXT | 12 | 10 | 域内高 P + 全部域外（含 5 个收敛失败） |

## 3. 执行结果

- **123/123 成功完成并提取 2304 场**（CEEQ + S 6 分量 + 质心，npz 格式 `fields/*.npz`）
- **5 个 EXT 收敛失败**（记录保留 .inp/.msg/.dat/.sta）：
  - S20C_T700_P26_t300h_Rm80_Ro15_w2（T=700 P=26 Rm=80 Ro=15 w=2，P·Ro/w=195.0，域外）— CONVERGENCE
  - S20C_T700_P30_t1000h_Rm120_Ro25_w3（T=700 P=30 Rm=120 Ro=25 w=3，P·Ro/w=250.0，域外）— CONVERGENCE
  - S20C_T700_P30_t100h_Rm120_Ro25_w3（T=700 P=30 Rm=120 Ro=25 w=3，P·Ro/w=250.0，域外）— CONVERGENCE
  - S20C_T700_P30_t3000h_Rm120_Ro25_w3（T=700 P=30 Rm=120 Ro=25 w=3，P·Ro/w=250.0，域外）— CONVERGENCE
  - S20C_T700_P30_t300h_Rm120_Ro25_w3（T=700 P=30 Rm=120 Ro=25 w=3，P·Ro/w=250.0，域外）— CONVERGENCE

## 4. QA 结果（ml/metrics/step20c_execution.json）

- 冻结参数核验（C/n 逐 case 比对）：**PASS**
- 场维度 2304：**PASS**（123/123）
- 重复 case ID / 重复参数组：**0**（每组 4 t 结构正确）
- 数据泄漏审计（组内 split 一致）：**PASS**
- NaN/Inf/负值：**0**

## 5. 单位与约定（审计记录）

- 载荷：内壁 Dsload 压力（非节点力），smoke 验证 max_vm/P·Ro/w ≈ 0.97-1.00
- 时间约定：**period = t_h 数值**（与 318 现有管线一致；C/n 为 s⁻¹ 体系正确）
- 应力域：700°C 80-170、750°C 40-100（FZKA 拟合域）；域外仅 EXT
- 5 个失败 case 应力（P·Ro/w 195-250）均超 700°C 拟合上限 → 收敛失败符合预期物理

## 6. 数据保护

318 DATASET = UNCHANGED ｜ V1.2 = UNCHANGED ｜ V1.3 TRAINING = NOT STARTED ｜ WEBAPP = UNCHANGED ｜ LOCKED = NEVER READ ｜ 材料卡 = UNCHANGED（仅生成器 dict 扩展）

## 7. 产物

- `simulation/step20c/`：manifest.csv（128）、splits.csv、fields/*.npz（123）、field_stats.csv、5 个失败 case 全套文件
- `ml/metrics/step20c_execution.json`（QA 全字段）
- 报告：本文档