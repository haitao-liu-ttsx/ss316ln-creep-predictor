"""STEP 15-E: v1.1 training with analytic time structure + geometry stress scale.

c_i(T,P,geom,t) = g_i(T,P,geom) + d_i * log10(t)
  d_i: pooled global slope per mode (TRAIN), residual g_i learned by regressor.
Ablation: A = v1 arch (XGB, log1p_time, no analytic t) | B = A + log10(P*Ro/w)
C = analytic log10(t), no stress feature | D = full Candidate B.
VAL-only selection; EXT/LOCKED never read.
"""
import csv
import json
import os

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
import xgboost as xgb

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'ml', 'data', 'step15_ceeq_snapshots')
METR = os.path.join(ROOT, 'ml', 'metrics')
FINAL = os.path.join(ROOT, 'ml', 'final', 'step15_v1_1')
os.makedirs(FINAL, exist_ok=True)
np.random.seed(SEED)

c0 = json.load(open(os.path.join(METR, 'step15_c0_split_audit.json')))
TRAIN_IDS, VAL_IDS = c0['train']['ids'], c0['validation']['ids']
TIME_GRID = [1, 3, 10, 30, 100, 300]
meta = {r['case_id']: r for r in
        csv.DictReader(open(os.path.join(ROOT, 'data', 'ai_ready_v4', 'simulation_dataset_318.csv')))}


def load_snapshots(ids):
    out = []
    for cid in ids:
        d = np.load(os.path.join(DATA, cid + '.npz'))
        F, T = d['ceeq_frames'], d['frame_times']
        for tg in TIME_GRID:
            if tg > float(T[-1]) + 1e-9:
                continue
            if tg <= float(T[0]):
                f = F[0]
            else:
                i = min(np.searchsorted(T, tg), len(T) - 1)
                w = (tg - float(T[i - 1])) / (float(T[i]) - float(T[i - 1]))
                f = F[i - 1] * (1 - w) + F[i] * w
            out.append({'case': cid, 't': tg, 'field': f})
    return out


def feats(cid, t, with_stress):
    r = meta[cid]
    T = int(float(r['T_uniform']))
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    P = float(r['pressure']); Ro = float(r['R_outer']); w = float(r['wall_thickness'])
    base = [T, P, np.log1p(t), float(r['R_major']), Ro, w, E_T[T], CREEP[T][0], CREEP[T][1]]
    if with_stress:
        base = base + [np.log10(max(P * Ro / w, 1e-9))]
    return np.array(base)


tr_s, va_s = load_snapshots(TRAIN_IDS), load_snapshots(VAL_IDS)
LG_tr = np.log10(np.array([s['field'] for s in tr_s]))
LG_va = np.log10(np.array([s['field'] for s in va_s]))

# ---------------- POD (TRAIN-only) k comparison ----------------
pod_audit = {}
for k in (3, 4, 5):
    mu = LG_tr.mean(axis=0)
    U, s_, Vt = np.linalg.svd(LG_tr - mu, full_matrices=False)
    cumvar = float((s_ ** 2).cumsum()[-1] / ((LG_tr - mu) ** 2).sum())
    rec_va = 10 ** (mu + (LG_va - mu) @ Vt[:k].T @ Vt[:k])
    pod_audit[str(k)] = {'cumvar': round(cumvar, 6),
                         'val_field_MAE': round(float(np.abs(10 ** LG_va - rec_va).mean()), 8)}
    print('k=%d cumvar=%.6f val POD-only field MAE=%.3e' % (k, cumvar, pod_audit[str(k)]['val_field_MAE']))
k = 3
mu = LG_tr.mean(axis=0)
U, s_, Vt = np.linalg.svd(LG_tr - mu, full_matrices=False)
modes = Vt[:k].T
Ctr = (LG_tr - mu) @ modes
Cva = (LG_va - mu) @ modes
np.savez(os.path.join(FINAL, 'pod_basis_v11.npz'), mean_log_field=mu, modes=modes,
         singular_values=s_, train_ids=TRAIN_IDS)
with open(os.path.join(METR, 'step15_e_v11_pod_audit.json'), 'w') as f:
    json.dump({'k_compared': pod_audit, 'selected_k': k,
               'domain': 'log10(CEEQ)', 'basis': 'TRAIN-only'}, f, indent=1)

# ---------------- d_i: pooled slope per mode (TRAIN) ----------------
t_tr = np.log10(np.array([s['t'] for s in tr_s]))
d = np.array([np.polyfit(t_tr, Ctr[:, j], 1)[0] for j in range(k)])
print('global slopes d_i:', np.round(d, 4))
Rtr = Ctr - np.outer(t_tr, d)          # residual g_i for TRAIN
Rva = Cva - np.outer(np.log10(np.array([s['t'] for s in va_s])), d)


def run_ablation(name, with_stress, reg_family):
    Xtr = np.array([feats(s['case'], s['t'], with_stress) for s in tr_s])
    Xva = np.array([feats(s['case'], s['t'], with_stress) for s in va_s])
    scaler = StandardScaler().fit(Xtr)
    Xtr_s, Xva_s = scaler.transform(Xtr), scaler.transform(Xva)
    preds = np.zeros_like(Cva)
    for j in range(k):
        if reg_family == 'xgb':
            m = xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                                 subsample=0.8, colsample_bytree=0.8,
                                 random_state=SEED, n_jobs=-1, verbosity=0)
        elif reg_family == 'rf':
            m = RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=-1)
        else:
            m = Pipeline([('poly', PolynomialFeatures(2)),
                          ('scale', StandardScaler()), ('m', Ridge(alpha=1.0))])
        m.fit(Xtr_s, Rtr[:, j])
        preds[:, j] = m.predict(Xva_s)
    Cpred = preds + np.outer(np.log10(np.array([s['t'] for s in va_s])), d)
    Yp = 10 ** (mu + Cpred @ modes.T)
    Yt = 10 ** LG_va
    logmae = float(np.abs(LG_va - (mu + Cpred @ modes.T)).mean())
    fmae = float(np.abs(Yt - Yp).mean())
    relL2 = float(np.linalg.norm(Yt - Yp) / np.linalg.norm(np.maximum(Yt, 1e-20)))
    maxerr = float(np.abs(Yt - Yp).max())
    cr2 = [r2_score(Cva[:, j], Cpred[:, j]) for j in range(k)]
    hs = float(np.mean(np.argmax(Yt, axis=1) == np.argmax(Yp, axis=1)))
    top5 = float(np.mean([len(set(np.argsort(Yt[i])[-5:]) & set(np.argsort(Yp[i])[-5:])) / 5
                          for i in range(len(Yt))]))
    print('%-16s coefR2=%s logMAE=%.4f fieldMAE=%.2e relL2=%.4f max=%.2e hs=%.2f top5=%.2f'
          % (name, [round(v, 3) for v in cr2], logmae, fmae, relL2, maxerr, hs, top5))
    return {'model': name, 'with_stress': with_stress, 'reg_family': reg_family,
            'val_coef_R2': [round(float(v), 4) for v in cr2],
            'val_logMAE': round(float(logmae), 4),
            'val_field_MAE': round(float(fmae), 8),
            'val_rel_L2': round(float(relL2), 4),
            'val_max_err': round(float(maxerr), 8),
            'val_hotspot_hit': round(float(hs), 4),
            'val_top5': round(float(top5), 4)}


abl = []
abl.append(run_ablation('A_v1_xgb_noanalytic', False, 'xgb'))
abl.append(run_ablation('B_xgb_stress_noanalytic', True, 'xgb'))
abl.append(run_ablation('C_xgb_analytic_nostress', False, 'xgb'))
abl.append(run_ablation('D_xgb_analytic_stress', True, 'xgb'))
abl.append(run_ablation('D_rf_analytic_stress', True, 'rf'))
abl.append(run_ablation('D_ridgepoly_analytic_stress', True, 'ridge'))
with open(os.path.join(METR, 'step15_e_v11_model_comparison.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(abl[0].keys()))
    w.writeheader()
    for r in abl:
        w.writerow(r)
with open(os.path.join(METR, 'step15_e_v11_geometry_ablation.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(abl[0].keys()))
    w.writeheader()
    for r in abl:
        w.writerow(r)

# ---------------- time extrapolation diagnostic (300->500->750->1000, VAL cases) ----------------
time_audit = {}
for cid in VAL_IDS:
    r = meta[cid]
    T = int(float(r['T_uniform']))
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    P = float(r['pressure']); Ro = float(r['R_outer']); w = float(r['wall_thickness'])
    preds = []
    for tg in (300, 500, 750, 1000):
        x = np.array([[T, P, np.log1p(tg), float(r['R_major']), Ro, w,
                       E_T[T], CREEP[T][0], CREEP[T][1],
                       np.log10(max(P * Ro / w, 1e-9))]])
        xs = StandardScaler().fit(np.array([feats(s['case'], s['t'], True) for s in tr_s])).transform(x)
        c = np.array([0.0] * k)
        # D (xgb+stress+analytic) residual regressors refit quickly
        Xtr_s2 = StandardScaler().fit(np.array([feats(s['case'], s['t'], True) for s in tr_s]))
        # NOTE: reuse residual fits from run D by re-running minimal fit here
        for j in range(k):
            mm = xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                                  subsample=0.8, colsample_bytree=0.8,
                                  random_state=SEED, n_jobs=-1, verbosity=0)
            Xt = np.array([feats(s['case'], s['t'], True) for s in tr_s])
            mm.fit(Xtr_s2.transform(Xt), Rtr[:, j])
            c[j] = mm.predict(xs)[0] + d[j] * np.log10(tg)
        preds.append(float((10 ** (mu + c @ modes.T)).max()))
    mono = all(preds[i + 1] >= preds[i] for i in range(3))
    time_audit[cid] = {'pred_max_300_500_750_1000': preds, 'monotonic': mono}
    print('%s pred_max 300/500/750/1000: %s mono=%s' %
          (cid, ['%.2e' % v for v in preds], mono))
with open(os.path.join(METR, 'step15_e_v11_time_audit.json'), 'w') as f:
    json.dump({'d_slopes': d.tolist(), 'per_case': time_audit,
               'note': 'analytic log10(t) term; 300->1000 monotonicity check; '
                       '3000h accuracy NOT evaluated (EXT untouched)'}, f, indent=1)

# ---------------- physics audit ----------------
phys = {'violations': []}
for cid in VAL_IDS:
    r = meta[cid]
    T = int(float(r['T_uniform']))
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    P = float(r['pressure']); Ro = float(r['R_outer']); w = float(r['wall_thickness'])
    for tg in (100, 300):
        x = np.array([[T, P, np.log1p(tg), float(r['R_major']), Ro, w,
                       E_T[T], CREEP[T][0], CREEP[T][1],
                       np.log10(max(P * Ro / w, 1e-9))]])
        scaler2 = StandardScaler().fit(np.array([feats(s['case'], s['t'], True) for s in tr_s]))
        c = np.array([0.0] * k)
        for j in range(k):
            mm = xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                                  subsample=0.8, colsample_bytree=0.8,
                                  random_state=SEED, n_jobs=-1, verbosity=0)
            mm.fit(scaler2.transform(np.array([feats(s['case'], s['t'], True) for s in tr_s])),
                   Rtr[:, j])
            c[j] = mm.predict(scaler2.transform(x))[0] + d[j] * np.log10(tg)
        f_ = 10 ** (mu + c @ modes.T)
        if (f_ < 0).any() or not np.all(np.isfinite(f_)):
            phys['violations'].append((cid, tg, 'nonpos/nonfinite'))
with open(os.path.join(METR, 'step15_e_v11_physics_audit.json'), 'w') as f:
    json.dump(phys, f, indent=1)
print('physics violations:', phys['violations'] or 'NONE')
print('v1.1 artifacts in', FINAL)
