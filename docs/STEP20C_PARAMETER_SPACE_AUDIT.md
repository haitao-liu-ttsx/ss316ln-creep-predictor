# STEP 20-C PRE-AUDIT — 参数空间审计（READ-ONLY）

日期: 2026-08-20 | 状态: AUDIT_COMPLETE（未运行任何生产 case、未修改任何文件）

---

## A. 当前架构（实际代码溯源）

```
simulation/case_matrix.yaml (v1, 222)  +  case_matrix_v2.yaml (v2, 298, blocks A-I)  +  case_matrix_v3.yaml (v3, 78)
        ↓ 块级参数设计（每块 = T/P/t/几何列表）
abaqus/scripts/generate_cases.py      # v1 生成器（含 random import → 早期部分 LHS/随机）
abaqus/scripts/generate_cases_v2.py   # v2/v3 生成器：块内 for T × for P × for t × for geom 笛卡尔循环（显式 "NO random LHS"）
        ↓ gen_inp()（build_geometry.py MATERIALS 库 + build_thermal.py 热物性 + CREEP dict）
simulation/generated_cases{,_v2,_v3,...}/ *.inp
        ↓ abaqus job（run_batch*.py）
*.odb
        ↓ postprocess（ml/ STEP13 管线）
data/ai_ready_v4/simulation_dataset_318.csv   # 318 行 × 38 列
```

- **PARAMETER GENERATOR** = `simulation/case_matrix*.yaml`（块式人工设计）
- **CASE GENERATOR** = `abaqus/scripts/generate_cases.py` + `generate_cases_v2.py`
- **MATERIAL GENERATOR** = `build_geometry.py`（MATERIALS: E/sy 按 T）+ `generate_cases.py` 的 `CREEP = {550:..., 600:..., 650:...}`（A/n 按 T）
- **DATASET GENERATOR** = ml/ STEP13 提取管线（ODB → 318 csv）

## B. 当前数据集（318）

- PATH = `data/ai_ready_v4/simulation_dataset_318.csv`，ROWS = **318**，COLUMNS = 38
- model_type: MODEL_B(弹塑性/热力) 261 + MODEL_C(蠕变) 57
- valid_for_AI: YES 242 / NO 76；quality_grade: A 132 / B 110 / D 49 / E 27
- **A_creep/n_creep 仅 57 行非空**（蠕变参数只对应 MODEL_C）；max_creep_rate 全空

## C-D. 参数空间

| 参数 | 取值（dataset 实际） | 数 | min | max | 单位 | 来源 |
|---|---|---|---|---|---|---|
| T | {550, 600, 650, 675, 700, 725, 750} | 7 | 550 | 750 | °C | 现有模型 |
| P | 27 个离散值（1–40，含 2.5 步进） | 27 | 0 | 40 | MPa | 现有模型 |
| t | {0, 1, 10, 100, 300, 1000, 3000} | 7 | 0 | 3000 | h | 现有模型 |
| Rm | {80..150} 8 值 | 8 | 80 | 150 | mm | 现有模型 |
| Ro | {15, 18, 20, 22, 25} | 5 | 15 | 25 | mm | 现有模型 |
| w | {2, 3, 4, 5} | 4 | 2 | 5 | mm | 现有模型 |
| ΔT（梯度行） | ±25/50/75/200 | — | -200 | 200 | °C | v2 梯度块 |

派生参数：R_inner=Ro−w、应力尺度 P·Ro/w、E(T)、σy(T)、C(T)、n(T)
固定参数：N=0.14、AIR、3072 节点/2304 C3D8R mesh、SYM BC、内壁 Dsload、自动增量

## E. 温度覆盖（重点）

| T | 总行数 | **蠕变行（MODEL_C）** | P 范围 |
|---|---|---|---|
| 550 | 35 | **19** | 2.5–20 |
| 600 | 41 | **18** | 2.5–20 |
| 650 | 81 | **20** | 2.5–20 |
| 675 | 15 | **0** | — |
| 700 | 49 | **0** ← 全部弹塑性/热力 t=0 | — |
| 725 | 15 | **0** | — |
| 750 | 82 | **0** ← 全部弹塑性/热力 t=0 | — |

**700/750°C 当前没有任何蠕变数据。** 318 中 700/750 行均使用 Pan 实测 E/σy（t=0 弹塑性基准）——**未使用 STEP20-A 新参数（因为从未生成蠕变 case）**。

## F. 材料覆盖

- E(T)/σy(T)：550/600（RCC-MR 公式 D 级）、650/700/750（Pan 实测 A 级）、675/725（插值 E 级）——**全部 7 温度可用**
- C(T)/n(T)：**只有 550/600/650**（GaneshKumar）→ **MATERIAL GENERATOR GAP**：`CREEP` dict 缺 700/750 行；`generate_cases_v2` 的 "creep T forbidden" 检查阻塞 700/750
- STEP20-A/B 已冻结并验证的 700/750 参数**尚未接入生成器**

## G. 数据质量

- 重复组合：0（生成器强制 dedup）
- 缺失：A_creep/n_creep 261 行空（MODEL_B 正常）；max_creep_rate 318 全空
- **converged=NO 76 行（全 MODEL_B t=0，750°C 占 34）**——已标 valid_for_AI=NO，未混入训练 ✓
- 失败 case 未混入（质量分级体系工作正常）

## H. 采样策略

**情况 D（多阶段追加）+ 块内笛卡尔**：
- v1（222）：早期块设计 + 部分 LHS/随机（generate_cases.py import random；LHS 177 行仅设计、无 ODB）
- v2（298）：块 A-I 确定性枚举（"NO random LHS"，块内 for 循环笛卡尔）
- v3（78，STEP12B）+ STEP14A/15G 追加 → 318
- **非全笛卡尔积**：是"人工块设计 × 块内笛卡尔 × 多阶段"的混合

## I. 理论组合与覆盖

- v1.2 蠕变域（3T）理论组合：3 × 5(P) × 6(t) × 160(几何) = **14,400**；实际 57 → **覆盖率 0.4%**
- 加入 700/750（5T）：**24,000** 理论
- 结论：**参数空间本身巨大，瓶颈是采样稀疏 + 高温蠕变零覆盖**，而非"维度太少"

## J. 推荐 STEP20-C 扩充（仅提案，未执行）

| 块 | T | P | t(h) | 几何 | 例数 |
|---|---|---|---|---|---|
| 700°C creep | 700 | {5,10,15,20} | {100,300,1000,3000} | 4 种（100/20/4, 80/15/2, 120/25/3, 150/20/4） | 64 |
| 750°C creep | 750 | 同上 | 同上 | 同上 | 64 |
| （可选）1000h 桥接 | 550/600/650 | {10,20} | {1000} | 非基准 2 种 | ~10 |

- **共 ~128 新增蠕变 cases** → 5-T 域（TRAIN/VAL 分层 + EXT 预留）
- 前置修改（STEP20-C 执行期）：`CREEP` dict += 700/750（冻结值）；case_matrix 新块；放宽 "creep T forbidden" 检查；**不触碰 v1.2 / 318 / 材料卡**
- 重要判断：新增 700/750 蠕变 case 是**提高信息量的必要扩充**（目前高温蠕变信息量 = 0），非机械增数

## 状态

STEP20-C PRE-AUDIT = COMPLETE ｜ 未运行生产 case ｜ 318 UNCHANGED ｜ V1.2 UNCHANGED ｜ V1.3 NOT STARTED ｜ WEBAPP UNCHANGED ｜ LOCKED NEVER READ ｜ 材料卡 UNCHANGED
