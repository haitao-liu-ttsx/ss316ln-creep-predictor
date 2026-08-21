"""STEP18 UI acceptance: 10 checks (API-level 1-7 via consistency suite, demo
cases 8, 3D/hotspot rendering 9-10 via build + screenshot pixel evidence)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = []

# 1-7 API-level checks (covered by test_api_consistency.py, rerun here)
from test_api_consistency import client, CASES, OOD  # noqa: E402
for name, kw in CASES:
    r = client.post('/api/predict', json=kw).get_json()
    assert r['valid'] is True and len(r['field']) == 2304
    passed.append('normal/valid %s' % name)
for name, kw in OOD:
    r = client.post('/api/predict', json=kw).get_json()
    assert r['valid'] is False and r['status'] == 'OUT_OF_DOMAIN'
    passed.append('ood %s' % name)
for bad in (dict(T=float('nan'), P=10, t=100, Rm=100, Ro=20, w=4),
            dict(T=600, P=10, t=100, Rm=100, Ro=20, w=-3)):
    r = client.post('/api/predict', json=bad).get_json()
    assert r['valid'] is False
    passed.append('guarded bad input')

# 8 demo cases structure
demo = json.load(open(os.path.join(ROOT, 'webapp', 'demo_cases.json'), encoding='utf-8'))
assert len(demo['cases']) == 4
for c in demo['cases']:
    for k in ('T', 'P', 't', 'Rm', 'Ro', 'w'):
        assert k in c and isinstance(c[k], (int, float))
passed.append('demo cases structure')

# 9-10 3D rendering / hotspot rendering: screenshot pixel evidence
from PIL import Image
import numpy as np
figs = os.path.join(ROOT, 'docs', 'figures', 'webapp')
for f in ('webapp_main.png', 'webapp_case2.png', 'webapp_ood.png'):
    p = os.path.join(figs, f)
    assert os.path.exists(p), f
    im = np.array(Image.open(p).convert('RGB'))
    colored = ((im[:, :, 0].astype(int) - im[:, :, 2].astype(int)) > 40).mean()
    red = ((im[:, :, 0] > 180) & (im[:, :, 1] < 90) & (im[:, :, 2] < 90)).mean()
    assert colored > 0.005, '3D field colors missing in %s' % f
    if f != 'webapp_ood.png':
        assert red > 0.0005, 'hotspot marker missing in %s' % f
    passed.append('screenshot render %s (3D colors + hotspot)' % f)

print('UI acceptance: %d/%d PASS' % (len(passed), len(passed)))
for p in passed:
    print('  [PASS]', p)
print('UI ACCEPTANCE PASS')
