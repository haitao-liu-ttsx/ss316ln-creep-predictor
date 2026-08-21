# STEP 11 热梯度塑性高精度验证 + AI-ready 数据最终清洗 报告

日期: 2026-08-20
状态: 数值验证 + 数据清洗完成; **AI 训练未开始** (遵守禁令)

---

## 1. G1-G6 网格系列结果 (GRAD_750_550, ΔT=200°C, P=0)

| 网格 | 壁厚层 | 单元数 | PEEQ_max | PZ_vol(mm³) | PZ厚度比 | PZ位置(θ,φ,k) |
|------|--------|--------|----------|-------------|----------|---------------|
| G1 | 3 | 2304 | 5.67e-4 | 184137 | 1.00 | (0,5,0) |
| G2 | 4 | 9216 | 1.03e-3 | 140404 | 1.00 | (11,6,0) |
| G3 | 6 | 24576 | 1.44e-3 | 94103 | 1.00 | (0,7,0) |
| G4 | 8 | 32768 | 1.67e-3 | 141154 | 1.00 | (15,7,0) |
| G5 | 10 | 40960 | 1.80e-3 | 112923 | 1.00 | (0,7,0) |
| G6 | 12 | 49152 | 1.89e-3 | 139886 | 1.00 | (0,7,0) |

## 2. PEEQ 收敛情况
G5→G6: **+4.9%** (<5% ✅ 单级); 但 G3→G4 +15.5%, G4→G5 +8.0% — 单调增长, 仅末级达标。

## 3. 塑性区体积收敛情况
**未收敛** — G5→G6 +23.9%, 持续波动 (94103-141154 mm³)。

## 4. 塑性区厚度收敛情况
**恒为 1.00 (全壁厚塑性)** — 内壁到外壁全部进入塑性 (ΔT=200°C 下 EPP 模型行为)。

## 5. 塑性区位置稳定性
**稳定** — 所有网格 PZ 位于 (θ≈0-15, φ≈5-7, k=0) = 内壁高温侧局部区域。

## 6. GRAD_750_550 最终是否 converged
**NO** (gradient_plastic_highly_mesh_sensitive = YES):
- PEEQ_max 仅末级 <5%, PZ_vol 持续波动 → 未通过"连续两最高网格 <5%"判据;
- **不修改材料参数** (遵守禁令);
- 相关 49 case → valid_for_AI=NO, valid_for_physics_reference=YES。

## 7. GRAD_550_750 是否通过
**通过** — medium (PEEQ=0) 与 fine (PEEQ=0) 均无隐藏塑性; vm 319→365 (弹性, 网格合理)。

## 8. 最终 valid_for_AI 数量
**150** (A=80 + B=70)。

## 9. 最终 physics_reference 数量
**72** (D=49 网格敏感 + E=23 缺 σy)。

## 10. 最终 DATA_REQUIRED 数量
**23** (550/600°C σy 缺失 → 弹性-only, valid_for_AI=NO)。

## 11. train/validation/test 数量
- **train: 73** / validation: 23 / **test: 54**
- 外推测试保证: test 组合 (Rm=150, T=750, P≥30, 蠕变 t=1000h) 在 train 中 **0 重叠** ✅

## 12. 参数空间覆盖率
- 全覆盖: T_uniform (5档), R_major (4), R_outer (3), wall (4), P (9档), 蠕变组合;
- 空洞: ΔT=150 仅 7, ΔT=-200 仅 1, P≥30 仅 11 — 已记录于 coverage_report.md。

## 13. 最终 AI 数据文件路径
```
data/ai_ready/simulation_dataset.csv   (222 行 × 33 列, 全量含 D/E)
data/ai_ready/train.csv                (73)
data/ai_ready/validation.csv           (23)
data/ai_ready/test.csv                 (54)
data/ai_ready/coverage_report.csv/md
```

## 14. 最终数据字典路径
```
docs/AI_DATA_DICTIONARY.md
```

---

## 禁止事项遵守确认
- ✅ 未训练 AI / 神经网络 / 代理模型
- ✅ 未修改 E/σy/CTE/k/Cp/rho (收敛问题不通过改材料解决)
- ✅ 未平滑 PEEQ、未虚构数据、无 sodium、无 316L 冒充
- ✅ 未为凑数量扩大数据集 (222 case 保留原量)
