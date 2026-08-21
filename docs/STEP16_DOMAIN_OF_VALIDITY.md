# STEP 16-E 有效域与禁止外推规范（Domain of Validity）

日期: 2026-08-20
对象: STEP15-v1.2 生产 surrogate（`ml/production/step15_v1_2/`，冻结）

## VALIDATED DOMAIN（有效域）

| 参数 | 范围 | 单位 |
|---|---|---|
| T | 550 – 650 | °C |
| P | 2.5 – 30 | MPa |
| t | 1 – 3000 | h |
| Rm | 80 – 150 | mm |
| Ro | 15 – 25 | mm |
| w | 2 – 5 | mm |
| P·Ro/w | ≤ 250 | MPa |

有效域由以下证据支撑：TRAIN（87 例蠕变场，68 train/19 val case-level）+ **EXT 27 独立外部验证**（logMAE 0.0314 / logR² 0.9998 / hotspot 27/27）。

## OUT OF DOMAIN（禁止外推，API 硬性守卫返回 OUT_OF_DOMAIN 并指明越界参数）

| 区域 | 原因 |
|---|---|
| **T = 700/750 °C** | **DATA_REQUIRED：Norton 蠕变参数缺失（MAT-05 仅 550/600/650 有效），无合法材料参数支持外推——不是预测失败，而是数据缺失** |
| t > 3000 h | 无训练/验证数据覆盖 |
| P > 30 MPa | 无高压蠕变训练数据（训练域 P≤30） |
| P·Ro/w > 250 | 高应力尺度域未覆盖 |
| 其他几何/材料域 | 未在本次训练/验证中覆盖 |

## 规范

- API 对 OOD 输入**拒绝静默预测**（返回 OUT_OF_DOMAIN + domain_issues 列表）
- 有效域内禁止突破的扩展需先完成：材料参数审计（700/750°C）→ Abaqus 数据扩充 → 重新训练/验证
- 所有 OOD 规则记录于 `PRODUCTION_MANIFEST.json` 与 `runtime/predict_field.py`
