"""STEP 15-C.1: save v1 model artifacts (POD k3 + XGB), inference API, physics
audit, field visualization data. EXT/LOCKED never read.
"""
import csv
import json
import os

import numpy as np
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'ml', 'data', 'step15_ceeq_snapshots')
METR = os.path.join(ROOT, 'ml', 'metrics')
FINAL = os.path.join(ROOT, 'ml', 'final', 'step15_v1')
FIG = os.path.join(ROOT, 'docs', 'figures')
os.makedirs(FINAL, exist_ok=True)
os.makedirs(FIG, exist_ok=True)
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


def feats(cid, t):
    r = meta[cid]
    T = int(float(r['T_uniform']))
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    return np.array([T, float(r['pressure']), np.log1p(t), float(r['R_major']),
                     float(r['R_outer']), float(r['wall_thickness']),
                     E_T[T], CREEP[T][0], CREEP[T][1]])


tr_s, va_s = load_snapshots(TRAIN_IDS), load_snapshots(VAL_IDS)
LG = np.log10(np.array([s['field'] for s in tr_s]))
mu = LG.mean(axis=0)
U, s_, Vt = np.linalg.svd(LG - mu, full_matrices=False)
k = 3
modes = Vt[:k].T
coef_tr = (LG - mu) @ modes
Xtr = np.array([feats(s['case'], s['t']) for s in tr_s])
Xva = np.array([feats(s['case'], s['t']) for s in va_s])
scaler = StandardScaler().fit(Xtr)
regs = []
for j in range(k):
    m = xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                         subsample=0.8, colsample_bytree=0.8,
                         random_state=SEED, n_jobs=-1, verbosity=0)
    m.fit(scaler.transform(Xtr), coef_tr[:, j])
    regs.append(m)
np.savez(os.path.join(FINAL, 'pod_basis.npz'), mean_log_field=mu, modes=modes,
         singular_values=s_, train_ids=TRAIN_IDS, time_grid=TIME_GRID)

# inference API
def predict_field(T, P, t, Rm, Ro, w, E, A_creep, n_creep):
    x = np.array([[T, P, np.log1p(t), Rm, Ro, w, E, A_creep, n_creep]])
    xs = scaler.transform(x)
    c = np.array([regs[j].predict(xs)[0] for j in range(k)])
    log_f = mu + c @ modes.T
    field = 10 ** log_f
    return {'ceeq_field': field.tolist(), 'max_ceeq': float(field.max()),
            'mean_ceeq': float(field.mean()), 'p95_ceeq': float(np.percentile(field, 95)),
            'hotspot_element': int(np.argmax(field)),
            'pod_coefficients': [float(v) for v in c]}

# demo: 1 train case + 1 val case
demo = []
for cid, tag in ((TRAIN_IDS[0], 'train'), (VAL_IDS[0], 'val')):
    r = meta[cid]
    T = int(float(r['T_uniform']))
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    for tg in (100,):
        out = predict_field(T, float(r['pressure']), tg, float(r['R_major']),
                            float(r['R_outer']), float(r['wall_thickness']),
                            E_T[T], CREEP[T][0], CREEP[T][1])
        # true field at tg (interp)
        d = np.load(os.path.join(DATA, cid + '.npz'))
        F, TT = d['ceeq_frames'], d['frame_times']
        i = min(np.searchsorted(TT, tg), len(TT) - 1)
        w_ = (tg - float(TT[i - 1])) / (float(TT[i]) - float(TT[i - 1]))
        true = F[i - 1] * (1 - w_) + F[i] * w_
        out['case_id'] = cid
        out['true_field'] = true.tolist()
        out['abs_err_field'] = (np.abs(true - np.array(out['ceeq_field']))).tolist()
        demo.append(out)
        # plot true vs pred vs abs err (element index x)
        fig, axes = plt.subplots(1, 3, figsize=(15, 3.6))
        axes[0].plot(true, lw=0.4, color='C0'); axes[0].set_title('%s %s true CEEQ' % (tag, cid))
        axes[1].plot(out['ceeq_field'], lw=0.4, color='C1')
        axes[1].set_title('predicted CEEQ')
        axes[2].plot(out['abs_err_field'], lw=0.4, color='C3')
        axes[2].set_title('absolute error')
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, 'step15_c1_%s_%s.png' % (tag, cid)))
        plt.close(fig)
        print('%s %s t=%sh: pred max=%.3e true max=%.3e fieldMAE=%.3e' %
              (tag, cid, tg, out['max_ceeq'], true.max(),
               float(np.abs(true - np.array(out['ceeq_field'])).mean())))

with open(os.path.join(FINAL, 'step15_v1_model.json'), 'w') as f:
    json.dump({'k': k, 'time_grid': TIME_GRID, 'train_ids': TRAIN_IDS,
               'scaler': 'StandardScaler (TRAIN-only fit)',
               'regressor': 'XGBoost per mode (n300, d4, lr0.05)',
               'pod_domain': 'log10(CEEQ)',
               'val_log_MAE': 0.0240, 'val_rel_L2': 0.0924,
               'demo': demo}, f, indent=1)
with open(os.path.join(FINAL, 'step15_v1_config.json'), 'w') as f:
    json.dump({'model': 'POD(k=3, log10) + XGBoost coefficients',
               'inputs': ['T', 'P', 't', 'Rm', 'Ro', 'w', 'E', 'A_creep', 'n_creep'],
               'output': 'CEEQ field (2304 element centroids) + engineering metrics',
               'split': 'TRAIN 31 / VAL 6 (case-level); EXT 27 and LOCKED 20 untouched',
               'checksums': {'318': '20f21ebc67ea', 'locked_test': 'fa573e330926'},
               'status': 'v1 finite-domain, NOT frozen, EXT not evaluated'}, f, indent=1)

# physics audit on VAL predicted fields
phys = {'violations': []}
for i, s in enumerate(va_s):
    r = meta[s['case']]
    T = int(float(r['T_uniform']))
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    out = predict_field(T, float(r['pressure']), s['t'], float(r['R_major']),
                        float(r['R_outer']), float(r['wall_thickness']),
                        E_T[T], CREEP[T][0], CREEP[T][1])
    f_ = np.array(out['ceeq_field'])
    if (f_ < 0).any(): phys['violations'].append((s['case'], 'negative'))
    if not np.all(np.isfinite(f_)): phys['violations'].append((s['case'], 'nonfinite'))
# time monotonicity per case (t=100 vs t=300 predicted)
for cid in VAL_IDS:
    r = meta[cid]
    T = int(float(r['T_uniform']))
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    if 100 <= float(r['time']):
        pass
    f100 = np.array(predict_field(T, float(r['pressure']), 100, float(r['R_major']),
                                  float(r['R_outer']), float(r['wall_thickness']),
                                  E_T[T], CREEP[T][0], CREEP[T][1])['ceeq_field'])
    f300 = np.array(predict_field(T, float(r['pressure']), 300, float(r['R_major']),
                                  float(r['R_outer']), float(r['wall_thickness']),
                                  E_T[T], CREEP[T][0], CREEP[T][1])['ceeq_field'])
    if (f300 < f100).any():
        phys['violations'].append((cid, 't_nonmonotonic_elements=%d' % (f300 < f100).sum()))
phys['violations'] = phys['violations'][:20]
with open(os.path.join(METR, 'step15_c1_physics_audit.json'), 'w') as f:
    json.dump(phys, f, indent=1)
print('v1 artifacts saved to', FINAL)
print('physics violations:', phys['violations'][:5] or 'NONE')
