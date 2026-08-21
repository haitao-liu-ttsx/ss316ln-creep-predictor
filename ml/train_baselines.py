"""STEP 13.6: baseline training (reproducible, seed 42).

Models (in order): Dummy(mean), LinearRegression, Ridge, RandomForest(300),
HistGradientBoosting(default+seed), XGBoost(conservative).
Targets: max_displacement (raw + log1p->expm1), max_von_mises (raw).
Split discipline: train fit -> validation report -> test ONE-SHOT report.
NO hyperparameter search in this round. All models saved to ml/models/,
per-case predictions to ml/predictions/, metrics to ml/metrics/baseline_metrics.csv.
"""
import csv
import json
import os
import sys

import numpy as np
import joblib
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEAT = os.path.join(ROOT, 'ml', 'features')
MODELS_DIR = os.path.join(ROOT, 'ml', 'models')
PRED_DIR = os.path.join(ROOT, 'ml', 'predictions')
METRICS_DIR = os.path.join(ROOT, 'ml', 'metrics')
AI = os.path.join(ROOT, 'data', 'ai_ready_v3')

np.random.seed(SEED)

# ---------------------------------------------------------------- configs
MODELS = {
    'dummy': DummyRegressor(strategy='mean'),
    'linear': LinearRegression(),
    'ridge': Ridge(alpha=1.0, random_state=SEED),
    'rf': RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=-1),
    'histgb': HistGradientBoostingRegressor(random_state=SEED),
    'xgb': xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8,
                            random_state=SEED, n_jobs=-1, verbosity=0),
}
TARGET_CONFIGS = [
    {'name': 'displacement', 'transform': 'raw',
     'metric_unit': 'mm', 'inverse': lambda y: y},
    {'name': 'displacement', 'transform': 'log1p',
     'metric_unit': 'mm', 'inverse': lambda y: np.expm1(y)},
    {'name': 'von_mises', 'transform': 'raw',
     'metric_unit': 'MPa', 'inverse': lambda y: y},
]


def load_split(s):
    X = np.load(os.path.join(FEAT, 'X_%s.npy' % s))
    extra = json.load(open(os.path.join(FEAT, 'y_%s_extra.json' % s)))
    ids = json.load(open(os.path.join(FEAT, 'case_ids_%s.json' % s)))
    meta = {}
    for r in csv.DictReader(open(os.path.join(AI, s + '.csv'))):
        meta[r['case_id']] = r
    return X, extra, ids, meta


def y_for(extra, name, transform):
    if name == 'displacement':
        return np.asarray(extra['log1p_max_displacement'] if transform == 'log1p'
                          else extra['max_displacement'], dtype=float)
    return np.asarray(extra['max_von_mises'], dtype=float)


def metrics(y, yp):
    mae = mean_absolute_error(y, yp)
    rmse = float(np.sqrt(mean_squared_error(y, yp)))
    r2 = r2_score(y, yp)
    return mae, rmse, r2


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(PRED_DIR, exist_ok=True)
    os.makedirs(METRICS_DIR, exist_ok=True)
    Xtr, e_tr, id_tr, m_tr = load_split('train')
    Xva, e_va, id_va, m_va = load_split('validation')
    Xte, e_te, id_te, m_te = load_split('test')

    metric_rows = []
    for cfg in TARGET_CONFIGS:
        name, trf = cfg['name'], cfg['transform']
        ytr = y_for(e_tr, name, trf)
        yva = y_for(e_va, name, trf)
        yte = y_for(e_te, name, trf)
        inv = cfg['inverse']
        for mname, model in MODELS.items():
            model.fit(Xtr, ytr)
            tag = '%s_%s_%s' % (mname, name, trf)
            joblib.dump(model, os.path.join(MODELS_DIR, tag + '.joblib'))
            # predictions in ORIGINAL physical units
            preds = {}
            for s, X, y, ids, meta in (('train', Xtr, ytr, id_tr, m_tr),
                                       ('validation', Xva, yva, id_va, m_va),
                                       ('test', Xte, yte, id_te, m_te)):
                yp = inv(model.predict(X))
                yt = inv(y)
                preds[s] = (yt, yp, ids, meta)
                mae, rmse, r2 = metrics(yt, yp)
                # log-space metrics (log1p domain) for scale-robustness
                lmae = mean_absolute_error(np.log1p(np.maximum(yt, 0)),
                                           np.log1p(np.maximum(yp, 0)))
                lrmse = float(np.sqrt(mean_squared_error(
                    np.log1p(np.maximum(yt, 0)), np.log1p(np.maximum(yp, 0)))))
                metric_rows.append({'model': mname, 'target': name,
                                    'transform': trf, 'split': s,
                                    'n': len(yt), 'MAE': round(mae, 5),
                                    'RMSE': round(rmse, 5), 'R2': round(r2, 5),
                                    'log1p_MAE': round(lmae, 5),
                                    'log1p_RMSE': round(lrmse, 5),
                                    'unit': cfg['metric_unit']})
            # per-case predictions (test + validation + train sample columns)
            rows = []
            for s, (yt, yp, ids, meta) in preds.items():
                for i, cid in enumerate(ids):
                    m = meta[cid]
                    T = m['T_uniform'] or m['T_inner'] or ''
                    rel = (yt[i] - yp[i]) / yt[i] if abs(yt[i]) > 1e-12 else ''
                    rows.append({'case_id': cid, 'split': s,
                                 'model_type': m['model_type'], 'T': T,
                                 'pressure': m['pressure'], 'R_major': m['R_major'],
                                 'time': m['time'],
                                 'y_true': round(float(yt[i]), 8),
                                 'y_pred': round(float(yp[i]), 8),
                                 'residual': round(float(yt[i] - yp[i]), 8),
                                 'absolute_error': round(abs(yt[i] - yp[i]), 8),
                                 'relative_error': '' if rel == '' else round(rel, 5)})
            with open(os.path.join(PRED_DIR, 'predictions_%s.csv' % tag), 'w',
                      newline='') as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                for r in rows:
                    w.writerow(r)
            print('done %s' % tag)
    with open(os.path.join(METRICS_DIR, 'baseline_metrics.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(metric_rows[0].keys()))
        w.writeheader()
        for r in metric_rows:
            w.writerow(r)
    # config record (drop lambda functions before serialization)
    with open(os.path.join(METRICS_DIR, 'baseline_config.json'), 'w') as f:
        json.dump({'seed': SEED, 'models': {k: str(v) for k, v in MODELS.items()},
                   'targets': [{'name': c['name'], 'transform': c['transform'],
                                'metric_unit': c['metric_unit']} for c in TARGET_CONFIGS],
                   'n_train': len(Xtr), 'n_validation': len(Xva), 'n_test': len(Xte)},
                  f, indent=1)
    print('metrics ->', os.path.join(METRICS_DIR, 'baseline_metrics.csv'))


if __name__ == '__main__':
    main()
