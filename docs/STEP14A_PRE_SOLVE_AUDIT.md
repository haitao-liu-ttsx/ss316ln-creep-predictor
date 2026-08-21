# STEP 14-A PRE-SOLVE DESIGN AUDIT

日期: 2026-08-20
状态: **20/20 PASSED — Abaqus 未执行**
证据: `ml/metrics/step14a_case_audit.json`（`ml/check_14a.py`）、`ml/metrics/step14a_case_design.csv`

## 1. 27 case 设计（VAL 18 + TEST 9）

**Validation 18 例**（时间层 500/750 h，基准几何 100/20/4）：
T{550,600,650} × P{5,10,20} × t{500,750} — 每 T×P 组合同时含 500 与 750（时间层×T/P 无混淆）

**Test 9 例**（t=3000 h，非基准几何轮换）：

| T | P=5 | P=10 | P=20 |
|---|---|---|---|
| 550 | (80,15,2) | (120,25,3) | (150,20,4) |
| 600 | (120,25,3) | (150,20,4) | (80,15,2) |
| 650 | (150,20,4) | (80,15,2) | (120,25,3) |

ID 格式：`CEEQ14A_T<T>_P<P>_t<500|750|3000>h_Rm<R>_Ro<O>_w<W>`（参数可直接从 ID 读出）

## 2. 审计项结果（20/20 PASS）

| # | 检查项 | 结果 |
|---|---|---|
| 1 | 27/27 参数完整 | ✅ n=27 |
| 2 | T 覆盖 550/600/650 | ✅ |
| 3 | P 覆盖 5/10/20 | ✅ |
| 4 | validation 时间 500/750 h | ✅（t=1000 与 locked test 冲突，按 PRE_AUDIT §5 调整为 750；仍在 500–1000h 区间） |
| 5 | test 时间 3000 h | ✅ |
| 6 | validation=18 | ✅ |
| 7 | test=9 | ✅ |
| 8 | 与历史全部 case 零重复 | ✅（318 已求解 + v2 候选 106 个 MODEL_C 主键全比，0 冲突；t=500/750 历史 0 例） |
| 9 | 与 locked test 零冲突 | ✅（t=1000 14 例与 t=3000 4 例全部避开） |
| 10 | 不修改 318 dataset | ✅（本审计只写 ml/metrics/ + 临时 INP 目录） |
| 11 | 不修改 STEP13 split | ✅ |
| 12 | 几何覆盖检查 | ✅（VAL 基准 + TEST 三种非基准；全部满足 Rm>2Ro、Ro>w） |
| 13 | 时间层 confounding | ✅（VAL 每 T×P 同时含 500/750） |
| 14 | T/P 分布检查 | ✅（VAL 与 TEST 的 T/P 集合一致） |
| 15 | CEEQ target 存在 | ✅（max_creep_strain） |
| 16 | CEEQ 零值策略 | ✅（train 37 例全非零；t≥1h Norton 率>0；沿用 STEP13 log10 非零域、无 epsilon） |
| 17 | log10 处理与 STEP13 一致 | ✅ |
| 18 | 材料参数合法 | ✅（Norton 550/600/650 全套；E 沿用 RCCMR/EXP；σy 对 MODEL_C 不适用） |
| 19 | Abaqus input 可生成 | ✅ 27/27 临时目录生成（含 *Creep, law=STRAIN / *Visco / *Temperature 卡），已清理 |
| 20 | case ID 唯一 / 不运行 Abaqus | ✅ 27/27 唯一；无求解调用 |

## 3. 结论

**STEP 14-A PRE-SOLVE AUDIT PASSED. Abaqus has NOT been executed.**

等待人工批准后执行：生成 27 INP（正式目录 `simulation/generated_cases_step14a_ceeq/`）→ INP 完整性检查 → 求解 → 质量审计 → CEEQ 专用数据集/训练/验证/锁定。
