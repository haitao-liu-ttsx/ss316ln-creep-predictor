# SS316LN 环状结构三维时空蠕变场 AI 快速预测 Web App

中文科研演示界面：POD + Polynomial Surrogate · 2304-element CEEQ Field。
模型来源：`ml/production/step15_v1_2/`（**唯一冻结模型**，Web App 不包含任何模型逻辑）。

## 安装与启动

### 1. 后端（Flask）

```
ml\.venv\Scripts\python.exe -m pip install flask flask-cors   # 首次
cd webapp\backend
ml\.venv\Scripts\python.exe app.py                             # http://127.0.0.1:5000
```

### 2. 前端（React + TS + Vite + Three.js）

```
cd webapp\frontend
npm install
npm run dev     # 开发模式：http://localhost:5173（/api 代理到 5000）
npm run build   # 生产构建 -> dist/
```

### 3. Demo

页面提供 4 个演示案例（`webapp/demo_cases.json`）：基准几何 / Rm150 3000h / 非基准高应力 3000h / OOD（T=700°C）。点击 Example Cases 下拉即加载参数并运行；也支持 URL 直达 `?demo=1..4`（如 `http://localhost:5173/?demo=4` 演示 OOD 面板）。截图：`docs/figures/webapp/`。

## API

- `POST /api/predict`：`{T,P,t,Rm,Ro,w}` → `{valid, field[2304], max/mean/p95_ceeq, hotspot_element/xyz/value, pod_coefficients, physics_status, stress_scale}`；OOD → `{valid:false, status:'OUT_OF_DOMAIN', violations:[...]}`
- `GET /api/health`：模型状态

## 模型有效域 / OOD

有效域：T 550–650°C ｜ P 2.5–30 MPa ｜ t 1–3000 h ｜ Rm 80–150 / Ro 15–25 / w 2–5 mm ｜ P·Ro/w ≤ 250 MPa。
禁止预测：700/750°C（DATA_REQUIRED，Norton 参数缺失）、t>3000h、P>30MPa、P·Ro/w>250 —— 返回 OUT_OF_DOMAIN 并指明越界参数。超出有效域必须回退 Abaqus 验证。

## 测试

```
cd webapp\tests
ml\.venv\Scripts\python.exe test_api_consistency.py   # 12/12 PASS；web==production max_abs_diff=0
```

## 项目结构

```
webapp/
├── frontend/   (React+TS+Vite+Three.js, dist/)
├── backend/    (app.py Flask API)
├── tests/      (一致性/域守卫/物理/确定性)
├── demo_cases.json
├── WEBAPP_MANIFEST.json
└── README.md
```

## 数据保护

LOCKED TEST 从未读取；318 dataset 与 STEP15-v1.2 冻结模型未修改；Web App 仅调用 production API。
