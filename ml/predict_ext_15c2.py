"""STEP 15-C.2.3: predict 27 EXT cases with FROZEN model. Inputs only, NO target."""
import csv
import json
import os

import numpy as np
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
FINAL = os.path.join(ROOT, 'ml', 'final', 'step15_v1')

basis = np.load(os.path.join(FINAL, 'pod_basis.npz'))
mu, modes = basis['mean_log_field'], basis['modes']
# refit scaler + XGB exactly as C.1 (deterministic, seed 42)
c0 = json.load(open(os.path.join(METR, 'step15_c0_split_audit.json')))
TRAIN_IDS = c0['train']['ids']
TIME_GRID = [1, 3, 10, 30, 100, 300]
meta = {r['case_id']: r for r in
        csv.DictReader(open(os.path.join(ROOT, 'data', 'ai_ready_v4', 'simulation_dataset_318.csv')))}
DATA = os.path.join(ROOT, 'ml', 'data', 'step15_ceeq_snapshots')


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


def feats(cid, t):
    r = meta[cid]
    T = int(float(r['T_uniform']))
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    return np.array([T, float(r['pressure']), np.log1p(t), float(r['R_major']),
                     float(r['R_outer']), float(r['wall_thickness']),
                     E_T[T], CREEP[T][0], CREEP[T][1]])


tr_s = load_snapshots(TRAIN_IDS)
LG = np.log10(np.array([s['field'] for s in tr_s]))
coef_tr = (LG - mu) @ modes
Xtr = np.array([feats(s['case'], s['t']) for s in tr_s])
scaler = StandardScaler().fit(Xtr)
k = 3
regs = []
for j in range(k):
    m = xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                         subsample=0.8, colsample_bytree=0.8,
                         random_state=42, n_jobs=-1, verbosity=0)
    m.fit(scaler.transform(Xtr), coef_tr[:, j])
    regs.append(m)

# predict EXT (inputs only)
ext = list(csv.DictReader(open(os.path.join(METR, 'step15_c2_ext_manifest.csv'))))
preds = []
for r in ext:
    T = int(float(r['T']))
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    x = np.array([[T, float(r['P']), np.log1p(float(r['t'])), float(r['Rm']),
                   float(r['Ro']), float(r['w']), E_T[T], CREEP[T][0], CREEP[T][1]]])
    c = np.array([regs[j].predict(scaler.transform(x))[0] for j in range(k)])
    log_field = mu + c @ modes.T
    field = 10 ** log_field
    preds.append({'case_id': r['case_id'], 'coeffs': c,
                  'log_field': log_field, 'field': field})
np.savez(os.path.join(METR, 'step15_c2_ext_predictions.npz'),
         case_ids=np.array([p['case_id'] for p in preds]),
         coeffs=np.array([p['coeffs'] for p in preds]),
         log_fields=np.array([p['log_field'] for p in preds]),
         fields=np.array([p['field'] for p in preds]))
print('EXT predictions written (27) - target NOT read')
for p in preds[:3]:
    print('  %s max_pred=%.3e' % (p['case_id'], p['field'].max()))
