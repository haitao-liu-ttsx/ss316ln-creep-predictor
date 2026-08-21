"""STEP 15-G.3: v1.2 training (merge 50 new cases, case-level split, POD k
comparison, 7 model candidates). EXT/LOCKED never read.
"""
import csv
import json
import os

import numpy as np
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
import xgboost as xgb

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'ml', 'data', 'step15_ceeq_snapshots')
DATA_NEW = os.path.join(ROOT, 'ml', 'data', 'step15g_snapshots')
METR = os.path.join(ROOT, 'ml', 'metrics')
FINAL = os.path.join(ROOT, 'ml', 'final', 'step15_v1_2')
os.makedirs(FINAL, exist_ok=True)
np.random.seed(SEED)

c0 = json.load(open(os.path.join(METR, 'step15_c0_split_audit.json')))
OLD_IDS = c0['train']['ids'] + c0['validation']['ids']   # 37 old cases (t<=300)
TIME_GRID = [1, 3, 10, 30, 100, 300]
meta = {r['case_id']: r for r in
        csv.DictReader(open(os.path.join(ROOT, 'data', 'ai_ready_v4', 'simulation_dataset_318.csv')))}


def load_old(ids):
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


new_qc = json.load(open(os.path.join(METR, 'step15_g_final_audit.json')))
assert new_qc['abaqus_success'] == 50 and new_qc['ceeq_pass'] == 50
new_design = list(csv.DictReader(open(os.path.join(METR, 'step15_g_odb_qc.csv'))))
NEW_IDS = [r['case_id'] for r in new_design]
print('merge: old=%d new=%d' % (len(OLD_IDS), len(NEW_IDS)))

new_snaps = []
for cid in NEW_IDS:
    d = np.load(os.path.join(DATA_NEW, cid + '.npz'))
    r = next(rr for rr in new_design if rr['case_id'] == cid)
    new_snaps.append({'case': cid, 't': int(r['t']), 'field': d['ceeq_field']})
old_snaps = load_old(OLD_IDS)
ALL = old_snaps + new_snaps
print('total snapshots: %d (old %d + new %d)' % (len(ALL), len(old_snaps), len(new_snaps)))


def case_meta(cid):
    if cid in meta:
        r = meta[cid]
        return {'T': int(float(r['T_uniform'])), 'P': float(r['pressure']),
                'Rm': float(r['R_major']), 'Ro': float(r['R_outer']),
                'w': float(r['wall_thickness'])}
    r = next(rr for rr in new_design if rr['case_id'] == cid)
    return {'T': int(float(r['T'])), 'P': float(r['P']),
            'Rm': float(r['Rm']), 'Ro': float(r['Ro']), 'w': float(r['w'])}


def feats(cid, t, with_stress):
    m = case_meta(cid)
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    base = [m['T'], m['P'], np.log1p(t), m['Rm'], m['Ro'], m['w'],
            E_T[m['T']], CREEP[m['T']][0], CREEP[m['T']][1]]
    if with_stress:
        base.append(np.log10(max(m['P'] * m['Ro'] / m['w'], 1e-9)))
    return np.array(base)


# ---------------- case-level split (stratified, seed 42) ----------------
cases = sorted(set(s['case'] for s in ALL))
# stratify: geometry, time-layer (3000/1000 vs short), P>=25
def strata(cid):
    m = case_meta(cid)
    tg = max(s['t'] for s in ALL if s['case'] == cid)
    return ('%s/%s/%s' % (int(m['Rm']), int(m['Ro']), int(m['w'])),
            'long' if tg >= 1000 else 'short',
            'hiP' if m['P'] >= 25 else 'loP')
buckets = {}
for cid in cases:
    buckets.setdefault(strata(cid), []).append(cid)
rng = np.random.RandomState(SEED)
train_ids, val_ids = [], []
for key, ids in sorted(buckets.items()):
    rng.shuffle(ids)
    n_val = max(1, int(round(len(ids) * 0.2)))
    val_ids += ids[:n_val]
    train_ids += ids[n_val:]
train_ids.sort(); val_ids.sort()
print('TRAIN=%d VAL=%d (case-level, stratified by geometry/time/P)' %
      (len(train_ids), len(val_ids)))
for cid in val_ids:
    m = case_meta(cid)
    tg = max(s['t'] for s in ALL if s['case'] == cid)
    print('  VAL %-36s T=%d P=%g t=%d geom=%d/%d/%d' %
          (cid, m['T'], m['P'], tg, m['Rm'], m['Ro'], m['w']))
with open(os.path.join(METR, 'step15_g3_split_audit.json'), 'w') as f:
    json.dump({'train': train_ids, 'val': val_ids, 'n_train': len(train_ids),
               'n_val': len(val_ids), 'strategy': 'case-level stratified 80/20, seed 42'}, f, indent=1)

S_tr = [s for s in ALL if s['case'] in train_ids]
S_va = [s for s in ALL if s['case'] in val_ids]
LG_tr = np.log10(np.array([s['field'] for s in S_tr]))
LG_va = np.log10(np.array([s['field'] for s in S_va]))

# ---------------- POD k comparison (TRAIN-only) ----------------
pod_rows = []
for kk in (2, 3, 4, 5):
    mu = LG_tr.mean(axis=0)
    U, s_, Vt = np.linalg.svd(LG_tr - mu, full_matrices=False)
    cumvar = float((s_ ** 2).cumsum()[-1] / ((LG_tr - mu) ** 2).sum())
    rec_va = 10 ** (mu + (LG_va - mu) @ Vt[:kk].T @ Vt[:kk])
    lmae = float(np.abs(LG_va - (mu + (LG_va - mu) @ Vt[:kk].T @ Vt[:kk])).mean())
    pod_rows.append({'k': kk, 'cumvar': round(cumvar, 6),
                     'val_logMAE_recon': round(lmae, 6)})
    print('POD k=%d cumvar=%.6f val recon logMAE=%.6f' % (kk, cumvar, lmae))
k = 3
mu = LG_tr.mean(axis=0)
U, s_, Vt = np.linalg.svd(LG_tr - mu, full_matrices=False)
modes = Vt[:k].T
Ctr = (LG_tr - mu) @ modes
Cva = (LG_va - mu) @ modes
t_tr = np.log10(np.array([s['t'] for s in S_tr]))
d = np.array([np.polyfit(t_tr, Ctr[:, j], 1)[0] for j in range(k)])
Rtr = Ctr - np.outer(t_tr, d)
Rva = Cva - np.outer(np.log10(np.array([s['t'] for s in S_va])), d)
np.savez(os.path.join(FINAL, 'pod_basis_v12.npz'), mean_log_field=mu, modes=modes,
         singular_values=s_, d_slopes=d, train_ids=train_ids, val_ids=val_ids)
with open(os.path.join(METR, 'step15_g3_pod_comparison.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(pod_rows[0].keys()))
    w.writeheader()
    for r in pod_rows:
        w.writerow(r)
print('d_slopes:', np.round(d, 4))

# ---------------- model candidates ----------------
Xtr9 = np.array([feats(s['case'], s['t'], False) for s in S_tr])
Xtr10 = np.array([feats(s['case'], s['t'], True) for s in S_tr])
Xva9 = np.array([feats(s['case'], s['t'], False) for s in S_va])
Xva10 = np.array([feats(s['case'], s['t'], True) for s in S_va])
sc9 = StandardScaler().fit(Xtr9)
sc10 = StandardScaler().fit(Xtr10)


def run(name, Xtr, Xva, analytic):
    scaler = StandardScaler().fit(Xtr)
    Xts, Xvs = scaler.transform(Xtr), scaler.transform(Xva)
    preds = np.zeros_like(Cva)
    for j in range(k):
        if 'xgb' in name:
            m = xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                                 subsample=0.8, colsample_bytree=0.8,
                                 random_state=SEED, n_jobs=-1, verbosity=0)
        elif 'rf' in name:
            m = RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=-1)
        elif 'poly' in name:
            m = Pipeline([('poly', PolynomialFeatures(2)), ('scale', StandardScaler()),
                          ('m', Ridge(alpha=1.0))])
        else:
            m = Ridge(alpha=1.0)
        target = Rtr[:, j] if analytic else Ctr[:, j]
        m.fit(Xts, target)
        if analytic:
            preds[:, j] = m.predict(Xvs) + d[j] * np.log10(np.array([s['t'] for s in S_va]))
        else:
            preds[:, j] = m.predict(Xvs)
    Yp = 10 ** (mu + preds @ modes.T)
    Yt = 10 ** LG_va
    logmae = float(np.abs(LG_va - (mu + preds @ modes.T)).mean())
    fmae = float(np.abs(Yt - Yp).mean())
    relL2 = float(np.linalg.norm(Yt - Yp) / np.linalg.norm(np.maximum(Yt, 1e-20)))
    hs = float(np.mean(np.argmax(Yt, 1) == np.argmax(Yp, 1)))
    top5 = float(np.mean([len(set(np.argsort(Yt[i])[-5:]) & set(np.argsort(Yp[i])[-5:])) / 5
                          for i in range(len(Yt))]))
    cr2 = [r2_score(Cva[:, j], preds[:, j]) for j in range(k)]
    print('%-30s logMAE=%.4f relL2=%.4f hs=%.2f top5=%.2f coefR2=%s' %
          (name, logmae, relL2, hs, top5, [round(v, 3) for v in cr2]))
    return {'model': name, 'val_logMAE': round(float(logmae), 4),
            'val_relL2': round(float(relL2), 4), 'val_field_MAE': round(float(fmae), 8),
            'val_hotspot': round(float(hs), 4), 'val_top5': round(float(top5), 4),
            'val_coef_R2': [round(float(v), 4) for v in cr2]}


results = []
for nm, Xtr_, Xva_, an in [
        ('linear9', Xtr9, Xva9, False), ('linear10', Xtr10, Xva10, False),
        ('rf9', Xtr9, Xva9, False), ('rf10', Xtr10, Xva10, False),
        ('xgb9', Xtr9, Xva9, False), ('xgb10', Xtr10, Xva10, False),
        ('poly10', Xtr10, Xva10, False),
        ('anlin10', Xtr10, Xva10, True), ('anrf10', Xtr10, Xva10, True),
        ('anxgb10', Xtr10, Xva10, True)]:
    results.append(run(nm, Xtr_, Xva_, an))
with open(os.path.join(METR, 'step15_g3_model_comparison.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    w.writeheader()
    for r in results:
        w.writerow(r)
print('v1.2 candidates evaluated on VAL (n=%d snapshots, %d cases)' %
      (len(S_va), len(val_ids)))
print('done ->', FINAL)
