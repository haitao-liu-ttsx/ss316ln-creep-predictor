"""STEP 15-C.1: first finite-domain CEEQ field surrogate (v1).

Case-level split (C.0 frozen): TRAIN 31 / VAL 6 / EXT 27 / LOCKED 20.
POD basis fit on TRAIN snapshots ONLY (k=3/4/5). Regressors: Linear/Ridge,
RandomForest, XGBoost, MLP -> POD coefficients. Field-level evaluation on VAL.
EXT target NEVER read here. Time interpolation: linear in CEEQ (steady creep),
grid [1,3,10,30,100,300] for the train pool domain, zero extrapolation.
"""
import json
import os

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'ml', 'data', 'step15_ceeq_snapshots')
METR = os.path.join(ROOT, 'ml', 'metrics')
FINAL = os.path.join(ROOT, 'ml', 'final', 'step15_v1')
os.makedirs(FINAL, exist_ok=True)
np.random.seed(SEED)

c0 = json.load(open(os.path.join(METR, 'step15_c0_split_audit.json')))
TRAIN_IDS = c0['train']['ids']
VAL_IDS = c0['validation']['ids']
print('TRAIN=%d VAL=%d' % (len(TRAIN_IDS), len(VAL_IDS)))
TIME_GRID = [1, 3, 10, 30, 100, 300]  # train-pool domain (t<=300), zero extrapolation


def load_snapshots(ids):
    """case-level snapshots: (case, t_grid point within case coverage) -> field."""
    out = []
    for cid in ids:
        d = np.load(os.path.join(DATA, cid + '.npz'))
        F = d['ceeq_frames']          # [n_frames, 2304]
        T = d['frame_times']
        t_max = float(T[-1])
        for tg in TIME_GRID:
            if tg > t_max + 1e-9:
                continue              # no extrapolation
            # linear interpolation in time (steady creep: CEEQ ~ t)
            if tg <= T[0]:
                f = F[0]
            else:
                i = np.searchsorted(T, tg)
                i = min(i, len(T) - 1)
                t0, t1 = float(T[i - 1]), float(T[i])
                w = (tg - t0) / (t1 - t0)
                f = F[i - 1] * (1 - w) + F[i] * w
            out.append({'case': cid, 't': tg, 'field': f})
    return out


def case_feats(cid, t, meta):
    r = meta[cid]
    T = int(float(r['T_uniform']))
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    return np.array([T, float(r['pressure']), np.log1p(t),
                     float(r['R_major']), float(r['R_outer']),
                     float(r['wall_thickness']), E_T[T], CREEP[T][0], CREEP[T][1]])


import csv
meta = {r['case_id']: r for r in
        csv.DictReader(open(os.path.join(ROOT, 'data', 'ai_ready_v4', 'simulation_dataset_318.csv')))}

tr_s = load_snapshots(TRAIN_IDS)
va_s = load_snapshots(VAL_IDS)
print('snapshots: train=%d val=%d' % (len(tr_s), len(va_s)))
Xtr = np.array([case_feats(s['case'], s['t'], meta) for s in tr_s])
Ytr = np.array([s['field'] for s in tr_s])
Xva = np.array([case_feats(s['case'], s['t'], meta) for s in va_s])
Yva = np.array([s['field'] for s in va_s])
print('X shapes:', Xtr.shape, Xva.shape)

# ---------------- POD in log10 domain (train-only) ----------------
# raw-domain coefficients are ~1e-15 -> regression impossible; log10 domain
# coefficients are O(1). Reconstruction: 10^(mu + c.M) -> CEEQ >= 0 by construction.
LG = np.log10(Ytr)                 # [n, 2304]
results = []
for k in (3, 4, 5):
    mu = LG.mean(axis=0)
    Xc = LG - mu
    U, s, Vt = np.linalg.svd(Xc, full_matrices=False)
    modes = Vt[:k].T            # [2304, k]
    coeff_tr = Xc @ modes       # [n_tr, k]
    coeff_va = (np.log10(Yva) - mu) @ modes
    cumvar = (s ** 2).cumsum() / (Xc ** 2).sum()
    rec_tr = 10 ** (mu + coeff_tr @ modes.T)
    rec_va = 10 ** (mu + coeff_va @ modes.T)
    tr_fmae = np.abs(Ytr - rec_tr).mean()
    va_fmae = np.abs(Yva - rec_va).mean()
    tr_lmae = np.abs(np.log10(Ytr) - np.log10(rec_tr)).mean()
    va_lmae = np.abs(np.log10(Yva) - np.log10(rec_va)).mean()
    print('k=%d cumvar=%.5f | log10-POD rec: train MAE=%.3e logMAE=%.4f | val MAE=%.3e logMAE=%.4f'
          % (k, cumvar[k - 1], tr_fmae, tr_lmae, va_fmae, va_lmae))
    # ---------------- coefficient regressors ----------------
    scaler = StandardScaler().fit(Xtr)   # TRAIN-only
    Xtr_s, Xva_s = scaler.transform(Xtr), scaler.transform(Xva)
    models = {
        'ridge': Ridge(alpha=1.0),
        'rf': RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=-1),
        'xgb': xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                                subsample=0.8, colsample_bytree=0.8,
                                random_state=SEED, n_jobs=-1, verbosity=0),
        'mlp': MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=3000,
                            random_state=SEED),
    }
    for mname, m in models.items():
        preds = np.zeros_like(coeff_va)
        for j in range(k):
            mj = m if mname != 'mlp' else MLPRegressor(hidden_layer_sizes=(64, 32),
                                                       max_iter=3000, random_state=SEED)
            mj.fit(Xtr_s, coeff_tr[:, j])
            preds[:, j] = mj.predict(Xva_s)
        Yp = 10 ** (mu + preds @ modes.T)     # raw-domain reconstruction
        fmae = np.abs(Yva - Yp).mean()
        frmse = float(np.sqrt(((Yva - Yp) ** 2).mean()))
        # robust relative L2: denominator with floor to avoid near-zero blow-up
        denom = np.sqrt((np.maximum(Yva, 1e-20) ** 2).sum())
        rel_l2 = float(np.linalg.norm(Yva - Yp) / denom)
        max_err = float(np.abs(Yva - Yp).max())
        # log-domain field error
        lmae = float(np.abs(np.log10(Yva) - np.log10(np.maximum(Yp, 1e-300))).mean())
        lrmse = float(np.sqrt((np.log10(Yva) - np.log10(np.maximum(Yp, 1e-300))) ** 2).mean())
        c_mae = np.abs(coeff_va - preds).mean(axis=0)
        c_r2 = [r2_score(coeff_va[:, j], preds[:, j]) for j in range(k)]
        results.append({'pod_k': k, 'model': mname,
                        'val_coef_MAE': [round(float(v), 5) for v in c_mae],
                        'val_coef_R2': [round(float(v), 4) for v in c_r2],
                        'val_field_MAE': round(float(fmae), 6),
                        'val_field_RMSE': round(frmse, 6),
                        'val_rel_L2': round(rel_l2, 6),
                        'val_max_err': round(max_err, 6),
                        'val_log_MAE': round(lmae, 4), 'val_log_RMSE': round(lrmse, 4)})
        print('  k=%d %-5s val coefR2=%s field MAE=%.3e logMAE=%.4f relL2=%.5f max=%.3e'
              % (k, mname, [round(v, 3) for v in c_r2], fmae, lmae, rel_l2, max_err))
    # save basis for k
    np.savez(os.path.join(FINAL, 'pod_basis_k%d.npz' % k),
             mean_field=mu, modes=modes, singular_values=s,
             cumvar=cumvar, train_ids=TRAIN_IDS)

import csv as _csv
with open(os.path.join(METR, 'step15_c1_model_comparison.csv'), 'w', newline='') as f:
    w = _csv.DictWriter(f, fieldnames=list(results[0].keys()))
    w.writeheader()
    for r in results:
        w.writerow(r)
print('model comparison written')
# quick best-by-field-MAE summary
best = min(results, key=lambda r: r['val_field_MAE'])
print('BEST by VAL field MAE: k=%d model=%s MAE=%.3e relL2=%.4f' %
      (best['pod_k'], best['model'], best['val_field_MAE'], best['val_rel_L2']))
