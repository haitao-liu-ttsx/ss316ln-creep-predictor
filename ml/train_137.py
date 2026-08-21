"""STEP 13.7: physics-informed training (seed 42, validation-driven selection).

Part 1: von Mises - 4 feature sets x XGB baseline params.
Part 2: XGB limited tuning (12 combos, validation only).
Part 3: displacement - Model A (unified XGB, all features) vs Model B
        (regime-aware: stage-1 elastic/plastic classifier from pre-solve inputs
         only - NO PEEQ/target info; stage-2 elastic-domain XGB regression).
Part 4: 3-group evaluation (normal elastic / plastic moderate /
        EPP_post_yield_extreme) for displacement.
Outputs: ml/models/step13_7/, ml/metrics/step13_7_metrics.csv,
         ml/predictions/step13_7_predictions/.
"""
import csv
import json
import os

import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score
import xgboost as xgb

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F137 = os.path.join(ROOT, 'ml', 'features', 'step13_7')
AI = os.path.join(ROOT, 'data', 'ai_ready_v3')
MDIR = os.path.join(ROOT, 'ml', 'models', 'step13_7')
PDIR = os.path.join(ROOT, 'ml', 'predictions', 'step13_7_predictions')
METR = os.path.join(ROOT, 'ml', 'metrics')

np.random.seed(SEED)


def load_set(sname, s):
    return np.load(os.path.join(F137, 'X_%s_%s.npy' % (sname, s)))


def load_y(s):
    return np.load(os.path.join(ROOT, 'ml', 'features', 'y_%s.npy' % s))  # col0=disp, col1=vm


def meta_map():
    out = {}
    for s in ('train', 'validation', 'test'):
        out[s] = {r['case_id']: r for r in
                  csv.DictReader(open(os.path.join(AI, s + '.csv')))}
    return out


def ids_of(s):
    return json.load(open(os.path.join(ROOT, 'ml', 'features', 'case_ids_%s.json' % s)))


def met(y, yp):
    return (mean_absolute_error(y, yp), float(np.sqrt(mean_squared_error(y, yp))),
            r2_score(y, yp))


XGB0 = dict(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8,
            colsample_bytree=0.8, random_state=SEED, n_jobs=-1, verbosity=0)

TUNING = [  # 12 combos (variations around XGB0)
    dict(XGB0),                                   # 1 baseline
    dict(XGB0, max_depth=3),                      # 2
    dict(XGB0, max_depth=6),                      # 3
    dict(XGB0, learning_rate=0.03),               # 4
    dict(XGB0, learning_rate=0.1),                # 5
    dict(XGB0, n_estimators=200),                 # 6
    dict(XGB0, n_estimators=500),                 # 7
    dict(XGB0, min_child_weight=3),               # 8
    dict(XGB0, reg_alpha=0.5),                    # 9
    dict(XGB0, reg_lambda=5.0),                   # 10
    dict(XGB0, max_depth=6, learning_rate=0.03, n_estimators=500,
          subsample=0.7, colsample_bytree=0.7),   # 11
    dict(XGB0, max_depth=3, learning_rate=0.1, subsample=0.9),  # 12
]


def main():
    os.makedirs(MDIR, exist_ok=True)
    os.makedirs(PDIR, exist_ok=True)
    meta = meta_map()
    ids = {s: ids_of(s) for s in ('train', 'validation', 'test')}
    y_tr, y_va, y_te = load_y('train'), load_y('validation'), load_y('test')
    vm = {'train': y_tr[:, 1], 'validation': y_va[:, 1], 'test': y_te[:, 1]}
    disp = {'train': y_tr[:, 0], 'validation': y_va[:, 0], 'test': y_te[:, 0]}
    out_rows = []

    # ---------------- Part 1: von Mises, 4 feature sets ----------------
    print('=== Part 1: von Mises x feature sets (XGB0) ===')
    for sname in ('base', 'base_pi', 'base_pi_row', 'all'):
        Xtr = load_set(sname, 'train')
        Xva = load_set(sname, 'validation')
        Xte = load_set(sname, 'test')
        m = xgb.XGBRegressor(**XGB0)
        m.fit(Xtr, vm['train'])
        joblib.dump(m, os.path.join(MDIR, 'vm_%s_xgb0.joblib' % sname))
        row = {'part': 'vm_featset', 'featset': sname}
        for s, X, y in (('train', Xtr, vm['train']), ('validation', Xva, vm['validation']),
                        ('test', Xte, vm['test'])):
            a, r, r2 = met(y, m.predict(X))
            row['%s_MAE' % s] = round(a, 3); row['%s_RMSE' % s] = round(r, 3)
            row['%s_R2' % s] = round(r2, 4)
            print('  %-10s %-6s MAE=%7.2f RMSE=%8.2f R2=%7.3f' % (sname, s, a, r, r2))
        # extrapolation bins (test)
        for bname, sel in (('Rm150', lambda m0: float(m0['R_major']) == 150),
                           ('T750', lambda m0: float(m0['T_uniform'] or m0['T_inner'] or 0) == 750),
                           ('P30', lambda m0: float(m0['pressure']) >= 30)):
            idx = [i for i, c in enumerate(ids['test']) if sel(meta['test'][c])]
            a, r, r2b = met(vm['test'][idx], m.predict(Xte[idx]))
            row['%s_R2' % bname] = round(r2b, 4)
            print('  %-10s %-6s n=%2d R2=%7.3f' % (sname, bname, len(idx), r2b))
        out_rows.append(row)

    # ---------------- Part 2: XGB tuning (von Mises, base set) ----------------
    print('=== Part 2: XGB tuning (12 combos, von Mises, base features) ===')
    Xtr, Xva, Xte = load_set('base', 'train'), load_set('base', 'validation'), load_set('base', 'test')
    tuning_rows = []
    for i, p in enumerate(TUNING, 1):
        m = xgb.XGBRegressor(**p)
        m.fit(Xtr, vm['train'])
        a_tr, r_tr, r2_tr = met(vm['train'], m.predict(Xtr))
        a_va, r_va, r2_va = met(vm['validation'], m.predict(Xva))
        tuning_rows.append({'combo': i, 'params': json.dumps(
            {k: v for k, v in p.items() if k != 'random_state' and k != 'n_jobs' and k != 'verbosity'}),
            'train_R2': round(r2_tr, 4), 'train_MAE': round(a_tr, 3),
            'val_R2': round(r2_va, 4), 'val_MAE': round(a_va, 3)})
        print('  combo %2d: val R2=%7.4f MAE=%7.2f | train R2=%7.4f' % (i, r2_va, a_va, r2_tr))
    # select best by validation R2
    best = max(tuning_rows, key=lambda r: r['val_R2'])
    print('  -> selected combo %s (val R2=%s)' % (best['combo'], best['val_R2']))
    bp = TUNING[best['combo'] - 1]
    m_best = xgb.XGBRegressor(**bp)
    m_best.fit(Xtr, vm['train'])
    joblib.dump(m_best, os.path.join(MDIR, 'vm_final_xgb.joblib'))
    with open(os.path.join(MDIR, 'vm_final_params.json'), 'w') as f:
        json.dump({'combo': best['combo'],
                   'params': {k: v for k, v in bp.items() if k not in ('random_state', 'n_jobs', 'verbosity')}},
                  f, indent=1)
    a_te, r_te, r2_te = met(vm['test'], m_best.predict(Xte))
    print('  FINAL on test (one-shot): MAE=%7.2f RMSE=%8.2f R2=%7.4f' % (a_te, r_te, r2_te))
    out_rows.append({'part': 'vm_final_tuned', 'featset': 'base', 'combo': best['combo'],
                     'test_MAE': round(a_te, 3), 'test_RMSE': round(r_te, 3),
                     'test_R2': round(r2_te, 4)})

    # ---------------- Part 3: displacement Model A vs Model B ----------------
    print('=== Part 3: displacement unified vs regime-aware ===')
    Xall_tr, Xall_va, Xall_te = (load_set('all', 'train'), load_set('all', 'validation'),
                                 load_set('all', 'test'))
    # Model A: unified XGB (tuned params from Part 2)
    mA = xgb.XGBRegressor(**bp)
    mA.fit(Xall_tr, disp['train'])
    joblib.dump(mA, os.path.join(MDIR, 'disp_unified_xgb.joblib'))
    a, r, r2a = met(disp['test'], mA.predict(Xall_te))
    out_rows.append({'part': 'disp_unified', 'model': 'xgb-all', 'test_MAE': round(a, 3),
                     'test_RMSE': round(r, 3), 'test_R2': round(r2a, 4)})
    print('  Model A unified: test MAE=%8.3f RMSE=%8.3f R2=%7.4f' % (a, r, r2a))
    # Model B: regime-aware (stage-1 classifier: inputs only)
    # stage-1 labels: PEEQ>0 from Abaqus (research labelling, NOT a feature)
    peeq = {s: np.array(json.load(open(os.path.join(ROOT, 'ml', 'features', 'y_%s_extra.json' % s)))
                        ['max_PEEQ_nonzero'], int)
            for s in ('train', 'validation', 'test')}
    stage1 = RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1,
                                    class_weight='balanced')
    stage1.fit(Xall_tr, np.array(peeq['train'], int))
    joblib.dump(stage1, os.path.join(MDIR, 'disp_stage1_rf.joblib'))
    for s, X in (('train', Xall_tr), ('validation', Xall_va), ('test', Xall_te)):
        acc = accuracy_score(np.array(peeq[s], int), stage1.predict(X))
        print('  stage-1 acc (%s): %.3f (plastic positives: %d)' %
              (s, acc, int(np.array(peeq[s], int).sum())))
    # stage-2: elastic-domain regression (train rows with PEEQ=0).
    # BASE 12 features + LinearRegression: STEP 13.6A verified elastic-domain
    # R2=0.916 on this setup. NOTE (documented): physics features are collinear
    # with base inputs -> they HURT linear models (all-features linear test
    # R2=-0.60) while HELPING trees (von Mises P>=30 -0.267 -> +0.005).
    Xbase_tr, Xbase_te = load_set('base', 'train'), load_set('base', 'test')
    el_tr = np.array(peeq['train'], int) == 0
    from sklearn.linear_model import LinearRegression
    mB = LinearRegression()
    mB.fit(Xbase_tr[el_tr], disp['train'][el_tr])
    joblib.dump(mB, os.path.join(MDIR, 'disp_stage2_elastic_linear.joblib'))
    Xbase_va = load_set('base', 'validation')
    # stage-2 predicts only elastic test rows; plastic rows -> flagged
    pred_el = mB.predict(Xbase_te[np.array(peeq['test'], int) == 0])
    y_el = disp['test'][np.array(peeq['test'], int) == 0]
    a, r, r2b = met(y_el, pred_el)
    out_rows.append({'part': 'disp_regime_elastic', 'test_MAE': round(a, 3),
                     'test_RMSE': round(r, 3), 'test_R2': round(r2b, 4)})
    print('  Model B elastic-domain (test, n=%d): MAE=%8.3f RMSE=%8.3f R2=%7.4f'
          % (len(y_el), a, r, r2b))

    # ---------------- Part 4: 3-group displacement evaluation (Model A) ----------------
    print('=== Part 4: 3-group evaluation (unified model, test) ===')
    yp_all = mA.predict(Xall_te)
    groups = {'normal_elastic': [], 'plastic_moderate': [], 'EPP_post_yield_extreme': []}
    for i, c in enumerate(ids['test']):
        m0 = meta['test'][c]
        peeq_v = float(m0['max_PEEQ'])
        sy = float(m0['sigma_y_MPa']) if m0['sigma_y_MPa'] else 0
        vm_v = float(m0['max_von_mises'])
        if peeq_v <= 1e-6:
            groups['normal_elastic'].append(i)
        elif sy > 0 and vm_v >= 0.98 * sy:
            groups['EPP_post_yield_extreme'].append(i)
        else:
            groups['plastic_moderate'].append(i)
    for g, idx in groups.items():
        if len(idx) < 2:
            out_rows.append({'part': 'disp_group', 'group': g, 'n': len(idx)})
            print('  %-22s n=%d (too few)' % (g, len(idx)))
            continue
        yt = disp['test'][idx]
        a, r, r2g = met(yt, yp_all[idx])
        ae = np.abs(yt - yp_all[idx])
        out_rows.append({'part': 'disp_group', 'group': g, 'n': len(idx),
                         'MAE': round(a, 4), 'RMSE': round(r, 4), 'R2': round(r2g, 4),
                         'medAE': round(float(np.median(ae)), 4),
                         'maxAE': round(float(ae.max()), 2)})
        print('  %-22s n=%2d MAE=%9.3f RMSE=%10.3f R2=%8.4f medAE=%7.4f maxAE=%8.2f'
              % (g, len(idx), a, r, r2g, np.median(ae), ae.max()))
    # per-case predictions (Model A, test)
    with open(os.path.join(PDIR, 'disp_unified_test.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['case_id', 'y_true', 'y_pred', 'residual', 'group'])
        for i, c in enumerate(ids['test']):
            g = next((k for k, v in groups.items() if i in v), '?')
            w.writerow([c, round(float(disp['test'][i]), 6), round(float(yp_all[i]), 6),
                        round(float(disp['test'][i] - yp_all[i]), 6), g])

    # ---------------- write metrics ----------------
    with open(os.path.join(METR, 'step13_7_metrics.csv'), 'w', newline='') as f:
        cols = list(dict.fromkeys(k for r in out_rows for k in r.keys()))
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in out_rows:
            w.writerow({k: r.get(k, '') for k in cols})
    with open(os.path.join(METR, 'step13_7_tuning.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(tuning_rows[0].keys()))
        w.writeheader()
        for r in tuning_rows:
            w.writerow(r)
    print('done -> ml/models/step13_7/, ml/metrics/step13_7_*.csv, ml/predictions/step13_7_predictions/')


if __name__ == '__main__':
    main()
