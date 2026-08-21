# STEP 13 最终报告（Final Report）

日期: 2026-08-20
范围: STEP 13.1–13.10 论文级阶段成果整合
配套: `STEP13_MASTER_RESULTS.md`（总表）、`STEP13_REPRODUCIBILITY_AUDIT.md`（可复现审计）、`ml/final/`（锁定模型）

---

## 1. 为什么从 222 扩展到 318？

222 例（STEP 10/11）在 675/725°C、ΔT=25/75、中间几何、蠕变时间 300/3000h、低压区存在系统性空洞；STEP 12B 精选 78 例填补（→300）；STEP 13.8A 的 18 例专门填补 **Pi_yield 过渡区（train 原 0 例）与高压薄壁区**（→318）。每一步都由参数空间审计（STEP 12A）与数据缺口分析（STEP 13.7）驱动，非随机扩样。

## 2. 为什么增加 transition-region cases？

STEP 13.6/13.6A 诊断：位移失败与 P≥30 外推失败根因 = train 无塑性转变样本（PEEQ>0 在 train 仅 1 例；Pi_yield>1 为 0 例）。18 例设计使 Pi_yield 覆盖 0.70–1.51 连续谱（elastic→onset→shallow→strong plastic）。

## 3. 为什么引入 Pi_yield？

P·Ro/(w·σy) 是薄壳环向应力/屈服强度无量纲比，物理上编码塑性触发判据；STEP 13.6A 相关分析显示其与 displacement (r=0.593) 和 PEEQ (r=0.581) 最高相关。作为**连续 physics-informed 特征**引入（非硬编码定律），对树模型有效、对线性模型有害（共线，已记录）。

## 4. 新增数据是否真实改善模型？

**是**（controlled ablation，同一 test）：318+12f test R²=0.8674 vs 300+12f=0.856（数据贡献 +0.011）；**P≥30 从 +0.005 升至 +0.4553**；unified displacement 从 −0.018 升至 +0.350。18 例中 12 例塑性（含 3 例 onset 微屈服）为 stage-1 提供真实正样本（1→11）。

## 5. Physics features 是否真实改善模型？

**是**：300+16f=0.864 vs 300+12f=0.856（+0.008）；且与数据贡献**超可加协同**（合计 +0.074 > 0.008+0.011）。表述：controlled ablation provides strong evidence that the transition-region data and physics-informed features jointly improve extrapolation performance（非严格因果证明）。

## 6. P≥30 外推是否改善？

**显著改善**：−0.267（基线）→ +0.005（physics 特征）→ **+0.4553**（+transition 数据）。但 MAE 30 MPa（n=10，含薄壁 EPP 饱和 case）——**仍有较大误差，列入"有限可靠"边界**。

## 7. 位移问题为什么比 VM 难？

- von Mises 物理有界：弹性域 vm≈P·Ro/w、塑性域饱和于 σy → 外推可学
- displacement 在 EPP 屈服后**无硬化流动 → 无上界**（LHS241 697mm 由 PEEQ=40 主导）→ 统一回归必然失败
- 分解后：弹性域 R²=0.917（优秀）、塑性域量级不可靠 → 本质是**本构模型（EPP）的物理限制，不是回归方法问题**

## 8. EPP extreme cases 怎么处理？

**不删除、不修改、不隐藏**（红线全程遵守）：LHS241/LHS116/LHS064 保留在 test；统一模型与弹性域模型的 R² 受影响均如实报告（maxAE 695/550mm 单点主导）；三阶段方案将其归入 Stage-3（regime flag + exploratory），标记 `EPP_post_yield_extreme`。

## 9. CEEQ 当前为什么不能正式建模？

MODEL_C 的 validation 覆盖 = **0 例**（划分按时间规则：t≤300 train、≥1000 test）→ 无独立验证集；非零样本 37(train)+20(test)；exploratory test R²=0.650（log10 域）**不构成 production 证据**。正式建模必须先解决 validation 覆盖（STEP 14-A）。

## 10. 当前 surrogate model 的适用边界

**可靠**：
- von Mises 全域（test R²=0.930，MAE 12.4 MPa）
- 弹性位移（R²=0.917，稳定）
- 温度外推（T750 R²=0.941）、几何外推（Rm150 R²=0.915）
- 中高压 von Mises 外推（P≥30 R²=0.455，趋势正确）

**有限**：
- 塑性 regime 分类（recall 0.833，transition 区仍有漏检）
- P≥30 VM 量级（MAE 30 MPa）
- unified displacement（R²=0.350）

**不可靠/未验证**：
- EPP post-yield displacement 量级（exploratory only）
- production CEEQ（无 MODEL_C validation）

## 11. 下一阶段最重要的数据缺口

1. **MODEL_C validation 覆盖**（CEEQ 正式建模前提）
2. **高压弹性域+塑性过渡区更多样本**（P≥30 n=10 上限；Pi_yield 1.0–1.2 各温度多几何）
3. **硬化本构数据**（EPP post-yield 位移非物理无界的根本解）

## 12. 最终结论（克制表述）

> 在当前 Abaqus EPP 数值模型和设计参数域内（550–750°C、P 0–40 MPa、Rm 80–150 mm、Ro 15–25 mm、wall 2–5 mm），physics-informed XGBoost surrogate 对 **von Mises stress** 已表现出较高预测精度（test R²=0.930），并对温度、压力、几何及高压外推具有较好的泛化能力（P≥30 R² 从 −0.267 提升至 +0.455）。

> **plastic post-yield displacement 和 creep（CEEQ）仍然是后续研究重点**，当前仅具 regime 识别能力与 exploratory 量级估计，不构成生产级预测。

## 13. STEP 14 候选方向（仅提出，不执行）

| 候选 | 内容 | 前置条件 |
|---|---|---|
| **STEP 14-A** | 增加 MODEL_C validation cases → 正式 CEEQ surrogate | 新 split design 或补充蠕变 case |
| **STEP 14-B** | 引入硬化本构（多线性/幂硬化）→ 解决 EPP post-yield displacement 非物理无界 | Abaqus 材料模型变更（需批准） |
| **STEP 14-C** | 跨尺度扩展：irradiation/microstructure → 本构参数映射 | 文献数据审计 |
| **STEP 14-D** | 不确定性量化 / active learning（外推区采样） | 现模型之上 |

**未自动选择任何方向，等待人工指示。**

---
*本报告为 STEP 13 阶段收尾；全部数字可复现（seed 42），历史产物保留。*
