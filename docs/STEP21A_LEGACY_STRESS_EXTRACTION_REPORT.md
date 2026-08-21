# STEP21-A 旧 107 例蠕变案例应力场补提取与 V1.3 统一数据层构建报告

日期: 2026-08-21 ｜ 状态: **STEP21-A = COMPLETE**（107/107 成功提取，230 例统一数据层构建完成）

## 一、任务目标

从旧 107 例蠕变 case 的原始 ODB 补提取应力场（最终 t_h 时刻，积分点值），执行与 STEP20-D 完全一致的坐标转换，建立 V1.3 统一数据层（7 target + von_mises_true 参考）。未训练、未修改任何源数据。

## 二、旧 107 例数据源

- 57 例 MODEL_C（B 系列 + CR 系列，ODB 位于 generated_cases / generated_cases_v2）
- 50 例 G（CEEQ15G_*，ODB 位于 generated_cases_step15g）
- 温度覆盖：550×36、600×35、650×36；全部有 ODB 且含 S + CEEQ 场

## 三、ODB 提取方法

- Step = TM（唯一蠕变步）；**最终帧**（frame_time 记录，抽样验证 B007/B008/B009 frame_time=100.0 == t_h ✓）
- S = 积分点原始值（C3D8R 单 IP = 单元质心），**无节点平均/外推/平滑**（与 STEP20-D 完全一致）
- CEEQ 直接从同一 ODB 同帧提取（与 S 同源，保证时间/空间一致）

## 四、坐标转换

S_local = Qᵀ S_cartesian Q，Q = [er, eθ, ez]（环轴 Z、θ=atan2(y,x)），逐质心旋转——真正的张量转换，非字段重命名。

## 五、空间点匹配

legacy 质心 vs _mesh 重建：max 坐标偏差 **2.27e-6**（与 STEP20-D 同量级，浮点误差级）→ 2304 点、排序、拓扑与 STEP20-D 完全一致。

## 六、数学 QA（逐 case）

| 项 | 最差值（107 例） | 结果 |
|---|---|---|
| 应力张量对称性 | 7.1e-15 | PASS |
| trace 保持 | 3.8e-6（B 系列单精度源数据） | PASS |
| von Mises 不变性 | 1.2e-7 | PASS |
| CEEQ ≥ 0 | 全部非负（min≈6.7e-16） | PASS |

## 七、数值 QA（legacy / new / combined 统计）

| 场 | legacy min~max | new min~max | combined 域 |
|---|---|---|---|
| Srr | -1.392e+01 ~ 2.182e+02 | -1.746e+01 ~ 1.967e+02 | -1.746e+01 ~ 2.182e+02 |
| Stt | -1.397e+01 ~ 2.181e+02 | -1.749e+01 ~ 1.967e+02 | -1.749e+01 ~ 2.181e+02 |
| Szz | -1.626e+01 ~ 2.564e+02 | -1.902e+01 ~ 2.128e+02 | -1.902e+01 ~ 2.564e+02 |
| Srt | -6.254e+01 ~ 6.254e+01 | -5.464e+01 ~ 5.464e+01 | -6.254e+01 ~ 6.254e+01 |
| Srz | -1.272e+02 ~ 1.272e+02 | -1.073e+02 ~ 1.073e+02 | -1.272e+02 ~ 1.272e+02 |
| Stz | -1.272e+02 ~ 1.272e+02 | -1.072e+02 ~ 1.072e+02 | -1.272e+02 ~ 1.272e+02 |
| CEEQ | 3.779e-21 ~ 4.823e-04 | 1.130e-08 ~ 1.279e-02 | 3.779e-21 ~ 1.279e-02 |
| von_mises | 7.301e+00 ~ 2.538e+02 | 2.337e+01 ~ 2.069e+02 | 7.301e+00 ~ 2.538e+02 |

NaN/Inf = 0；负 CEEQ = 0；无空场。legacy 应力域（B 系列低 P 早期 case 应力较低）与 new 域自然衔接，非异常。

## 八、成功/失败统计

- legacy：**107/107 成功**（MODEL_C 57/57、G 50/50），失败 0
- new：123 成功（STEP20-D 全量纳入）
- **V1.3 统一数据层 = 230 例**（7 target 全部可用）
- 5 个 EXT 失败 case：manifest 保留 status=FAILED_CONVERGENCE，无伪造场

## 九、新旧 schema 一致性

随机抽样 5 legacy + 5 new：字段名/形状（2304,）/dtype 完全一致 → **PASS**。字段：centroids + Srr/Stt/Szz/Srt/Srz/Stz/CEEQ/von_mises_true (+ 原始 Cartesian 分量)。

## 十、split 一致性

- 旧 87 例沿用 V1.2 冻结 split（TRAIN 68 / VAL 19）；20 例历史 case 标 LEGACY_UNSPLIT（如实，不伪造 split）
- 新 123 沿用 STEP20-C/E 冻结 split（TRAIN 64 / VAL 16 / EXT 43）
- group=(T,P,Rm,Ro,w) 无跨 split；新旧组温度天然隔离 → 无泄漏

## 十一、数据完整性

318 = UNCHANGED ｜ V1.2 = UNCHANGED ｜ STEP20-C = UNCHANGED ｜ STEP20-D = UNCHANGED ｜ V1.3 TRAINING = NOT STARTED ｜ LOCKED = UNTOUCHED ｜ WebApp = UNCHANGED ｜ 旧 ODB = 未修改

## 十二、新增文件

- `simulation/v13_prepared/fields/legacy_*.npz`（107 个）
- `simulation/v13_prepared/manifest.csv`（230 例统一清单）
- `simulation/v13_prepared/legacy_extract_results.json`（逐 case QA 记录）
- `ml/metrics/step21a_legacy_stress_extraction.json`（机器可读 QA）
- 提取脚本：`simulation/v13_prepared/extract_legacy.py` + `run_extract.py`

## 十三、是否允许进入 STEP21-B：**YES**（230 例统一 7-target 数据层就绪）