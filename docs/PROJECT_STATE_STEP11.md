# 项目状态快照 — STEP 11 完成时

日期: 2026-08-20
说明: 从项目实际文件与 STEP 报告核对生成, 非记忆。此快照后未修改任何模型/材料/数据。

---

## 1. 当前项目路径
```
D:\harness_work\ss316ln_toroidal_tube\
```

## 2. 当前完成到 STEP 11
STEP 1-11 全部完成; STEP 9(热-力耦合)、10(批量数据)、11(梯度塑性验证)报告在 `docs/`。

## 3. SS316LN_N014 材料定义
- 材料: SS316LN 奥氏体不锈钢
- material_id: SS316LN_N014 (核心) / SS316LN_N014_EXP / SS316LN_N014_RCCMR (E 版本)
- 氮含量目标: ~0.14 wt.% (MAT-05/04-14N IGCAR NE316LN)
- 晶体结构: austenitic FCC
- 温度范围: 550-750°C

## 4. N≈0.14% 的材料筛选结果
- MAT-05 (GaneshKumar2013, N=0.14%): 蠕变/塑性参数核心来源
- MAT-04-14N (Mathew2015, N=0.14%): 同批, 成分一致 (C0.026/Cr17.4/Ni11.9/Mo2.47)
- MAT-02 (Pan2024, N=0.13%): 仅作为实测力学参考 (E/σy/UTS), 不伪装成 0.14% 实验
- 评分优先: N≈0.14 > SS316LN 身份 > 550-750°C 实测 > 热处理明确

## 5. Air 环境限制
- 全部数据/模型: environment=AIR ONLY
- 所有 case 标记 environment=AIR

## 6. Sodium 数据明确排除
- 钠环境数据全部 use_for_model=NO, 记录于 materials/SS316LN_N014/{EXP,RCCMR}/excluded_sodium.csv
- Pan2024 的氧饱和钠 Norton n (24.2/9.38/17.56) 与断裂时间全部排除

## 7. E(T)
| 模型 | 来源 | 数据 |
|------|------|------|
| EXP (实测, A类) | Pan2024 MAT-02 | 650°C=171, 700°C=141, 750°C=119 GPa |
| RCCMR (公式, D类) | E=201660-84.8*T(°C) | 550°C=155.0, 600°C=150.8, 650°C=146.5, 700°C=142.3 GPa |
| 750°C RCCMR | 超出适用范围 | OUT_OF_VALIDITY_RANGE (未建) |

## 8. sigma_y 数据及缺失温度
| 温度 | σy (MPa) | 状态 |
|------|----------|------|
| 550°C | — | **DATA_REQUIRED** (缺失) |
| 600°C | — | **DATA_REQUIRED** (缺失) |
| 650°C | 227 | EXPERIMENTAL (MAT-02) |
| 700°C | 212 | EXPERIMENTAL (MAT-02) |
| 750°C | 199 | EXPERIMENTAL (MAT-02) |
注: 550/600°C 只建 elastic-only case, valid_for_AI=NO

## 9. Norton creep 参数及适用温度
| 温度 | A (s⁻¹/MPaⁿ) | n | 状态 |
|------|---------------|-----|------|
| 550°C | 7.75e-32 | 9.51 | EXPERIMENTAL (MAT-05) |
| 600°C | 3.56e-30 | 9.04 | EXPERIMENTAL (MAT-05) |
| 650°C | 2.35e-25 | 7.57 | EXPERIMENTAL (MAT-05) |
| 700°C | — | — | **DATA_REQUIRED** |
| 750°C | — | — | **DATA_REQUIRED** |
原始形式: ε̇=C·σⁿ, C[%/h/MPaⁿ]: 550°C=2.79e-27, 600°C=1.28e-24, 650°C=8.46e-20

## 10. ν=0.30 ASSUMED
- 5 篇文献均未提供泊松比
- ν=0.30 标记 data_type=ASSUMED, 非实验值
- 全部模型使用

## 11. rho/Cp/k/CTE 及其来源和数据等级
| 参数 | 来源 | 等级 | 值 (550-750°C) |
|------|------|------|----------------|
| ρ | IAEA Type 316 插值 | C/E | 7840.5→7746 kg/m³ |
| Cp | IAEA Type 316 插值 | C/E | 535.5→562.5 J/(kgK) |
| k | IAEA Type 316 插值 | C/E | 17.9→21.0 W/(mK) |
| CTE | IAEA linear 插值 | C/E | 19.30e-6→19.85e-6 /K (瞬时) |
| ρ 20°C 锚点 | ATI 316LN | B | 8000 kg/m³ |
标记: INTERPOLATED_REFERENCE, 非 SS316LN_N014 直接实验
等级体系: A=目标实验, B=成分相容316LN参考, C=316/316L参考, D=派生, E=插值, F=外推

## 12. 环形圆管几何参数
- R_major=100 mm, R_outer=20 mm, R_inner=16 mm, wall=4 mm (基准)
- 参数范围: R_major∈{80,100,120,150}, R_outer∈{15,20,25}, wall∈{2,3,4,5}
- R_inner=R_outer-wall (自动); 校验 R_inner>0, R_outer>wall, R_major>2·R_outer
- 基准 R_major/R_outer=5:1, t/R=0.20 (非薄壁)

## 13. 当前边界条件
- **对称约束** (热膨胀相容): θ=0/180 平面固定 U2, θ=90/270 平面固定 U1, 一点固定 U3
- 刚体矩阵秩=6, 0 个膨胀阻塞约束 (sym_bc_rank.py 验证)
- 原 4 点约束 (A:U1U3 B:U1U2 C:U1U3 D:U2U3) 因锁死热膨胀被废弃

## 14. 当前网格策略
- C3D8R / DC3D8 (热传导)
- 默认 medium: 48×16×3 (2304 单元)
- 收敛系列: coarse 24×8×2 / medium / fine 96×24×4 / extra_fine 128×32×6 / G4 8层 / G5 10层 / G6 12层
- 网格收敛验证: 均匀温度/压力工况已收敛 (<1%); 梯度塑性未收敛 (STEP 11)

## 15. STEP 9 热-力耦合验证结果
- 热传导: TH-01/TH-02 稳态 gradT=200°C 精确, HFL≈1100 W/m² ✅
- 热膨胀: 均匀温度 vm=0, U∝αΔT·R ✅
- 热应力: GRAD_750_550 内壁 750°C 局部塑性 (vm=199=σy); GRAD_550_750 弹性拉伸 ✅
- 压力: vm=5.01·P 线性 ✅
- 敏感性: k 只影响热流, CTE 驱动位移 (±5%), Cp/rho 稳态无影响 ✅
- 报告: docs/STEP9_thermal_mechanical_validation.md

## 16. STEP 10 数据集结果
- 222 case 全部求解 OK (9 benchmark + 174 LHS + 39 creep)
- 生成器: generate_cases.py (参数化, 修复梯度温度每行单节点 bug)
- 梯度塑性 49 case 标记 mesh-not-converged
- 报告: docs/STEP10_data_generation_report.md

## 17. STEP 11 数据集结果
- G1-G6 网格系列 (3-12 壁厚层): PEEQ 5.7e-4→1.89e-3 单调增
- 塑性区体积未收敛 (±24%), 塑性厚度恒 1.00 (全壁厚塑性)
- 塑性位置稳定 (θ≈0-15, φ≈5-7, 内壁高温侧)
- 结论: gradient_plastic_highly_mesh_sensitive=YES
- 报告: docs/STEP11_report.md, validation/STEP11_gradient_convergence.md

## 18. 当前总 case 数量
**222**

## 19. valid_for_AI 数量
**150** (A=80 + B=70)

## 20. physics_reference 数量
**72** (D=49 网格敏感 + E=23 缺 σy)

## 21. DATA_REQUIRED 数量
**23** (550/600°C σy 缺失)

## 22. mesh-sensitive 数量
**49** (梯度塑性, STEP 11 确认)

## 23. 当前 train/validation/test 文件
```
data/ai_ready/train.csv        (73)
data/ai_ready/validation.csv   (23)
data/ai_ready/test.csv         (54)
```
划分按参数空间外推 (STEP 11.13): test 组合 (Rm=150, T=750, P≥30, t=1000h) 与 train 0 重叠

## 24. 当前 simulation_dataset.csv
```
data/ai_ready/simulation_dataset.csv  (222 行 × 33 列)
```
含输入/材料/输出/质量字段, 见 docs/AI_DATA_DICTIONARY.md

## 25. 所有主要脚本路径
```
abaqus/scripts/build_geometry.py     # 几何+INP 生成
abaqus/scripts/build_thermal.py      # 热-力耦合 INP 生成
abaqus/scripts/generate_cases.py     # 参数化批量生成 (STEP 10)
abaqus/scripts/build_material_db.py  # 材料库构建
abaqus/scripts/rebuild_models.py     # 双模型重建
abaqus/scripts/run_batch.py          # 批量求解
abaqus/scripts/run_missing.py        # 补跑缺失
abaqus/scripts/mesh_convergence_grad.py  # 梯度网格收敛
abaqus/scripts/step11_convergence.py     # STEP 11 收敛
abaqus/scripts/sensitivity_thermal.py    # 热物性敏感性
postprocess/postprocess.py           # ODB 提取
postprocess/extract_step9.py         # STEP 9 提取
postprocess/build_sim_dataset.py     # AI 数据接口
postprocess/build_ai_ready.py        # AI 数据集组装 (v1)
postprocess/rebuild_ai_ready.py      # AI 数据集重建 (STEP 11 分级)
postprocess/coverage_split.py        # train/val/test 划分
validation/pre_run_check.py          # 运行前检查
validation/sym_bc_rank.py            # 对称 BC 秩验证
validation/expansion_bc_analysis.py  # 膨胀相容 BC 分析
```

## 26. 下一步目标: STEP 12A
数据增强 (case_matrix_v2.yaml + generate_cases_v2.py), 目标 total≈500, valid_for_AI≈400。
规则: 新增 ~280 case (中温 575/625/675/725、低压 1-8、中间几何、ΔT 25/75/125/175、蠕变扩展),
全部真实 Abaqus 求解, 禁止编造数据/σy/700-750°C 蠕变, 保留旧数据。

## 27. STEP 12A 目标
- 总 case ≈ 500
- valid_for_AI ≈ 400 (达到 380 即停)
- physics_reference ≈ 50-100
- 生成 v2 全套文件 (full_simulation_database_v2.csv 等)

---

## 快照后状态
此文档生成后未运行 Abaqus、未修改任何模型/材料/数据/脚本。
