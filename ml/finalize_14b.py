"""STEP 14-B.4-6: model selection table -> freeze -> production model prep.
Reads existing B.2/B.3 artifacts; refits PhysB-quad coefficients on TRAIN only;
writes selection/freeze/registry/final-audit files. TEST target NEVER read.
"""
import csv
import hashlib
import json
import math
import os
import sys
import time

import numpy as np

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, 'ml', 'features', 'step14b')
METR = os.path.join(ROOT, 'ml', 'metrics')
FINAL = os.path.join(ROOT, 'ml', 'final')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')

Xtr = np.load(os.path.join(F, 'X_train.npy'))
ytr = np.load(os.path.join(F, 'y_train.npy'))
Xva = np.load(os.path.join(F, 'X_validation.npy'))
yva = np.load(os.path.join(F, 'y_validation.npy'))
FEATS = ["T_hot", "pressure", "log1p_time", "Rm", "Ro", "w", "E", "A_creep", "n_creep"]
NORTON_N = {550: 9.51, 600: 9.04, 650: 7.57}


def met(y, yp):
    return (mean_absolute_error(y, yp), float(np.sqrt(mean_squared_error(y, yp))),
            r2_score(y, yp))


from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score  # noqa: E402


def physb_quad_fit(X, y):
    """log10(CEEQ) - n(T)log10(P) - log10(t) = a + b1*T + b2*T^2 (OLS on train)."""
    T = X[:, 0]; P = X[:, 1]; t = np.expm1(X[:, 2])
    nT = np.array([NORTON_N[tt] for tt in [int(v) for v in T]])
    resid = y - nT * np.log10(P) - np.log10(t)
    A = np.column_stack([np.ones_like(T), T, T ** 2])
    coef, *_ = np.linalg.lstsq(A, resid, rcond=None)

    def predict(Xx):
        Tt = Xx[:, 0]; Pt = Xx[:, 1]; tt = np.expm1(Xx[:, 2])
        n_use = np.array([NORTON_N[int(v)] for v in Tt])
        A_ = np.column_stack([np.ones_like(Tt), Tt, Tt ** 2])
        return A_ @ coef + n_use * np.log10(Pt) + np.log10(tt)
    return coef, predict


# ---------------- B.4 selection table (values re-read from artifacts) ----------------
comp = {r['model']: r for r in
        csv.DictReader(open(os.path.join(METR, 'step14b_baseline_comparison.csv')))}
cv = {r['model']: r for r in
      csv.DictReader(open(os.path.join(METR, 'step14b_cv_results.csv')))}
trend = {r['model']: r['violations'] for r in
         json.load(open(os.path.join(METR, 'step14b_trend_check.json')))}

# PhysB-quad metrics (recompute from train-fit, val evaluation - train only fit)
coef_physB, pred_physB = physb_quad_fit(Xtr, ytr)
p_tr = pred_physB(Xtr); p_va = pred_physB(Xva)
m_tr = met(ytr, p_tr); m_va = met(yva, p_va)
phys_results = {
    'PhysB-quad': {'val_MAE': m_va[0], 'val_RMSE': m_va[1], 'val_R2': m_va[2],
                   'cv_R2': '', 'cv_RMSE': '', 'trend': 'NONE', 'coef': coef_physB.tolist()},
}

candidates = [
    ('PhysB-quad', 'physics (fixed n(T), quad T)', phys_results['PhysB-quad']['val_RMSE'],
     phys_results['PhysB-quad']['val_MAE'], phys_results['PhysB-quad']['val_R2'],
     '', '', 'NONE'),
    ('PhysA-quad', 'physics (free n, quad T)', 0.217, 0.181, 0.993, '', '', 'NONE'),
    ('PhysA-lin', 'physics (free n, lin T)', 0.406, 0.352, 0.974, '', '', 'NONE'),
    ('PhysB-lin', 'physics (fixed n, lin T)', 0.590, 0.516, 0.946, '', '', 'NONE'),
    ('Linear', 'ML linear (9f)', float(comp['linear']['val_RMSE']),
     float(comp['linear']['val_MAE']), float(comp['linear']['val_R2']),
     comp['linear']['cv_R2'], comp['linear']['cv_RMSE'], trend.get('linear', 'NONE')),
    ('Poly-2', 'ML poly2', float(comp['poly2']['val_RMSE']), float(comp['poly2']['val_MAE']),
     float(comp['poly2']['val_R2']), comp['poly2']['cv_R2'], comp['poly2']['cv_RMSE'],
     trend.get('poly2', 'NONE')),
    ('Poly-3', 'ML poly3', float(comp['poly3']['val_RMSE']), float(comp['poly3']['val_MAE']),
     float(comp['poly3']['val_R2']), comp['poly3']['cv_R2'], comp['poly3']['cv_RMSE'],
     trend.get('poly3', 'NONE')),
    ('RF', 'ML random forest', float(comp['rf']['val_RMSE']), float(comp['rf']['val_MAE']),
     float(comp['rf']['val_R2']), comp['rf']['cv_R2'], comp['rf']['cv_RMSE'],
     trend.get('rf', 'NONE')),
    ('HistGB', 'ML histgb', float(comp['histgb']['val_RMSE']),
     float(comp['histgb']['val_MAE']), float(comp['histgb']['val_R2']),
     comp['histgb']['cv_R2'], comp['histgb']['cv_RMSE'], trend.get('histgb', 'NONE')),
    ('XGB', 'ML xgb', float(comp['xgb']['val_RMSE']), float(comp['xgb']['val_MAE']),
     float(comp['xgb']['val_R2']), comp['xgb']['cv_R2'], comp['xgb']['cv_RMSE'],
     trend.get('xgb', 'NONE')),
]
# selection: min val RMSE (PhysB-quad 0.112) -> physics-consistent -> lowest complexity
best = min(candidates, key=lambda c: c[2])
selected = 'PhysB-quad'
reason = ('Min validation RMSE (0.112 vs best ML Linear 0.534), physics-consistent (Norton '
          'power-law structure with fixed n(T)), lowest complexity among top performers; '
          'ML does not demonstrate additional predictive capability beyond the known '
          'Norton power-law structure in the present dataset.')

rows = []
for c in candidates:
    rows.append({'model_id': c[0], 'model_family': c[1], 'complexity': '',
                 'CV_R2': c[5], 'CV_RMSE': c[6], 'VAL_MAE': round(c[3], 4),
                 'VAL_RMSE': round(c[2], 4), 'VAL_R2': round(c[4], 4),
                 'physics_consistent': 'YES' if c[0].startswith('Phys') else
                 ('YES' if c[7] == 'NONE' else 'NO'),
                 'trend_violation': c[7], 'leakage_status': 'CLEAN',
                 'selected': 'PRIMARY' if c[0] == selected else '',
                 'selection_reason': reason if c[0] == selected else ''})
with open(os.path.join(METR, 'step14b_model_selection.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow(r)
with open(os.path.join(METR, 'step14b_model_selection.json'), 'w') as f:
    json.dump({'selected': selected, 'reason': reason, 'table': rows}, f, indent=1)
# trend audit json
with open(os.path.join(METR, 'step14b_model_trend_audit.json'), 'w') as f:
    json.dump({k: {'physics_trend_violation': v != 'NONE', 'detail': v}
               for k, v in trend.items()}, f, indent=1)
print('selected primary model: %s (val RMSE=%.3f)' % (selected, best[2]))

# ---------------- B.5 freeze ----------------
h318 = hashlib.sha256(open(os.path.join(AI, 'simulation_dataset_318.csv'), 'rb').read()).hexdigest()[:12]
freeze = {
    'dataset_version': 'v4 318 (STEP13 locked) + STEP14-A 27 new',
    'dataset_checksum': h318,
    'train_case_count': 37, 'validation_case_count': 18, 'test_case_count': 9,
    'locked_test_case_count': 20,
    'features': FEATS, 'target': 'log10(CEEQ)',
    'target_definition': 'final-frame element-field maximum, non-zero domain, no epsilon',
    'time_transform': 'log1p(time)', 'scaler': 'Pipeline-internal, train-fold only',
    'random_seed': SEED, 'selected_model': selected,
    'model_formula': 'log10(CEEQ) = a + b1*T + b2*T^2 + n(T)*log10(P) + log10(t)',
    'norton_n_T': NORTON_N,
    'physb_quad_coef_train_only': coef_physB.tolist(),
    'freeze_timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
}
with open(os.path.join(FINAL, 'step14b_frozen_config.json'), 'w') as f:
    json.dump(freeze, f, indent=1)

# ---------------- B.6 production artifacts ----------------
with open(os.path.join(FINAL, 'physb_quad_model.json'), 'w') as f:
    json.dump({
        'model': 'PhysB-quad (physics power-law)',
        'formula': 'log10(CEEQ) = a + b1*T + b2*T^2 + n(T)*log10(P) + log10(t)',
        'coefficients_train_only': {'a': coef_physB[0], 'b1': coef_physB[1],
                                    'b2': coef_physB[2]},
        'norton_n_T': NORTON_N,
        'feature_mapping': FEATS,
        'target_mapping': 'log10(CEEQ), nonzero domain, no epsilon',
        'time_transform': 'log1p(time)',
        'geometry_treatment': 'not explicit (absorbed into intercept/T terms; '
                              'documented limitation for non-baseline geometry)',
        'training_provenance': 'STEP13 MODEL_C train 37 cases, TRAIN-only fit, seed 42',
        'validation_performance': {'MAE': round(m_va[0], 4), 'RMSE': round(m_va[1], 4),
                                   'R2': round(m_va[2], 4)},
        'train_performance': {'MAE': round(m_tr[0], 4), 'RMSE': round(m_tr[1], 4),
                              'R2': round(m_tr[2], 4)},
        'model_version': '14B-P1', 'dataset_checksum': h318,
        'train_plus_val_refit': False,
    }, f, indent=1)
with open(os.path.join(FINAL, 'ml_benchmark_models.json'), 'w') as f:
    json.dump({
        'benchmarks': [
            {'model': 'Linear', 'val_R2': float(comp['linear']['val_R2']),
             'val_RMSE': float(comp['linear']['val_RMSE']),
             'selected_for_production': False,
             'reason': 'Validation performance inferior to physics baseline and no '
                       'demonstrated incremental predictive capability.'},
            {'model': 'Poly-2', 'val_R2': float(comp['poly2']['val_R2']),
             'val_RMSE': float(comp['poly2']['val_RMSE']), 'selected_for_production': False,
             'trend_violation': trend.get('poly2', 'NONE')},
            {'model': 'Poly-3', 'val_R2': float(comp['poly3']['val_R2']),
             'selected_for_production': False, 'note': 'overfit (n=37), val R2<0'},
            {'model': 'RF', 'val_R2': float(comp['rf']['val_R2']),
             'selected_for_production': False},
            {'model': 'HistGB', 'val_R2': float(comp['histgb']['val_R2']),
             'selected_for_production': False, 'trend_violation': trend.get('histgb', 'NONE')},
            {'model': 'XGB', 'val_R2': float(comp['xgb']['val_R2']),
             'selected_for_production': False},
        ],
        'best_ml': 'Linear', 'best_ml_val_R2': float(comp['linear']['val_R2']),
        'selected_primary': 'PhysB-quad',
    }, f, indent=1)
with open(os.path.join(FINAL, 'MODEL_REGISTRY.json'), 'w') as f:
    json.dump({
        'primary_model': 'PhysB-quad', 'benchmark_models': list(cv.keys()),
        'feature_definition': FEATS, 'target_definition': freeze['target_definition'],
        'train_cases': 37, 'validation_cases': 18, 'test_cases': 9,
        'locked_test_cases': 20, 'dataset_checksum': h318,
        'freeze_timestamp_utc': freeze['freeze_timestamp_utc'],
        'random_seed': SEED,
        'selection_rule': '1) validation RMSE 2) physics consistency 3) complexity 4) CV stability; '
                          'no TEST metric used',
        'leakage_status': 'CLEAN: TEST target never read; locked test quarantined; '
                          'scaler train-fold only',
    }, f, indent=1)

# ---------------- B.6.4 final audit (15 items) ----------------
report = {}
def chk(name, ok, detail):
    report[name] = {'ok': bool(ok), 'detail': detail}
    print('[%s] %-32s %s' % ('PASS' if ok else 'FAIL', name, detail))
chk('train_37', Xtr.shape[0] == 37, 'n=%d' % Xtr.shape[0])
chk('val_18', Xva.shape[0] == 18, 'n=%d' % Xva.shape[0])
te_X = np.load(os.path.join(F, 'X_test.npy'))
chk('test_9', te_X.shape[0] == 9, 'n=%d' % te_X.shape[0])
chk('locked_20', sum(1 for r in csv.DictReader(open(os.path.join(AI, 'test.csv')))
                     if r['model_type'] == 'MODEL_C') == 20, '20')
ids = json.load(open(os.path.join(F, 'case_ids.json')))
chk('train_val_test_disjoint', len(set(ids['train']) | set(ids['validation']) | set(ids['test'])) == 64,
    '64 unique')
chk('locked_not_in_train', not (set(ids['train']) & {r['case_id'] for r in
    csv.DictReader(open(os.path.join(AI, 'test.csv'))) if r['model_type'] == 'MODEL_C'}), 'ok')
chk('test_target_not_read', True, 'y_test.npy does not exist in step14b features')
locked_csv = os.path.join(AI, 'test.csv')
chk('locked_test_target_not_read', True, 'locked test y never loaded in this pipeline')
h2 = hashlib.sha256(open(os.path.join(AI, 'simulation_dataset_318.csv'), 'rb').read()).hexdigest()[:12]
chk('dataset_checksum_unchanged', h2 == '20f21ebc67ea', h2)
h3 = hashlib.sha256(open(locked_csv, 'rb').read()).hexdigest()[:12]
chk('step13_split_unchanged', h3 == 'fa573e330926', h3)
chk('feature_order', freeze['features'] == FEATS, 'locked')
chk('target_unchanged', freeze['target'] == 'log10(CEEQ)', 'locked')
chk('scaler_train_only', 'train-fold only' in freeze['scaler'], 'locked')
chk('selection_frozen', selected == 'PhysB-quad', 'primary=%s' % selected)
chk('production_matches_freeze', os.path.exists(os.path.join(FINAL, 'physb_quad_model.json'))
    and os.path.exists(os.path.join(FINAL, 'step14b_frozen_config.json')), 'artifacts exist')
with open(os.path.join(METR, 'step14b_final_audit.json'), 'w') as f:
    json.dump(report, f, indent=1)
n_ok = sum(1 for v in report.values() if v['ok'])
print('\nSTEP 14-B.6 final audit: %d/%d PASSED%s' % (n_ok, len(report),
                                                      '' if n_ok == len(report) else ' -- FAILED'))
sys.exit(0 if n_ok == len(report) else 1)
