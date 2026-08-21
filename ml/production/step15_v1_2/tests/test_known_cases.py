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
