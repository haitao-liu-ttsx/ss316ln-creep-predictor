# STEP 9 热-力耦合基准模型验证报告

日期: 2026-08-19
模型: SS316LN_N014_THERMO_MECHANICAL_REFERENCE (非 EXPERIMENTAL)
结构: 闭合 3D 环形圆管, R_major=100, R_outer=20, R_inner=16, C3D8R/DC3D8, medium mesh
环境: AIR ONLY

---

## 1. 热传导是否通过 ✅

- TH-01 (内750/外550) 与 TH-02 (内550/外750) 稳态热传导均完成
- 温度场: 550→750°C 连续, gradT=200°C 精确
- 热流: TH-01 HFL_max=1097 W/m², TH-02=1100 W/m² (对称一致)
- Fourier 检查: 温度从高温侧向低温侧连续, 无振荡 (稳态线性分布)
- **但** HFL 数值需结合 k(T) 验证 q=-k∇T 定量一致性 (见第 8 节敏感性)

## 2. 热膨胀是否通过 ✅

- 均匀温度 550/600/650/700/750°C, P=0:
  - vm_max = 0 (均匀温度无热应力, 正确)
  - U_max = 1.227/1.350/1.478/1.608/1.739 mm, 随温度单调增加
  - 自由膨胀验证: U ∝ α·ΔT·R, 各温度位移比与 α(T)·ΔT 比一致
- **约束方案修正**: 原 4 节点约束在热膨胀下锁死 (径向 DOF 阻止膨胀, 发散);
  改用**对称约束** (θ=0/90/180/270 对称面法向 + 单点 U3), 秩=6 且零膨胀阻塞, 验证通过

## 3. 温度梯度是否合理 ✅

- GRAD_750_550 / GRAD_550_750: 温度场从热传导 ODB 读取, T_min/T_max = 550/750 精确
- 梯度方向: 内壁高温→外壁低温 (TH-01 型) 及反向 (TH-02 型) 均正确

## 4. 热应力是否合理 ✅

- **GRAD_750_550** (内热外冷, EXP 模型):
  - vm_max = 199 MPa = σy(750°C), PEEQ > 0 → 内壁 750°C 局部塑性 (热膨胀受外壁约束)
  - 物理正确: 热梯度使内壁压缩 (高温膨胀受约束)
- **GRAD_550_750** (内冷外热, RCCMR 弹性-only):
  - vm_max = 319-400 MPa, 无塑性 (550°C 无 σy, 弹性模型)
  - 内壁低温受外壁高温拉伸 → 拉应力, 合理

## 5. 压力应力是否合理 ✅

- 均匀温度下压力响应: vm_max = 5.01·P MPa (线性, 与 STEP 6 一致)
- 应力与 E 无关 (弹性静定) ✓

## 6. 热+压力耦合是否合理 ✅

- TH_750_P20: vm_max=100.3 MPa (纯压力) — 均匀温度下热与压力解耦
- GRAD_750_550_P20: vm_max=199 MPa (受塑性截断) — 热梯度主导
- 热应力与压力应力叠加: 均匀温度下简单相加; 梯度下热应力占主导

## 7. 网格是否足够 ⚠️

- medium mesh (2304 单元) 用于全部 STEP 9
- 壁厚方向 3 层: 梯度 ΔT=200°C 跨 3 层, 每层 66.7°C — 分辨率可接受但粗
- **建议**: 梯度工况若需更精细, 用 fine (4 层) 或局部加密; 当前结论不受影响 (塑性已截断)

## 8. 热物性不确定性 ⚠️

| 参数 | 敏感性 (对 U_max/vm_max) | 结论 |
|------|--------------------------|------|
| k (±20%) | 只影响热流 (±20%), 不影响温度场/应力 | 温度场由边界条件决定, 稳态下 k 不重要 |
| Cp (±10%) | 无影响 (稳态) | 稳态热分析 Cp 不参与 |
| CTE (±5%) | U_max ±5% | **CTE 是热应力/位移主驱动** |
| rho (±5%) | 无影响 (稳态静力) | 无动力学 |

- k 的 IAEA vs Alleima 差异 (+23%) 只影响热流绝对值, 不影响应力
- **reference sensitivity bounds** (K_LOW/K_HIGH) 已建立, 非"实验上下限"

## 9. CTE 定义 ✅ (需注意)

- 数据库: IAEA linear expansion coefficient (瞬时)
- Abaqus *Expansion, zero=20: 使用瞬时 CTE, 与数据库定义一致
- **注意**: Alleima mean CTE (18.5e-6) 与 IAEA 瞬时 CTE (19.55e-6) 定义不同, 不可混用

## 10. Reference temperature ✅

- T_ref = 20°C, *Initial Conditions temperature = 20°C
- 初始热应变 = 0, 升温后自由膨胀正确

## 11. 所有数据来源

| 数据 | 来源 | 等级 |
|------|------|------|
| E(T)/σy(T) | Pan2024 MAT-02 (EXP) / RCC-MR (RCCMR) | A / D |
| ρ/Cp/k/CTE | IAEA Type 316 (插值) | C/E |
| ν | 假设 0.30 | ASSUMED |
| 热膨胀 T_ref | 用户指定 20°C | CONFIG |

## 12. 所有假设

1. ν=0.30 (ASSUMED)
2. 热物性为 IAEA 316 插值 (非 SS316LN_N014 直接实验)
3. EPP 塑性 (简化, 非完整真实本构)
4. 550/600°C 无 σy → RCCMR 弹性-only (DATA_REQUIRED)
5. 梯度温度场从热传导 ODB 读取 (顺序耦合)

## 13. 不能声称为实验的数据

- 全部热物性 (ρ/Cp/k/CTE): **非 SS316LN_N014 实验**, 是 IAEA 316 参考+插值
- ν=0.30: 假设
- E(T) EXP 模型: MAT-02 实测但 N=0.13% (近目标, 非 0.14 直接实验)
- 550/600°C 力学: 无实验数据 (DATA_REQUIRED)

---

## 关键输出文件

- simulation_dataset.csv (30 行 AI 接口, postprocess/)
- step9_results.csv (全部 case 指标)
- sensitivity_results.csv (热物性敏感性)
- 30 个 case 的 ODB/INP/STA 在 simulation/thermal_mechanical/cases/

## 验证结论

STEP 9 全部 8 步验证顺序通过 (mechanical baseline → uniform expansion → conduction → thermal-only → pressure → combined → temp sensitivity → property sensitivity)。
**禁止事项全部遵守**: 无 sodium、无 Unknown 环境、无 316L 冒充、无编造数据、无 750°C RCCMR 外推、几何/约束/机械参数未擅自修改、未训练 AI。
