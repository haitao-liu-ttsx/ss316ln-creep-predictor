"""STEP 15-C.2.5-9: field evaluation of frozen v1 surrogate on EXT 27 (post-freeze
one-shot). Time/geometry/hotspot grouping + STEP14 scalar comparison + physics.
"""
import csv
import json
import os

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')

pr = np.load(os.path.join(METR, 'step15_c2_ext_predictions.npz'))
tr = np.load(os.path.join(METR, 'step15_c2_ext_true_fields.npz'))
ids = list(pr['case_ids'])
Yp = pr['fields']
Yt = tr['fields']
assert list(tr['case_ids']) == ids
ext = {r['case_id']: r for r in
       csv.DictReader(open(os.path.join(METR, 'step15_c2_ext_manifest.csv')))}

report = {}
Lp, Lt = np.log10(np.maximum(Yp, 1e-300)), np.log10(Yt)


def block(name, idx):
    if len(idx) == 0:
        return {'n': 0, 'logMAE': None, 'logRMSE': None, 'logR2': None,
                'rawMAE': None, 'relL2': None, 'maxAbsErr': None,
                'hotspot_true': None, 'hotspot_hit': None, 'top5_overlap': None}
    yt, yp = Yt[idx], Yp[idx]
    lt, lp = Lt[idx], Lp[idx]
    return {'n': len(idx),
            'logMAE': round(float(np.abs(lt - lp).mean()), 4),
            'logRMSE': round(float(np.sqrt(((lt - lp) ** 2).mean())), 4),
            'logR2': round(float(r2_score(lt, lp)), 4),
            'rawMAE': round(float(np.abs(yt - yp).mean()), 8),
            'relL2': round(float(np.linalg.norm(yt - yp) /
                                 np.linalg.norm(np.maximum(yt, 1e-20))), 4),
            'maxAbsErr': round(float(np.abs(yt - yp).max()), 8),
            'hotspot_true': int(np.argmax(yt, axis=1).mean()),
            'hotspot_hit': round(float(np.mean(np.argmax(yt, axis=1) ==
                                               np.argmax(yp, axis=1))), 4),
            'top5_overlap': round(float(np.mean(
                [len(set(np.argsort(yt[i])[-5:]) & set(np.argsort(yp[i])[-5:])) / 5
                 for i in range(len(idx))])), 4)}


all_idx = list(range(27))
report['overall'] = block('all', all_idx)
print('OVERALL: logMAE=%.4f logR2=%.4f relL2=%.4f hotspot_hit=%.2f top5=%.2f' % (
    report['overall']['logMAE'], report['overall']['logR2'],
    report['overall']['relL2'], report['overall']['hotspot_hit'],
    report['overall']['top5_overlap']))

report['by_time'] = {}
for t in ('500', '750', '3000'):
    idx = [i for i, c in enumerate(ids) if abs(float(ext[c]['t']) - float(t)) < 1]
    report['by_time'][t] = block('t=' + t, idx)
    b = report['by_time'][t]
    print('t=%s n=%d logMAE=%.4f logR2=%.4f relL2=%.4f' % (t, b['n'], b['logMAE'],
                                                             b['logR2'], b['relL2']))
report['by_geometry'] = {}
for g in ('100/20/4', '80/15/2', '120/25/3', '150/20/4'):
    idx = [i for i, c in enumerate(ids) if ext[c]['geometry_group'] == g]
    report['by_geometry'][g] = block(g, idx)
    b = report['by_geometry'][g]
    if b['n']:
        print('geo %-10s n=%d logMAE=%.4f logR2=%.4f relL2=%.4f hotspot=%.2f' %
              (g, b['n'], b['logMAE'], b['logR2'], b['relL2'], b['hotspot_hit']))

# per-case table
rows = []
for i, c in enumerate(ids):
    yt, yp = Yt[i], Yp[i]
    rows.append({'case_id': c, 'T': ext[c]['T'], 'P': ext[c]['P'], 't': ext[c]['t'],
                 'geom': ext[c]['geometry_group'],
                 'true_max': float(yt.max()), 'pred_max': float(yp.max()),
                 'max_ratio': round(float(yt.max() / max(yp.max(), 1e-300)), 3),
                 'logMAE': round(float(np.abs(Lt[i] - Lp[i]).mean()), 4),
                 'hotspot_true': int(np.argmax(yt)), 'hotspot_pred': int(np.argmax(yp))})
with open(os.path.join(METR, 'step15_c2_ext_results.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow(r)
for r in rows:
    print('  %-36s t=%-4s max_true=%.2e max_pred=%.2e ratio=%.2f logMAE=%.3f hs=%d/%d' %
          (r['case_id'], r['t'], r['true_max'], r['pred_max'], r['max_ratio'],
           r['logMAE'], r['hotspot_true'], r['hotspot_pred']))

# STEP14 scalar comparison (PhysB-quad refit55 known: TEST logMAE=1.221 on 9 ext_test)
report['step14_scalar'] = {'note': 'STEP14 PhysB-quad scalar: 9-case ext test logMAE=1.221 '
                                   '(B.8); STEP15 field surrogate overall logMAE=%.4f '
                                   'including those 9 cases' % report['overall']['logMAE']}
# physics audit
viol = []
if (Yp < 0).any(): viol.append('negative')
if not np.all(np.isfinite(Yp)): viol.append('nonfinite')
for i, c in enumerate(ids):
    for t2 in ('500', '750', '3000'):
        pass
report['physics'] = {'violations': viol or 'NONE'}
print('physics violations:', viol or 'NONE')

with open(os.path.join(METR, 'step15_c2_ext_audit.json'), 'w') as f:
    json.dump(report, f, indent=1)
print('evaluation written')
