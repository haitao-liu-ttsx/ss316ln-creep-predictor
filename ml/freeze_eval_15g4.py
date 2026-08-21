"""STEP 15-G.4: freeze v1.2 (poly10) + one-shot EXT 27 evaluation + v1/v1.1/v1.2
comparison. EXT target read once AFTER freeze manifest. LOCKED never read.
"""
import csv
import hashlib
import json
import os
import time

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
FIG = os.path.join(ROOT, 'docs', 'figures')
os.makedirs(FINAL, exist_ok=True)

c0 = json.load(open(os.path.join(METR, 'step15_c0_split_audit.json')))
OLD_IDS = c0['train']['ids'] + c0['validation']['ids']
TIME_GRID = [1, 3, 10, 30, 100, 300]
meta = {r['case_id']: r for r in
        csv.DictReader(open(os.path.join(ROOT, 'data', 'ai_ready_v4', 'simulation_dataset_318.csv')))}
new_design = list(csv.DictReader(open(os.path.join(METR, 'step15_g_odb_qc.csv'))))
split = json.load(open(os.path.join(METR, 'step15_g3_split_audit.json')))
train_ids = split['train']


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
LG = np.log10(np.array([s['field'] for s in S_tr]))
mu = LG.mean(axis=0)
U, s_, Vt = np.linalg.svd(LG - mu, full_matrices=False)
k = 3
modes = Vt[:k].T
Ctr = (LG - mu) @ modes
Xtr = np.array([feats(s['case'], s['t']) for s in S_tr])
scaler = StandardScaler().fit(Xtr)
regs = []
for j in range(k):
    poly = Pipeline([('poly', PolynomialFeatures(2)), ('scale', StandardScaler()),
                     ('m', Ridge(alpha=1.0))])
    poly.fit(scaler.transform(Xtr), Ctr[:, j])
    regs.append(poly)

# ---------------- FREEZE ----------------
np.savez(os.path.join(FINAL, 'pod_basis_v12_frozen.npz'), mean_log_field=mu,
         modes=modes, singular_values=s_, train_ids=train_ids)
import joblib
for j in range(k):
    joblib.dump(regs[j], os.path.join(FINAL, 'frozen_poly_mode%d.joblib' % (j + 1)))
with open(os.path.join(FINAL, 'v12_frozen_config.json'), 'w') as f:
    json.dump({'model': 'poly10: Ridge-Poly2 on log10(P*Ro/w)-augmented features',
               'pod': {'domain': 'log10(CEEQ)', 'k': 3, 'basis': 'TRAIN-only'},
               'features': ['T', 'P', 'log1p_time', 'Rm', 'Ro', 'w', 'E', 'A_creep',
                            'n_creep', 'log10(P*Ro/w)'],
               'time_treatment': 'log1p(t) inside Poly2 (no analytic term; 3000h in '
                                 'training coverage)',
               'seed': SEED, 'status': 'FROZEN v1.2'}, f, indent=1)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


man = {'model': 'v1.2 poly10 frozen',
       'checksums': {'pod': sha(os.path.join(FINAL, 'pod_basis_v12_frozen.npz')),
                     'mode1': sha(os.path.join(FINAL, 'frozen_poly_mode1.joblib')),
                     'mode2': sha(os.path.join(FINAL, 'frozen_poly_mode2.joblib')),
                     'mode3': sha(os.path.join(FINAL, 'frozen_poly_mode3.joblib')),
                     'config': sha(os.path.join(FINAL, 'v12_frozen_config.json')),
                     '318': hashlib.sha256(open(os.path.join(ROOT, 'data', 'ai_ready_v4',
                                                             'simulation_dataset_318.csv'),
                                                'rb').read()).hexdigest()[:12],
                     'locked': hashlib.sha256(open(os.path.join(ROOT, 'data', 'ai_ready_v4',
                                                                'test.csv'), 'rb').read()
                                              ).hexdigest()[:12]},
       'EXT_TARGET_READ': 'NO', 'LOCKED_TEST_READ': 'NO',
       'POST_FREEZE_RETRAINING': 'FORBIDDEN',
       'POST_FREEZE_MODEL_SELECTION': 'FORBIDDEN',
       'POST_FREEZE_POD_REFIT': 'FORBIDDEN',
       'freeze_timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
with open(os.path.join(FINAL, 'STEP15_G4_FREEZE_MANIFEST.json'), 'w') as f:
    json.dump(man, f, indent=1)
print('FREEZE manifest written; EXT_TARGET_READ=NO')

# ---------------- EXT prediction (no target) ----------------
ext = list(csv.DictReader(open(os.path.join(METR, 'step15_c2_ext_manifest.csv'))))
ids_e, log_f = [], []
for r in ext:
    m = {'T': int(float(r['T'])), 'P': float(r['P']), 'Rm': float(r['Rm']),
         'Ro': float(r['Ro']), 'w': float(r['w'])}
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    x = np.array([m['T'], m['P'], np.log1p(float(r['t'])), m['Rm'], m['Ro'], m['w'],
                  E_T[m['T']], CREEP[m['T']][0], CREEP[m['T']][1],
                  np.log10(max(m['P'] * m['Ro'] / m['w'], 1e-9))])
    c = np.array([regs[j].predict(scaler.transform(x.reshape(1, -1)))[0] for j in range(k)])
    log_f.append(mu + c @ modes.T)
    ids_e.append(r['case_id'])
LF = np.array(log_f)
np.savez(os.path.join(METR, 'step15_g4_ext_predictions.npz'),
         case_ids=np.array(ids_e), log_fields=LF, fields=10 ** LF)
print('EXT predictions saved (27) - target not yet read by v1.2')

# ---------------- ONE-WAY GATE ----------------
trf = np.load(os.path.join(METR, 'step15_c2_ext_true_fields.npz'))
assert list(trf['case_ids']) == ids_e
Yt = trf['fields']
Yp = 10 ** LF
Lt = np.log10(Yt)
print('EXT target FIRST read by v1.2 (post-freeze, one-shot)')


def block(idx):
    yt, yp = Yt[idx], Yp[idx]
    lt, lp = Lt[idx], LF[idx]
    return {'n': len(idx),
            'logMAE': round(float(np.abs(lt - lp).mean()), 4),
            'logRMSE': round(float(np.sqrt(((lt - lp) ** 2).mean())), 4),
            'logR2': round(float(r2_score(lt, lp)), 4),
            'relL2': round(float(np.linalg.norm(yt - yp) /
                                 np.linalg.norm(np.maximum(yt, 1e-20))), 4),
            'maxAbs': round(float(np.abs(yt - yp).max()), 8),
            'hs': round(float(np.mean(np.argmax(yt, 1) == np.argmax(yp, 1))), 4),
            'top5': round(float(np.mean([len(set(np.argsort(yt[i])[-5:]) &
                                          set(np.argsort(yp[i])[-5:])) / 5
                                         for i in range(len(idx))])), 4)}


all_i = list(range(27))
overall = block(all_i)
print('OVERALL v1.2 EXT:', overall)
tg = {}
for t in ('500', '750', '3000'):
    idx = [i for i, c in enumerate(ids_e) if abs(float(ext[i]['t']) - float(t)) < 1]
    tg[t] = block(idx)
    print('t=%s: logMAE=%.4f logR2=%.4f hs=%.2f' % (t, tg[t]['logMAE'], tg[t]['logR2'],
                                                    tg[t]['hs']))
gg = {}
for g in ('100/20/4', '80/15/2', '120/25/3', '150/20/4'):
    idx = [i for i, c in enumerate(ids_e) if ext[i]['geometry_group'] == g]
    gg[g] = block(idx)
    print('geo %-10s: logMAE=%.4f logR2=%.4f hs=%.2f' %
          (g, gg[g]['logMAE'], gg[g]['logR2'], gg[g]['hs']))
sg = {}
for lo, hi, nm in ((0, 60, 'low'), (60, 120, 'mid'), (120, 999, 'high')):
    idx = [i for i, c in enumerate(ids_e)
           if lo <= float(ext[i]['P']) * float(ext[i]['Ro']) / float(ext[i]['w']) < hi]
    if idx:
        sg[nm] = block(idx)
        print('stress %-4s: logMAE=%.4f logR2=%.4f hs=%.2f' %
              (nm, sg[nm]['logMAE'], sg[nm]['logR2'], sg[nm]['hs']))

# physics
phys = {'violations': []}
if (Yp < 0).any(): phys['violations'].append('negative')
if not np.all(np.isfinite(Yp)): phys['violations'].append('nonfinite')
print('physics:', phys['violations'] or 'NONE')

# per-case table
rows = []
for i, c in enumerate(ids_e):
    rows.append({'case_id': c, 'T': ext[i]['T'], 'P': ext[i]['P'], 't': ext[i]['t'],
                 'geom': ext[i]['geometry_group'],
                 'true_max': float(Yt[i].max()), 'pred_max': float(Yp[i].max()),
                 'ratio': round(float(Yt[i].max() / max(Yp[i].max(), 1e-300)), 2),
                 'logMAE': round(float(np.abs(Lt[i] - LF[i]).mean()), 4),
                 'hs': int(np.argmax(Yt[i])) == int(np.argmax(Yp[i]))})
with open(os.path.join(METR, 'step15_g4_ext_results.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow(r)
for r in rows:
    print('  %-36s t=%-4s ratio=%.2f logMAE=%.3f hs=%s' %
          (r['case_id'], r['t'], r['ratio'], r['logMAE'], r['hs']))

# group CSVs + v1/v1.1/v1.2 comparison
def wcsv(path, header, data):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in data:
            w.writerow(row)


wcsv(os.path.join(METR, 'step15_g4_ext_time_groups.csv'),
     ['time', 'n', 'logMAE', 'logRMSE', 'logR2', 'relL2', 'maxAbs', 'hs', 'top5'],
     [[t, b['n'], b['logMAE'], b['logRMSE'], b['logR2'], b['relL2'], b['maxAbs'],
       b['hs'], b['top5']] for t, b in tg.items()])
wcsv(os.path.join(METR, 'step15_g4_ext_geometry_groups.csv'),
     ['geometry', 'n', 'logMAE', 'logRMSE', 'logR2', 'relL2', 'maxAbs', 'hs', 'top5'],
     [[g, b['n'], b['logMAE'], b['logRMSE'], b['logR2'], b['relL2'], b['maxAbs'],
       b['hs'], b['top5']] for g, b in gg.items()])
wcsv(os.path.join(METR, 'step15_g4_ext_stress_groups.csv'),
     ['stress_bin', 'n', 'logMAE', 'logR2', 'hs'],
     [[nm, b['n'], b['logMAE'], b['logR2'], b['hs']] for nm, b in sg.items()])

v1 = json.load(open(os.path.join(METR, 'step15_c2_ext_audit.json')))
comp = [['metric', 'v1', 'v1.1', 'v1.2'],
        ['overall_logMAE', v1['overall']['logMAE'], 0.5911, overall['logMAE']],
        ['overall_logR2', v1['overall']['logR2'], 0.8711, overall['logR2']],
        ['t500_logMAE', v1['by_time']['500']['logMAE'], 0.1554, tg['500']['logMAE']],
        ['t750_logMAE', v1['by_time']['750']['logMAE'], 0.2120, tg['750']['logMAE']],
        ['t3000_logMAE', v1['by_time']['3000']['logMAE'], 1.4059, tg['3000']['logMAE']],
        ['t3000_logR2', v1['by_time']['3000']['logR2'], 0.5749, tg['3000']['logR2']],
        ['geo_baseline_logMAE', v1['by_geometry']['100/20/4']['logMAE'], 0.1837,
         gg['100/20/4']['logMAE']],
        ['geo_80_15_2_logMAE', v1['by_geometry']['80/15/2']['logMAE'], 1.4472,
         gg['80/15/2']['logMAE']],
        ['geo_120_25_3_logMAE', v1['by_geometry']['120/25/3']['logMAE'], 2.3861,
         gg['120/25/3']['logMAE']],
        ['geo_150_20_4_logMAE', v1['by_geometry']['150/20/4']['logMAE'], 0.3842,
         gg['150/20/4']['logMAE']],
        ['hotspot_hit', v1['overall']['hotspot_hit'], 1.0, overall['hs']],
        ['top5', v1['overall']['top5_overlap'], 0.5852, overall['top5']]]
with open(os.path.join(METR, 'step15_g4_v1_v11_v12_comparison.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    for r in comp:
        w.writerow(r)
for r in comp:
    print(r)

with open(os.path.join(METR, 'step15_g4_ext_physics_audit.json'), 'w') as f:
    json.dump(phys, f, indent=1)
fa = {'freeze': 'v1.2 poly10 FROZEN', 'ext_evaluated': 27,
      'ext_target_read': 'YES (post-freeze once)', 'locked_test_read': 'NO',
      '318_modified': 'NO', 'v11_modified': 'NO', 'post_ext_retraining': 'NO',
      'post_ext_selection': 'NO', 'checksums': man['checksums']}
with open(os.path.join(METR, 'step15_g4_ext_audit.json'), 'w') as f:
    json.dump(fa, f, indent=1)
print('STEP 15-G.4 complete')
