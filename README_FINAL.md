# SS316LN 环状结构三维时空蠕变场 Surrogate — 最终交付

## 1. Scientific Objective

基于 Abaqus 真实求解数据，建立 SS316LN（N≈0.14%）环状/环形结构的三维时空蠕变 CEEQ 场 surrogate：
`[T, P, t, Rm, Ro, w] → CEEQ(x,y,z,t)`（2304 element-centroid 场），支持工程热点识别与蠕变场评估。

## 2–3. 架构

- **STEP14（scalar physics baseline）**：PhysB-quad Norton 幂律 → max CEEQ 标量；validation R²=0.998；证明已知物理规律解释标量蠕变缩放
- **STEP15（field surrogate，本项目最终 AI surrogate）**：`POD(log10 CEEQ, k=3) + Poly2/Ridge 模态系数回归 + log10(P·Ro/w)` → 2304 场重构

## 4–6. 方法与数据管线

- 数据：318 历史（57 蠕变场）+ STEP14-A 27（独立 EXT）+ STEP15-G 50 例新增（48×3000h + 2×1000h）→ 87 例可训练蠕变场（case-level split 68/19）
- POD：log10 域、TRAIN-only basis、k=3（场内在维度≈2 的发现支撑小样本建模）
- 回归：Ridge-Poly2（10 特征含 log10(P·Ro/w)）；seed 42 全确定性

## 7–9. Production API 与域守卫

- API：`ml/production/step15_v1_2/runtime/predict_field.py` → `predict_field(T,P,t,Rm,Ro,w)` → `{ceeq_field[2304], max/mean/p95, hotspot_element, pod_coefficients, validity}`；另 `predict_time_series` / `get_hotspot`
- 有效域：T 550–650、P 2.5–30、t 1–3000h、Rm 80–150、Ro 15–25、w 2–5、P·Ro/w≤250（详见 `docs/STEP16_DOMAIN_OF_VALIDITY.md`）
- OOD 行为：700/750°C（DATA_REQUIRED）、t>3000、P>30、P·Ro/w>250 → 返回 OUT_OF_DOMAIN + 越界说明，**禁止静默预测**

## 10–11. 验证与限制

- EXT 27 独立外部验证（冻结后一次性）：**logMAE=0.0314 / logR²=0.9998 / relL2=0.148 / hotspot 27/27 / physics violations=0**；3000h logR²=0.9996
- 限制：有效域限定；1000h 桥接层稀疏；P·Ro/w>250 与 700/750°C 未覆盖（材料 DATA_REQUIRED）；top5=0.33（次级热点偏差，如实记录）

## 12–14. 可复现性与引用

- 固定 seed 42；可复现性测试与 G.4 保存预测**零差异**（max_abs_diff=0）；checksum 全记录（`ml/metrics/step16_final_asset_audit.json`）
- 文件结构：`ml/production/step15_v1_2/`（model/schema/runtime/tests/manifest）、`ml/final/`（v1/v1.1/v1.2 冻结版本）、`docs/`（STEP13–16 全系列报告）、`simulation/`（Abaqus 全证据）
- 引用式声明：*"Within the validated domain, STEP15-v1.2 provides a three-dimensional spatiotemporal CEEQ field surrogate for SS316LN toroidal/annular structures."*

**数据完整性与隔离声明：LOCKED TEST was never used for model development or final model selection.**（318 checksum `20f21ebc67ea`、locked `fa573e330926` 全程保持；STEP14/STEP15-v1/v1.1/v1.2 全部冻结未改。）
