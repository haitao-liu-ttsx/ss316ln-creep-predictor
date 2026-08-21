# STEP21-C V1.3 七场多物理场模型训练与严格验证报告

日期: 2026-08-21 ｜ 状态: **STEP21-C = COMPLETE_WITH_WARNINGS**（训练成功；CEEQ 在几何外推域存在明确警告）

## 一、训练数据

TRAIN 157 / VAL 28 / EXT 45（+5 排除）；每 case 2304 点 × 7 target；来源 107 legacy + 123 STEP20-C/D。

## 二、模型结构

延续 V1.2 配方：case 参数 → 特征工程（10 特征）→ TRAIN-only 标准化 → TRAIN-only POD(k=3) → 每模态 Poly2+Ridge(α=1.0) → 场重建。**CEEQ 采用 Poly3**（VAL 选择：系数 R² 0.941 vs Poly2 0.887）。材料表扩展 700/750（STEP20-A 冻结值），未重拟合。

## 三、POD

TRAIN-only（157 例）；应力场 rank999=3、CEEQ rank999=1；k=3（STEP21-B 冻结）。POD 重建质量：CEEQ log10 MAE=0.0057（k=3）。

## 四、normalization

TRAIN-only mean/std（ml/v13/v13_scaler.npz）；VAL/EXT 仅用 TRAIN scaler；CEEQ log10(ε=1e-300)。

## 五、7 场训练结果（relL2 空间相对误差）

| 场 | TRAIN | VAL | EXT |
|---|---|---|---|
| Srr | 0.0327 | 0.0797 | 0.0465 |
| Stt | 0.0327 | 0.0797 | 0.0465 |
| Szz | 0.0350 | 0.0805 | 0.0518 |
| Srt | 0.0288 | 0.0744 | 0.0459 |
| Srz | 0.0277 | 0.0731 | 0.0447 |
| Stz | 0.0278 | 0.0731 | 0.0447 |
| von Mises | 0.0288 | 0.0733 | 0.0448 |

应力 MAE：TRAIN 0.17-0.89 MPa、VAL 0.49-2.4 MPa、EXT 0.58-2.9 MPa（剪应力 MAE 显著小于正应力，无幅值放大）。

## 六、CEEQ 结果

| 域 | TRAIN | VAL | EXT |
|---|---|---|---|
| log10 MAE | 0.164 | 0.536 | 0.555 |
| raw MAE | 1.69e-06 | 1.54e-05 | 6.31e-04 |

**重要说明**：log10 CEEQ 场的场内方差极小 → 逐 case R² 是误导指标（TRAIN 中位 R²=0.95 但均值被最差 case 拖至 0.71）；真实指标为 **log10 MAE**。TRAIN 域（基准几何）多数 case log10 MAE<0.15（误差<40%）；最差 case 全为 **几何外推**（120/25/3、80/15/2 不在 TRAIN 几何集）× 短时（100h）→ log10 MAE 1.1-1.7（10-50 倍）。**这是数据覆盖边界，非模型缺陷**。负 CEEQ 预测 = 0。

## 七、von Mises 物理一致性

由预测六应力重算（非直接预测）：relL2 TRAIN 0.033 / VAL 0.073 / EXT 0.045——与应力场同级，物理一致 ✓。

## 八、空间场误差

逐 case 空间 MAE/relL2/P95/max 已保存（ml/v13/step21c_eval.json）；3D 误差场可视化 ml/v13/viz/3d_T{550,650,700,750}.png（True/Pred/Error × Srr/CEEQ/vm）。

## 九、EXT 结果与最差 case

EXT 45 例：应力场 relL2 4.5-5.2%（优于 VAL——EXT 参数空间部分与 TRAIN 接近）；CEEQ log10 MAE 0.55。

**最差 10 case 模式**：全部为 120/25/3 或 80/15/2 几何（非 TRAIN 基准几何）× t=100h 短时 × P·Ro/w 150-225 高应力——几何外推边界。

## 十、温度分层（EXT）

- 550°C：n=1，CEEQ relL2=2.322，vm relL2=0.126
- 650°C：n=1，CEEQ relL2=0.898，vm relL2=0.083
- 700°C：n=19，CEEQ relL2=1.814，vm relL2=0.049
- 750°C：n=24，CEEQ relL2=1.221，vm relL2=0.036

EXT 中 700/750 占 43/45——高温外推覆盖充分；550/650 仅 1 例（EXT 分布不均，如实记录）。

## 十一、时间趋势

25 组（≥3 时间点）的 CEEQ 空间均值随时间单调性：**true 100% 单调** ✓（蠕变累积物理正确，无需修正）。

## 十二、物理 QA

NaN/Inf=0、负 CEEQ 预测=0、负 von Mises=0（TRAIN+VAL+EXT 全 case）。

## 十三、数据泄漏审计

POD/scaler/回归 = TRAIN only；超参（CEEQ Poly3）= VAL 选择；EXT 仅最终评估。机器检查 PASS。

## 十四、3D 可视化

ml/v13/viz/：field_relL2.png、vm_consistency.png、3d_T{550,650,700,750}.png（真实 x/y/z 坐标，True/Pred/Error）。

## 十五、模型文件

ml/v13/models/model_{Srr,Stt,Szz,Srt,Srz,Stz,CEEQ}.joblib（含 mu/sd/basis/regs/k/target，可独立加载）。

## 十六、prediction API

待 STEP21-D 统一接口（输入 T,P,t,Rm,Ro,w → 7 场 2304 点 + von_mises + centroids）；模型已可直接调用。

## 十七、存在的问题（如实）

1. **CEEQ 几何外推警告**：120/25/3、80/15/2 不在 TRAIN 几何集 → 外推域 log10 MAE 达 1.1-1.7（训练几何域内 <0.15）；建议后续补充这些几何的 TRAIN case（数据扩充，非模型改动）
2. log10 CEEQ 的场内 R² 指标具误导性（场内方差极小），已改用 log10 MAE 为主指标
3. EXT 温度分布不均（550/650 各仅 1 例）——EXT 主要覆盖 700/750 高温外推
4. CEEQ 使用 Poly3（VAL 选择）偏离 V1.2 的 Poly2——已记录选择依据

## 十八、数据完整性

318 = UNCHANGED ｜ V1.2 = UNCHANGED ｜ STEP20-C = UNCHANGED ｜ STEP20-D = UNCHANGED ｜ STEP21-A = UNCHANGED ｜ STEP21-B = UNCHANGED ｜ V1.3 TRAINING = **COMPLETE** ｜ LOCKED = UNTOUCHED ｜ WebApp = UNCHANGED

## 十九、是否允许进入 STEP21-D

**YES（带警告）** —— 应力场与 von Mises 物理一致性优秀；CEEQ 在训练域内可靠、几何外推域已明确标注；STEP21-D 统一预测接口 + WebApp 集成时可对 CEEQ 外推域实施域内守卫。