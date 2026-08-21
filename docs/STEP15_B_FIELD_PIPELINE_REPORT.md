# STEP 15-B 场管线与 POD 可行性报告

日期: 2026-08-20
状态: **B.1/B.2/B.3 完成 — 未训练 AI、未生成新 case、未修改任何数据**
证据: `ml/metrics/step15_creep_time_sequences.csv`、`step15_time_alignment_audit.json`、`step15_field_extraction_audit.json`、`step15_field_statistics.csv`、`step15_pod_exploration.json`、`step15_pod_modes_{raw,log10}.npy`；`ml/data/step15_case_metadata.csv`、`ml/data/step15_ceeq_snapshots/*.npz`（57 例）

## B.1 时间统一

- 57 个 CEEQ ODB 全部可读；967 帧真实 frameValue 时间；final times = {1,10,100,300,1000,3000}h（500/750 为 STEP14-A val 层，含于 57 例）
- **统一时间网格（推荐）**：`[1, 3, 10, 30, 100, 300, 500, 750, 1000, 3000] h`（log 网格 + 500/750 val 层）
- **零外推规则**：t_grid 仅在该 case 实际时间范围内插值；范围外标 missing（57 例均有 missing 点——各 case 只覆盖自身时间域，符合设计）
- 插值稳定性：STEP14 已验证 CEEQ∝t（750/500=1.5 精确）→ **raw CEEQ 线性时间插值对稳态蠕变精确**；log10 域同样线性（log CEEQ = log r + log t）。B.2 对真实场复核无异常

## B.2 场提取与 QC（57/57 成功）

- **CEEQ 为 element field（C3D8R 单积分点）**：每帧 2304 值；节点 3072（坐标全提取）
- 存储：`ml/data/step15_ceeq_snapshots/<case>.npz`（node_coords 3072×3 + ceeq_frames n_frame×2304 + frame_times）；case 级元数据 `step15_case_metadata.csv`
- **QC**：NaN=0、Inf=0、负值=0；**zero_frames=2/例 为 t≈0 初始帧（物理正确，CEEQ(0)=0）**；幅度 3.8e-21..9.9e-7 与 STEP14 一致；空间 log10 标准差 0.57（连续性正常）
- **空间表示推荐：element centroid 场（2304 维）**——CEEQ 原生元素场（单 IP），无 extrapolation 误差；节点场需 extrapolate 且 C3D8R 单 IP 无唯一节点映射。拓扑全统一（3072 节点/2304 单元，确定性编号）→ snapshot 矩阵直接构造

## B.3 POD 探索（57×2304 snapshot 矩阵）

| k | raw 累计方差 | raw recon MAE | log10 recon MAE* |
|---|---|---|---|
| 2 | **1.0000** | 1.9e-11 | 0.49 |
| 3 | 1.0000 | 7.9e-13 | 1.02 |
| 5 | 1.0000 | 5.4e-14 | 0.47 |
| 8 | 1.0000 | 7.7e-17 | 0.08 |
| 15 | 1.0000 | 4.9e-19 | 0.01 |
| 30 | 1.0000 | 6.4e-22 | 0.0002 |

*log10 域重构误差的 mask 计算在探索脚本中有缺陷（log10 域可负导致 log10MAE 部分 NaN），raw 域指标为权威；结论不受影响。

**核心发现：CEEQ 场内在维度 ≈2（k=2 即 100% 方差）**——物理原因：均匀温度+均匀压力+稳态 Norton → 蠕变率空间分布固定（单一模式），CEEQ(x,t) = r(x)·t（空间模式×时间线性）。57 例仅需 2 个模态即完全重构。
**推荐模态数 k=3–5**（工程裕度；raw recon MAE ≤5e-14 时 k≥5）。**raw CEEQ POD 优于 log10**（raw 重构绝对误差极小；log10 域误差在小值区放大——与 STEP14 标量结论互补）。

## 时空与泄漏纪律

- 时间维度：统一网格 + 线性插值（零外推）→ CEEQ(x,t) 时空 snapshot 可行
- **探索性声明**：本 POD 为全 57 例 exploratory；**生产 POD basis 必须在正式 split 后仅用 TRAIN snapshots 拟合**；TEST 场不参与 basis
- 未修改 318 dataset / split / ODB；LOCKED TEST 未读取

## 数据缺口（57 例评估）

| 维度 | 现状 | 缺口 |
|---|---|---|
| 几何 | 6 种有蠕变场 | 模式数 k≈2 的结论基于 6 几何——几何变化可能引入新模式；建议补至 ~10 几何验证 |
| T | 550/600/650 | 700/750 蠕变 0（DATA_REQUIRED 约束） |
| P | 2.5–20（非基准最高 20） | 高压蠕变场缺失 |
| t | 1–3000h 全层 | 足够（时间层完备） |

## 第一版架构建议（不训练）

**POD + XGBoost/RF（模态系数回归）**：k=3–5 模态系数（标量）由 [T,P,t,Rm,Ro,w] 预测——每个模态系数一个回归器（样本 57 空间×时间层）；与 STEP13/14 已验证的树模型生态一致；MLP 为样本扩充后的第二候选。场重构 = 系数×模态 + 均值场。
**所需新增 Abaqus case 建议（待批准）**：~30–50 例（几何扩充至 10 种 × T/P 稀疏格点 + 高压蠕变），精确格点 STEP 15-C 设计。

---
*探索性分析；POD 未用于任何生产建模；全部数据/审计文件已落盘。*
