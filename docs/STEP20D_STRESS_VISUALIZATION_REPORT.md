# STEP20-D 应力分量提取、坐标转换与三维可视化报告

日期: 2026-08-21 ｜ 状态: **STEP20-D = COMPLETE**（全部核心验收条件通过）

## 1. STEP20-D 目的

利用 STEP20-C 已冻结的 123 个成功 Abaqus 结果，将全局笛卡尔应力张量（S=2304×6）转换为环形管局部圆柱坐标应力分量（Srr/Sθθ/Szz/Srθ/Srz/Sθz），完成数学验证并建立三维可视化原型。未重新运行任何 Abaqus case。

## 2. STEP20-C 数据来源

- 128 设计 case：123 成功 + 5 个 EXT 域外收敛失败（保留原始文件，未伪造数据）
- 冻结参数：700°C C=2.92e-22/n=6.97；750°C C=2.78e-18/n=5.56（s⁻¹/MPaⁿ）
- 分层：TRAIN=64 / VAL=16 / EXT=43 成功 + 5 失败（组级防泄漏，QA PASS）
- 输入数据：`simulation/step20c/fields/*.npz`（centroids + S + CEEQ）

## 3. 现有 S=2304×6 的真实含义（D.1/D.2 审计）

- 六个分量 = **S11, S22, S33, S12, S13, S23 = 全局笛卡尔 (Sxx, Syy, Szz, Sxy, Sxz, Syz)**
- 来源：`extract_fields.py` 直接读取 Abaqus `fieldOutputs["S"].values` → `v.data`（无任何转换）
- 位置：积分点值（C3D8R 减缩积分单 IP = 单元质心），**无节点平均、无外推**
- 2304 点坐标：`centroids`（每 case 独立保存，确定性 torus 网格顺序一致）
- 数值抽查：S11/S22 均值相等（环向对称载荷）、S12/S13/S23 均值≈0（物理合理）；centroids 与几何吻合（外层半径 = Rm+Ri）

## 4. 坐标系定义（D.3）

- torus 环轴线 = 全局 **Z 轴**；环向角 **θ = atan2(y, x)**（XY 平面内）
- 局部基（逐质心）：**er = (cosθ, sinθ, 0)**（径向向外）、**eθ = (-sinθ, cosθ, 0)**（环向切向）、**ez = (0, 0, 1)**（轴向）
- 依据：inp 无 `*ORIENTATION`；节点坐标首圈位于 XY 平面（z=0）；与 STEP19 应力坐标审计一致

## 5. Cartesian → 局部圆柱坐标转换方法（D.4）

对每个质心：构造 Q = [er, eθ, ez]（列向量），计算 **S_local = Qᵀ S Q**，取分量：

| 局部分量 | 定义 | 文件字段名 |
|---|---|---|
| 径向应力 Srr | S_local[0,0] | Srr |
| 环向应力 Sθθ | S_local[1,1] | Stt |
| 轴向应力 Szz | S_local[2,2] | Szz |
| 面内剪应力 Srθ | S_local[0,1] | Srt |
| 剪应力 Srz | S_local[0,2] | Srz |
| 剪应力 Sθz | S_local[1,2] | Stz |

**明确说明**：绝非“改名字”式转换（S11→Srr 等）；转换基于实际几何坐标的逐质心旋转。

## 6-7. 应力输出与量级抽查

| case | Srr_max | Stt_max | Szz_max | Srt_max | Srz_max | Stz_max | vm_max |
|---|---|---|---|---|---|---|---|
| 700°C P30 t300h（参考 145.6） | 116.4 | 116.5 | 137.2 | 38.4 | 73.7 | 73.7 | **145.57** |
| 750°C P12 t300h（参考 59.95） | 47.5 | 47.5 | 56.8 | 15.6 | 30.2 | 30.2 | **59.95** |

物理合理性：薄壁环形压力容器轴向应力（Szz）最大、环向次之、径向最小；von Mises 与 STEP20-C smoke 参考逐位一致。123 case 全域 vm_max = 37.8–206.9 MPa，CEEQ_max = 1.7e-7–1.3e-2。

## 8. 数学 QA（D.5/D.7，机器精度）

| 检查项 | 最差值（123 case） | 结果 |
|---|---|---|
| 应力张量对称性（Srθ=Sθr 等） | 4.3e-14 | **PASS** |
| 应力迹保持（trace 不变） | 8.5e-14 | **PASS** |
| von Mises 转换前后一致 | 4.3e-16（相对） | **PASS** |

## 9. 数据覆盖与完整性

- 成功 case = **123/123**（全部转换完成，`simulation/step20d/fields/*.npz`）
- 空间点 = **2304/2304**（每 case：centroids(2304,3) + Srr/Stt/Szz/Srt/Srz/Stz/CEEQ/von_mises 各 (2304,) + 原始 Sxx..Syz）
- 空间点顺序：与 STEP20-C 完全一致（确定性 torus 网格，未重排）
- 5 个失败 case：保留 .inp/.msg/.dat/.sta，**未制造任何伪应力数据**（仅 provenance 记录）

## 10. 三维可视化（D.8/D.9）

- 文件：`simulation/step20d/visualization/viz.html`（双击 file:// 直接打开，Three.js CDN）
- 功能：8 个代表案例（700/750°C × 4 应力档，全场数据内嵌）+ 全部 123 case 元数据；8 个物理场切换；绝对/相对色标；应力 diverging（蓝-白-红）、CEEQ 彩色映射；显示 case/T/P/t/几何/分层/场范围/单位
- 三维真实性：真实 x/y/z 质心坐标（非投影散点），拖拽/缩放/平移
- QA：puppeteer 实测页面加载、8 case/8 场切换、信息栏更新、**0 JS 错误**
- 未修改生产 WebApp（独立原型，后续步骤再决定接入）

## 11. 失败 EXT case 处理

5 个 case（全部 EXT 域外，P·Ro/w 195–250 > 700°C 拟合上限 170）：status=FAILED，failure_reason=CONVERGENCE（塑性 σy=212 + 蠕变耦合无法收敛）。保留原始求解文件，禁止伪造/插值/复制邻近数据。

## 12. 数据完整性声明

318 DATASET = UNCHANGED ｜ V1.2 = UNCHANGED ｜ STEP20-C = UNCHANGED ｜ V1.3 TRAINING = NOT STARTED ｜ LOCKED = UNTOUCHED ｜ WebApp = UNCHANGED ｜ 700/750°C 材料参数 = UNCHANGED ｜ case_matrix = UNCHANGED

## 13. 新增文件清单

- `simulation/step20d/fields/*.npz`（123 个转换后场数据）
- `simulation/step20d/field_stats.csv`（123 case × 14 统计列）
- `simulation/step20d/manifest.csv`（123 OK + 5 FAILED 全记录）
- `simulation/step20d/visualization/viz.html` + `data.js`（三维可视化）
- `ml/metrics/step20d_stress_visualization.json`（机器可读 QA）
- 转换脚本：`postprocess/step20d_convert.py`、`step20d_viz_build.py`、`step20d_finalize.py`

## 14. 存在的问题（如实）

- 5 个 EXT 域外 case 因塑性+蠕变不收敛无场数据（物理边界，非缺陷）
- 可视化原型内嵌 8 个代表 case 全场；其余 115 个 case 的全场数据在 npz 中，后续接入 WebApp 时可全量加载
- 三维可视化默认显示未变形几何（按 §21 要求，未做变形夸大）