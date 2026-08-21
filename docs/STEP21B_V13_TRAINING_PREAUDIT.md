# STEP21-B V1.3 训练前最终数据 QA 与训练准备报告

日期: 2026-08-21 ｜ 状态: **STEP21-B = PRE-AUDIT COMPLETE**（split 全部解决，正式训练未启动）

## 一、20 个 LEGACY_UNSPLIT 来源审计

- 原因：v1.2 训练仅使用 87 例（37 旧 + 50 G），318 中另有 20 个 MODEL_C 蠕变 case（多为 t=1000h 长时 case 及 t=3000h 案例）不在 v1.2 split 清单中
- 证据：step15_g3_split_audit.json（train/val 列表）中无这些 case；它们来自 v1 早期生成（case_matrix v1）
- 修正：9 个无几何后缀 case 经质心实测确认默认几何 Rm100/Ro20/w4（r∈[81.2,118.3]）；P2p5 解析修正为 2.5

## 二、split 恢复方法

| 方法 | case 数 | 说明 |
|---|---|---|
| HISTORICAL_GROUP_RECOVERY | 17 | group 已存在于既有 split → 按 group 恢复（14 例在 TRAIN、1 例在 VAL、2 例经修正几何后匹配） |
| V1.3_REASSIGNED | 3 | 全新 group（新几何 120/25/3@550、新低压域 P2.5@650 等）→ 按 V1.2 设计类比归属 EXT（外推） |
| V1.3_GROUP_UNIFIED | 8 | V1.2 case 级分层导致的 7 个跨 TRAIN/VAL group → 统一至主体 split（TRAIN） |

V1.2 原始 split 文件未修改；全部处理在 V1.3 新 manifest 层完成。

## 三、最终 TRAIN / VAL / EXT

| split | case 数 | group 数 | 说明 |
|---|---|---|---|
| TRAIN | 157 | 71 | 新旧合并 + 恢复/统一 |
| VAL | 28 | 15 | 仅保留无交叉 group |
| EXT | 45 | 13 | 含新几何/低压域外推 |
| EXCLUDED | 5 | — | EXT 收敛失败（FAILED_CONVERGENCE） |

20 个 LEGACY_UNSPLIT 去向：17 恢复 + 3 重分配（EXT），全部解决。

## 四、group leakage

TRAIN ∩ VAL ∩ EXT = **空（无泄漏）**；组内所有 t 同 split。

## 五、V1.3 输入（冻结，同 STEP20-E）

T, P, t, Rm, Ro, w + 派生特征 log1p(t)、log10(P·Ro/w)、E/A/n 温度查表（全部来自 case 元数据与材料表，无 target 信息）。

## 六、V1.3 7-target 输出（冻结）

Srr, Stt, Szz, Srt, Srz, Stz, CEEQ（每 case 2304×7）；von_mises_true 仅作 QA 参考。

## 七、CEEQ 处理（冻结）

log10(CEEQ)，epsilon=1e-300；逆变换 CEEQ = 10^log10。

## 八、normalization（冻结）

- TRAIN-only：输入特征 + 每场目标 mean/std 标准化（ml/v13/v13_scaler.npz + meta json）
- VAL/EXT 仅用 TRAIN scaler；EXT 禁止参与任何拟合

## 九、POD 策略（冻结）

POD basis = **TRAIN-only**（157 例）；每场独立 POD + Ridge-Poly2（延续 V1.2 架构）。

## 十、POD rank 审计结果（TRAIN-only SVD）

| 场 | rank95 | rank99 | rank999 | ev@50 | 推荐 rank |
|---|---|---|---|---|---|
| Srr | 1 | 1 | 3 | 1.0000 | 3 |
| Stt | 1 | 1 | 3 | 1.0000 | 3 |
| Szz | 1 | 1 | 3 | 1.0000 | 3 |
| Srt | 1 | 1 | 3 | 1.0000 | 3 |
| Srz | 1 | 1 | 2 | 1.0000 | 3 |
| Stz | 1 | 1 | 2 | 1.0000 | 3 |
| CEEQ | 1 | 1 | 1 | 1.0000 | 3 |

物理解释：弹性应力场形状由几何决定、P 线性缩放 → 单模态主导；log10(CEEQ) 场随时间的演化近似自相似 → 低秩。

## 十一、von Mises physics metric（冻结）

训练后由预测六应力重算 von_mises_pred_from_tensor，与 von_mises_true 对比（MAE/RMSE/相对误差/R²，分 TRAIN/VAL/EXT 报告）。

## 十二、EXT 规则（冻结）

EXT（45 例）仅最终外推评估；不参与 normalization/POD/回归拟合/超参选择/early stopping。

## 十三、dry-run

TRAIN 157 / VAL 28 / EXT 45 × 7 target 加载全部 PASS（shape (N,2304)、dtype 一致）。

## 十四、数据完整性

318 = UNCHANGED ｜ V1.2 = UNCHANGED ｜ STEP20-C = UNCHANGED ｜ STEP20-D = UNCHANGED ｜ STEP21-A = UNCHANGED ｜ V1.3 TRAINING = NOT STARTED ｜ LOCKED = UNTOUCHED ｜ WebApp = UNCHANGED

## 十五、是否允许进入 STEP21-C（正式训练）

**YES** —— split 全部解决（20/20）、group 无泄漏、scaler/POD 规则冻结、dry-run PASS、数据层 230 例就绪。