"""STEP 13.10: permutation importance (318), CEEQ exploratory, monotonicity
checks, A/B/C/D ablation summary. seed 42, no test-driven tuning.
"""
import csv
import json
import os

import numpy as np
import joblib
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, 'ml', 'features', 'v4')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
MDIR = os.path.join(ROOT, 'ml', 'models', 'step13_10')
METR = os.path.join(ROOT, 'ml', 'metrics')

np.random.seed(SEED)


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
    feats = json.load(open(os.path.join(F, 'feature_names.json')))['features']
    lines = []

    # ---------------- 6. permutation importance (vm model, 318) ----------------
    m_vm = joblib.load(os.path.join(MDIR, 'vm_final_xgb.joblib'))
    Xva, yva = X['validation'], y['validation'][:, 1]
    pi = permutation_importance(m_vm, Xva, yva, n_repeats=10, random_state=SEED, n_jobs=-1)
    imp = pi.importances_mean
    order = np.argsort(imp)[::-1]
    lines.append('=== permutation importance (von Mises, validation, 318) ===')
    imp_rows = []
    for i in order:
        lines.append('  %-14s %8.4f' % (feats[i], imp[i]))
        imp_rows.append({'feature': feats[i], 'importance': round(float(imp[i]), 4)})
    with open(os.path.join(METR, 'step13_10_importance.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['feature', 'importance'])
        w.writeheader()
        for r in imp_rows:
            w.writerow(r)
    print('\n'.join(lines[:8]))
    print('  ... (full in step13_10_importance.csv)')

    # ---------------- 7. CEEQ exploratory (MODEL_C only) ----------------
    print('=== 7. CEEQ exploratory (MODEL_C only) ===')
    mc = {s: [i for i, c in enumerate(ids[s]) if meta[s][c]['model_type'] == 'MODEL_C']
          for s in ('train', 'validation', 'test')}
    print('  MODEL_C: train=%d val=%d test=%d' % (len(mc['train']), len(mc['validation']), len(mc['test'])))
    ceeq = {s: np.asarray(extra[s]['max_creep_strain'], float) for s in ('train', 'validation', 'test')}
    # log10 nonzero domain
    yl = {}
    idx = {}
    for s in ('train', 'test'):
        nz = [i for i in mc[s] if ceeq[s][i] > 0]
        idx[s] = nz
        yl[s] = np.log10(np.array([ceeq[s][i] for i in nz]))
    print('  nonzero: train=%d test=%d (log10 domain)' % (len(idx['train']), len(idx['test'])))
    # features for creep: MODEL_C rows use same 16 features (A_creep/n_creep filled)
    mdl = xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.1,
                           random_state=SEED, n_jobs=-1, verbosity=0)
    mdl.fit(X['train'][idx['train']], yl['train'])
    joblib.dump(mdl, os.path.join(MDIR, 'ceeq_exploratory_xgb.joblib'))
    yp = mdl.predict(X['test'][idx['test']])
    yt = yl['test']
    a, r, r2c = met(yt, yp)
    print('  CEEQ log10 test: MAE=%.3f RMSE=%.3f R2=%.4f (log10 domain, n=%d)' %
          (a, r, r2c, len(yt)))
    lines.append('ceeq_log10 test MAE=%.3f RMSE=%.3f R2=%.4f n=%d (train-only fit, '
                 'NO independent validation: val MODEL_C=0)' % (a, r, r2c, len(yt)))
    # per-case predictions + extrapolation bins (T/P/time)
    ceeq_rows = []
    for i, c in zip(idx['test'], range(len(yt))):
        m0 = meta['test'][ids['test'][i]]
        ceeq_rows.append({'case_id': ids['test'][i], 'T': m0['T_uniform'],
                          'P': m0['pressure'], 'time': m0['time'],
                          'y_true_log10': round(float(yt[c]), 4),
                          'y_pred_log10': round(float(yp[c]), 4),
                          'y_true': '%.3e' % float(ceeq['test'][i])})
    with open(os.path.join(METR, 'step13_10_ceeq.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(ceeq_rows[0].keys()))
        w.writeheader()
        for r in ceeq_rows:
            w.writerow(r)
    for bname, key in (('T<=600', 'T'), ('T=650', 'T'), ('P<=10', 'P'),
                       ('P>=20', 'P'), ('t=1000', 'time'), ('t=3000', 'time')):
        sel = [k for k, i in enumerate(idx['test'])
               if _bin(meta['test'][ids['test'][i]], bname, key)]
        if len(sel) < 2:
            continue
        a2, r2_, r22 = met(yt[sel], yp[sel])
        lines.append('ceeq_%s n=%d MAE=%.3f RMSE=%.3f R2=%.4f' % (bname, len(sel), a2, r2_, r22))
        print('  CEEQ %-8s n=%d MAE=%.3f R2=%.4f' % (bname, len(sel), a2, r22))

    # ---------------- 8. monotonicity check ----------------
    print('=== 8. monotonicity check (predicted CEEQ vs known trends) ===')
    viol = []
    # T: same P/time, higher T -> higher creep
    pairs = [('CR_650_P10_T1000h', 'CR_600_P10_T1000h'),
             ('CR_650_P20_T1000h', 'CR_600_P20_T1000h'),
             ('CR_650_P5_T100h_Rm150_Ro20_w4', 'CR_600_P5_T100h_Rm150_Ro20_w4')]
    pred_map = {r['case_id']: r for r in ceeq_rows}
    for hi, lo in pairs:
        if hi in pred_map and lo in pred_map:
            ok = float(pred_map[hi]['y_pred_log10']) > float(pred_map[lo]['y_pred_log10'])
            viol.append(('T_up', hi, lo, ok))
            print('  T monotonicity %s vs %s: %s' % (hi, lo, 'OK' if ok else 'VIOLATION'))
    # P: higher P -> higher creep (same T/time)
    for hi, lo in (('CR_650_P20_T1000h', 'CR_650_P10_T1000h'),
                   ('CR_650_P20_T3000h_Rm100_Ro20_w4', 'CR_650_P2p5_T3000h_Rm100_Ro20_w4')):
        if hi in pred_map and lo in pred_map:
            ok = float(pred_map[hi]['y_pred_log10']) > float(pred_map[lo]['y_pred_log10'])
            viol.append(('P_up', hi, lo, ok))
            print('  P monotonicity %s vs %s: %s' % (hi, lo, 'OK' if ok else 'VIOLATION'))
    # time: longer -> higher creep
    for hi, lo in (('CR_650_P10_T1000h', 'CR_650_P10_T100h'),
                   ('CR_650_P20_T3000h_Rm100_Ro20_w4', 'CR_650_P20_T1000h_Rm100_Ro20_w4')):
        if hi in pred_map and lo in pred_map:
            ok = float(pred_map[hi]['y_pred_log10']) > float(pred_map[lo]['y_pred_log10'])
            viol.append(('t_up', hi, lo, ok))
            print('  t monotonicity %s vs %s: %s' % (hi, lo, 'OK' if ok else 'VIOLATION'))
    lines.append('monotonicity violations: %d (pairs checked %d)' %
                 (sum(1 for v in viol if not v[3]), len(viol)))

    # ---------------- 9. ablation summary ----------------
    lines.append('=== ablation A/B/C/D (von Mises test R2) ===')
    lines.append('A: 300 data + 12 features = 0.856 (STEP 13.6 XGB0)')
    lines.append('B: 300 data + 16 features = 0.864 (STEP 13.7 all)')
    lines.append('C: 318 data + 12 features = TBD (run)')
    lines.append('D: 318 data + 16 features = 0.9304 (STEP 13.9/13.10)')

    with open(os.path.join(METR, 'step13_10_analysis.txt'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('analysis -> ml/metrics/step13_10_analysis.txt')


def _bin(m, bname, key):
    if key == 'T':
        v = float(m['T_uniform'] or 0)
        return v <= 600 if bname == 'T<=600' else v == 650
    if key == 'P':
        v = float(m['pressure'] or 0)
        return v <= 10 if bname == 'P<=10' else v >= 20
    v = float(m['time'] or 0)
    return v == 1000 if bname == 't=1000' else v == 3000


if __name__ == '__main__':
    main()
