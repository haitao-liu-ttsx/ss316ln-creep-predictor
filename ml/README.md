# SS316LN Toroidal Tube — ML Baseline Pipeline (STEP 13)

## 环境（2026-08-20 建立，独立 venv，不污染 Abaqus Python）

| 项 | 值 |
|---|---|
| Python | 3.10.5（由 Abaqus SMApy python3.10 `-m venv` 创建，独立于 Abaqus 环境） |
| OS | Windows 11 (win32) |
| numpy | 2.2.6 |
| scipy | 1.15.3 |
| pandas | 2.3.3 |
| scikit-learn | 1.7.2 |
| matplotlib | 3.10.9 |
| joblib | 1.5.3 |
| xgboost | 3.2.0 |
| random seed | 42（全部脚本固定） |

venv 路径: `ml/.venv/`（激活: `ml\.venv\Scripts\python.exe`）
说明: Abaqus SMApy Python 只含 numpy/scipy/matplotlib，缺 pandas/sklearn/pip；
按批准方案建独立 venv，Abaqus 环境未被修改。

## 数据（不可修改）

- `data/ai_ready_v3/simulation_dataset_300.csv`（300 行 × 33 列，STEP 12B 产物）
- 划分（STEP 13.5 修复后）: train 104 / validation 46 / test 74
- 质量规则 A/B/D/E、valid_for_AI=224 未变；675/725 σy 为 INTERPOLATED（B 级）

## 脚本

| 脚本 | 职责 |
|---|---|
| `audit_dataset.py` | STEP 13.1 schema/统计审计（纯 stdlib）→ `metrics/audit_dataset.json` |
| `audit_split.py` | STEP 13.5 split 7 项审计（v1 0 变化 / Rm150 / 梯子 / 同键 / 异常） |
| `build_features.py` | feature pipeline → `features/`（numpy + 列名 + 配置） |
| `train_baselines.py` | Dummy/Linear/Ridge/RF/HistGB/XGB → `models/` + `metrics/baseline_metrics.csv` |
| `evaluate_models.py` | 三集评估 + MODEL_B/C 分组 |
| `evaluate_extrapolation.py` | T/P/Rm/time 外推分箱统计 |
| `plots.py` | 图表 → `figures/` |

## 禁止清单（项目红线）

- 不修改 Abaqus 输出 / 不人工填充 target / 不把插值 σy 当实验
- 不删除表现差的 test case / 不用 test 调参 / 不随机重划分掩盖外推失败
- 不修改 A/B/D/E 质量规则；不训练深度模型（本轮 baseline 阶段）
