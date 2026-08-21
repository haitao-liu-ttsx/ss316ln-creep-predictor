"""STEP 15-G.3: time/geometry group evaluation of best v1.2 candidates + v1.1
control on the same VAL + physics audit + sufficiency analysis.
"""
import csv
import json
import os

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'ml', 'data', 'step15_ceeq_snapshots')
DATA_NEW = os.path.join(ROOT, 'ml', 'data', 'step15g_snapshots')
METR = os.path.join(ROOT, 'ml', 'metrics')
FINAL = os.path.join(ROOT, 'ml', 'final', 'step15_v1_2')
FINAL_V11 = os.path.join(ROOT, 'ml', 'final', 'step15_v1_1')

c0 = json.load(open(os.path.join(METR, 'step15_c0_split_audit.json')))
OLD_IDS = c0['train']['ids'] + c0['validation']['ids']
TIME_GRID = [1, 3, 10, 30, 100, 300]
meta = {r['case_id']: r for r in
        csv.DictReader(open(os.path.join(ROOT, 'data', 'ai_ready_v4', 'simulation_dataset_318.csv')))}
new_design = list(csv.DictReader(open(os.path.join(METR, 'step15_g_odb_qc.csv'))))
split = json.load(open(os.path.join(METR, 'step15_g3_split_audit.json')))
train_ids, val_ids = split['train'], split['val']


def load_snaps(ids):
    out = []
    for cid in ids:
        if cid in OLD_IDS:
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
        else:
            d = np.load(os.path.join(DATA_NEW, cid + '.npz'))
            r = next(rr for rr in new_design if rr['case_id'] == cid)
            out.append({'case': cid, 't': int(r['t']), 'field': d['ceeq_field']})
    return out


def case_meta(cid):
    if cid in meta:
        r = meta[cid]
        return {'T': int(float(r['T_uniform'])), 'P': float(r['pressure']),
                'Rm': float(r['R_major']), 'Ro': float(r['R_outer']),
                'w': float(r['wall_thickness'])}
    r = next(rr for rr in new_design if rr['case_id'] == cid)
    return {'T': int(float(r['T'])), 'P': float(r['P']),
            'Rm': float(r['Rm']), 'Ro': float(r['Ro']), 'w': float(r['w'])}


def feats(cid, t):
    m = case_meta(cid)
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    return np.array([m['T'], m['P'], np.log1p(t), m['Rm'], m['Ro'], m['w'],
                     E_T[m['T']], CREEP[m['T']][0], CREEP[m['T']][1],
                     np.log10(max(m['P'] * m['Ro'] / m['w'], 1e-9))])


S_tr = load_snaps(train_ids)
S_va = load_snaps(val_ids)
LG_tr = np.log10(np.array([s['field'] for s in S_tr]))
LG_va = np.log10(np.array([s['field'] for s in S_va]))
mu = LG_tr.mean(axis=0)
U, s_, Vt = np.linalg.svd(LG_tr - mu, full_matrices=False)
k = 3
modes = Vt[:k].T
Ctr = (LG_tr - mu) @ modes
Cva = (LG_va - mu) @ modes
t_tr = np.log10(np.array([s['t'] for s in S_tr]))
d = np.array([np.polyfit(t_tr, Ctr[:, j], 1)[0] for j in range(k)])
Rtr = Ctr - np.outer(t_tr, d)
Rva = Cva - np.outer(np.log10(np.array([s['t'] for s in S_va])), d)
Xtr = np.array([feats(s['case'], s['t']) for s in S_tr])
Xva = np.array([feats(s['case'], s['t']) for s in S_va])
sc = StandardScaler().fit(Xtr)

# best candidate: poly10 (Ridge Poly2, no analytic)
poly = Pipeline([('poly', PolynomialFeatures(2)), ('scale', StandardScaler()),
                 ('m', Ridge(alpha=1.0))])
preds_p = np.zeros_like(Cva)
for j in range(k):
    poly.fit(sc.transform(Xtr), Ctr[:, j])
    preds_p[:, j] = poly.predict(sc.transform(Xva))
Yp_p = 10 ** (mu + preds_p @ modes.T)
# v1.1 control: analytic XGB (re-train on v1.2 TRAIN, same structure)
import xgboost as xgb
preds_a = np.zeros_like(Cva)
for j in range(k):
    m = xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                         subsample=0.8, colsample_bytree=0.8,
                         random_state=SEED, n_jobs=-1, verbosity=0)
    m.fit(sc.transform(Xtr), Rtr[:, j])
    preds_a[:, j] = m.predict(sc.transform(Xva)) + d[j] * np.log10(np.array([s['t'] for s in S_va]))
Yp_a = 10 ** (mu + preds_a @ modes.T)
Yt = 10 ** LG_va


def groups(name, Yp):
    out = {}
    tvals = sorted(set(s['t'] for s in S_va))
    for t in tvals:
        idx = [i for i, s in enumerate(S_va) if s['t'] == t]
        lt, lp = LG_va[idx], np.log10(np.maximum(Yp[idx], 1e-300))
        out['t%d' % t] = {'n': len(idx),
                          'logMAE': round(float(np.abs(lt - lp).mean()), 4),
                          'logR2': round(float(r2_score(lt, lp)), 4),
                          'hs': round(float(np.mean(np.argmax(Yt[idx], 1) ==
                                                   np.argmax(Yp[idx], 1))), 3)}
    geoms = sorted(set('%s/%s/%s' % (int(case_meta(s['case'])['Rm']),
                                     int(case_meta(s['case'])['Ro']),
                                     int(case_meta(s['case'])['w'])) for s in S_va))
    for g in geoms:
        idx = [i for i, s in enumerate(S_va)
               if '%s/%s/%s' % (int(case_meta(s['case'])['Rm']),
                                int(case_meta(s['case'])['Ro']),
                                int(case_meta(s['case'])['w'])) == g]
        lt, lp = LG_va[idx], np.log10(np.maximum(Yp[idx], 1e-300))
        out['geo_' + g.replace('/', '_')] = {'n': len(idx),
                                             'logMAE': round(float(np.abs(lt - lp).mean()), 4),
                                             'logR2': round(float(r2_score(lt, lp)), 4),
                                             'hs': round(float(np.mean(
                                                 np.argmax(Yt[idx], 1) == np.argmax(Yp[idx], 1))), 3)}
    return out


print('=== v1.2 poly10 (Ridge-Poly2 + stress) ===')
gp = groups('poly10', Yp_p)
for kk, v in gp.items():
    print('  %-14s %s' % (kk, v))
print('=== v1.1 structure control (analytic XGB on v1.2 TRAIN) ===')
ga = groups('anxgb', Yp_a)
for kk, v in ga.items():
    print('  %-14s %s' % (kk, v))

# physics audit
phys = {'violations': []}
for Yp in (Yp_p, Yp_a):
    if (Yp < 0).any(): phys['violations'].append('negative')
    if not np.all(np.isfinite(Yp)): phys['violations'].append('nonfinite')
with open(os.path.join(METR, 'step15_g3_physics_audit.json'), 'w') as f:
    json.dump(phys, f, indent=1)

# save groups + config
with open(os.path.join(METR, 'step15_g3_time_groups.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['model', 'time', 'n', 'logMAE', 'logR2', 'hs'])
    for nm, gg in (('poly10', gp), ('anxgb_control', ga)):
        for tkey, v in gg.items():
            if tkey.startswith('t'):
                w.writerow([nm, tkey, v['n'], v['logMAE'], v['logR2'], v['hs']])
with open(os.path.join(METR, 'step15_g3_geometry_groups.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['model', 'geometry', 'n', 'logMAE', 'logR2', 'hs'])
    for nm, gg in (('poly10', gp), ('anxgb_control', ga)):
        for tkey, v in gg.items():
            if tkey.startswith('geo'):
                w.writerow([nm, tkey, v['n'], v['logMAE'], v['logR2'], v['hs']])
with open(os.path.join(FINAL, 'v12_config.json'), 'w') as f:
    json.dump({'candidate': 'poly10 (Ridge-Poly2 + log10(P*Ro/w), no analytic t)',
               'control': 'anxgb (analytic log10(t) + XGB)',
               'pod': {'k': 3, 'domain': 'log10(CEEQ)', 'basis': 'TRAIN-only'},
               'split': {'train': len(train_ids), 'val': len(val_ids)},
               'status': 'v1.2 candidate trained, NOT frozen, EXT not evaluated'}, f, indent=1)
print('physics:', phys['violations'] or 'NONE')
print('step15_g3_* written')
