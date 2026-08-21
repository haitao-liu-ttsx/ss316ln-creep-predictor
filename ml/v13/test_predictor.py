"""STEP21-D API unit tests (TEST 1-9)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from predictor import predict, predict_serializable  # noqa: E402

fails = []


def check(name, cond, detail=''):
    print('[%s] %s %s' % ('PASS' if cond else 'FAIL', name, detail))
    if not cond:
        fails.append(name)


# TEST 1: TRAIN real case
r = predict(700, 16, 1000, 100, 20, 4)
check('TEST1 TRAIN case prediction OK', r['status'] == 'OK' and
      r['fields']['Srr'].shape == (2304,) and r['domain_status'] in ('SAFE', 'WARNING'),
      'status=%s domain=%s' % (r['status'], r['domain_status']))

# TEST 2: VAL real case
r = predict(700, 16, 1000, 80, 15, 2)
check('TEST2 VAL case prediction OK', r['status'] == 'OK', r.get('domain_status'))

# TEST 3: EXT real case (120/25/3)
r = predict(700, 20, 100, 120, 25, 3)
check('TEST3 EXT case OK + domain flag', r['status'] == 'OK' and
      r['domain_status'] in ('WARNING', 'OUT_OF_DOMAIN'), r.get('domain_status'))
check('TEST3 stress still output', r['fields']['Szz'].shape == (2304,))

# TEST 4: 120/25/3 -> CEEQ warning/out, stress OK
check('TEST4 geometry 120/25/3 flagged', r['domain_status'] in ('WARNING', 'OUT_OF_DOMAIN'),
      r.get('domain_status'))

# TEST 5: 80/15/2 -> same
r = predict(750, 8, 1000, 80, 15, 2)
check('TEST5 geometry 80/15/2 flagged', r['status'] == 'OK' and
      r['domain_status'] in ('WARNING', 'OUT_OF_DOMAIN'), r.get('domain_status'))

# TEST 6: T=800 -> OUT_OF_DOMAIN
r = predict(800, 10, 100, 100, 20, 4)
check('TEST6 T=800 out of domain', r['status'] != 'OK' or r['domain_status'] == 'OUT_OF_DOMAIN',
      'status=%s' % r['status'])

# TEST 7: negative P
r = predict(700, -5, 100, 100, 20, 4)
check('TEST7 negative P invalid', r['status'] == 'INPUT_INVALID')

# TEST 8: w <= 0
r = predict(700, 10, 100, 100, 20, 0)
check('TEST8 w<=0 invalid', r['status'] == 'INPUT_INVALID')

# TEST 9: invalid geometry (Ro <= w)
r = predict(700, 10, 100, 100, 20, 25)
check('TEST9 invalid geometry (Ro<=w)', r['status'] == 'INPUT_INVALID', r.get('status'))

# von Mises sanity: non-negative + finite
import numpy as np
r = predict(650, 10, 3000, 100, 20, 4)
check('vm >= 0 and finite', r['status'] == 'OK' and r['fields']['von_mises'].min() >= 0 and
      bool(np.all(np.isfinite(r['fields']['von_mises']))), '')

# CEEQ non-negative
check('CEEQ >= 0', r['fields']['CEEQ'].min() >= 0)

# serializable wrapper
import json
r2 = predict_serializable(700, 16, 1000, 100, 20, 4)
try:
    json.dumps(r2)
    check('serializable JSON OK', True)
except Exception as e:  # noqa: BLE001
    check('serializable JSON OK', False, str(e)[:80])

print('\n%d/%d PASS' % (9 - len(fails), 9))
sys.exit(1 if fails else 0)
