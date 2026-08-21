"""STEP 13.6: extrapolation evaluation + MODEL_B/C grouping + A-only sensitivity.

Model selection rule: validation performance (never test). Best per target:
  von_mises    -> xgb (val R2 0.896)
  displacement -> linear (val MAE 0.70; all models fail extrapolation, reported honestly)
Extrapolation bins: T (<=700/725/750), P (<=20/25/>=30), Rm (<=120/130/140/150),
creep time (<=300/1000/3000, MODEL_C only). A-only = train grade-A rows only.
PEEQ/CEEQ exploratory stats with explicit insufficient-positives marking.
"""
import csv
import json
import os

import numpy as np
import joblib
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEAT = os.path.join(ROOT, 'ml', 'features')
MODELS_DIR = os.path.join(ROOT, 'ml', 'models')
METRICS_DIR = os.path.join(ROOT, 'ml', 'metrics')
AI = os.path.join(ROOT, 'data', 'ai_ready_v3')

np.random.seed(SEED)


def load():
    X = {}
    extra = {}
    meta = {}
    ids = {}
    for s in ('train', 'validation', 'test'):
        X[s] = np.load(os.path.join(FEAT, 'X_%s.npy' % s))
        extra[s] = json.load(open(os.path.join(FEAT, 'y_%s_extra.json' % s)))
        ids[s] = json.load(open(os.path.join(FEAT, 'case_ids_%s.json' % s)))
        meta[s] = {r['case_id']: r for r in
                   csv.DictReader(open(os.path.join(AI, s + '.csv')))}
    return X, extra, meta, ids


def met(y, yp):
    return (mean_absolute_error(y, yp), float(np.sqrt(mean_squared_error(y, yp))),
            r2_score(y, yp))


def bin_report(name, bins, yt, yp, meta, ids, out):
    for bname, sel in bins:
        idx = [i for i, cid in enumerate(ids) if sel(meta[cid])]
        if len(idx) < 3:
            out.append('%s %-12s n=%d (too few, skipped)' % (name, bname, len(idx)))
            continue
        mae, rmse, r2 = met(yt[idx], yp[idx])
        out.append('%s %-12s n=%3d MAE=%8.3f RMSE=%8.3f R2=%7.3f' %
                   (name, bname, len(idx), mae, rmse, r2))


def main():
    X, extra, meta, ids = load()
    lines = []

    # ---- selected models (by validation) ----
    sel = {
        'von_mises': ('xgb_von_mises_raw', 'max_von_mises', 'raw'),
        'displacement': ('linear_displacement_raw', 'max_displacement', 'raw'),
        'displacement_log': ('linear_displacement_log1p', 'max_displacement', 'log1p'),
    }
    for key, (tag, tcol, trf) in sel.items():
        model = joblib.load(os.path.join(MODELS_DIR, tag + '.joblib'))
        lines.append('=== %s (model=%s, transform=%s) ===' % (key, tag, trf))
        for s in ('train', 'validation', 'test'):
            yt = np.asarray(extra[s]['max_von_mises' if 'von' in key else 'max_displacement'], float)
            if trf == 'log1p':
                yp = np.expm1(model.predict(X[s]))
            else:
                yp = model.predict(X[s])
            mae, rmse, r2 = met(yt, yp)
            lines.append('  %-10s n=%3d MAE=%9.3f RMSE=%9.3f R2=%7.3f' % (s, len(yt), mae, rmse, r2))
        # MODEL_B / MODEL_C grouping (test)
        for mt in ('MODEL_B', 'MODEL_C'):
            idx = [i for i, cid in enumerate(ids['test']) if meta['test'][cid]['model_type'] == mt]
            if not idx:
                continue
            yt = np.asarray(extra['test']['max_von_mises' if 'von' in key else 'max_displacement'], float)
            mae, rmse, r2 = met(yt[idx], yp[idx])
            lines.append('  test %-8s n=%3d MAE=%9.3f RMSE=%9.3f R2=%7.3f' % (mt, len(idx), mae, rmse, r2))
        # extrapolation bins (test)
        yt = np.asarray(extra['test']['max_von_mises' if 'von' in key else 'max_displacement'], float)
        bin_report('T', [('<=700', lambda m: float(m['T_uniform'] or m['T_inner'] or 0) <= 700),
                         ('725', lambda m: float(m['T_uniform'] or m['T_inner'] or 0) == 725),
                         ('750', lambda m: float(m['T_uniform'] or m['T_inner'] or 0) == 750)],
                   yt, yp, meta['test'], ids['test'], lines)
        bin_report('P', [('<=20', lambda m: float(m['pressure']) <= 20),
                         ('25', lambda m: float(m['pressure']) == 25),
                         ('>=30', lambda m: float(m['pressure']) >= 30)],
                   yt, yp, meta['test'], ids['test'], lines)
        bin_report('Rm', [('<=120', lambda m: float(m['R_major']) <= 120),
                          ('130', lambda m: float(m['R_major']) == 130),
                          ('140', lambda m: float(m['R_major']) == 140),
                          ('150', lambda m: float(m['R_major']) == 150)],
                   yt, yp, meta['test'], ids['test'], lines)
    # creep-time extrapolation (MODEL_C, displacement + vm)
    lines.append('=== creep time extrapolation (MODEL_C, test vs train) ===')
    for tcol in ('max_displacement', 'max_von_mises'):
        for s in ('train', 'test'):
            idx = [i for i, cid in enumerate(ids[s]) if meta[s][cid]['model_type'] == 'MODEL_C']
            if not idx:
                lines.append('  %-15s %-5s MODEL_C: no samples' % (tcol, s))
                continue
            yt = np.asarray(extra[s][tcol], float)
            yp = np.asarray(extra[s][tcol], float)  # placeholder replaced below
            model = joblib.load(os.path.join(MODELS_DIR,
                                ('xgb_von_mises_raw' if tcol == 'max_von_mises' else 'linear_displacement_raw') + '.joblib'))
            yp = model.predict(X[s]) if tcol == 'max_von_mises' else model.predict(X[s])
            mae, rmse, r2 = met(yt[idx], yp[idx])
            lines.append('  %-15s %-5s MODEL_C n=%2d MAE=%9.3f RMSE=%9.3f R2=%7.3f'
                         % (tcol, s, len(idx), mae, rmse, r2))
        bins = [('<=300', lambda m: float(m['time'] or 0) <= 300),
                ('1000', lambda m: float(m['time'] or 0) == 1000),
                ('3000', lambda m: float(m['time'] or 0) == 3000)]
        idx_all = [i for i, cid in enumerate(ids['test']) if meta['test'][cid]['model_type'] == 'MODEL_C']
        yt = np.asarray(extra['test'][tcol], float)
        model = joblib.load(os.path.join(MODELS_DIR,
                            ('xgb_von_mises_raw' if tcol == 'max_von_mises' else 'linear_displacement_raw') + '.joblib'))
        yp = model.predict(X['test'])
        bin_report('CT', bins, yt, yp, meta['test'], ids['test'], lines)

    # ---- A-only sensitivity ----
    lines.append('=== A+B vs A-only (train on grade A only, test report) ===')
    Xtr, extra_tr, meta_tr, ids_tr = X['train'], extra['train'], meta['train'], ids['train']
    a_idx = [i for i, cid in enumerate(ids_tr) if meta_tr[cid]['quality_grade'] == 'A']
    lines.append('  train grade-A rows: %d (A+B rows: %d)' % (len(a_idx), len(ids_tr)))
    for tcol, tag in (('max_von_mises', 'xgb_von_mises_raw'), ('max_displacement', 'linear_displacement_raw')):
        yt_tr = np.asarray(extra_tr[tcol], float)
        yt_te = np.asarray(extra['test'][tcol], float)
        # A+B (already trained) vs A-only
        ab = joblib.load(os.path.join(MODELS_DIR, tag + '.joblib'))
        ao = joblib.load(os.path.join(MODELS_DIR, tag.replace('xgb_', 'xgb_').replace('linear_', 'linear_') + '.joblib'))
        # retrain A-only equivalent model type
        if 'xgb' in tag:
            m_ao = xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                                    subsample=0.8, colsample_bytree=0.8, random_state=SEED, n_jobs=-1, verbosity=0)
        else:
            m_ao = LinearRegression()
        m_ao.fit(Xtr[a_idx], yt_tr[a_idx])
        for s in ('test',):
            yt = yt_te
            yp_ab = ab.predict(X[s])
            yp_ao = m_ao.predict(X[s])
            m1 = met(yt, yp_ab); m2 = met(yt, yp_ao)
            lines.append('  %-18s A+B: MAE=%8.3f RMSE=%8.3f R2=%7.3f | A-only: MAE=%8.3f RMSE=%8.3f R2=%7.3f'
                         % (tcol, m1[0], m1[1], m1[2], m2[0], m2[1], m2[2]))

    # ---- PEEQ / CEEQ exploratory ----
    lines.append('=== PEEQ/CEEQ exploratory (insufficient positives marking) ===')
    for tcol in ('max_PEEQ', 'max_creep_strain'):
        for s in ('train', 'validation', 'test'):
            v = np.asarray(extra[s][tcol], float)
            nz = int((v > 1e-12).sum())
            lines.append('  %-18s %-10s n=%3d nonzero=%d (%.1f%%)' %
                         (tcol, s, len(v), nz, 100.0 * nz / len(v)))
        v = np.asarray(extra['train'][tcol], float)
        lines.append('  %-18s train nonzero=%d -> %s' %
                     (tcol, int((v > 1e-12).sum()),
                      'insufficient positive training samples: no reliable 2-stage model'
                      if int((v > 1e-12).sum()) < 10 else 'exploratory possible'))

    with open(os.path.join(METRICS_DIR, 'extrapolation_report.txt'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
