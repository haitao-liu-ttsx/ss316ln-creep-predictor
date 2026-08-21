"""STEP 15-D.1/2: POD coefficient time-structure + geometry stress-scale analysis.
Diagnostic only; C.2 EXT used as diagnosis (already read), never for selection.
"""
import csv
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'ml', 'data', 'step15_ceeq_snapshots')
METR = os.path.join(ROOT, 'ml', 'metrics')
FINAL = os.path.join(ROOT, 'ml', 'final', 'step15_v1')

basis = np.load(os.path.join(FINAL, 'pod_basis.npz'))
mu, modes = basis['mean_log_field'], basis['modes']
k = modes.shape[1]

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


def coeff_series(ids):
    """per case: rows of [case, t, c1, c2, c3]."""
    rows = []
    for s in load_snapshots(ids):
        c = (np.log10(s['field']) - mu) @ modes
        rows.append({'case': s['case'], 't': s['t'], 'c1': c[0], 'c2': c[1], 'c3': c[2]})
    return rows


tr_rows = coeff_series(TRAIN_IDS)
va_rows = coeff_series(VAL_IDS)
print('coefficient rows: train=%d val=%d' % (len(tr_rows), len(va_rows)))

# D.1: per-case c_i vs log10(t) linear fit (slope/intercept/R2) over available t-points
res = {'per_case': {}, 'summary': {}}
slopes = {j: [] for j in range(k)}
r2s = {j: [] for j in range(k)}
for cid in TRAIN_IDS + VAL_IDS:
    rows = [r for r in tr_rows + va_rows if r['case'] == cid]
    if len(rows) < 3:
        continue
    x = np.log10(np.array([r['t'] for r in rows]))
    fits = {}
    for j in range(k):
        y = np.array([r['c%d' % (j + 1)] for r in rows])
        b, a = np.polyfit(x, y, 1)
        yp = a + b * x
        ss = 1 - ((y - yp) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        fits['c%d' % (j + 1)] = {'slope': round(float(b), 4),
                                 'intercept': round(float(a), 4), 'R2': round(float(ss), 4)}
        slopes[j].append(b)
        r2s[j].append(ss)
    res['per_case'][cid] = fits
for j in range(k):
    res['summary']['c%d' % (j + 1)] = {
        'slope_mean': round(float(np.mean(slopes[j])), 4),
        'slope_std': round(float(np.std(slopes[j])), 4),
        'R2_mean': round(float(np.mean(r2s[j])), 4),
        'n_cases': len(slopes[j])}
print('slope stats:', json.dumps(res['summary'], indent=1))

# D.2: geometry stress scale vs max CEEQ (train+val+ext diagnostics)
ext_pr = np.load(os.path.join(METR, 'step15_c2_ext_predictions.npz'))
ext_tr = np.load(os.path.join(METR, 'step15_c2_ext_true_fields.npz'))
ext_meta = {r['case_id']: r for r in
            csv.DictReader(open(os.path.join(METR, 'step15_c2_ext_manifest.csv')))}
pts = []
for cid, f in zip(ext_tr['case_ids'], ext_tr['fields']):
    r = ext_meta[cid]
    pts.append({'case': cid, 'P': float(r['P']), 'Ro': float(r['Ro']),
                'w': float(r['w']), 'maxC': float(f.max())})
for s in load_snapshots(TRAIN_IDS + VAL_IDS):
    r = meta[s['case']]
    pts.append({'case': s['case'], 'P': float(r['pressure']),
                'Ro': float(r['R_outer']), 'w': float(r['wall_thickness']),
                'maxC': float(s['field'].max())})
import numpy as _np
P = _np.array([p['P'] for p in pts]); Ro = _np.array([p['Ro'] for p in pts])
w = _np.array([p['w'] for p in pts]); mc = _np.array([p['maxC'] for p in pts])
l10 = _np.log10(_np.maximum(mc, 1e-300))
cands = {'P': P, 'Ro': Ro, 'w': w, 'P_Ro_w': P * Ro / w,
         'log10_P_Ro_w': _np.log10(P * Ro / w)}
corr = {}
for name, x in cands.items():
    corr[name] = {'r_vs_log10max': round(float(_np.corrcoef(x, l10)[0, 1]), 4),
                  'r_vs_max': round(float(_np.corrcoef(x, mc)[0, 1]), 4)}
print('correlation of stress-scale candidates vs log10(max CEEQ):')
for name, c in corr.items():
    print('  %-14s %s' % (name, c))

with open(os.path.join(METR, 'step15_d_time_structure_analysis.json'), 'w') as f:
    json.dump(res, f, indent=1)
with open(os.path.join(METR, 'step15_d_geometry_feature_analysis.json'), 'w') as f:
    json.dump({'correlations': corr, 'n_points': len(pts)}, f, indent=1)
print('D.1/D.2 analysis written')
