# STEP21-D V1.3 统一预测接口、Domain Guard 与 WebApp 集成报告

日期: 2026-08-21 ｜ 状态: **STEP21-D = COMPLETE**（全部验收条件通过）

## 一、统一 Prediction API

- `ml/v13/predictor.py`：输入 T(°C)/P(MPa)/t(h)/Rm/Ro/w(mm) → 7 场(2304) + von Mises + centroids(2304,3) + summary + domain
- `predict()` 返回 numpy 数组；`predict_serializable()` 返回 JSON 可移植格式
- 模型启动时加载一次并缓存（predictor 模块级 _cache）；材料表 550-750 冻结查表

## 二、模型加载

7 个 joblib（ml/v13/models/）首调 57ms、二次调用 43ms（全部模型 + POD 重建 + von Mises）。

## 三、7 场输出

Srr/Stt/Szz/Srt/Srz/Stz/CEEQ，每场 (2304,)；与训练一致的 POD 重建管线（TRAIN-only basis/scaler）。

## 四、von Mises

由预测六应力实时计算（公式为标准三维 von Mises）；无独立 vm 模型；非负性检查通过。

## 五、CEEQ

模型输出 log10(CEEQ) → 10^ 逆变换；非负；NaN/Inf/负 → 报错不静默 clip。

## 六、Domain Guard（核心）

- 三级状态：SAFE / WARNING / OUT_OF_DOMAIN
- 边界全部来自 **TRAIN 157 例实际覆盖**（非手工阈值）：T/P/t/Rm/Ro/w/P·Ro/w 范围 + 几何覆盖 + **T×几何联合覆盖** + 稀疏覆盖检测
- **关键修正**：120/25/3、80/15/2 在 TRAIN 有 11 例但均为 550-650℃ 旧数据——700/750×这些几何属**温度×几何联合外推** → WARNING
- 即使 CEEQ 域外，**应力场照常输出**（不搞一刀切）

## 七、三维可视化（WebApp）

V1.3 模式：真实 x/y/z 质心（2304 点）、8 场切换、应力 diverging 色标（蓝-白-红）、CEEQ/vm 连续色标、绝对/相对色标切换、未变形几何（默认）。

## 八、单位

应力 MPa ｜ CEEQ 无量纲 ｜ T °C ｜ P MPa ｜ t h ｜ 几何 mm ｜ P·Ro/w MPa（界面明确显示）

## 九、测试

| 测试 | 结果 |
|---|---|
| API 单元测试（9 项：TRAIN/VAL/EXT/几何/温度/非法输入） | **9/9 PASS** |
| WebApp 集成（V1.3 切换/预测/域状态/8 场/EXT 警告/V1.2 恢复） | **9/9 PASS**，0 JS 错误 |
| V1.2 UI 冒烟回归 | **16/16 PASS** |
| V1.2 API consistency | **12/12 PASS**（max_abs_diff=0.0） |

## 十、性能

单 case 预测（含全部 7 模型 + 重建 + von Mises）：首调 57ms（模型加载）、稳态 **43ms**——满足交互式响应。

## 十一、WebApp 回归

现有 V1.2 模式零改动（渲染路径/API/测试全保留）；新增 V1.3 标签页模式切换，默认保持 V1.2。

## 十二、已知限制（如实）

1. CEEQ 在 T×几何联合外推域（如 700°C×120/25/3）为 WARNING 级——界面显示"建议 Abaqus 验证"，不阻断应力输出
2. /api/predict_v13 响应体较大（~10MB JSON，2304×8 场）——首次解析略慢，可后续考虑压缩格式
3. 前端 V1.3 模式不含时间播放（多场快照显示）——V1.2 播放功能保留

## 十三、数据完整性

318 = UNCHANGED ｜ V1.2 = UNCHANGED ｜ STEP20-C = UNCHANGED ｜ STEP20-D = UNCHANGED ｜ STEP21-A = UNCHANGED ｜ STEP21-B = UNCHANGED ｜ STEP21-C = UNCHANGED ｜ V1.3 = **FROZEN** ｜ LOCKED = UNTOUCHED

## 十四、新增文件

- `ml/v13/predictor.py`、`domain_guard.py`、`test_predictor.py`
- `webapp/backend/app.py`（新增 /api/predict_v13 路由，V1.2 路由不动）
- `webapp/frontend/src/api.ts`（V1.3 类型与调用）、`App.tsx`（V1.3 模式 + V13Viewer）、`style.css`
- `ml/metrics/step21d_v13_deployment.json` + 本报告
- `simulation/v13_prepared/domain_guard_train_coverage.json`（TRAIN 覆盖边界）

## 十五、是否允许进入 STEP22

**YES** —— 全部验收条件通过（7 模型独立加载、API 可用、2304 点输出、8 场切换、von Mises 实时计算、CEEQ 逆变换、Domain Guard 正常、测试全过、原 WebApp 未破坏）。