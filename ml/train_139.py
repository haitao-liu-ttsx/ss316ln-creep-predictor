"""STEP 13.9: retrain on 318-row dataset (seed 42, validation-driven).

- von Mises: XGB 'all' features, combo-5 params (STEP 13.7 selection) + 3
  limited variants checked on validation; report Train/Val/Test + extrapolation
  bins incl. P>=30 (baseline comparison: STEP 13.7 = -0.267 on old test).
- displacement: regime-aware (stage-1 RF classifier now with 17 positive
  samples incl. 16 new; stage-2 elastic-domain linear) + unified XGB.
- MODEL_B/MODEL_C grouping on test.
Outputs: ml/models/step13_9/, ml/metrics/step13_9_metrics.csv.
"""
import csv
import json
import os

import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score
import xgboost as xgb

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, 'ml', 'features', 'v4')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
MDIR = os.path.join(ROOT, 'ml', 'models', 'step13_9')
METR = os.path.join(ROOT, 'ml', 'metrics')

np.random.seed(SEED)
os.makedirs(MDIR, exist_ok=True)


def met(y, yp):
    return (mean_absolute_error(y, yp), float(np.sqrt(mean_squared_error(y, yp))),
            r2_score(y, yp))


def main():
    X = {s: np.load(os.path.join(F, 'X_%s.npy' % s)) for s in ('train', 'validation', 'test')}
    y = {s: np.load(os.path.join(F, 'y_%s.npy' % s)) for s in ('train', 'validation', 'test')}
    extra = {s: json.load(open(os.path.join(F, 'y_%s_extra.json' % s))) for s in ('train', 'validation', 'test')}
    ids = {s: json.load(open(os.path.join(F, 'case_ids_%s.json' % s))) for s in ('train', 'validation', 'test')}
    meta = {s: {r['case_id']: r for r in csv.DictReader(open(os.path.join(AI, s + '.csv')))}
            for s in ('train', 'validation', 'test')}
    vm = {s: y[s][:, 1] for s in ('train', 'validation', 'test')}
    disp = {s: y[s][:, 0] for s in ('train', 'validation', 'test')}
    out = []

    # ---------------- 1. von Mises XGB (all features) ----------------
    print('=== 1. von Mises XGB (all features) ===')
    params = [dict(n_estimators=300, max_depth=4, learning_rate=0.1, subsample=0.8,
                   colsample_bytree=0.8, random_state=SEED, n_jobs=-1, verbosity=0),
              dict(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8,
                   colsample_bytree=0.8, random_state=SEED, n_jobs=-1, verbosity=0),
              dict(n_estimators=500, max_depth=6, learning_rate=0.03, subsample=0.7,
                   colsample_bytree=0.7, random_state=SEED, n_jobs=-1, verbosity=0)]
    best = None
    for i, p in enumerate(params, 1):
        m = xgb.XGBRegressor(**p)
        m.fit(X['train'], vm['train'])
        _, _, r2va = met(vm['validation'], m.predict(X['validation']))
        print('  variant %d: val R2=%.4f' % (i, r2va))
        if best is None or r2va > best[0]:
            best = (r2va, i, m)
    m_vm = best[2]
    joblib.dump(m_vm, os.path.join(MDIR, 'vm_final_xgb.joblib'))
    for s in ('train', 'validation', 'test'):
        a, r, r2v = met(vm[s], m_vm.predict(X[s]))
        out.append({'part': 'vm', 'split': s, 'MAE': round(a, 3), 'RMSE': round(r, 3),
                    'R2': round(r2v, 4)})
        print('  %-10s MAE=%7.2f RMSE=%8.2f R2=%7.4f' % (s, a, r, r2v))
    # extrapolation bins (test) incl. P>=30
    for bname, sel in (('Rm150', lambda m0: float(m0['R_major']) == 150),
                       ('T750', lambda m0: float(m0['T_uniform'] or m0['T_inner'] or 0) == 750),
                       ('P25', lambda m0: float(m0['pressure']) == 25),
                       ('P30', lambda m0: float(m0['pressure']) >= 30)):
        idx = [i for i, c in enumerate(ids['test']) if sel(meta['test'][c])]
        a, r, r2b = met(vm['test'][idx], m_vm.predict(X['test'][idx]))
        out.append({'part': 'vm_extrap', 'bin': bname, 'n': len(idx), 'MAE': round(a, 3),
                    'RMSE': round(r, 3), 'R2': round(r2b, 4)})
        print('  test %-6s n=%2d MAE=%7.2f RMSE=%8.2f R2=%7.4f' % (bname, len(idx), a, r, r2b))
    # MODEL_B/C
    for mt in ('MODEL_B', 'MODEL_C'):
        idx = [i for i, c in enumerate(ids['test']) if meta['test'][c]['model_type'] == mt]
        a, r, r2g = met(vm['test'][idx], m_vm.predict(X['test'][idx]))
        out.append({'part': 'vm_group', 'group': mt, 'n': len(idx), 'MAE': round(a, 3),
                    'RMSE': round(r, 3), 'R2': round(r2g, 4)})
        print('  test %-8s n=%2d MAE=%7.2f R2=%7.4f' % (mt, len(idx), a, r2g))

    # ---------------- 2. displacement regime-aware ----------------
    print('=== 2. displacement regime-aware (stage-1 + stage-2) ===')
    peeq_nz = {s: np.array(extra[s]['max_PEEQ_nonzero'], int) for s in ('train', 'validation', 'test')}
    print('  stage-1 positive samples: train=%d val=%d test=%d' %
          (peeq_nz['train'].sum(), peeq_nz['validation'].sum(), peeq_nz['test'].sum()))
    s1 = RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1,
                                class_weight='balanced')
    s1.fit(X['train'], peeq_nz['train'])
    joblib.dump(s1, os.path.join(MDIR, 'disp_stage1_rf.joblib'))
    for s in ('train', 'validation', 'test'):
        acc = accuracy_score(peeq_nz[s], s1.predict(X[s]))
        print('  stage-1 acc %-10s %.3f' % (s, acc))
    el_tr = peeq_nz['train'] == 0
    s2 = LinearRegression()
    s2.fit(X['train'][el_tr], disp['train'][el_tr])
    joblib.dump(s2, os.path.join(MDIR, 'disp_stage2_linear.joblib'))
    # elastic-domain test evaluation
    el_te = peeq_nz['test'] == 0
    y_el, yp_el = disp['test'][el_te], s2.predict(X['test'][el_te])
    a, r, r2e = met(y_el, yp_el)
    out.append({'part': 'disp_regime_elastic', 'n': int(el_te.sum()),
                'MAE': round(a, 4), 'RMSE': round(r, 4), 'R2': round(r2e, 4)})
    print('  stage-2 elastic-domain (test n=%d): MAE=%.4f RMSE=%.4f R2=%.4f'
          % (el_te.sum(), a, r, r2e))
    # unified XGB for comparison
    m_u = xgb.XGBRegressor(**params[0])
    m_u.fit(X['train'], disp['train'])
    a, r, r2u = met(disp['test'], m_u.predict(X['test']))
    out.append({'part': 'disp_unified', 'MAE': round(a, 3), 'RMSE': round(r, 3),
                'R2': round(r2u, 4)})
    print('  unified XGB test: MAE=%.3f R2=%.4f' % (a, r2u))

    with open(os.path.join(METR, 'step13_9_metrics.csv'), 'w', newline='') as f:
        cols = list(dict.fromkeys(k for r in out for k in r.keys()))
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in out:
            w.writerow({k: r.get(k, '') for k in cols})
    print('done -> ml/models/step13_9/, ml/metrics/step13_9_metrics.csv')


if __name__ == '__main__':
    main()
