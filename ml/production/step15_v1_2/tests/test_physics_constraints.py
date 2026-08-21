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
