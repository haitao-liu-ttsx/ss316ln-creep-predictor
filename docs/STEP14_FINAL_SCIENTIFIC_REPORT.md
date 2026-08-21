# STEP 14 最终科研报告（标量 max-CEEQ surrogate 闭环）

日期: 2026-08-20
状态: **STEP14-A COMPLETE / STEP14-B COMPLETE / 标量模型 FROZEN / TEST 一次性评估完成 / LOCKED TEST 隔离 / STEP15 NOT STARTED**
配套: STEP14A_*（3 份）、STEP14B_*（4 份）系列报告 + `ml/final/`（冻结与生产产物）

---

## 1. 数据生产（STEP14-A）：27/27 真实 Abaqus case

- Abaqus 2024 / Standard，cpus=4，license 全程正常
- **18 validation（t=500/750h，基准几何 100/20/4）+ 9 test（t=3000h，非基准几何拉丁方）**
- 全链路 27/27：INP → solve → ODB → CEEQ 提取（最终帧、元素场 max）→ log10(CEEQ)
- 无 NaN/Inf/zero/negative；final time 全部精确；318 与 locked test checksum 全程 unchanged

## 2. 数据链（lineage 锁定）

| 集 | n | 来源 | t (h) | 几何 |
|---|---|---|---|---|
| TRAIN | 37 | STEP13 MODEL_C train（318 dataset） | 1–300 | 34/37 基准 |
| VALIDATION | 18 | STEP14-A 新增 | 500/750 | 基准 |
| TEST | 9 | STEP14-A 新增 | 3000 | 非基准拉丁方 |
| LOCKED TEST | 20 | 历史隔离（未用于任何模型指标） | 100/1000/3000 | 混合 |

四集互斥（case_id + 主键双口径）；LOCKED 全程隔离。

## 3. 物理规律验证（STEP14-A 数据与锁定 Norton 本构相容）

- **CEEQ ∝ t**：validation 全部 18 例 750/500 = **1.500** 精确
- **P×2 → CEEQ×~730** = 2^9.51（n=9.51 精确）
- **T 550→600→650 单调增**
- 交叉检查：首例 500h CEEQ=7.85e-16 vs 历史 1000h 1.569e-15（∝t 线性闭式验证）

## 4. 模型选择（validation 驱动）

| 模型 | Val RMSE | Val R² |
|---|---|---|
| **PhysB-quad（PRIMARY）** | **0.112** | **0.998** |
| Linear（最佳 ML） | 0.534 | 0.956 |

- 选择规则：Val RMSE 优先 → 物理合理性 → 复杂度 → CV 稳定性
- **物理基线 > ML 基线**（4.8× RMSE 差距）；未因"AI 项目"偏袒 ML
- 公式：log10(CEEQ) = a + b₁T + b₂T² + n(T)·log10 P + log10 t；n(T)={550→9.51, 600→9.04, 650→7.57}（Norton 锁定）
- 冻结（B.6）→ TRAIN+VAL refit 55 例（B.7，系数微调，audit 10/10）→ TEST（B.8）

## 5. TEST 最终结果（一次性，9 例双重外推）

| 模型 | MAE | RMSE | R² | max | median |
|---|---|---|---|---|---|
| **PhysB-quad (refit55)** | **1.221** | **1.415** | **0.692** | 2.07 | 1.29 |
| Linear | 1.518 | 1.892 | 0.449 | 2.91 | 1.52 |

- **PhysB-quad 仍优于 Linear**；Val R²=0.998 → TEST 0.692：双重外推（3000h + 非基准几何）导致明显降级
- 时间外推维度：∝t 项本身正确（无系统性时间漂移证据）；误差主要来自几何项缺失

## 6. Geometry domain shift（STEP14 最重要科研发现）

**T650/P20 案例**：
- 历史基准几何 CEEQ ≈ 9.9e-7；新几何 (120,25,3) 真实 ≈ **4.99e-5**（×50）
- PhysB-quad 预测 ≈ 1.07e-6（**低估 ~47×**）
- 机制：P·Ro/w 应力比 100 → 250 MPa → Norton n=7.57 幂律放大（物理自洽）
- 几何分组：应力比 7.5 的 (150,20,4) MAE=0.26（好）vs 8.33 的 (120,25,3) MAE=1.93（差）

**结论（明确记录）**：*scalar Norton baseline does not contain sufficient explicit geometry/mechanical information to represent geometry-dependent creep amplification.* —— 非软件/Abaqus 错误，是模型结构局限。

## 7. 物理趋势与泄漏

- 趋势：1 项 mild violation（按 P·Ro/w 排序的预测单调性，模型无几何项所致）如实记录；CEEQ>0/finite/无 NaN/预测域可比
- 泄漏审计：B.3 12/12、B.6 15/15、B.7 10/10、B.8 11/11 全部 PASS；TEST target 仅 B.8 读取一次；318 checksum `20f21ebc67ea`、split `fa573e330926` 全程 unchanged

## 8. 三层次科研结论

**结论 A**：STEP 14 标量 physics baseline（PhysB-quad）成功建立——train/val/test 严格隔离闭环，validation R²=0.998、TEST R²=0.692（量级正确）。

**结论 B**：在当前数据上，没有证据表明普通 ML baseline 能够超过已知 Norton physics（validation 0.956 vs 0.998；TEST 0.449 vs 0.692）。*"ML does not add predictive capability beyond the known Norton law for the present scalar target."*

**结论 C**：几何 domain shift 暴露了 scalar Norton 模型的结构性局限。

**关键科研定位**："ML has not yet been given the appropriate spatial-field learning problem." —— 上述结论**不能**被解释成"ML 无法建模 SS316LN 蠕变"。

## 9. Limitations（如实）

1. 标量 max-CEEQ 输出：无空间分布信息（CEEQ(x,y,z,t) 未知）
2. 无显式几何项：非基准几何 domain shift 低估 ~47×
3. 时间外推上限：t=3000h 验证，更长时间未覆盖
4. 材料域：550–650°C Norton（700/750 蠕变 DATA_REQUIRED）；σy 550/600 缺失
5. 小样本（train 37）限制 ML 潜力评估

## 10. STEP 15 规划（仅规划，未执行）

**科学动机**：STEP 14 的 (T,P,t)→scalar 结构无法表达 geometry-dependent stress redistribution、local stress concentration、spatial creep localization 与三维场演化。

**升级路线**：
```
Abaqus ODB → QC → spatial field dataset → POD/PCA → modal coefficients → ML/MLP → field reconstruction → 3D visualization
```

15 项规划要点：① ODB field inventory（CEEQ/S/EE/U 节点场）② 统一空间表示（节点/积分点方案，环形结构 θ-φ-r 参数化）③ 几何参数化（Rm/Ro/w 连续）④ 空间归一化 ⑤ POD/PCA 矩阵构建 ⑥ 模态数选择准则 ⑦ 模态系数 target 定义 ⑧ MLP 架构候选（含物理约束项）⑨ train/val/test 策略（沿用 37/18/9 逻辑 + 场级）⑩ 几何/时间外推协议 ⑪ 场重构（POD 投影）⑫ 场级指标（field MAE/RMSE/最大局部误差）⑬ 物理单调性约束（T/P/t 趋势入 loss 或后验检查）⑭ 不确定性/外推检测（模态残差、域内/外指示）⑮ Web 可视化（θ-φ 展开 + t 轴动画）。

**所需 ODB 建议范围**（供决策，未执行）：场级建模需覆盖 T×P×t×几何格点——建议首批 **60–120 个 ODB**（现有 318 例的 ODB 已含全部场输出，可先审计复用；新增主要覆盖 700/750°C 蠕变与更多几何组合，数量待 STEP 15 详细设计）。

## 11. 最终状态

STEP14-A：**COMPLETE** ｜ STEP14-B：**COMPLETE** ｜ STEP 14 标量模型：**FROZEN**（PhysB-quad refit55）｜ TEST：**一次性评估完成** ｜ LOCKED TEST：**仍隔离** ｜ 318 dataset：**unchanged** ｜ STEP13 split：**unchanged** ｜ **STEP15：NOT STARTED** ｜ **最终三维 SS316LN 环状结构 AI surrogate：NOT YET BUILT**

---
*本报告全部数字来自可复现脚本（seed 42）与真实 Abaqus 求解；无任何数据/模型在 TEST 后修改。*
