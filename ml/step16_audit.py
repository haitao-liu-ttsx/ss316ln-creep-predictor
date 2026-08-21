"""STEP 16-A/B: final asset audit + production API acceptance (read-only, no
model changes, no LOCKED read)."""
import csv
import hashlib
import json
import math
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
PROD = os.path.join(ROOT, 'ml', 'production', 'step15_v1_2')
sys.path.insert(0, os.path.join(PROD, 'runtime'))
from predict_field import predict_field  # noqa: E402

# ---------------- A. asset audit ----------------
assets = [
    ('318_dataset', os.path.join(ROOT, 'data', 'ai_ready_v4', 'simulation_dataset_318.csv'),
     '20f21ebc67ea'),
    ('locked_test', os.path.join(ROOT, 'data', 'ai_ready_v4', 'test.csv'), 'fa573e330926'),
    ('step14_final', os.path.join(ROOT, 'ml', 'final', 'step14b_refit_model.json'), None),
    ('v1_pod', os.path.join(ROOT, 'ml', 'final', 'step15_v1', 'pod_basis.npz'), None),
    ('v11_pod', os.path.join(ROOT, 'ml', 'final', 'step15_v1_1', 'pod_basis_v11_frozen.npz'), None),
    ('v12_pod', os.path.join(ROOT, 'ml', 'final', 'step15_v1_2', 'pod_basis_v12_frozen.npz'), None),
    ('v12_config', os.path.join(ROOT, 'ml', 'final', 'step15_v1_2', 'v12_frozen_config.json'), None),
    ('prod_manifest', os.path.join(PROD, 'PRODUCTION_MANIFEST.json'), None),
    ('prod_runtime', os.path.join(PROD, 'runtime', 'predict_field.py'), None),
    ('g4_ext_results', os.path.join(METR, 'step15_g4_ext_results.csv'), None),
    ('g4_ext_audit', os.path.join(METR, 'step15_g4_ext_audit.json'), None),
]
audit = {}
for name, path, expect in assets:
    if not os.path.exists(path):
        audit[name] = {'path': path, 'exists': False, 'status': 'MISSING'}
        continue
    h = hashlib.sha256(open(path, 'rb').read()).hexdigest()[:12]
    status = 'OK' if (expect is None or h == expect) else 'CHECKSUM_MISMATCH'
    audit[name] = {'path': path, 'exists': True, 'sha256': h, 'expected': expect,
                   'status': status,
                   'mtime': time.strftime('%Y-%m-%d %H:%M', time.localtime(
                       os.path.getmtime(path)))}
    print('[%s] %-16s %s' % ('PASS' if status == 'OK' else 'FAIL', name, h))
bad = [k for k, v in audit.items() if v['status'] != 'OK']
with open(os.path.join(METR, 'step16_final_asset_audit.json'), 'w') as f:
    json.dump(audit, f, indent=1)
print('asset audit: %d assets, issues=%s' % (len(assets), bad or 'NONE'))

# ---------------- B. API acceptance ----------------
tests = [
    ('valid_domain', dict(T=600, P=10, t=100, Rm=100, Ro=20, w=4), 'VALID'),
    ('T_lower', dict(T=550, P=10, t=100, Rm=100, Ro=20, w=4), 'VALID'),
    ('T_upper', dict(T=650, P=10, t=100, Rm=100, Ro=20, w=4), 'VALID'),
    ('P_lower', dict(T=600, P=2.5, t=100, Rm=100, Ro=20, w=4), 'VALID'),
    ('P_upper', dict(T=600, P=30, t=100, Rm=100, Ro=20, w=4), 'VALID'),
    ('t_min', dict(T=600, P=10, t=1, Rm=100, Ro=20, w=4), 'VALID'),
    ('t_max', dict(T=600, P=10, t=3000, Rm=100, Ro=20, w=4), 'VALID'),
    ('geom_boundary', dict(T=600, P=10, t=100, Rm=80, Ro=15, w=2), 'VALID'),
    ('stress_boundary', dict(T=600, P=30, t=100, Rm=100, Ro=25, w=3), 'VALID'),
    ('T700', dict(T=700, P=10, t=100, Rm=100, Ro=20, w=4), 'OUT_OF_DOMAIN'),
    ('t3001', dict(T=600, P=10, t=3001, Rm=100, Ro=20, w=4), 'OUT_OF_DOMAIN'),
    ('P31', dict(T=600, P=31, t=100, Rm=100, Ro=20, w=4), 'OUT_OF_DOMAIN'),
    ('stress_over', dict(T=600, P=30, t=100, Rm=100, Ro=25, w=2), 'OUT_OF_DOMAIN'),
]
api = {'cases': []}
all_pass = True
for name, kw, expect in tests:
    r = predict_field(**kw)
    f = r['ceeq_field']
    if expect == 'VALID':
        shape_ok = f is not None and len(f) == 2304
        finite = f is not None and np.all(np.isfinite(f))
        pos = f is not None and (np.array(f) >= 0).all()
    else:  # OUT_OF_DOMAIN: no field by design
        shape_ok = finite = pos = f is None
    ok = (r['validity'] == expect and shape_ok and finite and pos)
    all_pass &= ok
    api['cases'].append({'name': name, 'params': kw, 'expected': expect,
                         'got': r['validity'], 'shape_ok': bool(shape_ok),
                         'finite': bool(finite), 'nonneg': bool(pos), 'pass': bool(ok)})
    print('[%s] %-16s expect=%-14s got=%-14s' % ('PASS' if ok else 'FAIL', name,
                                                  expect, r['validity']))
# determinism: repeated inference identical
r1 = predict_field(600, 10, 100, 100, 20, 4)
r2 = predict_field(600, 10, 100, 100, 20, 4)
det = np.array(r1['ceeq_field']) == np.array(r2['ceeq_field'])
api['deterministic'] = bool(det.all())
all_pass &= bool(det.all())
# NaN/Inf/negative input handling
for bad_in in (dict(T=float('nan'), P=10, t=100, Rm=100, Ro=20, w=4),
               dict(T=600, P=10, t=100, Rm=100, Ro=20, w=-3)):
    try:
        rb = predict_field(**bad_in)
        guarded = rb['validity'] == 'OUT_OF_DOMAIN'
    except Exception:
        guarded = True
    api.setdefault('bad_input_guarded', []).append(guarded)
    all_pass &= guarded
with open(os.path.join(METR, 'step16_api_acceptance.json'), 'w') as f:
    json.dump({'all_pass': bool(all_pass), 'n_tests': len(tests) + 2, 'api': api,
               'bad_input_guarded': [bool(b) for b in api.get('bad_input_guarded', [])]}, f, indent=1)
print('API acceptance: %s (%d cases + determinism + bad-input)' %
      ('PASS' if all_pass else 'FAIL', len(tests)))
sys.exit(0 if all_pass and not bad else 1)
