# STEP23 公网部署指南（316LN 三维高温蠕变场预测器）

日期: 2026-08-21 | 状态: 部署包已就绪，本地生产模式已验证

## 〇、关于"挂靠 deepseek / chatgpt 模型"的说明

本 Demo 的部署**与 LLM 无关**——它是纯 Python(Flask) + 前端(React/Three.js) 的常规 Web 应用，模型是本地 sklearn 代理模型（7 个 joblib 文件，共约 1 MB）。Norton 参考站点使用的 `.chatgpt.site` 域名只是其托管服务商的子域，并非"用 ChatGPT 运行"。

**任何能运行 Python 的云平台都可部署**，推荐顺序：
1. **Render.com（免费层，最省事）**——仓库推送后自动构建
2. **PythonAnywhere（免费层）**——无需 GitHub，网页上传
3. **国内云服务器**（阿里云/腾讯云轻量，需备案）——国内访问最快

## 一、部署架构（单服务，已验证）

```
浏览器 → Render/PythonAnywhere 的 Web 服务（单端口）
              ├─ Flask 静态服务 → 前端 dist/（React 页面）
              └─ Flask API → /api/predict_v13（V1.3 七场）与 /api/predict（V1.2）
```

- 前端已构建进 `webapp/frontend/dist/`（含 8 场 3D 可视化）
- 模型文件在 `ml/v13/models/`（7 个 joblib）+ `ml/v13/global_ranges.json` + `predictor.py` + `domain_guard.py`
- 后端依赖：`webapp/backend/requirements.txt`
- 部署配置：`render.yaml`（Render 专用）

## 二、方案 A：Render.com（推荐，免费层够用）

1. 注册 GitHub → 新建私有仓库 → 推送本项目（**注意**：排除大文件——可选 `.gitignore` 添加 `ml/.venv/`、`simulation/`、`webapp/frontend/node_modules/`、`data/`；**必须保留**：`webapp/backend/`、`ml/v13/`、`ml/production/step15_v1_2/runtime/predict_field.py`、`webapp/frontend/`）
2. 注册 render.com（GitHub 登录）→ New → **Blueprint** → 选择仓库
3. Render 读取 `render.yaml` 自动构建：
   - buildCommand：装前端依赖 + build + 装后端依赖
   - startCommand：`gunicorn --chdir webapp/backend app:app -b 0.0.0.0:$PORT --workers 1 --timeout 120`
4. 部署完成后 Render 给 `https://<name>.onrender.com` 公网地址——**其他电脑直接打开即可**
5. 免费层注意：冷启动约 1 分钟（首次访问慢）；每月 750 小时免费额度足够

## 三、方案 B：PythonAnywhere（免费层，无需 GitHub）

1. 注册 pythonanywhere.com → Web → Add new web app → Flask
2. 上传代码（Files 页面上传 zip 后解压，或用 GitHub 导入）
3. Web 配置：Source 目录指向 `webapp/backend/`，WSGI 文件改为：
   ```python
   import sys, os
   sys.path.insert(0, '/home/<用户名>/<路径>/webapp/backend')
   from app import app as application
   ```
4. 虚拟环境安装 requirements.txt（Bash 控制台）
5. 免费层域名：`<用户名>.pythonanywhere.com`——公网可访问
6. **注意**：PythonAnywhere 免费层不支持 npm build → 需在本地 build 后把 `dist/` 一起上传（dist 已在仓库/本地）

## 四、方案 C：国内云服务器

1. 购买轻量服务器（阿里云/腾讯云，2C2G 足够）→ 安装 Python 3.10+ 与 Node 18+
2. 上传代码 → `cd webapp/frontend && npm install && npm run build`
3. `pip install -r webapp/backend/requirements.txt`
4. 启动：`gunicorn --chdir webapp/backend app:app -b 0.0.0.0:5000 --workers 1 --timeout 120`
5. 安全组放行 5000 端口（或 Nginx 反代 80）→ 公网 IP 直接访问
6. 使用域名需备案（中国大陆）

## 五、部署后验证清单

- [ ] 打开公网地址 → 页面加载（316LN 三维高温蠕变场预测器）
- [ ] 默认 V1.2 模式正常（CEEQ 场）
- [ ] 切到 [V1.3 多物理场] → 域状态"安全域"、4 张摘要卡、3D 环形显示
- [ ] 8 个场切换正常（Srr/Sθθ/Szz/Srθ/Srz/Sθz/CEEQ/von Mises）
- [ ] 改温度（550-750 五档）→ 颜色变化；放映按钮 → 时间演化动画
- [ ] 改 T=700/P=20/t=100/Rm=120/Ro=25/w=3 → 域警告显示
- [ ] 其他电脑（不同网络）打开同一链接可正常使用

## 六、已就绪的部署文件

| 文件 | 用途 |
|---|---|
| `webapp/backend/app.py` | Flask 单服务（静态 dist + /api/predict_v13 + /api/predict） |
| `webapp/backend/requirements.txt` | 后端依赖 |
| `render.yaml` | Render 自动部署配置 |
| `webapp/frontend/dist/` | 生产前端构建产物 |
| `ml/v13/` | 模型 + predictor + domain_guard + global_ranges |

## 七、科学审查结论（详见 STEP23_SCIENCE_AUDIT.md）

模型科学正确（材料溯源/数学验证/物理一致性/防泄漏全部实证通过）；4 项已知局限（700/750 炉次 C 级、时间单位约定、POD 几何外推近似、750°C 拟合点少）已在 Domain Guard 与文案中声明。部署不改变模型行为。
