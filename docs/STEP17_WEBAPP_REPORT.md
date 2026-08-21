# STEP 17 Web App 交付报告

日期: 2026-08-20
状态: **STEP17_WEBAPP = COMPLETE — Web App 可运行；模型未改、LOCKED 未读**
目录: `webapp/`（frontend/ + backend/ + tests/ + demo_cases.json + README + WEBAPP_MANIFEST.json）

## 1. Architecture

- **Backend**：Flask（127.0.0.1:5000），`POST /api/predict` / `GET /api/health`；仅加载 `ml/production/step15_v1_2/model/`（冻结 v1.2，唯一模型来源）
- **Frontend**：React 18 + TypeScript + Vite + Three.js（node 24 构建成功，`npm run build` → dist/）；开发模式 `/api` 代理到 5000

## 2. Model integration

前端不包含任何模型数学逻辑；全部推理经 backend → production `predict_field()`。**Web API 输出与 production API 输出逐元素完全一致（max_abs_diff = 0.0）**——一致性测试 12/12 PASS。

## 3. API

`/api/predict {T,P,t,Rm,Ro,w}` → `{valid, field[2304], max/mean/p95_ceeq, hotspot_element/xyz/value, pod_coefficients, physics_status, stress_scale}`；OOD → `{valid:false, status:'OUT_OF_DOMAIN', violations:[...]}`（含 700/750°C DATA_REQUIRED 说明）。

## 4. 3D rendering

Three.js 点云渲染：确定性 torus mesh（48×16×3 参数化，与 production mapping 同序）；log10(CEEQ) 色标（HSL 映射）+ linear 切换；红色球体标记 ★Hotspot；θ-φ-r 规范结构与 3D 旋转视图。

## 5–6. Domain / Physics guard

- Domain guard **直接复用 production `validate_input`**（前端不做独立边界定义）；越界实时显示 OUT OF DOMAIN + 越界参数与允许范围；NaN/Inf/负输入被守卫（runtime 已增强非有限输入检查——模型逻辑零修改，仅输入校验）
- Physics guard：CEEQ≥0、finite 检查，`physics_status` PASS/WARNING（预测结果从不修改）

## 7. Deterministic test

`test_api_consistency.py`：12/12 PASS（5 有效域 case 逐元素 diff=0 + 4 OOD + NaN/负输入 + 重复推理确定性）；live 服务器实测 health/predict/OOD 均 200。

## 8. Demo cases

4 例（基准 300h / Rm150 3000h / 非基准高应力 3000h / OOD T=700°C）——点击即加载并运行。

## 9. Performance

单次 inference ≈ 数十 ms（Ridge-Poly2 解析预测），远超 <1s 目标；未做任何性能性模型改动。

## 10. Final status

STEP17_WEBAPP = **COMPLETE** ｜ MODEL = V1.2 FROZEN ｜ API = PRODUCTION ｜ 3D FIELD = WORKING ｜ DOMAIN GUARD = PASS ｜ PHYSICS GUARD = PASS ｜ DETERMINISTIC = PASS ｜ DEMO CASES = PASS ｜ **LOCKED TEST = NEVER READ** ｜ **318 DATASET = UNCHANGED** ｜ **FINAL STATUS = WEB APP READY**

---
*启动方式详见 `webapp/README.md`；未进入 STEP18，等待人工检查网页。*
