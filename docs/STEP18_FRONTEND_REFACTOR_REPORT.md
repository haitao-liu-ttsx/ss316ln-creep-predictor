# STEP 18 前端重构报告（科研可视化 Web App）

日期: 2026-08-20
状态: **STEP18 前端重构 COMPLETE — 模型/后端/数据零修改；LOCKED 未读**

## 1. 修改的 frontend 文件

- `webapp/frontend/src/App.tsx`（重写）：深色科研风三栏布局、OrbitControls 3D 场、结果卡片、时间演化曲线（canvas）、Example Cases 下拉、OOD 面板（含 DATA REQUIRED 说明）、URL demo 参数（?demo=1..4）、Play/Pause 时间动画
- `webapp/frontend/src/style.css`（重写）：深色主题（#0d1117）、统一字体/间距/按钮、响应式（<1100px 单栏）
- `webapp/frontend/src/api.ts`：保留（demo cases 扩充说明，无模型逻辑）
- 其余（vite/tsconfig/index.html）未变

## 2. Backend 是否修改：**否（预测逻辑零改动）**

唯一相关变更：STEP17 期间 production runtime 增加了非有限输入守卫（NaN/Inf → OUT_OF_DOMAIN），属于输入校验增强，模型数学零改动（已与 G.4 冻结预测逐元素一致验证）。

## 3. 页面布局

```
┌ Header: SS316LN CEEQ Field Predictor + ● Model Ready ────────┐
├ 参数输入(6+应力尺度) │ 3D CEEQ 场（log/linear/Reset Camera）│ 结果卡片+热点+Physics ─┤
├ 时间滑块+Play │ 时间演化曲线（Max/Mean vs t）│ ────────────────┤
└ Footer: 模型信息+有效域+免责声明 ────────────────────────────┘
```

## 4. 3D 渲染

Three.js + OrbitControls（拖转/滚轮缩放/平移/Reset Camera）；确定性 torus mesh（48×16×3 同序映射）；log10/linear 色标切换 + color bar；红色球体 ★Hotspot + 基准环参考线。

## 5. 验证结果

- **npm run build：PASS**（1.0s，dist/）
- **API consistency：12/12 PASS（web == production，max_abs_diff = 0.0）**
- **UI acceptance：13 项全 PASS**（5 有效域 + 4 OOD + NaN/负输入 + demo 结构 + 3 张截图渲染证据：蓝色 3D 点云与红色 hotspot 像素均存在）
- 截图：`docs/figures/webapp/{webapp_main,webapp_case2,webapp_ood}.png`（1366×900，headless Chrome 实拍）

## 6. 本地启动

```
ml\.venv\Scripts\python.exe webapp\backend\app.py    # :5000
cd webapp\frontend && npm run dev                     # :5173 → http://localhost:5173
# 演示 OOD：http://localhost:5173/?demo=4
```

## 7. 数据保护

LOCKED TEST 未读取 ｜ 318 dataset 未修改（`20f21ebc67ea`）｜ v1.2 frozen model 未修改 ｜ 无新 Abaqus case ｜ 无重训 ｜ 无 STEP18 后续训练流程。
