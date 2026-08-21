# STEP 15-C.0 三维时空蠕变场 Surrogate 设计（仅设计，未训练）

日期: 2026-08-20
状态: **设计+审计完成 — 未训练、未生成 case、未读取 locked**
目标: 类似 Norton-Pipe Field Demo 的 SS316LN 环状结构场 surrogate：`[T,P,t,Rm,Ro,w,E,A_creep,n_creep] → CEEQ(x,y,z,t)`
证据: `ml/metrics/step15_c0_{split_audit,pod_leakage_audit,feature_schema,evaluation_schema}.json`、`ml/final/STEP15_SURROGATE_SPEC.json`

## 1. 数据基础（STEP15-A/B 确认）

- 57 个 CEEQ 场 case（318 内 MODEL_C）；**locked 20 例隔离后训练池 = 37 例**（t 1/10/100/300h；几何 34 基准 + 80/15/2×1 + 90/18/3×2）
- 场表示：element centroid 2304 维（固定拓扑 48×16×3）；时间网格 [1,3,10,30,100,300,500,750,1000,3000]
- **STEP14-A 27 例（t 500/750 基准 18 + t 3000 非基准 9）为独立外部外推测试层**（不属 318，未锁定，可作 EXT test）

## 2. Case-level 数据划分（严格防 snapshot 泄漏）

| 集 | n | 构成 | 用途 |
|---|---|---|---|
| TRAIN | 31 | t≤300 分层（t=100 余 11、300 全 6、1/10 余 7/7） | POD basis 拟合 + 系数回归训练 |
| VALIDATION | 6 | t=1×2/10×2/100×2（B007/B008 等，case-level 留出） | 模型选择/调参 |
| TEST-EXT（时间外推+几何 shift） | 27 | STEP14-A（500/750 基准 18 + 3000 非基准 9） | 冻结后一次性评估 |
| LOCKED | 20 | 318 locked | **永不读取** |

- **case-level 原则**：同一 case 的全部时间 snapshot 同属一个 split（时间维度通过网格插值在 case 内展开，不跨 split）
- 时间外推 test = 500/750/3000h 层；几何 shift test = 9 例非基准拉丁方；T-P 插值 = val 6 例与 train 覆盖的插值区间

## 3. POD leakage 审计（硬约束）

- **POD basis 仅由 TRAIN（31 例）field snapshots 拟合**；VAL/EXT/LOCKED 一律只投影到冻结 basis
- TEST field 不参与 basis/scaler/调参/选择；LOCKED 永不读取
- 318 checksum `20f21ebc67ea`、locked `fa573e330926` 保持

## 4. 三种 surrogate baseline（统一接口，暂不训练）

- **A. Physics-inspired**：单空间模式×时间线性 r(x)·t（STEP15-B 证实 CEEQ 场内在维度≈2 的解析基线）
- **B. XGBoost/RF → POD 系数**（每模态一个回归器；STEP13/14 验证的树模型生态）
- **C. MLP → POD 系数**（架构候选文档化，样本扩充后对比）
- 统一输入 9 特征（T_hot/pressure/log1p_time/Rm/Ro/w/E/A_creep/n_creep）；统一评估协议

## 5. 评价指标（三层）

- 系数级：MAE/RMSE/R²（每模态）
- 场级：global MAE/RMSE、relative L2、max CEEQ error、hotspot error、重构误差
- 物理一致性：CEEQ≥0、finite、t/P/T 单调、几何响应合理

## 6. k=3/4/5 三套候选

三套 POD 维度均保存设计（`step15_pod_modes_*.npy` 已有 raw 模态可投影）；C.1 分别拟合系数回归器后按 validation 选择（**不按 EXT test 选择**）。

## 7. Inference API 设计

```
输入: T, P, t, Rm, Ro, w  →  (E/A_creep/n_creep 由材料表查 T)
输出: CEEQ field (2304,) + max/mean/p99/hotspot_element + relative_L2
未来: CEEQ(theta, phi, r, t) 规范坐标输出
```

## 8. 可视化接口设计

- element centroid (x,y,z) → 环面规范坐标 (θ,φ,r)（θ∈[0,2π)×48、φ×16、r 4 层）
- 视图：3D 表面/体积、θ-φ-r 展开、时间动画、热点叠加

## 9. 核心问题回答（A–H）

**A. 57 例是否足够第一版？** 训练池 37 例（+6 val）——**足够训练"有限域 v1"**（场内在维度≈2 使系数回归只需小样本）；但覆盖有限（T 3 值、几何 6 种、P≤20），属 v1 有限域版而非完整 surrogate。
**B. 优先增加哪些 case？** geometry（6→10 种）> 高压蠕变场 > T（700/750 受 DATA_REQUIRED 阻塞）> time（已完备）。
**C. 增加多少？** ~30–50 例（v1.5 覆盖格点，C.1 细化）。
**D. 优先维度？** geometry 第一（模式对几何敏感，k≈2 结论的稳健性依赖多几何验证）。
**E. 能否建立第一版 field surrogate？** **能**（v1 有限域）；完整版需 C 中扩充。
**F. 第一版推荐？** **XGBoost/RF（POD 系数）**——小样本稳健、生态已验证；MLP 样本扩充后对比。
**G. 模态数？** **k=3–5**（k=2 已 100% 方差，3–5 裕度）。
**H. TEST 独立保证？** case-level split + POD basis train-only + EXT 一次性评估 + locked 隔离 + 全部 checksum 锁定。

---
*纯设计；未训练、未生成 case、未读 locked/EXT target 之外数据。*
