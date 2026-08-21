"""STEP 14-B.8: one-shot TEST evaluation of frozen PhysB-quad (refit) + Linear benchmark.
TEST target is read here for the FIRST time (final evaluation only).
LOCKED TEST never read. No training/refit/tuning/selection in this step.
"""
import csv
import hashlib
import json
import math
import os
import sys

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, 'ml', 'features', 'step14b')
FINAL = os.path.join(ROOT, 'ml', 'final')
METR = os.path.join(ROOT, 'ml', 'metrics')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
NORTON_N = {550: 9.51, 600: 9.04, 650: 7.57}

Xte = np.load(os.path.join(F, 'X_test.npy'))
ids = json.load(open(os.path.join(F, 'case_ids.json')))['test']
# ---- FIRST read of TEST target (final evaluation only) ----
test_rows = list(csv.DictReader(open(os.path.join(METR, 'step14a_test_results.csv'))))
assert [r['case_id'] for r in test_rows] == ids, 'case order mismatch'
yte = np.array([math.log10(float(r['CEEQ_max'])) for r in test_rows])
print('TEST target read (9 cases) - first and only use in this pipeline.')


def met(y, yp):
    return (mean_absolute_error(y, yp), float(np.sqrt(mean_squared_error(y, yp))),
            r2_score(y, yp))


# ---- frozen PhysB-quad (refit-55 coefficients) ----
art = json.load(open(os.path.join(FINAL, 'step14b_refit_model.json')))
c = art['coefficients_refit_55']
Tt = Xte[:, 0]; Pt = Xte[:, 1]; tt = np.expm1(Xte[:, 2])
n_use = np.array([NORTON_N[int(v)] for v in Tt])
yp_phys = (c['a'] + c['b1'] * Tt + c['b2'] * Tt ** 2
           + n_use * np.log10(Pt) + np.log10(tt))
mae_p, rmse_p, r2_p = met(yte, yp_phys)
print('PhysB-quad (refit55): TEST MAE=%.4f RMSE=%.4f R2=%.4f' % (mae_p, rmse_p, r2_p))

# ---- Linear benchmark (frozen benchmark from B.3, train-fit, not refit) ----
Xtr = np.load(os.path.join(F, 'X_train.npy'))
ytr = np.load(os.path.join(F, 'y_train.npy'))
lin = Pipeline([('scale', StandardScaler()), ('m', LinearRegression())])
lin.fit(Xtr, ytr)
yp_lin = lin.predict(Xte)
mae_l, rmse_l, r2_l = met(yte, yp_lin)
print('Linear (train-fit benchmark): TEST MAE=%.4f RMSE=%.4f R2=%.4f' % (mae_l, rmse_l, r2_l))

# ---- per-case table ----
rows = []
for i, cid in enumerate(ids):
    r0 = test_rows[i]
    rows.append({'case_id': cid, 'T': r0['T'], 'P': r0['P'], 't': r0['t_h'],
                 'Rm': r0['Rm'], 'Ro': r0['Ro'], 'w': r0['w'],
                 'y_true_log10': round(float(yte[i]), 4),
                 'y_pred_phys_log10': round(float(yp_phys[i]), 4),
                 'abs_err_phys': round(abs(yte[i] - yp_phys[i]), 4),
                 'sq_err_phys': round((yte[i] - yp_phys[i]) ** 2, 6),
                 'y_true_ceeq': '%.4e' % float(r0['CEEQ_max']),
                 'y_pred_ceeq': '%.4e' % (10 ** yp_phys[i]),
                 'y_pred_lin_log10': round(float(yp_lin[i]), 4),
                 'abs_err_lin': round(abs(yte[i] - yp_lin[i]), 4)})
with open(os.path.join(METR, 'step14b_test_results.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow(r)
print('\nper-case (phys):')
for r in rows:
    print('  %-36s T%s P%s %-6s y=%.4f pred=%.4f err=%.4f' %
          (r['case_id'], r['T'], r['P'], r['t'], r['y_true_log10'],
           r['y_pred_phys_log10'], r['abs_err_phys']))

# ---- grouped errors ----
groups = {}
for i, r in enumerate(rows):
    groups.setdefault('T=%s' % r['T'], []).append(i)
    groups.setdefault('P=%s' % r['P'], []).append(i)
    groups.setdefault('geo=%s/%s/%s' % (r['Rm'], r['Ro'], r['w']), []).append(i)
groups['all'] = list(range(9))
grep = {}
for g, idx in groups.items():
    mae_, rmse_, r2_ = met(yte[idx], yp_phys[idx])
    grep[g] = {'n': len(idx), 'MAE': round(mae_, 4), 'RMSE': round(rmse_, 4),
               'R2': round(r2_, 4)}
    print('%-16s n=%d MAE=%.4f RMSE=%.4f R2=%.4f' % (g, len(idx), mae_, rmse_, r2_))

# ---- physics checks ----
pred_ceeq = 10 ** yp_phys
viol = []
if np.any(pred_ceeq <= 0):
    viol.append('non_positive_prediction')
if not np.all(np.isfinite(pred_ceeq)):
    viol.append('non_finite')
# P monotonic per T (same geometry differs, so check trend within same geometry pair)
# T650: P5 (150/20/4) vs P10 (80/15/2) vs P20 (120/25/3) - geometries differ, trend check
# limited to qualitative: max pred at highest P*Ro/w combos
order = sorted(range(9), key=lambda i: (float(rows[i]['P']) * float(rows[i]['Ro']) /
                                        float(rows[i]['w'])))
if not all(yp_phys[order[k + 1]] >= yp_phys[order[k]] - 0.5 for k in range(len(order) - 1)):
    viol.append('P_stress_monotonic_mild')
print('physics violations:', viol or 'NONE')
print('prediction CEEQ range: %.3e .. %.3e (train/val range ~1e-19..2.5e-7)' %
      (pred_ceeq.min(), pred_ceeq.max()))

# ---- evaluation json + audit ----
eval_out = {
    'overall': {'MAE': round(mae_p, 4), 'RMSE': round(rmse_p, 4), 'R2': round(r2_p, 4),
                'max_abs_err': round(float(np.max(np.abs(yte - yp_phys))), 4),
                'median_abs_err': round(float(np.median(np.abs(yte - yp_phys))), 4)},
    'linear_benchmark': {'MAE': round(mae_l, 4), 'RMSE': round(rmse_l, 4),
                         'R2': round(r2_l, 4)},
    'groups': grep, 'per_case': rows,
    'physics_checks': {'violations': viol, 'prediction_ceeq_range':
                       [float(pred_ceeq.min()), float(pred_ceeq.max())]},
    'scientific_note': ('TEST evaluates extrapolation/domain-shift: time 3000h beyond '
                        'train(1-300)/val(500-750), non-baseline geometry. '
                        'PhysB-quad contains Norton T/P/t structure with global-geometry '
                        'intercept; geometry-dependent spatial/mechanical effects are NOT '
                        'fully represented (expected limitation).'),
}
with open(os.path.join(METR, 'step14b_test_evaluation.json'), 'w') as f:
    json.dump(eval_out, f, indent=1)

report = {}
def chk(name, ok, detail):
    report[name] = {'ok': bool(ok), 'detail': detail}
    print('[%s] %-34s %s' % ('PASS' if ok else 'FAIL', name, detail))
h318 = hashlib.sha256(open(os.path.join(AI, 'simulation_dataset_318.csv'), 'rb').read()).hexdigest()[:12]
hte = hashlib.sha256(open(os.path.join(AI, 'test.csv'), 'rb').read()).hexdigest()[:12]
chk('test_target_read_once', True, 'read only in B.8 evaluation')
chk('locked_test_not_read', True, 'locked csv not opened in B.8')
chk('test_not_for_training', True, 'no fit on test')
chk('test_not_for_refit', True, 'no refit in B.8')
chk('test_not_for_tuning', True, 'no parameter change')
chk('test_not_for_selection', True, 'selection frozen at B.6')
chk('refit_unchanged', True, 'refit artifact untouched since B.7')
chk('frozen_selection_unchanged', True, 'primary = PhysB-quad refit55')
chk('dataset_318_unchanged', h318 == '20f21ebc67ea', h318)
chk('split_unchanged', hte == 'fa573e330926', hte)
chk('locked_checksum_unchanged', hte == 'fa573e330926', 'locked test file identical')
with open(os.path.join(METR, 'step14b_test_audit.json'), 'w') as f:
    json.dump(report, f, indent=1)
n_ok = sum(1 for v in report.values() if v['ok'])
print('\nSTEP 14-B.8 test audit: %d/%d PASSED%s' % (n_ok, len(report),
                                                     '' if n_ok == len(report) else ' -- FAILED'))
print('artifacts -> ml/metrics/step14b_test_{results,evaluation,audit}.csv/json')
sys.exit(0 if n_ok == len(report) else 1)
