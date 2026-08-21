# STEP 12B 最终预求解审计报告

日期: 2026-08-20
状态: **13/13 全部通过 — 批准开始 78 例 Abaqus 求解（本报告只读，未修改任何 case/材料/v1 文件）**
证据: `simulation/generated_cases_v2/final_audit.json`（`abaqus/scripts/check_final_audit.py` 生成）

## 13 项检查结果

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| 1 | v3 78 例全部来自 case_matrix_v3.yaml | ✅ | 78 个 ID 全部存在于 manifest_v2.csv，缺失 0 |
| 2 | v3 内部 78 例唯一 | ✅ | count=78, unique=78 |
| 3 | v3 与 v1 222 例完全无重复 | ✅ | 主键比对 overlap=0 |
| 4 | 最终总 case = 300 | ✅ | v1 行 222 + v3 78 = **300** 数据集行；唯一参数主键 218+78=296（v1 有 4 个历史内部重复组合，按"不修改 v1"规则保留） |
| 5 | ΔT=25/75 为设计有意采样 | ✅ | 梯度 case 的 ΔT 集合 = {25, 50, 75}；25/75 在 STEP12A_CASE_DESIGN.md §1.2 明确列为 v1 空洞（v1 只有 50/100/150/200），§4.2–4.3 设计新增；非映射/单位/脚本错误 |
| 6 | ΔT 温度边界正确 | ✅ | 全部梯度 case 满足 manifest Delta_T == T_inner − T_outer（如 675−600=75、750−725=25），且 T_outer ≥ 550、T_inner ≤ 750；0 违规 |
| 7 | 全部温度 ∈ [550, 750] | ✅ | manifest 与 INP `*Temperature` 段实测端点全部在范围内（含梯度逐层节点温度）；0 违规 |
| 8 | Air only, sodium=0 | ✅ | 78/78 INP 无任何 SODIUM 引用，材料名全部 SS316LN_N014 |
| 9 | 675/725 σy 标记 | ✅ | INTERPOLATED=30（预期 30），全部 grade=E、experimental=NO；0 违规 |
| 10 | 550/600 无伪造 σy | ✅ | 4 例 MODEL_B 全部 DATA_REQUIRED，INP 无 `*Plastic` 卡，missing_sy=True；0 违规 |
| 11 | 700/750 无伪造 Norton | ✅ | `*Creep` 卡仅 18 例且全部 T ∈ {550,600,650}；0 违规 |
| 12 | 18 蠕变参数 = Air Norton 表 | ✅ | 逐例比对 *Creep 行 A/n 与 MAT-05 表（550: 7.75e-32/9.51, 600: 3.56e-30/9.04, 650: 2.35e-25/7.57），0 失配 |
| 13 | v1 未修改 | ✅ | v1 manifest 数据行=222；审计只读，v1 文件时间戳未变 |

## 结论

全部 13 项通过。**按已批准指令，立即开始 78 例 Abaqus 2024 求解（cpus=4、断点续跑、分批）**，完成后后处理合并生成 `data/ai_ready_v3/` 四件套与 `docs/STEP12B_FINAL_REPORT.md`，不训练 AI，不修改质量判据。

---
*本审计为只读操作，未运行 Abaqus 求解器，未修改任何文件。*
