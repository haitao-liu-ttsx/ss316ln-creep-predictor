"""STEP 15-F: freeze v1.1 Candidate D, one-shot EXT evaluation, v1 vs v1.1.

Freeze: XGB residual regressors (TRAIN-only) + analytic d_i*log10(t) +
log10(P*Ro/w) feature; POD basis (log10, k=3, TRAIN-only) copied frozen.
One-way gate: predictions saved BEFORE first read of EXT target (C.2-extracted
true fields). LOCKED never read.
"""
import csv
import hashlib
import json
import os
import time

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
import xgboost as xgb

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'ml', 'data', 'step15_ceeq_snapshots')
METR = os.path.join(ROOT, 'ml', 'metrics')
FINAL = os.path.join(ROOT, 'ml', 'final', 'step15_v1_1')
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
    P = float(r['pressure']); Ro = float(r['R_outer']); w = float(r['wall_thickness'])
    return np.array([T, P, np.log1p(t), float(r['R_major']), Ro, w, E_T[T],
                     CREEP[T][0], CREEP[T][1], np.log10(max(P * Ro / w, 1e-9))])


tr_s = load_snapshots(TRAIN_IDS)
LG = np.log10(np.array([s['field'] for s in tr_s]))
mu = LG.mean(axis=0)
U, s_, Vt = np.linalg.svd(LG - mu, full_matrices=False)
k = 3
modes = Vt[:k].T
Ctr = (LG - mu) @ modes
t_log = np.log10(np.array([s['t'] for s in tr_s]))
d = np.array([np.polyfit(t_log, Ctr[:, j], 1)[0] for j in range(k)])
Rtr = Ctr - np.outer(t_log, d)
Xtr = np.array([feats(s['case'], s['t']) for s in tr_s])
scaler = StandardScaler().fit(Xtr)
regs = []
for j in range(k):
    m = xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                         subsample=0.8, colsample_bytree=0.8,
                         random_state=SEED, n_jobs=-1, verbosity=0)
    m.fit(scaler.transform(Xtr), Rtr[:, j])
    regs.append(m)


def predict(x_row, t):
    c = np.array([regs[j].predict(scaler.transform(x_row.reshape(1, -1)))[0]
                  for j in range(k)]) + d * np.log10(t)
    return mu + c @ modes.T


# ---------------- FREEZE manifest ----------------
np.savez(os.path.join(FINAL, 'pod_basis_v11_frozen.npz'),
         mean_log_field=mu, modes=modes, singular_values=s_, d_slopes=d,
         train_ids=TRAIN_IDS)
for j in range(k):
    regs[j].save_model(os.path.join(FINAL, 'frozen_xgb_mode%d.json' % (j + 1)))
with open(os.path.join(FINAL, 'frozen_model_config.json'), 'w') as f:
    json.dump({'k': k, 'time_structure': 'c_i = g_i + d_i*log10(t)',
               'd_slopes': d.tolist(), 'geometry_feature': 'log10(P*Ro/w)',
               'features': ['T', 'P', 'log1p_time', 'Rm', 'Ro', 'w', 'E', 'A_creep',
                            'n_creep', 'log10(P*Ro/w)'],
               'scaler': 'StandardScaler TRAIN-only',
               'pod_domain': 'log10(CEEQ)', 'pod_k': k}, f, indent=1)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


man = {'model': 'v1.1 Candidate D (XGB residual + analytic log10(t) + log10(P*Ro/w))',
       'pod': {'domain': 'log10(CEEQ)', 'k': 3, 'basis': 'TRAIN-only'},
       'checksums': {'pod_basis': sha(os.path.join(FINAL, 'pod_basis_v11_frozen.npz')),
                     'config': sha(os.path.join(FINAL, 'frozen_model_config.json')),
                     'mode1': sha(os.path.join(FINAL, 'frozen_xgb_mode1.json')),
                     'mode2': sha(os.path.join(FINAL, 'frozen_xgb_mode2.json')),
                     'mode3': sha(os.path.join(FINAL, 'frozen_xgb_mode3.json')),
                     '318': hashlib.sha256(open(os.path.join(ROOT, 'data', 'ai_ready_v4',
                                                            'simulation_dataset_318.csv'),
                                               'rb').read()).hexdigest()[:12],
                     'locked': hashlib.sha256(open(os.path.join(ROOT, 'data', 'ai_ready_v4',
                                                                'test.csv'), 'rb').read()
                                              ).hexdigest()[:12]},
       'freeze_timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'ext_target_status': 'NOT_READ_by_v11'}
with open(os.path.join(FINAL, 'STEP15_F_FREEZE_MANIFEST.json'), 'w') as f:
    json.dump(man, f, indent=1)
print('FREEZE manifest written')

# ---------------- EXT prediction (no target) ----------------
ext = list(csv.DictReader(open(os.path.join(METR, 'step15_c2_ext_manifest.csv'))))
ids_e, log_fields = [], []
for r in ext:
    T = int(float(r['T']))
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    P = float(r['P']); Ro = float(r['Ro']); w = float(r['w'])
    x = np.array([T, P, np.log1p(float(r['t'])), float(r['Rm']), Ro, w, E_T[T],
                  CREEP[T][0], CREEP[T][1], np.log10(max(P * Ro / w, 1e-9))])
    log_fields.append(predict(x, float(r['t'])))
    ids_e.append(r['case_id'])
LF = np.array(log_fields)
np.savez(os.path.join(METR, 'step15_f_v11_ext_predictions.npz'),
         case_ids=np.array(ids_e), log_fields=LF, fields=10 ** LF)
print('EXT predictions saved (27) - target not yet read by v1.1')

# ---------------- ONE-WAY GATE: first EXT target read (v1.1) ----------------
trf = np.load(os.path.join(METR, 'step15_c2_ext_true_fields.npz'))
assert list(trf['case_ids']) == ids_e
Yt = trf['fields']
Yp = 10 ** LF
Lt, Lp = np.log10(Yt), LF
print('EXT target read by v1.1: 27 cases (post-freeze, one-shot)')

# ---------------- evaluation ----------------
def block(idx):
    yt, yp = Yt[idx], Yp[idx]
    lt, lp = Lt[idx], Lp[idx]
    return {'n': len(idx),
            'logMAE': round(float(np.abs(lt - lp).mean()), 4),
            'logRMSE': round(float(np.sqrt(((lt - lp) ** 2).mean())), 4),
            'logR2': round(float(r2_score(lt, lp)), 4),
            'relL2': round(float(np.linalg.norm(yt - yp) /
                                 np.linalg.norm(np.maximum(yt, 1e-20))), 4),
            'maxErr': round(float(np.abs(yt - yp).max()), 8),
            'hotspot': round(float(np.mean(np.argmax(yt, 1) == np.argmax(yp, 1))), 4),
            'top5': round(float(np.mean([len(set(np.argsort(yt[i])[-5:]) &
                                          set(np.argsort(yp[i])[-5:])) / 5
                                         for i in range(len(idx))])), 4)}


all_i = list(range(27))
print('OVERALL v1.1:', block(all_i))
rows = []
for i, c in enumerate(ids_e):
    rows.append({'case_id': c, 'T': ext[i]['T'], 'P': ext[i]['P'], 't': ext[i]['t'],
                 'geom': ext[i]['geometry_group'],
                 'true_max': float(Yt[i].max()), 'pred_max': float(Yp[i].max()),
                 'ratio': round(float(Yt[i].max() / max(Yp[i].max(), 1e-300)), 2),
                 'logMAE': round(float(np.abs(Lt[i] - Lp[i]).mean()), 4),
                 'hs_true': int(np.argmax(Yt[i])), 'hs_pred': int(np.argmax(Yp[i]))})
with open(os.path.join(METR, 'step15_f_v11_ext_results.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow(r)
for r in rows:
    print('  %-36s t=%-4s ratio=%.1f logMAE=%.3f hs=%d/%d' %
          (r['case_id'], r['t'], r['ratio'], r['logMAE'], r['hs_true'], r['hs_pred']))

# time groups
tg = {}
for t in ('500', '750', '3000'):
    idx = [i for i, c in enumerate(ids_e) if abs(float(ext[i]['t']) - float(t)) < 1]
    tg[t] = block(idx)
    print('t=%s: %s' % (t, tg[t]))
with open(os.path.join(METR, 'step15_f_v11_time_groups.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['time', 'n', 'logMAE', 'logRMSE', 'logR2', 'relL2', 'maxErr', 'hotspot', 'top5'])
    for t, b in tg.items():
        w.writerow([t] + [b['n'], b['logMAE'], b['logRMSE'], b['logR2'], b['relL2'],
                          b['maxErr'], b['hotspot'], b['top5']])

# geometry groups
gg = {}
for g in ('100/20/4', '80/15/2', '120/25/3', '150/20/4'):
    idx = [i for i, c in enumerate(ids_e) if ext[i]['geometry_group'] == g]
    gg[g] = block(idx)
    print('geo %-10s: %s' % (g, gg[g]))
with open(os.path.join(METR, 'step15_f_v11_geometry_groups.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['geometry', 'n', 'logMAE', 'logRMSE', 'logR2', 'relL2', 'maxErr',
                'hotspot', 'top5'])
    for g, b in gg.items():
        w.writerow([g] + [b['n'], b['logMAE'], b['logRMSE'], b['logR2'], b['relL2'],
                          b['maxErr'], b['hotspot'], b['top5']])

# physics
phys = {'violations': []}
if (Yp < 0).any(): phys['violations'].append('negative')
if not np.all(np.isfinite(Yp)): phys['violations'].append('nonfinite')
with open(os.path.join(METR, 'step15_f_v11_physics_audit.json'), 'w') as f:
    json.dump(phys, f, indent=1)
print('physics:', phys['violations'] or 'NONE')

# v1 vs v1.1 comparison (C.2 results reference)
v1 = json.load(open(os.path.join(METR, 'step15_c2_ext_audit.json')))
comp = [{'metric': 'overall_logMAE', 'v1': v1['overall']['logMAE'],
         'v11': block(all_i)['logMAE']},
        {'metric': 'overall_logR2', 'v1': v1['overall']['logR2'],
         'v11': block(all_i)['logR2']},
        {'metric': 't500_logMAE', 'v1': v1['by_time']['500']['logMAE'],
         'v11': tg['500']['logMAE']},
        {'metric': 't750_logMAE', 'v1': v1['by_time']['750']['logMAE'],
         'v11': tg['750']['logMAE']},
        {'metric': 't3000_logMAE', 'v1': v1['by_time']['3000']['logMAE'],
         'v11': tg['3000']['logMAE']},
        {'metric': 't3000_logR2', 'v1': v1['by_time']['3000']['logR2'],
         'v11': tg['3000']['logR2']},
        {'metric': 'geo_baseline_logMAE', 'v1': v1['by_geometry']['100/20/4']['logMAE'],
         'v11': gg['100/20/4']['logMAE']},
        {'metric': 'geo_80_15_2_logMAE', 'v1': v1['by_geometry']['80/15/2']['logMAE'],
         'v11': gg['80/15/2']['logMAE']},
        {'metric': 'geo_120_25_3_logMAE', 'v1': v1['by_geometry']['120/25/3']['logMAE'],
         'v11': gg['120/25/3']['logMAE']},
        {'metric': 'geo_150_20_4_logMAE', 'v1': v1['by_geometry']['150/20/4']['logMAE'],
         'v11': gg['150/20/4']['logMAE']},
        {'metric': 'hotspot_hit', 'v1': v1['overall']['hotspot_hit'],
         'v11': block(all_i)['hotspot']},
        {'metric': 'top5', 'v1': v1['overall']['top5_overlap'],
         'v11': block(all_i)['top5']}]
with open(os.path.join(METR, 'step15_f_v11_comparison_v1_vs_v11.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['metric', 'v1', 'v11'])
    w.writeheader()
    for r in comp:
        w.writerow(r)
        print('%-24s v1=%-8s v11=%-8s' % (r['metric'], r['v1'], r['v11']))

# visualizations (baseline 500h, non-baseline 3000h)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
for cid in ('CEEQ14A_T550_P5_t500h_Rm100_Ro20_w4',
            'CEEQ14A_T650_P20_t3000h_Rm120_Ro25_w3'):
    i = ids_e.index(cid)
    fig, axes = plt.subplots(1, 3, figsize=(15, 3.6))
    axes[0].plot(Yt[i], lw=0.4, color='C0'); axes[0].set_title('%s true' % cid)
    axes[1].plot(Yp[i], lw=0.4, color='C1'); axes[1].set_title('v1.1 pred')
    axes[2].plot(np.abs(Yt[i] - Yp[i]), lw=0.4, color='C3'); axes[2].set_title('abs err')
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'step15_f_v11_%s.png' % cid[:30]))
    plt.close(fig)

# final audit
fa = {'freeze': 'v1.1 Candidate D frozen', 'ext_evaluated': 27,
      'ext_target_read': 'YES (post-freeze one-shot)',
      'locked_test_read': 'NO', '318_modified': 'NO', 'v1_modified': 'NO',
      'post_ext_retraining': 'NO', 'post_ext_model_selection': 'NO',
      'checksums': man['checksums']}
with open(os.path.join(METR, 'step15_f_v11_final_audit.json'), 'w') as f:
    json.dump(fa, f, indent=1)
print('STEP 15-F complete')
