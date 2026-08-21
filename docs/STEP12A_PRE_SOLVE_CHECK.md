# STEP 12A 预求解检查报告 (PRE-SOLVE CHECK)

日期: 2026-08-20 12:28
状态: **8/8 检查全部通过 — 待批准后开始 Abaqus 求解（本报告生成时未运行任何 Abaqus）**
生成器: `abaqus/scripts/generate_cases_v2.py`（复用 v1 `generate_cases.gen_inp`，仅 monkey-patch 输出目录 + 内存注入插值材料）
数据证据: `simulation/generated_cases_v2/pre_solve_check.json`、`dedup_report.txt`

---

## 1. 生成产物

| 文件 | 内容 |
|---|---|
| `simulation/case_matrix_v2.yaml` | 27 个区块定义（A–I 九组），确定性枚举，无随机 |
| `abaqus/scripts/generate_cases_v2.py` | 生成器 + 去重断言 + 8 项预检查 |
| `simulation/generated_cases_v2/*.inp` | **298 个**（medium 48×16×3，与 v1 同网格） |
| `simulation/generated_cases_v2/manifest_v2.csv` | 298 行 × 21 列（v1 16 列 + sy_source_type/grade/experimental + block） |
| `simulation/generated_cases_v2/pre_solve_check.json` | 8 项检查原始结果 |
| `simulation/generated_cases_v2/dedup_report.txt` | 去重证据 |
| `materials/SS316LN_N014/derived_interpolation_675_725.csv` | 675/725 插值记录（INTERPOLATED/E/NO）— **新文件，现有材料 CSV 零修改** |

## 2. 八项检查结果（全部 PASS）

| # | 检查 | 结果 | 证据 |
|---|---|---|---|
| 1 | INP 数量 | ✅ | INP=298 = manifest 行数 298，无残留文件（生成前清理旧 .inp） |
| 2 | 参数范围 | ✅ | T/T_inner/T_outer ∈ [550,750]，P ∈ [1,30]，Rm ∈ [80,150]，Ro ∈ [15,25]，wall ∈ [2,5]，ΔT ∈ {25,50,75}，蠕变 t ∈ {100,300,1000,3000}；0 违规 |
| 3 | 材料卡 | ✅ | 298/298 含 `*Material, name=SS316LN_N014` + `*Elastic`，E ∈ [119000,171000] MPa；MODEL_B 塑性卡与 σy 有无严格一致；`*Creep` 仅出现在 MODEL_C 且 T ∈ {550,600,650}；P>0 全部含 `*Dsload`；0 违规 |
| 4 | 温度范围 | ✅ | 每个 INP 的 `*Temperature` 节点温度实测 ∈ [550,750]；0 违规 |
| 5 | Air 环境 | ✅ | 298/298 INP 无任何 SODIUM 引用（修正了 `', NA'` 误匹配 `', NAME='` 卡名的检查缺陷）；材料名全为 SS316LN_N014 |
| 6 | σy source 标记 | ✅ | **INTERPOLATED=114**（全部 T∈{675,725}，grade=E，experimental=NO）；**EXPERIMENTAL=106**（全部 T∈{650,700,750}，grade=A，YES）；**DATA_REQUIRED=8**（全部 T∈{550,600}）；0 违规 |
| 7 | sodium 检查（manifest） | ✅ | case 名/区块名无 sodium 特征；0 条 |
| 8 | 旧 222 不变 | ✅ | v1 manifest 数据行=222；v1 各文件 mtime（08-19/08-20 10:50–10:53）全部早于本次生成（12:28）；v2 只写 `generated_cases_v2/` 与新增记录文件 |

## 3. 去重证据（dedup_report.txt 实测）

```
v1 manifest rows:           222（4 个历史内部重复组合，见 §5，未修改）
v1 unique param keys:       218
v2 cases generated:         298
  - v2 internal unique:     298（== 298: True）
  - duplicate vs v1:        0（must be 0: True）
  - total unique key set:   516（= 218 v1 唯一 + 298 v2）
```

- 新 298 内部无重复 ✅
- 新 298 与旧 222 **零参数重复** ✅（主键 = model + 温度组合 + P + Rm + Ro + wall + t）
- 合并唯一主键 516 = 218（v1 唯一）+ 298（v2）✅
- 去重断言在生成器中为硬性检查：任何重复立即中止（开发中已捕获并修正 1 处设计错误，见 §6.2）

## 4. 抽查证据（人工复核 INP 数值）

| case | E (MPa) | σy (MPa) | 蠕变 | 温度 |
|---|---|---|---|---|
| `U_675_P10_Rm100_Ro20_w4` | 156000（插值） | 219.5（插值） | — | 均匀 675 |
| `U_725_P30_Rm100_Ro20_w4` | 130000（插值） | 205.5（插值） | — | 均匀 725 |
| `G_725_650_P10_Rm100_Ro20_w4` | 130000（插值） | 205.5（插值） | — | 梯度 725→650 逐节点 |
| `CR_650_P20_T3000h_Rm100_Ro20_w4` | 171000（EXP） | 227（EXP，v1 同行为） | A=2.35e-25, n=7.57 @650（实验值原样） | 均匀 650，Visco t=3000h |

## 5. v1 遗留发现（记录，不修改）

v1 manifest.csv 222 行中存在 **4 个历史内部重复组合**（LHS 抽样与 benchmark/creep 枚举碰撞）：
- `B001` == `LHS297`（MODEL_B, 650°C, P=5, 基准几何）
- `B007` == `CR_550_P10_T100h`、`B008` == `CR_600_P10_T100h`、`B009` == `CR_650_P10_T100h`

按"旧 222 不变"规则，v1 文件保持原样；此问题在 v2 数据集中以唯一主键去重处理（dataset 构建时按主键合并，v1 重复行仍保留但标注）。建议后续 STEP 单独审计。

## 6. 与设计文档的数字修正（3 处，均已在 STEP12A_CASE_DESIGN.md 同步）

1. **v2 数量 280 → 298**: D2 蠕变区块（T{550,600,650}×P{5,10}×t{100,1000}×3 几何）按 yaml 全展开 = 36 例；原设计稿写 18 为算术笔误。多出的 18 例全部为蠕变几何×时间空洞填充，质量无降级。
2. **总计 502 → 520**: 222 + 298 = 520。
3. **预期 valid ~420 → ~435–440**（D 区块 70 例中预期 66 valid）。
4. **H 区块修正**: 原 `T=650×P=5×{(90,18,3),(110,22,4)}` 与 F1 区块重复 — 被去重断言捕获，改为 `T=750×P{2.5,5}×4 新几何`，仍 8 例。

## 7. 插值材料记录（批准规则 1–6 的落实）

`derived_interpolation_675_725.csv`:
```
675: E=156.0 GPa, sy=219.5 MPa | anchors 650,700 | INTERPOLATED | E | experimental=NO
725: E=130.0 GPa, sy=205.5 MPa | anchors 700,750 | INTERPOLATED | E | experimental=NO
```
- 仅用于 v2 参数化仿真生成，**不进入任何实验验证报告**
- 650/700/750 实验 σy（227/212/199）与 EXP E（171/141/119 GPa）未改动
- 550/600 σy 保持 DATA_REQUIRED，未插值未编造

## 8. 结论与下一步

✅ **全部 8 项预求解检查通过 + 去重证据完整。**
下一步（等待批准）: 分批运行 Abaqus 求解 298 例（`run_batch_v2`，cpus=4，--skip-existing 断点续跑，预计 1–2 天墙钟）→ 后处理 → 合并 520 行 dataset → v2 重划分 → STEP12A_REPORT.md。

---
*本报告生成过程中未调用任何 Abaqus 求解器。*
