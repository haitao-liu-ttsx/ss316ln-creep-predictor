# STEP 15-G.3 v1.2 训练报告

日期: 2026-08-20
状态: **v1.2 候选训练与内部验证完成 — 未冻结、EXT/LOCKED 未读**
产物: `ml/final/step15_v1_2/`（pod_basis_v12.npz、v12_config.json）、`ml/metrics/step15_g3_*.json/csv`

## 1. 数据合并

- 旧 37 例（t≤300h 多时间层）+ **新 50 例（48×3000h + 2×1000h）** = **87 例、187 snapshots**
- case-level 分层 split（seed 42）：**TRAIN 68 / VAL 19**（VAL 含 **10 例 3000h 新 case**——长时间外推层首次进入 VAL；几何/时间/压力分层保证多样性）
- G.2 QC 全过（50/50）后合并；EXT/LOCKED 全程未读

## 2. POD（TRAIN-only，k 比较）

k=2/3/4/5 累计方差均 1.0；VAL 重构 logMAE：k=2→0.022、k=3→0.0046、k=4→0.0027、k=5→0.0007 → **选 k=3**（方差饱和点，最简）。d 斜率=[89.3, −0.49, 0.07]。

## 3. 模型比较（VAL 41 snapshots，含 10×3000h）

| 候选 | logMAE | coef R² | hs | top5 |
|---|---|---|---|---|
| **poly10（Ridge-Poly2 + stress）** | **0.0607** | 0.999/0.962/0.977 | 1.00 | 0.80 |
| linear10 | 0.1907 | 0.993/0.942/0.965 | 1.00 | 0.79 |
| xgb9 / xgb10 | 0.2523 / 0.3010 | 0.98+ | 1.00 | 0.84 |
| anxgb10（解析时间控制） | 0.3467 | 0.98/0.90/0.98 | 1.00 | 0.79 |
| rf9 / rf10 | 0.4564 / 0.5299 | 0.95+ | 1.00 | 0.65–0.72 |

**VAL 最佳 = poly10（Ridge-Poly2 + log10(P·Ro/w)）**——数据覆盖充分后简单模型反超树模型（与 v1.1 的 XGB 时代相反）。

## 4. 时间/几何分组（poly10 vs v1.1 结构控制）

| 层 | poly10 logMAE | anxgb 控制 | 结论 |
|---|---|---|---|
| t≤300h | 0.035–0.073 | 0.22–0.66 | poly10 优 |
| **t=3000h（10 例外推层）** | **0.0558（logR²=0.9996）** | 0.410 | **新数据 + Poly2 温和外推彻底修复 3000h**（v1.1 EXT 时为 1.41） |
| 基准几何 | 0.041 | 0.142 | poly10 优 |
| 90/18/3 | 0.047 | 0.760 | poly10 优 |
| 80/15/2 | 0.130 | 0.501 | poly10 优 |

## 5. Physics：0 violations；hotspot 全部 1.00

## 6. 数据充分性（如实回答）

1. **新增 50 例是否改善 geometry coverage**：**是**——非基准几何从 5→10 种覆盖（VAL 已验证 90/18/3、80/15/2 等）
2. **48×3000h 是否改善 long-time learning**：**是（决定性）**——VAL 3000h logR²=0.9996
3. **2×1000h 是否足够**：**不足（如实记录）**——1000h 桥接层仍稀疏（历史 14 + 新 2）；当前 VAL 无 1000h 独立层，1000h 由插值覆盖
4. **P≥25 的 12 例是否改善高压力域**：**是**（VAL 含 P30 例，logR²≥0.99）
5. **P·Ro/w=250 是否仍是上限**：**是**（>250 未覆盖，记录为边界）
6. **是否仍需下一批 cases**：**是（若需 1000h 精确覆盖与 >250 应力域）**——建议下一批补 1000h×非基准（~10–15 例）+ 高应力尺度（P 40×薄壁）

## 7. 结论

v1.2 候选（poly10）在含 3000h 外推层的 VAL 上 logR²≈0.999、全时间/几何层 hotspot 1.00——**数据扩充 + 简单模型达到当前域内近完美场预测**。v1.2 未冻结；最终外部判定需冻结后 EXT（G.4）。

## 8. 状态声明

STEP 15-G.3 COMPLETE ｜ V1.2 TRAINING = **COMPLETE** ｜ V1.2 PRODUCTION FREEZE = **NO** ｜ EXT TARGET READ = **NO** ｜ LOCKED TEST READ = **NO** ｜ 318 DATASET MODIFIED = **NO** ｜ V1.1 MODIFIED = **NO** ｜ NEW CASES USED = **50/50** ｜ TRAIN CASES = 68 ｜ VAL CASES = 19 ｜ POD FIT = **TRAIN ONLY** ｜ MODEL SELECTION = **TRAIN/VAL ONLY** ｜ 1000h COVERAGE = **SPARSE** ｜ 3000h COVERAGE = **IMPROVED** ｜ P·Ro/w MAX = **250**

---
*v1.2 候选完成内部验证；EXT 最终测试与冻结待 G.4 批准。*
