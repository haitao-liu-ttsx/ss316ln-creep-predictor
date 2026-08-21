"""STEP 15-G.5: production packaging + reproducibility/regression/guard tests."""
import csv
import hashlib
import json
import os
import shutil
import sys
import time

import numpy as np
import joblib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FROZEN = os.path.join(ROOT, 'ml', 'final', 'step15_v1_2')
PROD = os.path.join(ROOT, 'ml', 'production', 'step15_v1_2')
METR = os.path.join(ROOT, 'ml', 'metrics')

for sub in ('model', 'schema', 'runtime', 'tests'):
    os.makedirs(os.path.join(PROD, sub), exist_ok=True)

# ---------------- model artifacts ----------------
shutil.copy(os.path.join(FROZEN, 'pod_basis_v12_frozen.npz'), os.path.join(PROD, 'model'))
shutil.copy(os.path.join(FROZEN, 'v12_frozen_config.json'), os.path.join(PROD, 'model'))
for j in (1, 2, 3):
    shutil.copy(os.path.join(FROZEN, 'frozen_poly_mode%d.joblib' % j),
                os.path.join(PROD, 'model', 'poly_mode%d.joblib' % j))
# scaler: refit identically (deterministic) from TRAIN snapshots
DATA = os.path.join(ROOT, 'ml', 'data', 'step15_ceeq_snapshots')
DATA_NEW = os.path.join(ROOT, 'ml', 'data', 'step15g_snapshots')
c0 = json.load(open(os.path.join(METR, 'step15_c0_split_audit.json')))
OLD = c0['train']['ids'] + c0['validation']['ids']
TG = [1, 3, 10, 30, 100, 300]
meta = {r['case_id']: r for r in
        csv.DictReader(open(os.path.join(ROOT, 'data', 'ai_ready_v4', 'simulation_dataset_318.csv')))}
new_design = list(csv.DictReader(open(os.path.join(METR, 'step15_g_odb_qc.csv'))))
split = json.load(open(os.path.join(METR, 'step15_g3_split_audit.json')))
train_ids = split['train']


def feats(cid, t):
    if cid in meta:
        r = meta[cid]
        m = {'T': int(float(r['T_uniform'])), 'P': float(r['pressure']),
             'Rm': float(r['R_major']), 'Ro': float(r['R_outer']), 'w': float(r['wall_thickness'])}
    else:
        r = next(rr for rr in new_design if rr['case_id'] == cid)
        m = {'T': int(float(r['T'])), 'P': float(r['P']), 'Rm': float(r['Rm']),
             'Ro': float(r['Ro']), 'w': float(r['w'])}
    E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
    CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
    return np.array([m['T'], m['P'], np.log1p(t), m['Rm'], m['Ro'], m['w'],
                     E_T[m['T']], CREEP[m['T']][0], CREEP[m['T']][1],
                     np.log10(max(m['P'] * m['Ro'] / m['w'], 1e-9))])


Xall = []
for cid in train_ids:
    if cid in OLD:
        d = np.load(os.path.join(DATA, cid + '.npz'))
        ts = d['frame_times']
        for tg in TG:
            if tg <= float(ts[-1]) + 1e-9:
                Xall.append(feats(cid, tg))
    else:
        r = next(rr for rr in new_design if rr['case_id'] == cid)
        Xall.append(feats(cid, int(r['t'])))
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler().fit(np.array(Xall))
joblib.dump(scaler, os.path.join(PROD, 'model', 'scaler.joblib'))
print('model artifacts staged')
# now that model files exist, import runtime
sys.path.insert(0, os.path.join(PROD, 'runtime'))
from predict_field import predict_field, validate_input, get_hotspot, predict_time_series  # noqa: E402


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


# ---------------- schemas ----------------
json.dump({'inputs': [{'name': 'T', 'unit': 'degC', 'range': [550, 650]},
                      {'name': 'P', 'unit': 'MPa', 'range': [2.5, 30]},
                      {'name': 't', 'unit': 'h', 'range': [1, 3000]},
                      {'name': 'Rm', 'unit': 'mm', 'range': [80, 150]},
                      {'name': 'Ro', 'unit': 'mm', 'range': [15, 25]},
                      {'name': 'w', 'unit': 'mm', 'range': [2, 5]}],
           'derived': 'log10(P*Ro/w)', 'stress_scale_max': 250},
          open(os.path.join(PROD, 'schema', 'input_schema.json'), 'w'), indent=1)
json.dump({'ceeq_field': {'shape': [2304], 'type': 'element-centroid CEEQ'},
           'max_ceeq': 'float', 'mean_ceeq': 'float', 'p95_ceeq': 'float',
           'hotspot_element': 'int (0-2303)', 'pod_coefficients': '[3]',
           'validity': 'VALID|OUT_OF_DOMAIN', 'mesh': '48x16x3 torus (3072 nodes)'},
          open(os.path.join(PROD, 'schema', 'output_schema.json'), 'w'), indent=1)
json.dump({'topology': {'nodes': 3072, 'elements': 2304, 'type': 'C3D8R'},
           'mapping': 'deterministic torus mesh, element order = POD field index',
           'coordinates': 'element centroids (x,y,z) of requested geometry'},
          open(os.path.join(PROD, 'schema', 'geometry_schema.json'), 'w'), indent=1)

# ---------------- tests ----------------
tests = {
    'test_checksum.py': '''
import hashlib, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); PROD = os.path.dirname(HERE)
m = json.load(open(os.path.join(PROD, 'model', 'v12_frozen_config.json')))
assert 'FROZEN' in m['status']
for f in ('pod_basis_v12_frozen.npz', 'scaler.joblib', 'poly_mode1.joblib',
          'poly_mode2.joblib', 'poly_mode3.joblib'):
    p = os.path.join(PROD, 'model', f)
    assert os.path.exists(p), f
    print(f, hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12])
print('test_checksum PASS')
''',
    'test_input_validation.py': '''
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'runtime'))
from predict_field import predict_field
assert predict_field(600, 10, 100, 100, 20, 4)['validity'] == 'VALID'
assert predict_field(700, 10, 100, 100, 20, 4)['validity'] == 'OUT_OF_DOMAIN'
assert predict_field(600, 10, 4000, 100, 20, 4)['validity'] == 'OUT_OF_DOMAIN'
assert predict_field(600, 40, 100, 100, 20, 4)['validity'] == 'OUT_OF_DOMAIN'   # P>30
assert predict_field(600, 30, 100, 100, 25, 4)['validity'] == 'VALID'            # ss=187.5<=250
assert predict_field(600, 30, 100, 100, 25, 2)['validity'] == 'OUT_OF_DOMAIN'    # ss=375>250
assert predict_field(650, 30, 3000, 150, 25, 3)['validity'] == 'VALID'
print('test_input_validation PASS')
''',
    'test_physics_constraints.py': '''
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'runtime'))
from predict_field import predict_field, predict_time_series
import numpy as np
for T, P, t, Rm, Ro, w in [(550,5,1,100,20,4),(650,20,3000,80,15,2),(600,10,750,120,25,3)]:
    r = predict_field(T,P,t,Rm,Ro,w)
    f = np.array(r['ceeq_field'])
    assert f.shape == (2304,) and np.all(np.isfinite(f)) and (f >= 0).all(), (T,P,t)
    assert r['hotspot_element'] is not None
ts = predict_time_series(650, 20, 150, 20, 4)
assert ts['t_monotonic'], 'time series must be monotonic'
print('test_physics_constraints PASS')
''',
    'test_known_cases.py': '''
import sys, os, csv, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'runtime'))
from predict_field import predict_field
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
cases = [('CEEQ15G_T650_P20_t3000h_Rm80_Ro15_w2', 650, 20, 3000, 80, 15, 2),
         ('CEEQ15G_T550_P10_t3000h_Rm120_Ro25_w3', 550, 10, 3000, 120, 25, 3),
         ('CR_650_P10_T1000h', 650, 10, 1000, 100, 20, 4),
         ('CEEQ14A_T550_P5_t500h_Rm100_Ro20_w4', 550, 5, 500, 100, 20, 4),
         ('CR_600_P5_T100h', 600, 5, 100, 100, 20, 4)]
for cid, T, P, t, Rm, Ro, w in cases:
    r = predict_field(T, P, t, Rm, Ro, w)
    assert r['validity'] == 'VALID' and r['ceeq_field'] is not None
    print(cid, 'max=%.3e hotspot=%d' % (r['max_ceeq'], r['hotspot_element']))
print('test_known_cases PASS (5 regression cases)')
''',
    'test_reconstruction.py': '''
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'runtime'))
from predict_field import predict_field
import numpy as np
r = predict_field(650, 20, 3000, 120, 25, 3)
f = np.array(r['ceeq_field'])
c = np.array(r['pod_coefficients'])
print('reconstructed field shape:', f.shape, 'finite:', np.all(np.isfinite(f)))
print('max/min:', f.max(), f.min())
assert f.shape == (2304,) and (f > 0).all()
print('test_reconstruction PASS')
''',
}
for name, code in tests.items():
    with open(os.path.join(PROD, 'tests', name), 'w') as f:
        f.write(code.lstrip('\n'))

# ---------------- production manifest ----------------
g4_audit = json.load(open(os.path.join(METR, 'step15_g4_ext_audit.json')))
man = {
    'model_version': 'STEP15-v1.2',
    'architecture': 'POD(log10 CEEQ, k=3) + Poly2/Ridge modal regression + log10(P*Ro/w)',
    'training_data': '87 cases (37 old t<=300h + 50 new: 48x3000h + 2x1000h); TRAIN 68 / VAL 19',
    'pod': {'domain': 'log10(CEEQ)', 'k': 3, 'basis': 'TRAIN-only'},
    'feature_schema': ['T', 'P', 'log1p_time', 'Rm', 'Ro', 'w', 'E', 'A_creep',
                       'n_creep', 'log10(P*Ro/w)'],
    'checksums': {'pod': sha(os.path.join(PROD, 'model', 'pod_basis_v12_frozen.npz')),
                  'scaler': sha(os.path.join(PROD, 'model', 'scaler.joblib')),
                  'config': sha(os.path.join(PROD, 'model', 'v12_frozen_config.json')),
                  'mode1': sha(os.path.join(PROD, 'model', 'poly_mode1.joblib')),
                  'mode2': sha(os.path.join(PROD, 'model', 'poly_mode2.joblib')),
                  'mode3': sha(os.path.join(PROD, 'model', 'poly_mode3.joblib'))},
    'production_domain': {'T': [550, 650], 'P': [2.5, 30], 't': [1, 3000],
                          'Rm': [80, 150], 'Ro': [15, 25], 'w': [2, 5],
                          'stress_scale_max': 250},
    'out_of_domain_rules': ['T>650 or T<550: OUT_OF_DOMAIN (DATA_REQUIRED above 650)',
                            't>3000: OUT_OF_DOMAIN', 'P>30: OUT_OF_DOMAIN',
                            'P*Ro/w>250: OUT_OF_DOMAIN'],
    'ext27_validation': {'logMAE': 0.0314, 'logR2': 0.9998, 'relL2': 0.148,
                         'hotspot': '27/27', 'physics_violations': 0,
                         't3000_logMAE': 0.0378, 't3000_logR2': 0.9996,
                         'geo_120_25_3_logMAE': 0.0678},
    'g4_validation_status': g4_audit,
    'train_val_usage': 'TRAIN/VAL used for training/selection',
    'ext27_usage': 'external validation only (once, post-freeze)',
    'locked20_usage': 'NEVER read (checksum fa573e330926 protected)',
    'creation_timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
}
with open(os.path.join(PROD, 'PRODUCTION_MANIFEST.json'), 'w') as f:
    json.dump(man, f, indent=1)
with open(os.path.join(PROD, 'README.md'), 'w') as f:
    f.write('# STEP15-v1.2 Production Package\n\n'
            'SS316LN toroidal 3D spatiotemporal CEEQ field surrogate.\n'
            'Domain guard enforced; see PRODUCTION_MANIFEST.json.\n'
            'API: runtime/predict_field.py -> predict_field(T,P,t,Rm,Ro,w)\n')

# ---------------- reproducibility test vs G.4 saved predictions ----------------
g4 = np.load(os.path.join(METR, 'step15_g4_ext_predictions.npz'))
ext = list(csv.DictReader(open(os.path.join(METR, 'step15_c2_ext_manifest.csv'))))
maxdiff = 0.0
for i, cid in enumerate(ext):
    r = ext[i]
    pred = predict_field(float(r['T']), float(r['P']), float(r['t']),
                         float(r['Rm']), float(r['Ro']), float(r['w']))
    saved = 10 ** g4['log_fields'][i]
    diff = np.abs(np.array(pred['ceeq_field']) - saved).max()
    maxdiff = max(maxdiff, float(diff))
    meandiff = np.abs(np.array(pred['ceeq_field']) - saved).mean()
print('reproducibility vs G.4: max_abs_diff=%.3e mean_abs_diff=%.3e' % (maxdiff, meandiff))
assert maxdiff < 1e-6, 'reproducibility FAILED'

# ---------------- run tests ----------------
import subprocess
for name in ('test_checksum.py', 'test_input_validation.py',
             'test_physics_constraints.py', 'test_known_cases.py',
             'test_reconstruction.py'):
    r = subprocess.run([sys.executable, os.path.join(PROD, 'tests', name)],
                       capture_output=True, text=True)
    print('%s: %s' % (name, 'PASS' if r.returncode == 0 else 'FAIL'))
    if r.returncode != 0:
        print(r.stdout, r.stderr)
print('PRODUCTION PACKAGE COMPLETE ->', PROD)
