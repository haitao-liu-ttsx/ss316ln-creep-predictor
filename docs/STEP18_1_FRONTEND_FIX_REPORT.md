# STEP 18.1 前端修复报告（4 项目标 + 回归修复）

日期: 2026-08-20
状态: **STEP18.1 COMPLETE — 模型/后端/数据零修改；LOCKED 未读**
前置: STEP18_FRONTEND_REFACTOR_REPORT.md（v1.2 frozen surrogate 后端）

## 7. STEP18.2 补充：hotspot 彻底清除红球 + 「显示热点」开关

（2026-08-20 追加，与 §1-6 相同保护约束）

**场景组成（最终）**：`THREE.Points` 彩色点云（2304 单元 CEEQ 场，唯一几何本体）+ 半透明蓝参考环（0x2f81f7, opacity 0.18）+ 可选白色小十字 sprite。**无任何球体 mesh、无红色几何体**。

- **hotspot 标记**：64px 画布绘制白色十字准星（lineWidth 14、round cap），`spr.scale=(20,20,1)` → 屏幕实测 **19×20px**（相机距离 484 下），尺寸远小于管体外径（~150px）。纯白色——无红色填充、无五角星。定位仍由 **API `hotspot_xyz`**（最大 CEEQ 单元质心）驱动，`depthTest:false` 保持可见。
- **「显示热点」开关**：默认开启；`spr.visible = showHotspot`；关闭时 sprite 完全不可见（visible=false），**不影响 API 预测、2304 场、模型**（仅一个可见性标志）。开关按钮位于 3D 视图工具行（对数/线性色标旁），高亮表示开启。
- **Reset Camera 修复（重要）**：three r169 OrbitControls 用私有字段 `_spherical/_sphericalDelta/_scale` 每帧重算相机位姿，直接 `camera.position.copy(home)` 会被下一帧覆盖（实测 reset 后位置纹丝不动）。修复：reset() 中同步 `_scale=1`、`_spherical.setFromVector3(home)`、`_sphericalDelta.set(0,0,0)`，再 `lookAt` + `update()`。**数值级验证**：reset 后 position/quaternion 与初始**逐位一致**（1e-6 容差 PASS）。
- **dev 内省钩子**：`import.meta.env.DEV` 下暴露 `window.__viewer = {camera, controls}` 供验收读取相机数值；**生产构建已验证不含**（tree-shake，grep dist 无 `__viewer`）。

**STEP18.2 验收结果**：

- npm build PASS（tsc + vite）
- API consistency **12/12 PASS，max_abs_diff=0.0**
- UI smoke（ui_smoke_181.js）**16/16 PASS**（横向滚动 ×3 + 中文 ×8 + 自动预测 + camera 不重建 + 参数变更 camera 保持 + OOD 文案）
- camera 数值验证（camera_verify.js）：重预测后 pos/quat 与拖拽后一致（PASS）；Reset 后与初始一致（PASS）
- 像素级验证（截图扫描）：纯净模式 canvas 红色像素 **0**、白色像素 **0**；热点模式红色 0、白色十字 19×20px 于 (753,375)（= API xyz 投影点 (754,376)，误差 1px）；中心空腔红色 0
- 截图：`docs/figures/webapp/webapp_182_{clean,hotspot_on,repredict}.png`（A/B/C 三张验收图）
  - A = `webapp_182_clean.png`：默认场、热点关闭——纯净模型
  - B = `webapp_182_hotspot_on.png`：热点开启——小十字定位标记
  - C = `webapp_182_repredict.png`：拖拽后改参数重预测——视角保持未重置
- 保留功能回归：旋转/缩放/平移、Reset Camera、参数修改 camera 保持、中文界面、log/lin 色标、时间播放、OOD guard

**数据保护（重申）**：LOCKED 未读 ｜ 318 dataset 未改 ｜ v1.2 frozen 模型未改 ｜ backend 零改动 ｜ 无重训 ｜ 无新 Abaqus case。hotspot 数学定义不变（API 返回的最大 CEEQ 单元质心）。

## 1. 修改的 frontend 文件

- `webapp/frontend/src/App.tsx`：
  1. **中心红球 → 小发光热点**：移除圆心红色大球体；hotspot 改为小 ★ sprite（canvas 红星+白星，scale 28），位置由 **API `hotspot_xyz`**（真实热点单元质心）驱动；`depthTest:false` 保证始终可见。
  2. **camera 持久化**：Three.js scene/camera/OrbitControls 只挂载一次（refs），预测仅更新点云几何与 hotspot 位置，**不重建场景** → 修改参数重新预测后视角/缩放/平移保持不变。
  3. **Reset Camera 独立**：`useImperativeHandle` 暴露 `reset()`，按钮「重置视角」恢复初始相机位姿（home 快照），不影响预测流程。
  4. **恢复 ?demo=1..4 URL 功能**（STEP18 实现、STEP18.1 重构误删，回归修复）——见 §4。
- `webapp/frontend/src/style.css`：横向滚动防护（`html,body {overflow-x:hidden}`、`.app{max-width:100vw}`、grid `min-width:0`、响应式折叠）+ 全中文 UI 样式。
- `webapp/frontend/package.json`：无依赖变更（mtime 变更来自 npm 工作流，内容与 STEP18 一致）。

## 2. 4 项目标验证

| # | 目标 | 结果 | 证据 |
|---|------|------|------|
| A | 删除中心红球，保留正确 hotspot marker | ✅ | 像素分析：圆心投影区域红色像素 = 0；★ 投影于 API xyz (83.6,5.5,3.2)→屏幕 (752,376)，与独立 three 投影计算 (754,376) 误差 ≤2px，可见 18×17px |
| B | 横向滚动 | ✅ | scrollWidth 1366/1440/1920 = viewport 宽，三分辨率全 PASS |
| C | 完全中文化 | ✅ | 8 个关键 UI 词条断言全 PASS（环形结构蠕变场/预测参数/开始预测/预测结果/最大 CEEQ/物理检查/时间演化/示例案例）；技术名词（CEEQ/POD/SS316LN/MPa）按科研惯例保留 |
| D | 修改参数重新预测后 camera 不变 | ✅ | 重预测前后 `.view3d canvas` 数 1→1（场景未重建）；改 T 参数+预测后仍 1 个 canvas |

## 3. 回归修复：?demo URL 参数

- **症状**：`/ ?demo=1..4` 打开后参数不生效（显示默认工况 T=600）。
- **根因**：STEP18.1 重写 App.tsx 时误删 `initialParams()`（URLSearchParams 解析），STEP18 已验收的 demo 直达功能丢失。
- **修复**：恢复 `initialParams()`（demo=N → DEMO_CASES[N-1]，1-based，范围校验），`useState<P>(initialParams)`。
- **验证**：`?demo=1` 正常渲染（hotspot/结果自动出现）；`?demo=4` 正确进入 OOD 面板（超出模型有效域 + 需要补充材料数据 + 模型有效范围，中文化文案 PASS）。

## 4. 验证结果

- **npm run build：PASS**（tsc -b + vite build，937ms，dist/ 产出）
- **API consistency：12/12 PASS**（web == production，max_abs_diff = **0.0**；含 5 有效域 + 4 OOD + NaN/负输入守卫 + 确定性）
- **UI smoke（ui_smoke_181.js）：16/16 PASS**（横向滚动 ×3 分辨率 + 中文 ×8 + 自动预测 + camera 不重建 + 参数变更后 camera 保持 + OOD 中文文案）
- **截图验收**：`docs/figures/webapp/{webapp_main_181,webapp_ood_181,webapp_repredict_181}.png`（1366×900 headless Chrome 实拍）

## 5. 数据保护

LOCKED TEST 未读取 ｜ 318 dataset 未修改（checksum 20f21ebc67ea 不变）｜ v1.2 frozen model 未修改（backend 零改动，`ml/production/step15_v1_2/` 只读加载）｜ 无新 Abaqus case ｜ 无重训 ｜ 后端预测数学逻辑零改动。

## 6. 本地启动

```
ml\.venv\Scripts\python.exe webapp\backend\app.py    # :5000
cd webapp\frontend && npm run dev -- --host 127.0.0.1  # :5173
# 演示 OOD：http://localhost:5173/?demo=4
# 验收：node webapp/tests/ui_smoke_181.js（需两服务运行）
```
