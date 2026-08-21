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
