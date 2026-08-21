# STEP20-E V1.3 多物理场训练数据架构审计与冻结报告

日期: 2026-08-21 ｜ 状态: **STEP20-E = COMPLETE**（架构已冻结，未启动训练）

## 一、数据源清单

| 数据源 | 位置 | case 数 | 场内容 |
|---|---|---|---|
| 318 CSV（标量元数据） | data/ai_ready_v4/simulation_dataset_318.csv | 318 行（242 valid） | max_* 标量 |
| 旧 CEEQ 快照（57 例） | ml/data/step15_ceeq_snapshots/*.npz | 57 | CEEQ(2304) 多帧 |
| 旧 CEEQ 快照（G50） | ml/data/step15g_snapshots/*.npz | 50 | CEEQ(2304) 末帧 |
| 新 700/750 场（STEP20-D） | simulation/step20d/fields/*.npz | 123 | 8 场（6 应力+vm+CEEQ）2304 |
| 旧 ODB（含 S 未提取） | simulation/generated_cases*/ | 107 creep | S 张量在 ODB 内（has_S 已确认） |

## 二、318 数据实际审计结果

- 实际蠕变 case = 57（MODEL_C，T={550:19,600:18,650:20}）+ G50 = **107 例场数据**
- 旧快照格式：`ceeq_frames(n_frame, 2304)` + `node_coords(3072,3)`；G50：`ceeq_field(2304,)`
- **旧数据已提取的场只有 CEEQ**——应力场从未提取（ODB 中有，has_S=443 已确认）
- 时间定义：period = t_h 数值（旧快照末帧 = 完整 t_h，如 B007 末帧 100）

## 三、STEP20-D 数据审计结果

- 123 例 × 2304 点 × 8 场（Srr/Stt/Szz/Srt/Srz/Stz/von_mises/CEEQ + 原始 Cartesian 分量）
- 数学 QA：trace/对称/von Mises 一致性全部机器精度 PASS

## 四、数据兼容性结论

| 项 | 结论 | 证据 |
|---|---|---|
| 空间点数量 | **一致（2304）** | 新旧均 2304 |
| 空间点排序 | **一致** | 同一确定性 _mesh 生成器；实测偏差 2.3e-6 |
| 坐标系 | **一致** | 均全局笛卡尔 → 同转换（环轴 Z、θ=atan2） |
| 单位 | **一致** | mm-N-s-MPa |
| 时间定义 | **一致** | period=t_h 数值 |
| 字段 | **部分兼容** | CEEQ 全部可用（107+123）；应力场新 123 已提取、旧 107 需从 ODB 补提取（可行，STEP21-A） |

## 五、物理场架构分析

8 个可用场分三类：**独立张量分量**（Srr/Stt/Szz/Srt/Srz/Stz）、**派生量**（von Mises）、**独立非弹性场**（CEEQ）。

### 方案 A：7-target（推荐）
主模型输出 [Srr, Stt, Szz, Srt, Srz, Stz, CEEQ]；von Mises 由预测六应力计算，作为 physics consistency 验证量。
优点：避免派生量重复监督；输出物理结构清晰；可用 von_mises_pred vs true 做物理校验。

### 方案 B：8-target
直接预测 8 场。缺点：von Mises 与六应力存在确定性关系 → target 冗余、loss 权重重复强调应力信息、误差权衡复杂。

**最终推荐 = 方案 A（7-target）**。理由：数据量（123+107 例）与模型复杂度匹配；物理一致性可验证；von Mises 作为验证指标而非监督目标。

## 六、V1.3 输入（冻结）

- Case-level：T, P, t, Rm, Ro, w（6 个；派生特征按 V1.2 惯例：log1p(t)、log10(P·Ro/w)、E/A/n 温度查表）
- Spatial：**不显式编码**——POD 模态隐含空间结构（方案 C）
- 若未来 point-wise 化：推荐 sin(θ)/cos(θ) + r + z（torus 环向周期对称，避免角度跳变）

## 七、V1.3 输出（冻结）

7 target：Srr, Stt, Szz, Srt, Srz, Stz, CEEQ（每场独立 POD + 回归）

## 八、空间表示（冻结）

**方案 C（延续 V1.2 POD 架构）**：case 参数 → POD 系数（每场独立 basis，TRAIN-only 拟合）→ 2304 场重建。证据：V1.2 验证 logR²=0.999、整场输出、数据量匹配、WebApp 部署直接。

## 九、数据划分（冻结）

- group = (T,P,Rm,Ro,w)，组内 4 t 同 split；**新旧组零重叠**（温度维度天然隔离）
- 新数据：TRAIN 64 / VAL 16 / EXT 43 成功（5 失败排除）
- 旧数据：沿用 V1.2 既定 split（组级 TRAIN 68/VAL 19/EXT 27）
- **数据泄漏审计 = PASS**（组级隔离、无 t 跨 split、无场自预测）

## 十、Normalization（冻结）

- **仅 TRAIN 拟合**所有 scaler；VAL/EXT 用 TRAIN scaler；EXT 禁止参与任何拟合
- CEEQ：**log10 变换**（分布 1.1e-8~1.3e-2 跨 6 个数量级；log10 域 -7.95~-1.89 近均匀；与 V1.2 惯例一致）
- 应力：per-field 标准化（TRAIN mean/std）；剪应力量级（±54 MPa）远小于正应力（~200 MPa）→ 标准化必要

## 十一、多场 loss 设计（冻结原则）

per-field 标准化后的 MSE 求和（等权默认）；可选按物理量级加权——避免大应力分量主导 loss。

## 十二、CEEQ 数值处理建议

log10 变换（zero_ratio=0，无零值风险）；预测输出域内按 10^ 还原。

## 十三、von Mises 处理（冻结）

von_mises_pred = 由预测六应力张量计算；与真实 von_mises_true 对比 = V1.3 核心 physics consistency metric（不单独训练）。

## 十四、EXT 使用规则（冻结）

EXT（43 成功）仅作最终外推评估；**禁止用于训练/normalization 拟合/early stopping/模型选择**；5 个失败 case 保持 FAILED 不入张量。

## 十五、V1.3 数据结构（冻结）

`simulation/v13_prepared/`（STEP21 构建，本次仅设计）：
- `manifest.csv`：230 例（107 旧 + 123 新）源引用 + 派生元数据（不复制场数据）
- 场数据源：旧 CEEQ 快照（107）+ 新 step20d fields（123）+ STEP21-A 补提取的旧应力场
- schema 字段：case_id/source_dataset/source_case_id/T/P/Rm/Ro/w/time_h/split/status/field_available 各场/coordinate_system/points_per_case/field_path/schema_version

## 十六、是否可以进入 STEP21 Training：**YES**（数据架构已冻结；STEP21-A 先补提取旧 107 例应力场并构建 v13_prepared，然后训练）

## 十七、数据完整性

318 = UNCHANGED ｜ V1.2 = UNCHANGED ｜ STEP20-C = UNCHANGED ｜ STEP20-D = UNCHANGED ｜ V1.3 TRAINING = NOT STARTED ｜ LOCKED = UNTOUCHED ｜ WebApp = UNCHANGED

## 十八、新增文件

- `ml/metrics/step20e_v13_multifield_preaudit.json`（机器可读 QA）
- 本报告

## 十九、存在的问题（如实）

1. 旧 107 例应力场未提取（ODB 有 S，需 STEP21-A 补提取——已确认可行）
2. 旧快照无应力场意味着 V1.3 训练前必须完成补提取，否则 550/600/650 应力场缺失
3. 新数据 P 档（700: 16-30、750: 8-20）与旧数据 P 档（2.5-20）在高压区（20-30）重叠有限——EXT 设计已考虑
4. 750°C 仅 4 个拟合点支撑 n=5.56，低应力外推需 EXT 验证（STEP20-B 已单轴验证）