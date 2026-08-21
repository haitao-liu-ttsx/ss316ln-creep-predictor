# STEP 12B 精选 78 例新增 Case（v1 222 + v3 78 = 300）

日期: 2026-08-20
状态: **选择完成 — 未运行任何 Abaqus，未训练 AI**
选择来源: v2 候选 298 例（`simulation/generated_cases_v2/manifest_v2.csv`），确定性筛选，非随机
机器可读清单: `simulation/case_matrix_v3.yaml`（19 组 S1–S19）
验证脚本: `abaqus/scripts/select_v3_cases.py`（78 例存在性/唯一性/v1 去重断言，已通过）

---

## 1. 选择原则（最大化参数空间覆盖，优先填补 v1 空洞）

1. **675/725°C 插值 σy 层（v1 完全空洞）** — 均匀×关键压力、梯度×新 ΔT、×新几何、×薄壁（30 例）
2. **新 ΔT 值 25/75（v1 只有 50/100/150/200）** — 既有温度与新温度梯度对（17 例）
3. **新几何 Rm 90/110/130/140、Ro 18/22（v1 只有 80/100/120/150、15/20/25）** — 均匀与蠕变（30 例）
4. **蠕变空洞（v1 39 例全在基准几何 100/20/4、t=1/10/100/1000）** — 新时间 300/3000h、新几何（18 例）
5. **低压 P=1/3/6/8（v1 最低 2.5）**（6 例）
6. 关键压力 P=5/10/20/30 在新温度层上采样；P=40 不加（v1 已有 20 例且 σy 裕度不足，见 STEP12A 设计 §5 排除项 6）
7. 质量优先: 梯度工况全部满足 vm ≤ 0.85·σy 安全线（222 例实测标定），不纳入新的梯度塑性网格敏感工况；550/600 elastic-only 仅 4 例作新几何覆盖（正确标记 DATA_REQUIRED/physics_reference）

## 2. 验证结果（select_v3_cases.py 断言）

```
78 例全部存在于 manifest_v2        ✅
78 例内部唯一                       ✅
与 v1 222 例零参数重复              ✅
最终唯一总数 = 222 + 78 = 300      ✅
```

## 3. 精选 78 例明细

列说明: T=均匀温度或梯度内壁温度; ΔT=梯度温差（0=均匀）; creep=是否 MODEL_C; σy source=INTERPOLATED(E级)/EXPERIMENTAL(A级)/DATA_REQUIRED/NA(蠕变不用σy); 质量=预计分级（求解后以实际收敛状态复核）。

| # | case ID | T | ΔT | P | Rm | Ro | wall | creep | σy source | 类型 | 与v1重复 | 预计质量 | 组 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | U_675_P5_Rm100_Ro20_w4 | 675 | 0 | 5 | 100 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S1 |
| 2 | U_675_P10_Rm100_Ro20_w4 | 675 | 0 | 10 | 100 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S1 |
| 3 | U_675_P20_Rm100_Ro20_w4 | 675 | 0 | 20 | 100 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S1 |
| 4 | U_675_P30_Rm100_Ro20_w4 | 675 | 0 | 30 | 100 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S1 |
| 5 | U_725_P5_Rm100_Ro20_w4 | 725 | 0 | 5 | 100 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S1 |
| 6 | U_725_P10_Rm100_Ro20_w4 | 725 | 0 | 10 | 100 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S1 |
| 7 | U_725_P20_Rm100_Ro20_w4 | 725 | 0 | 20 | 100 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S1 |
| 8 | U_725_P30_Rm100_Ro20_w4 | 725 | 0 | 30 | 100 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S1 |
| 9 | U_675_P10_Rm80_Ro15_w2 | 675 | 0 | 10 | 80 | 15 | 2 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S2 |
| 10 | U_725_P10_Rm80_Ro15_w2 | 725 | 0 | 10 | 80 | 15 | 2 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S2 |
| 11 | G_675_600_P10_Rm100_Ro20_w4 | 675 | 75 | 10 | 100 | 20 | 4 | NO | INTERPOLATED | gradient | NO | valid_for_AI | S3 |
| 12 | G_725_650_P10_Rm100_Ro20_w4 | 725 | 75 | 10 | 100 | 20 | 4 | NO | INTERPOLATED | gradient | NO | valid_for_AI | S3 |
| 13 | G_675_650_P5_Rm100_Ro20_w4 | 675 | 25 | 5 | 100 | 20 | 4 | NO | INTERPOLATED | gradient | NO | valid_for_AI | S4 |
| 14 | G_725_675_P5_Rm100_Ro20_w4 | 725 | 50 | 5 | 100 | 20 | 4 | NO | INTERPOLATED | gradient | NO | valid_for_AI | S4 |
| 15 | G_725_700_P10_Rm100_Ro20_w4 | 725 | 25 | 10 | 100 | 20 | 4 | NO | INTERPOLATED | gradient | NO | valid_for_AI | S5 |
| 16 | G_675_625_P5_Rm80_Ro15_w2 | 675 | 50 | 5 | 80 | 15 | 2 | NO | INTERPOLATED | gradient | NO | valid_for_AI | S6 |
| 17 | G_650_625_P5_Rm100_Ro20_w4 | 650 | 25 | 5 | 100 | 20 | 4 | NO | EXPERIMENTAL | gradient | NO | valid_for_AI | S7 |
| 18 | G_700_675_P10_Rm100_Ro20_w4 | 700 | 25 | 10 | 100 | 20 | 4 | NO | EXPERIMENTAL | gradient | NO | valid_for_AI | S7 |
| 19 | G_650_575_P5_Rm100_Ro20_w4 | 650 | 75 | 5 | 100 | 20 | 4 | NO | EXPERIMENTAL | gradient | NO | valid_for_AI | S8 |
| 20 | G_700_625_P5_Rm100_Ro20_w4 | 700 | 75 | 5 | 100 | 20 | 4 | NO | EXPERIMENTAL | gradient | NO | valid_for_AI | S8 |
| 21 | G_750_725_P5_Rm100_Ro20_w4 | 750 | 25 | 5 | 100 | 20 | 4 | NO | EXPERIMENTAL | gradient | NO | valid_for_AI | S9 |
| 22 | G_750_725_P10_Rm100_Ro20_w4 | 750 | 25 | 10 | 100 | 20 | 4 | NO | EXPERIMENTAL | gradient | NO | valid_for_AI | S9 |
| 23 | U_650_P5_Rm90_Ro18_w3 | 650 | 0 | 5 | 90 | 18 | 3 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S10 |
| 24 | U_650_P10_Rm110_Ro22_w4 | 650 | 0 | 10 | 110 | 22 | 4 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S10 |
| 25 | U_650_P15_Rm130_Ro22_w3 | 650 | 0 | 15 | 130 | 22 | 3 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S10 |
| 26 | U_650_P10_Rm110_Ro20_w3 | 650 | 0 | 10 | 110 | 20 | 3 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S10 |
| 27 | U_700_P5_Rm140_Ro18_w4 | 700 | 0 | 5 | 140 | 18 | 4 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S10 |
| 28 | U_700_P10_Rm90_Ro18_w3 | 700 | 0 | 10 | 90 | 18 | 3 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S10 |
| 29 | U_700_P15_Rm110_Ro22_w4 | 700 | 0 | 15 | 110 | 22 | 4 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S10 |
| 30 | U_700_P15_Rm130_Ro22_w3 | 700 | 0 | 15 | 130 | 22 | 3 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S10 |
| 31 | U_675_P10_Rm110_Ro22_w4 | 675 | 0 | 10 | 110 | 22 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S11 |
| 32 | U_675_P15_Rm90_Ro18_w3 | 675 | 0 | 15 | 90 | 18 | 3 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S11 |
| 33 | U_725_P10_Rm130_Ro22_w3 | 725 | 0 | 10 | 130 | 22 | 3 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S11 |
| 34 | U_725_P5_Rm140_Ro18_w4 | 725 | 0 | 5 | 140 | 18 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S11 |
| 35 | U_750_P5_Rm90_Ro18_w3 | 750 | 0 | 5 | 90 | 18 | 3 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S12 |
| 36 | U_750_P2p5_Rm110_Ro22_w4 | 750 | 0 | 2.5 | 110 | 22 | 4 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S12 |
| 37 | U_750_P5_Rm130_Ro22_w3 | 750 | 0 | 5 | 130 | 22 | 3 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S12 |
| 38 | U_750_P2p5_Rm140_Ro18_w4 | 750 | 0 | 2.5 | 140 | 18 | 4 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S12 |
| 39 | U_550_P5_Rm90_Ro20_w4 | 550 | 0 | 5 | 90 | 20 | 4 | NO | DATA_REQUIRED | uniform | NO | physics_reference | S13 |
| 40 | U_550_P5_Rm130_Ro20_w4 | 550 | 0 | 5 | 130 | 20 | 4 | NO | DATA_REQUIRED | uniform | NO | physics_reference | S13 |
| 41 | U_600_P5_Rm110_Ro20_w4 | 600 | 0 | 5 | 110 | 20 | 4 | NO | DATA_REQUIRED | uniform | NO | physics_reference | S13 |
| 42 | U_600_P5_Rm140_Ro20_w4 | 600 | 0 | 5 | 140 | 20 | 4 | NO | DATA_REQUIRED | uniform | NO | physics_reference | S13 |
| 43 | CR_550_P2p5_T300h_Rm100_Ro20_w4 | 550 | 0 | 2.5 | 100 | 20 | 4 | YES | NA | creep | NO | valid_for_AI | S14 |
| 44 | CR_550_P20_T3000h_Rm100_Ro20_w4 | 550 | 0 | 20 | 100 | 20 | 4 | YES | NA | creep | NO | valid_for_AI | S14 |
| 45 | CR_600_P2p5_T300h_Rm100_Ro20_w4 | 600 | 0 | 2.5 | 100 | 20 | 4 | YES | NA | creep | NO | valid_for_AI | S14 |
| 46 | CR_600_P20_T3000h_Rm100_Ro20_w4 | 600 | 0 | 20 | 100 | 20 | 4 | YES | NA | creep | NO | valid_for_AI | S14 |
| 47 | CR_650_P15_T300h_Rm100_Ro20_w4 | 650 | 0 | 15 | 100 | 20 | 4 | YES | NA | creep | NO | valid_for_AI | S14 |
| 48 | CR_650_P20_T3000h_Rm100_Ro20_w4 | 650 | 0 | 20 | 100 | 20 | 4 | YES | NA | creep | NO | valid_for_AI | S14 |
| 49 | CR_650_P2p5_T3000h_Rm100_Ro20_w4 | 650 | 0 | 2.5 | 100 | 20 | 4 | YES | NA | creep | NO | valid_for_AI | S14 |
| 50 | CR_600_P15_T300h_Rm100_Ro20_w4 | 600 | 0 | 15 | 100 | 20 | 4 | YES | NA | creep | NO | valid_for_AI | S14 |
| 51 | CR_550_P5_T100h_Rm80_Ro15_w2 | 550 | 0 | 5 | 80 | 15 | 2 | YES | NA | creep | NO | valid_for_AI | S15 |
| 52 | CR_550_P10_T1000h_Rm120_Ro25_w3 | 550 | 0 | 10 | 120 | 25 | 3 | YES | NA | creep | NO | valid_for_AI | S15 |
| 53 | CR_600_P5_T100h_Rm150_Ro20_w4 | 600 | 0 | 5 | 150 | 20 | 4 | YES | NA | creep | NO | valid_for_AI | S15 |
| 54 | CR_600_P10_T1000h_Rm80_Ro15_w2 | 600 | 0 | 10 | 80 | 15 | 2 | YES | NA | creep | NO | valid_for_AI | S15 |
| 55 | CR_650_P5_T100h_Rm150_Ro20_w4 | 650 | 0 | 5 | 150 | 20 | 4 | YES | NA | creep | NO | valid_for_AI | S15 |
| 56 | CR_650_P10_T1000h_Rm120_Ro25_w3 | 650 | 0 | 10 | 120 | 25 | 3 | YES | NA | creep | NO | valid_for_AI | S15 |
| 57 | CR_550_P5_T300h_Rm90_Ro18_w3 | 550 | 0 | 5 | 90 | 18 | 3 | YES | NA | creep | NO | valid_for_AI | S15 |
| 58 | CR_550_P10_T1000h_Rm110_Ro22_w4 | 550 | 0 | 10 | 110 | 22 | 4 | YES | NA | creep | NO | valid_for_AI | S15 |
| 59 | CR_650_P5_T300h_Rm90_Ro18_w3 | 650 | 0 | 5 | 90 | 18 | 3 | YES | NA | creep | NO | valid_for_AI | S15 |
| 60 | CR_650_P10_T1000h_Rm110_Ro22_w4 | 650 | 0 | 10 | 110 | 22 | 4 | YES | NA | creep | NO | valid_for_AI | S15 |
| 61 | U_650_P1_Rm100_Ro20_w4 | 650 | 0 | 1 | 100 | 20 | 4 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S16 |
| 62 | U_650_P3_Rm100_Ro20_w4 | 650 | 0 | 3 | 100 | 20 | 4 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S16 |
| 63 | U_700_P3_Rm100_Ro20_w4 | 700 | 0 | 3 | 100 | 20 | 4 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S16 |
| 64 | U_700_P6_Rm100_Ro20_w4 | 700 | 0 | 6 | 100 | 20 | 4 | NO | EXPERIMENTAL | uniform | NO | valid_for_AI | S16 |
| 65 | U_675_P6_Rm100_Ro20_w4 | 675 | 0 | 6 | 100 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S16 |
| 66 | U_725_P8_Rm100_Ro20_w4 | 725 | 0 | 8 | 100 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S16 |
| 67 | G_750_675_P5_Rm100_Ro20_w4 | 750 | 75 | 5 | 100 | 20 | 4 | NO | EXPERIMENTAL | gradient | NO | valid_for_AI | S17 |
| 68 | G_750_675_P5_Rm150_Ro20_w4 | 750 | 75 | 5 | 150 | 20 | 4 | NO | EXPERIMENTAL | gradient | NO | valid_for_AI | S17 |
| 69 | U_675_P25_Rm100_Ro20_w4 | 675 | 0 | 25 | 100 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S18 |
| 70 | U_725_P25_Rm100_Ro20_w4 | 725 | 0 | 25 | 100 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S18 |
| 71 | G_675_600_P5_Rm80_Ro15_w2 | 675 | 75 | 5 | 80 | 15 | 2 | NO | INTERPOLATED | gradient | NO | valid_for_AI | S18 |
| 72 | G_725_650_P5_Rm120_Ro25_w3 | 725 | 75 | 5 | 120 | 25 | 3 | NO | INTERPOLATED | gradient | NO | valid_for_AI | S18 |
| 73 | G_650_575_P2p5_Rm80_Ro15_w2 | 650 | 75 | 2.5 | 80 | 15 | 2 | NO | EXPERIMENTAL | gradient | NO | valid_for_AI | S18 |
| 74 | G_700_625_P2p5_Rm120_Ro25_w3 | 700 | 75 | 2.5 | 120 | 25 | 3 | NO | EXPERIMENTAL | gradient | NO | valid_for_AI | S18 |
| 75 | U_675_P5_Rm150_Ro20_w4 | 675 | 0 | 5 | 150 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S18 |
| 76 | U_725_P10_Rm150_Ro20_w4 | 725 | 0 | 10 | 150 | 20 | 4 | NO | INTERPOLATED | uniform | NO | valid_for_AI | S18 |
| 77 | G_725_675_P10_Rm120_Ro25_w3 | 725 | 50 | 10 | 120 | 25 | 3 | NO | INTERPOLATED | gradient | NO | valid_for_AI | S18 |
| 78 | G_675_650_P10_Rm80_Ro15_w2 | 675 | 25 | 10 | 80 | 15 | 2 | NO | INTERPOLATED | gradient | NO | valid_for_AI | S19 |

## 4. 各组选择理由

| 组 | 数量 | 理由（填补的 v1 空洞） |
|---|---|---|
| S1 | 8 | 675/725°C 均匀 × 关键压力 P5/10/20/30 — 插值 σy 温度层（v1 完全无 675/725），关键压力梯度采样 |
| S2 | 2 | 675/725 × 薄壁 (80,15,2) — 插值 σy × 高 Ro/wall 应力放大几何 |
| S3 | 2 | 梯度 675-600 / 725-650 dT=75 — 插值 σy × 新 ΔT=75 |
| S4 | 2 | 梯度 675-650 / 725-675 dT=25/50 — 插值 σy × 新 ΔT 值 |
| S5 | 1 | 梯度 725-700 dT=25 — 插值 σy × 新 ΔT=25 高温梯度对 |
| S6 | 1 | 梯度 675-625 dT=50 × 薄壁 — 插值 σy × 薄壁 × 新 ΔT |
| S7 | 2 | 梯度 650-625 / 700-675 dT=25 — 既有温度 × 新 ΔT=25 |
| S8 | 2 | 梯度 650-575 / 700-625 dT=75 — 既有温度 × 新 ΔT=75（T_outer=575/625 新值） |
| S9 | 2 | 梯度 750-725 dT=25 × P5/10 — 750 内壁 × 新 ΔT=25 |
| S10 | 8 | 新几何 Rm90/110/130/140 + Ro18/22 × 650/700 × P5-15 — 全新几何参数空间 |
| S11 | 4 | 675/725 × 新几何 — 插值 σy × 新几何双重独有 |
| S12 | 4 | 750 × 新几何 — 实验 σy × 新几何（v1 的 750 全在旧几何） |
| S13 | 4 | 550/600 × 新 Rm — elastic-only 新几何覆盖（DATA_REQUIRED，σy 不编造，physics_reference） |
| S14 | 8 | 蠕变 t=300/3000h 新时间轴（v1 蠕变仅 t=1/10/100/1000） |
| S15 | 10 | 蠕变 × 新几何（v1 蠕变全基准几何）— 薄壁/中几何/Rm150，t=100/300/1000h |
| S16 | 6 | 低压 P=1/3/6/8 × 650-725 — 低压力分辨率（v1 最低 2.5） |
| S17 | 2 | 新梯度对 750-675 dT=75 — 新 (Ti,To) 对 × 实验 σy |
| S18 | 8 | 深度补充: P25×插值温度、薄壁 dT=75 梯度、Rm150 外推区均匀 |
| S19 | 1 | 薄壁中温梯度 675-650 dT=25 × P10 — 插值 σy × 薄壁 × 新 ΔT |

注: 组号与 `case_matrix_v3.yaml` 的区块名一一对应。

## 5. 质量标签规则（求解后复核）

- 74 例预计 valid_for_AI（梯度工况全部在设计安全线 vm ≤ 0.85·σy 内，基于 222 例实测标定；见 STEP12A_CASE_DESIGN §0）
- 4 例（S13）预计 physics_reference（550/600 DATA_REQUIRED elastic-only，正确标注，不因凑数而强行 valid）
- 蠕变 18 例预计 valid（应变预检 <1%，t=3000h 最严 650°C/P20 ≈ 0.35%）
- 若个别 case 求解后出现网格敏感/收敛异常 → 如实降级 physics_reference，不伪造标签

## 6. 统计汇总（最终汇报数字）

| 指标 | 数值 |
|---|---|
| v1 数量 | 222（零修改/零重算） |
| v2 候选数量 | 298 |
| 最终选择数量 | 78 |
| **最终总数量** | **300** |
| 温度覆盖 (T_uniform 或 T_inner) | 550:8 / 600:7 / 650:16 / 675:15 / 700:9 / 725:15 / 750:8 |
| ΔT 覆盖 | 0:58 / 25:7 / 50:3 / 75:10（v1 已有 50/100/150/200） |
| 压力覆盖 | 1:1 / 2.5:7 / 3:2 / 5:28 / 6:2 / 8:1 / 10:22 / 15:6 / 20:5 / 25:2 / 30:2（P40 不加: v1 已有 20 例 + σy 裕度不足） |
| 几何覆盖 | 13 种组合，含新值 Rm{90,110,130,140} 全部 + Ro{18,22} + 旧值 80/100/120/150、15/20/25 |
| 蠕变数量 | 18（550/600/650，t=300/1000/3000h，5 种新几何） |
| 675/725 插值 σy 数量 | 30（全部 INTERPOLATED / grade E / experimental=NO） |
| 与 v1 重复数量 | **0**（脚本断言） |
| 预计最终 valid_for_AI | 150 + ~72–74 ≈ **222–224**（含蠕变收敛风险 1–2 例容差；S13 的 4 例为 physics_reference） |

---
*本文件生成过程未调用 Abaqus，未训练 AI。*
