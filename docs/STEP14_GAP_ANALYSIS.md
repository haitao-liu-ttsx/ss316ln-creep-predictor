# STEP 14 ROADMAP / GAP ANALYSIS（规划与审计，不执行）

日期: 2026-08-20
状态: **只读规划。未新增 case、未修改材料/数据/模型/环境、未触碰 locked test。**
依据: STEP13_FINAL_REPORT / MASTER_RESULTS / REPRODUCIBILITY_AUDIT + 全部 metrics/analysis/schema/metadata

---

## 0. 当前状态基线（318 数据集锁定）

- 318 行 / valid 242 / split 120/48/74（v1 150 例零变化；test 74 例外推区锁定）
- FINAL VM：XGBoost 16f，test R²=0.9304（P≥30 0.455、Rm150 0.915、T750 0.941）
- 位移三阶段：stage-1 RF（acc 0.986/pl-recall 0.833）、stage-2 elastic linear（R²=0.917）、stage-3 exploratory
- CEEQ：exploratory log10 R²=0.650（MODEL_C train 37/val **0**/test 20）
- Pi_yield transition 实证：<1 弹性、1.00–1.14 onset、>1.14 塑性饱和

---

## 1. 方向 A — MODEL_C validation → CEEQ production model

### 1.1 当前已有数据（MODEL_C 实测分布）

| split | n | T | P | t (h) | 几何 |
|---|---|---|---|---|---|
| train | 37 | 550×13/600×12/650×12 | 2.5–20 | 1/10/100/300 | **100/20/4×34**，80/15/2×1，90/18/3×2 |
| validation | **0** | — | — | — | — |
| test | 20 | 550×6/600×6/650×8 | 2.5–20 | 100×2/1000×14/3000×4 | 100/20/4×13，120/25/3×2，150/20/4×2，80/15/2×1，110/22/4×2 |

### 1.2 缺失数据

1. **validation 时间层 500–1000 h：0 例**
2. 几何 confounding：train 34/37 在基准几何 → 蠕变对 Rm/Ro/wall 的敏感性无训练证据
3. t=3000 层仅 4 例（P 2.5/20 稀疏）

### 1.3 模型能/不能回答

- 能：给定 (T,P,基准几何,t≤1000) 的 log10 CEEQ 量级（exploratory R²=0.65）
- 不能：可靠量级（无独立验证）、几何外推、t>3000

### 1.4 CEEQ validation gap design（不破坏 locked test 的方案）

**原则**：CEEQ 建模走**独立子管线**（v5 专用子集 + 专用 split），vm/位移的 318 locked test 与主模型一律不动。

**时间三层设计**（用户优先方案）：

| 层 | 时间 | 来源 |
|---|---|---|
| train | 100–300 h | 现有 37 例（t 1–300，可含 t1/10 短时） |
| validation | **500–1000 h** | **需新增**（见下） |
| test | **3000 h** | 现有 4 例 + 新增（见下） |

**最小新增 case 建议（~27 例，未执行）**：
- VAL 层 18 例：T{550,600,650} × P{5,10,20} × t{500, 1000} × 基准几何（每格 1 例，时间层 = 500/1000 交错）
- TEST 层 9 例：T{550,600,650} × P{5,10,20} × t{3000} × 非基准几何 {(80,15,2),(120,25,3),(150,20,4)} 轮换（同时补几何 confounding）
- 若预算受限：VAL 12 例（P{5,10}）+ TEST 6 例 = 18 例

**Confounding 检查（已量化）**：
- 现有 train 的 T/P 分布在三层需对齐：VAL/TEST 新增按 T 550/600/650 等分、P 与 train 同集合 {5,10,20} → 避免"时间层×温度层"混淆
- 几何：新增 TEST 层刻意用非基准几何，使三层几何覆盖趋同；剩余几何偏差（train 34/37 基准）如实记录为残差 confounding
- 关键：**t=1000 的 14 例现有 test 保留在 locked test 中不动**（主模型外推对照）；CEEQ 专用 test 以 t=3000 层为准，报告两种口径（locked-test MODEL_C 20 例 vs 新三层）

### 1.5 其他

- 是否修改材料模型：否（Norton 参数不变）
- 是否影响 locked test：否（独立子管线）
- 工作量：Abaqus 18–27 例（~2–4 h 墙钟）+ 管线扩展（~1 天）
- 论文价值：高（蠕变长时外推是核材料核心问题）

---

## 2. 方向 B — EPP → 硬化本构 → post-yield displacement

### 2.1 已有数据（不编造，全部来自材料库）

- `materials/SS316LN_N014/plastic.csv`：**MAT-02 (Pan2024, N=0.13%) 真应力-真塑性应变数字化曲线**——650/700/750°C 各 7 点（σ 227→540/212→492/199→412 MPa，εp 0→0.22–0.26）——**C 级 digitized，非本项目实验**
- σy 三点（227/212/199）；550/600 σy DATA_REQUIRED

### 2.2 缺失数据

1. **550/600°C 硬化曲线**（σy 与曲线均缺）
2. N=0.14% 核级 316LN 的硬化曲线（MAT-02 为 N=0.13% 近似）
3. 应变范围：digitized 至 ~0.25 塑性应变（EPP 后屈服位移需要更大应变域验证，或接受 ≤0.25 域）
4. 卸载/循环数据（若涉及）

### 2.3 候选本构形式（列出，不选择）

- **多线性硬化**（Abaqus *PLASTIC table，直接用 digitized 曲线插值；最贴近数据）
- **Swift 幂硬化** σ = K(ε₀+εp)^n（拟合 3 温度，需 550/600 补点）
- **Voce 饱和硬化** σ = σy + R(1−e^(−b·εp))（饱和行为拟合）

### 2.4 评估

- 能回答：弹性域不变（现有模型有效）；屈服后位移获得物理上界（消除 EPP 流动 697mm 类伪像）
- 不能回答：无 550/600 数据 → 该温度域仍 DATA_REQUIRED
- 工作量：高（材料模型变更 + 全量重求解 300+ 例 + 重训）
- 论文价值：高（工程意义），但成本最高
- 是否影响 locked test：**是**（Abaqus 输出全部变化 → 当前 318/locked test 全部失效）→ 必须作为"独立新阶段"处理，需用户明确授权放弃或并行保留旧数据集

---

## 3. 方向 C — 跨尺度材料状态 → 宏观响应

### 3.1 层级缺口图（当前项目位置）

```
irradiation / material state（辐照、热老化、晶粒尺寸）  ← 项目无此层数据
        ↓
microstructure / defect descriptors（位错、析出、缺陷密度）  ← 文献层（941 行数据库有部分）
        ↓
constitutive parameters（E/σy/硬化/Norton A/n）  ← 项目材料库（固定 3 温度 σy、3 温度蠕变）
        ↓
Abaqus structural response（318 case）  ← 项目在此层（完整）
        ↓
AI surrogate（FINAL VM + 三阶段位移）  ← 项目在此层（完整）
```

**当前项目位于"本构参数→结构响应→surrogate"两层**；缺"材料状态→微观→本构参数"映射（参数-状态关系无数据）。

### 3.2 缺口

- 无辐照/热老化状态的实验本构参数（文献数据库有断裂时间等，但无状态-参数映射）
- 941 行文献库的 N≈0.14 筛选后可用参数仅 3 温度 σy/E + 3 温度蠕变

### 3.3 工作量与价值

- 工作量：极高（新数据采集或深度文献参数化）；论文价值：高（前沿）但依赖外部数据
- 前置：方向 A/B 之一完成，surrogate 成熟后才值得做参数-状态映射

---

## 4. 方向 D — Uncertainty Quantification / Active Learning

### 4.1 理论闭环设计（本 STEP 不执行）

```
surrogate uncertainty（ensemble XGB / 分位数回归 / 距离度量）
        ↓
candidate selection（外推区 + 高不确定性：Pi_yield∈[0.9,1.3] 未覆盖格点、P≥30 薄壁、t≥3000 蠕变）
        ↓
Abaqus acquisition（每轮 5–10 例）
        ↓
retraining（固定 seed，val 复核）
```

- 基于现有证据的候选热点：P≥30×w=2 弹性域（vm MAE 30 MPa 区）、Pi_yield 1.0–1.2×各几何（transition 边界细化）、MODEL_C t≥3000×非基准几何
- 当前可行性：无现成 UQ 模块（XGB 无原生不确定度，需 ensemble 或量化回归）→ 轻量实现可行（不装新环境：sklearn 自带）

### 4.2 评估

- 能回答：现有域内的不确定性边界、采样优先级
- 不能回答：域外物理（硬化/蠕变域外）
- 工作量：低-中（纯计算）；论文价值：中-高（与 A/B 数据缺口互补）

---

## 5. 优先级综合排序（科研价值 × 数据缺口 × 模型成熟度 × 工作量）

| 方向 | 科研价值 | 数据缺口紧迫性 | 模型成熟度 | 工作量 | 综合 |
|---|---|---|---|---|---|
| **A（CEEQ validation）** | 高 | **极高（val=0）** | 低（exploratory） | 低-中（18–27 例） | **P1** |
| **B（硬化本构）** | 高 | 高（550/600 缺） | 中（EPP 已知局限） | **极高（全量重算）** | **P2**（但需独立立项） |
| D（UQ/active learning） | 中-高 | 中（有明确热点） | 中（无 UQ 模块） | 低 | **P3** |
| C（跨尺度） | 高 | 高（但外部依赖） | 低 | 极高 | **P4**（依赖 A/B 成熟） |

**Priority 1 = A；Priority 2 = B（独立阶段）；Priority 3 = D；Priority 4 = C。**

## 6. 推荐路线

```
STEP 14-A（CEEQ 三层 validation：+18–27 例蠕变 case，独立 v5 子管线）
   ↓（A 完成、CEEQ production 建立后）
STEP 14-B（硬化本构独立阶段：材料升级 + 全量重求解，需新授权；旧 318 保留为 EPP 基准）
   ↓（可选并行）
STEP 14-D（UQ/active learning：纯计算，可在 A 之后立即开始）
   ↓（长线）
STEP 14-C（跨尺度：依赖文献参数化与外部数据）
```

## 7. 红线遵守声明

本文件未：修改 318 数据集、修改 locked test、新增 Abaqus case、修改材料模型、重训 production model、安装新环境、删除 extreme case、用 test 选择模型、包装 exploratory 结果。

---
*纯规划产物；所有新增 case 数量为设计建议，未生成任何 INP/未运行求解。*
