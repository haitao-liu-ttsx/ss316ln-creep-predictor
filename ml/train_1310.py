"""STEP 13.10: final validation - vm tuning (<=6 combos), stage-1 regime
calibration (physics threshold vs ML classifier), stage-2 stability, unified
and plastic/EPP displacement reporting. seed 42, validation-driven.
"""
import csv
import json
import os

import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (mean_absolute_error, mean_squared_error, r2_score,
                             accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix)
import xgboost as xgb

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, 'ml', 'features', 'v4')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
MDIR = os.path.join(ROOT, 'ml', 'models', 'step13_10')
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
    lines = []

    # ---------------- 1. von Mises tuning (<=6 combos) ----------------
    base = dict(n_estimators=300, max_depth=4, learning_rate=0.1, subsample=0.8,
                colsample_bytree=0.8, random_state=SEED, n_jobs=-1, verbosity=0)
    combos = [
        ('base13.9', dict(base)),                                        # 1 baseline
        ('lr0.05', dict(base, learning_rate=0.05)),                     # 2
        ('depth6', dict(base, max_depth=6)),                            # 3
        ('n500', dict(base, n_estimators=500)),                         # 4
        ('mincw3', dict(base, min_child_weight=3)),                     # 5
        ('reg_l2', dict(base, reg_lambda=2.0)),                         # 6
    ]
    tuning = []
    for name, p in combos:
        m = xgb.XGBRegressor(**p)
        m.fit(X['train'], vm['train'])
        a_tr, r_tr, r2_tr = met(vm['train'], m.predict(X['train']))
        a_va, r_va, r2_va = met(vm['validation'], m.predict(X['validation']))
        tuning.append({'combo': name, 'train_R2': round(r2_tr, 4), 'val_MAE': round(a_va, 3),
                       'val_RMSE': round(r_va, 3), 'val_R2': round(r2_va, 4)})
        print('tune %-10s val R2=%.4f MAE=%.2f | train R2=%.4f' % (name, r2_va, a_va, r2_tr))
    best_name = max(tuning, key=lambda r: r['val_R2'])['combo']
    best_p = dict(combos[[c[0] for c in combos].index(best_name)][1])
    m_best = xgb.XGBRegressor(**best_p)
    m_best.fit(X['train'], vm['train'])
    joblib.dump(m_best, os.path.join(MDIR, 'vm_final_xgb.joblib'))
    print('SELECTED by validation only: %s (val R2=%.4f)' % (best_name, max(t['val_R2'] for t in tuning)))
    lines.append('vm_selected=%s (validation-only)' % best_name)
    # baseline (13.9 combo) vs best: test one-shot + extrapolation
    m_base = xgb.XGBRegressor(**base)
    m_base.fit(X['train'], vm['train'])
    for mname, m in (('baseline13.9', m_base), ('best_tuned', m_best)):
        a, r, r2v = met(vm['test'], m.predict(X['test']))
        print('%s test: MAE=%.2f RMSE=%.2f R2=%.4f' % (mname, a, r, r2v))
        lines.append('vm_%s_test MAE=%.3f RMSE=%.3f R2=%.4f' % (mname, a, r, r2v))
        for bname, sel in (('Rm150', lambda m0: float(m0['R_major']) == 150),
                           ('T750', lambda m0: float(m0['T_uniform'] or m0['T_inner'] or 0) == 750),
                           ('P25', lambda m0: float(m0['pressure']) == 25),
                           ('P30', lambda m0: float(m0['pressure']) >= 30),
                           ('MB', lambda m0: m0['model_type'] == 'MODEL_B'),
                           ('MC', lambda m0: m0['model_type'] == 'MODEL_C')):
            idx = [i for i, c in enumerate(ids['test']) if sel(meta['test'][c])]
            a2, r2_, r22 = met(vm['test'][idx], m.predict(X['test'][idx]))
            lines.append('vm_%s_%s n=%d MAE=%.3f RMSE=%.3f R2=%.4f' % (mname, bname, len(idx), a2, r2_, r22))
    with open(os.path.join(METR, 'step13_10_tuning.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(tuning[0].keys()))
        w.writeheader()
        for r in tuning:
            w.writerow(r)

    # ---------------- 2. stage-1: physics threshold vs ML classifier ----------------
    print('=== 2. regime: physics threshold vs ML classifier (test) ===')
    peeq_nz = {s: np.array(extra[s]['max_PEEQ_nonzero'], int) for s in ('train', 'validation', 'test')}
    feat_idx = {n: i for i, n in enumerate(json.load(open(os.path.join(F, 'feature_names.json')))['features'])}
    pi_idx = feat_idx['Pi_yield']
    y_true = peeq_nz['test']
    regime_rows = []
    print('  %-14s %8s %8s %8s %8s %8s' % ('method', 'acc', 'prec', 'rec', 'F1', 'pl_rec'))
    for tau in (0.95, 1.0, 1.05, 1.10, 1.15):
        pred = (X['test'][:, pi_idx] >= tau).astype(int)
        acc = accuracy_score(y_true, pred)
        prec = precision_score(y_true, pred, zero_division=0)
        rec = recall_score(y_true, pred, zero_division=0)
        f1 = f1_score(y_true, pred, zero_division=0)
        regime_rows.append({'method': 'pi_thr_%.2f' % tau, 'acc': round(acc, 3),
                            'prec': round(prec, 3), 'rec': round(rec, 3),
                            'f1': round(f1, 3), 'detail': ''})
        print('  pi>=%-8.2f %8.3f %8.3f %8.3f %8.3f %8.3f' % (tau, acc, prec, rec, f1, rec))
    s1 = RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1,
                                class_weight='balanced')
    s1.fit(X['train'], peeq_nz['train'])
    joblib.dump(s1, os.path.join(MDIR, 'stage1_rf.joblib'))
    pred = s1.predict(X['test'])
    acc = accuracy_score(y_true, pred)
    prec = precision_score(y_true, pred, zero_division=0)
    rec = recall_score(y_true, pred, zero_division=0)
    f1 = f1_score(y_true, pred, zero_division=0)
    cm = confusion_matrix(y_true, pred)
    regime_rows.append({'method': 'ml_rf', 'acc': round(acc, 3), 'prec': round(prec, 3),
                        'rec': round(rec, 3), 'f1': round(f1, 3),
                        'detail': 'confusion TN=%d FP=%d FN=%d TP=%d' %
                                  (int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1]))})
    print('  %-14s %8.3f %8.3f %8.3f %8.3f %8.3f' % ('ml_rf', acc, prec, rec, f1, rec))
    print('  confusion (TN FP / FN TP):', cm.tolist())
    with open(os.path.join(METR, 'step13_10_regime.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['method', 'acc', 'prec', 'rec', 'f1', 'detail'])
        w.writeheader()
        for r in regime_rows:
            w.writerow(r)

    # ---------------- 3. stage-2 elastic displacement stability ----------------
    el_tr = peeq_nz['train'] == 0
    s2 = LinearRegression()
    s2.fit(X['train'][el_tr], disp['train'][el_tr])
    joblib.dump(s2, os.path.join(MDIR, 'stage2_elastic_linear.joblib'))
    el_te = peeq_nz['test'] == 0
    y_el, yp_el = disp['test'][el_te], s2.predict(X['test'][el_te])
    a, r, r2e = met(y_el, yp_el)
    ae = np.abs(y_el - yp_el)
    print('stage-2 elastic (13.10): MAE=%.4f RMSE=%.4f R2=%.4f medAE=%.4f maxAE=%.4f (n=%d)'
          % (a, r, r2e, np.median(ae), ae.max(), len(y_el)))
    lines.append('stage2_elastic R2=%.4f MAE=%.4f RMSE=%.4f medAE=%.4f maxAE=%.4f n=%d' %
                 (r2e, a, r, np.median(ae), ae.max(), len(y_el)))
    # history: 13.7 = 0.9166, 13.9 = 0.9167 -> stability if |diff|<0.02
    lines.append('stage2_stability: 13.7=0.9166 13.9=0.9167 13.10=%.4f -> %s' %
                 (r2e, 'STABLE (<0.02 change)' if abs(r2e - 0.9167) < 0.02 else 'CHANGED'))

    # ---------------- 4. unified displacement ----------------
    m_u = xgb.XGBRegressor(**base)
    m_u.fit(X['train'], disp['train'])
    a, r, r2u = met(disp['test'], m_u.predict(X['test']))
    print('unified XGB (13.10): MAE=%.3f RMSE=%.3f R2=%.4f' % (a, r, r2u))
    lines.append('unified_disp R2=%.4f (13.9=0.350)' % r2u)

    # ---------------- 5. plastic/EPP displacement reporting ----------------
    pl_te = peeq_nz['test'] == 1
    if pl_te.sum() > 0:
        y_pl = disp['test'][pl_te]
        yp_pl = m_u.predict(X['test'][pl_te])
        a, r, r2p = met(y_pl, yp_pl)
        ae = np.abs(y_pl - yp_pl)
        print('plastic (n=%d): MAE=%.3f RMSE=%.3f R2=%.4f medAE=%.3f maxAE=%.3f' %
              (pl_te.sum(), a, r, r2p, np.median(ae), ae.max()))
        lines.append('plastic_disp MAE=%.3f RMSE=%.3f R2=%.4f medAE=%.3f maxAE=%.3f '
                     '-> exploratory / insufficient reliable generalization' %
                     (a, r, r2p, np.median(ae), ae.max()))
        # extreme cases retained
        extreme = [(c, float(disp['test'][i])) for i, c in enumerate(ids['test'])
                   if pl_te[i] and float(disp['test'][i]) > 20]
        lines.append('plastic extreme retained: %s' % extreme)

    with open(os.path.join(METR, 'step13_10_metrics.txt'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('done -> ml/models/step13_10/, ml/metrics/step13_10_*')


if __name__ == '__main__':
    main()
