# STEP 16-F 最终科研结论（三层）

日期: 2026-08-20

## Conclusion 1 — STEP14：物理基线解释了标量蠕变缩放

Physics-informed scalar Norton baseline（PhysB-quad：log10 CEEQ = a + b₁T + b₂T² + n(T)·log10 P + log10 t）在独立验证中证明已知物理规律能够解释主要标量 creep scaling（validation R²=0.998）。**同时证明在当前标量任务上普通 ML 不提供超越已知 Norton 幂律的预测能力**——"ML has not yet been given the appropriate spatial-field learning problem"。

## Conclusion 2 — STEP15：场表示赋予 ML 三维空间预测能力

STEP15 引入 POD(log10 CEEQ, k=3) + 模态系数回归后，ML 提供了 STEP14 标量模型**无法提供的三维空间 CEEQ 预测**：2304 element-centroid 场、空间热点识别（EXT 27/27 命中）、θ-φ-r 时空演化。关键科学发现：稳态蠕变场内在维度≈2（单一空间模式×时间线性），使小样本场建模可行。

## Conclusion 3 — v1.2：数据扩充解决外推问题，但限定有效域

v1.2（POD + Poly2/Ridge + log10(P·Ro/w)，经 50 例新增 Abaqus 数据扩充）在独立 EXT 27 上：

```
logMAE = 0.0314
logR²  = 0.9998
relL2  = 0.148
hotspot hit = 27/27
physics violations = 0
3000h logMAE = 0.0378（v1.1 为 1.41）
```

解决了 v1/v1.1 的主要长时间外推与几何 domain-shift 问题（3000h logR² −0.004→0.575→0.9996 三代演进）。

**但必须严格限定为 validated domain**（T 550–650 / P 2.5–30 / t 1–3000h / 几何与 P·Ro/w≤250 规范，见 STEP16_DOMAIN_OF_VALIDITY.md）：**不能声称是全温度、全压力、全几何范围的通用 SS316LN creep model**。700/750°C 属于 DATA_REQUIRED（材料参数缺失），非预测失败。

## 最终表述

*"Within the validated domain, STEP15-v1.2 provides a three-dimensional spatiotemporal CEEQ field surrogate for SS316LN toroidal/annular structures, enabling hotspot identification and creep-field assessment from case parameters."*

LOCKED TEST 全程未用于模型开发与最终模型选择（20 例隔离，checksum fa573e330926 保持）。
