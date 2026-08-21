# STEP 12B 最终报告 — 300 Case 数据集完成

日期: 2026-08-20
状态: **78/78 求解成功 → 后处理完成 → 300 行数据集生成 → 划分完成。未训练 AI。**

## 1. 求解统计

- Abaqus 2024（`C:/SIMULIA/Commands/abaqus.bat`），cpus=4，断点续跑，分批
- **78/78 case COMPLETED**（60 弹性 ≈ 25–27 s/例 + 18 蠕变）；2 例（U_675_P10/P20）因求解早期 license 守护进程崩溃（ABAQUSLM status 28，重启 SSQ FLEXLM 服务修复）失败一次后重跑成功
- 全部真实 Abaqus 求解，无任何人工数据

## 2. 数据质量验证（对结果本身的物理自检）

| 检查 | 结果 |
|---|---|
| 均匀 675/725 vm ≈ 5.01·P | ✅ P5→25.1 / P10→50.1 / P20→100.3 / P30→150.4 MPa（与 222 例标定因子一致） |
| 梯度 case PEEQ | ✅ 全部 = 0（vm ≤ 0.85·σy 设计安全线生效，**零新增网格敏感 case**） |
| 蠕变应变自洽 | ✅ CR_650_P20_T3000h CEEQ≈1e-6 = CR_650_P10_T100h(1.7e-10) × 2^7.57 应力倍率 × 30 时间倍率，量级吻合（与 v1 39 例蠕变同一参数/同一行为） |
| 温度范围 | ✅ 全部 case T ∈ [550, 750] |
| 插值材料 | ✅ U_675/U_725 的 E=156000/130000 MPa、σy=219.5/205.5 MPa 正确进入求解 |

## 3. 合并数据集（300 行）

文件: `data/ai_ready_v3/simulation_dataset_300.csv`（33 列，与 v1 schema 一致）

| 指标 | 数值 |
|---|---|
| 总行数 | **300**（v1 222 原样 + v3 78） |
| v1 行 | 222（零修改/零重算/零删除） |
| v3 新增 | 78（全部真实求解） |
| 质量等级 | A=114（80 v1 + 34 v3）、B=110（70 v1 + 40 v3）、D=49（v1 网格敏感）、E=27（23 v1 + 4 v3 DATA_REQUIRED） |
| **valid_for_AI** | **224**（150 v1 + 74 v3） |
| physics_reference | 76（49 网格敏感 + 27 DATA_REQUIRED） |

v3 分级明细（78 例）: A=34（16 例 650/700/750 实验 σy 均匀 + 18 例蠕变）、B=40（20 梯度 + 20 例 675/725 插值 σy）、E=4（550/600 elastic-only）。
**675/725 插值 σy 全部为 B 级（reference/derived），绝非 A 级实验数据；550/600 无伪造 σy；700/750 无伪造蠕变。**

## 4. train/validation/test 划分

文件: `data/ai_ready_v3/{train,validation,test}.csv`（仅 valid_for_AI=YES 进入划分，v1 同规）

**2026-08-20 STEP 13.5 修复（问题 A: Rm=150 外推纯净性）后最终划分:**

| 集合 | 数量 | 占比 |
|---|---|---|
| train | 104 | 46.4% |
| validation | 46 | 20.5% |
| test | 74 | 33.0% |

（修复前 107/47/70；3 例 Rm150 蠕变/均匀由 train 移入 test、U_725_P10_Rm150 由 validation 移入 test；未人为凑数，详见 `docs/STEP13_LEAKAGE_AUDIT.md` 问题 A）

- **向后兼容验证: v1 的 150 例分类 0 变化**（v1 case 走 v1 原规则，train/validation/test 旧 73/23/54 逐 case 一致）
- 外推梯子: T train≤700→val 725/750→test 全；Rm train≤120→val 130/140→test 150；蠕变 t train≤300→test≥1000；均匀 P train≤20、P≥30 强制 test
- train/test 同键组合 11 个 = 10 蠕变时间外推（短时 train vs 长时 test）+ 1 梯度温度外推（T_in 650/700 vs 750，v1 原样）—— 设计特征，非参数泄漏
- 结构缺口（非泄漏）: validation 无 MODEL_C 样本（蠕变按时间规则仅进 train/test）→ MODEL_C 以 test 时间外推为主评估

## 5. 质量判据（未做任何改动）

沿用 v1 判据逐字执行（A/B/D/E 分级、solver 失败→D、梯度塑性→D/physics_reference、550/600 缺 σy→E/DATA_REQUIRED、700/750 蠕变→DATA_REQUIRED）。
**未因任何数量目标修改判据；valid=224 为自然结果。**

## 6. 产出文件清单

```
data/ai_ready_v3/simulation_dataset_300.csv   (300 行 × 33 列)
data/ai_ready_v3/train.csv                    (107)
data/ai_ready_v3/validation.csv               (47)
data/ai_ready_v3/test.csv                     (70)
simulation/generated_cases_v2/*.odb/.sta      (78 例求解产物)
simulation/generated_cases_v2/results_v3.csv  (78 例后处理指标)
simulation/generated_cases_v2/run_v3.log      (求解日志)
docs/STEP12B_SELECTED_78_CASES.md             (选择明细)
docs/STEP12B_FINAL_PRE_SOLVE_AUDIT.md         (13 项审计)
docs/STEP12B_FINAL_REPORT.md                  (本报告)
```

## 7. 遗留说明

1. v1 的 222 行含 4 个历史内部重复组合（B001==LHS297、B007/B008/B009==CR_*_P10_T100h），按"不修改 v1"规则保留；唯一参数主键 296
2. 蠕变应变量级极小（≤1e-6）是 Norton 参数在 σ≤100 MPa 下率极低的物理结果（n≈7.6–9.5），与 v1 39 例行为一致，非求解异常
3. 675/725 插值 σy（INTERPOLATED/E/NO）仅存在于仿真数据层，未进入任何实验验证文档

## 8. 下一步（待指示）

AI 训练阶段（train 107 / validation 47 / test 70，外推测试集已就绪）。不训练 AI 的约束继续保持。

---
*本报告全部数字来自实际求解与脚本输出；未训练 AI，未修改任何 v1 文件与材料参数。*
