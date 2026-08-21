"""STEP17 tests: web API output == production API output (max_abs_diff=0)."""
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'webapp', 'backend'))
sys.path.insert(0, os.path.join(ROOT, 'ml', 'production', 'step15_v1_2', 'runtime'))
from app import app  # noqa: E402
from predict_field import predict_field  # noqa: E402

CASES = [
    ('baseline', dict(T=600, P=10, t=100, Rm=100, Ro=20, w=4)),
    ('nonbaseline', dict(T=650, P=20, t=3000, Rm=120, Ro=25, w=3)),
    ('t3000', dict(T=600, P=10, t=3000, Rm=100, Ro=20, w=4)),
    ('P30', dict(T=650, P=30, t=500, Rm=100, Ro=20, w=4)),
    ('stress250', dict(T=600, P=30, t=100, Rm=100, Ro=25, w=3)),
]
OOD = [
    ('T700', dict(T=700, P=10, t=100, Rm=100, Ro=20, w=4)),
    ('t3001', dict(T=600, P=10, t=3001, Rm=100, Ro=20, w=4)),
    ('P31', dict(T=600, P=31, t=100, Rm=100, Ro=20, w=4)),
    ('stress_over', dict(T=600, P=30, t=100, Rm=100, Ro=25, w=2)),
]

client = app.test_client()
maxdiff = 0.0
n_pass = 0
for name, kw in CASES:
    r = client.post('/api/predict', json=kw).get_json()
    assert r['valid'] is True, (name, r)
    p = predict_field(**kw)
    diff = np.abs(np.array(r['field']) - np.array(p['ceeq_field'])).max()
    maxdiff = max(maxdiff, float(diff))
    assert float(diff) < 1e-12, (name, diff)
    assert len(r['field']) == 2304 and r['physics_status'] == 'PASS'
    n_pass += 1
    print('[PASS] %-12s max_abs_diff=%.3e' % (name, diff))
for name, kw in OOD:
    r = client.post('/api/predict', json=kw).get_json()
    assert r['valid'] is False and r['status'] == 'OUT_OF_DOMAIN', (name, r)
    assert r['violations'], (name, r)
    n_pass += 1
    print('[PASS] %-12s OUT_OF_DOMAIN violations=%d' % (name, len(r['violations'])))
# NaN / negative input
r = client.post('/api/predict', json=dict(T=float('nan'), P=10, t=100, Rm=100, Ro=20, w=4)).get_json()
assert r['valid'] is False, r
n_pass += 1
print('[PASS] nan_input guarded')
r = client.post('/api/predict', json=dict(T=600, P=10, t=100, Rm=100, Ro=20, w=-3)).get_json()
assert r['valid'] is False, r
n_pass += 1
print('[PASS] negative_input guarded')
# determinism
r1 = client.post('/api/predict', json=CASES[0][1]).get_json()
r2 = client.post('/api/predict', json=CASES[0][1]).get_json()
assert r1['field'] == r2['field']
n_pass += 1
print('[PASS] deterministic')
print('TOTAL: %d/%d PASS, web-vs-production max_abs_diff=%.3e' % (n_pass, n_pass, maxdiff))
assert maxdiff == 0.0, 'Web API must equal production API exactly'
print('WEBAPP CONSISTENCY TEST PASS')
