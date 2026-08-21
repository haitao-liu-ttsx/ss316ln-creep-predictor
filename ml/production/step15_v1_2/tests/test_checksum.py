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
