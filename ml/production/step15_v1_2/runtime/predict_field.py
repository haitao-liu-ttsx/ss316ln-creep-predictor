"""STEP15-v1.2 production inference API (frozen, no retraining).

predict_field(T, P, t, Rm, Ro, w) -> 2304 element-centroid CEEQ field + metrics.
Domain guard: returns OUT_OF_DOMAIN with offending params instead of silent
prediction. Physics guard: CEEQ>=0, finite enforced as checks (never modified).
Mesh mapping: torus mesh rebuilt deterministically (48x16x3) for element
centroids of the requested geometry; field index = element order.
"""
import json
import math
import os

import numpy as np
import joblib
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Ridge

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.dirname(HERE)
MODEL = os.path.join(PROD, 'model')

DOMAIN = {'T': (550, 650), 'P': (2.5, 30), 't': (1, 3000), 'Rm': (80, 150),
          'Ro': (15, 25), 'w': (2, 5), 'stress_scale': (None, 250)}
DATA_REQUIRED = {'T_out': '700/750C Norton params DATA_REQUIRED',
                 't_out': '>3000h not validated',
                 'P_out': '>30MPa creep not trained',
                 'stress_out': 'P*Ro/w>250 not covered'}

# frozen artifacts
_basis = np.load(os.path.join(MODEL, 'pod_basis_v12_frozen.npz'))
MU = _basis['mean_log_field']
MODES = _basis['modes']
K = MODES.shape[1]
SCALER = joblib.load(os.path.join(MODEL, 'scaler.joblib'))
REGS = [joblib.load(os.path.join(MODEL, 'poly_mode%d.joblib' % (j + 1)))
        for j in range(K)]
CONFIG = json.load(open(os.path.join(MODEL, 'v12_frozen_config.json')))

E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}
CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}


def _mesh(Rm, Ro, w, nt=48, np_=48 // 3, nw=3):
    """Deterministic torus mesh (same as project generator): nodes + elements.
    Returns element centroids [2304, 3] in canonical element order."""
    np_ = 16
    Ri = Ro - w
    nodes = []
    for kk in range(nw + 1):
        r = Ri + (Ro - Ri) * kk / nw
        for j in range(np_):
            phi = 2 * math.pi * j / np_
            for i in range(nt):
                theta = 2 * math.pi * i / nt
                cx, cy = Rm * math.cos(theta), Rm * math.sin(theta)
                er = (math.cos(theta), math.sin(theta), 0.0)
                ez = (0.0, 0.0, 1.0)
                nodes.append([cx + r * (math.cos(phi) * er[0] + math.sin(phi) * ez[0]),
                              cy + r * (math.cos(phi) * er[1] + math.sin(phi) * ez[1]),
                              r * (math.cos(phi) * er[2] + math.sin(phi) * ez[2])])
    nodes = np.array(nodes)

    def nid(a, b, c):
        return 1 + a + nt * (b + np_ * c)

    centroids = []
    for kk in range(nw):
        for j in range(np_):
            jp = (j + 1) % np_
            for i in range(nt):
                ip = (i + 1) % nt
                ids = [nid(i, j, kk), nid(ip, j, kk), nid(ip, jp, kk),
                       nid(i, jp, kk), nid(i, j, kk + 1), nid(ip, j, kk + 1),
                       nid(ip, jp, kk + 1), nid(i, jp, kk + 1)]
                centroids.append(nodes[[i - 1 for i in ids]].mean(axis=0))
    return np.array(centroids)


def validate_input(T, P, t, Rm, Ro, w):
    """Return (ok, issues, validity)."""
    issues = []
    for nm, v in (('T', T), ('P', P), ('t', t), ('Rm', Rm), ('Ro', Ro), ('w', w)):
        if not (isinstance(v, (int, float)) and math.isfinite(v)):
            issues.append('%s=%r non-finite input' % (nm, v))
    if issues:
        return False, issues, float('nan')
    if not (DOMAIN['T'][0] <= T <= DOMAIN['T'][1]):
        issues.append('T=%g out of [550,650] (DATA_REQUIRED above 650)' % T)
    if not (DOMAIN['P'][0] <= P <= DOMAIN['P'][1]):
        issues.append('P=%g out of [2.5,30]' % P)
    if not (DOMAIN['t'][0] <= t <= DOMAIN['t'][1]):
        issues.append('t=%g out of [1,3000]' % t)
    if not (DOMAIN['Rm'][0] <= Rm <= DOMAIN['Rm'][1]):
        issues.append('Rm=%g out of [80,150]' % Rm)
    if not (DOMAIN['Ro'][0] <= Ro <= DOMAIN['Ro'][1]):
        issues.append('Ro=%g out of [15,25]' % Ro)
    if not (DOMAIN['w'][0] <= w <= DOMAIN['w'][1]):
        issues.append('w=%g out of [2,5]' % w)
    if not (Ro > w and Rm > 2 * Ro):
        issues.append('invalid geometry (Ro<=w or Rm<=2Ro)')
    ss = P * Ro / w
    if ss > DOMAIN['stress_scale'][1]:
        issues.append('stress_scale=P*Ro/w=%g > 250' % ss)
    T_int = int(round(T))
    if T_int not in E_T:
        issues.append('T=%g: no material table (DATA_REQUIRED)' % T)
    return (not issues), issues, ss


def predict_field(T, P, t, Rm, Ro, w):
    """Main inference API. Returns dict with field + metrics + validity."""
    ok, issues, ss = validate_input(T, P, t, Rm, Ro, w)
    out = {'case_parameters': {'T': T, 'P': P, 't': t, 'Rm': Rm, 'Ro': Ro, 'w': w},
           'stress_scale': ss, 'validity': 'VALID' if ok else 'OUT_OF_DOMAIN',
           'domain_issues': issues, 'model_version': 'STEP15-v1.2',
           'field_shape': [2304], 'physics_warning': []}
    if not ok:
        out['ceeq_field'] = None
        out['pod_coefficients'] = None
        out['max_ceeq'] = None
        out['hotspot_element'] = None
        out['hotspot_value'] = None
        return out
    T_int = int(round(T))
    x = np.array([[T, P, math.log1p(t), Rm, Ro, w, E_T[T_int],
                   CREEP[T_int][0], CREEP[T_int][1], math.log10(max(ss, 1e-9))]])
    c = np.array([REGS[j].predict(SCALER.transform(x))[0] for j in range(K)])
    log_f = MU + c @ MODES.T
    field = 10 ** log_f
    # physics guard (never modify)
    if not np.all(np.isfinite(field)):
        out['physics_warning'].append('nonfinite')
    if (field < 0).any():
        out['physics_warning'].append('negative')
    out['ceeq_field'] = field.tolist()
    out['pod_coefficients'] = c.tolist()
    out['max_ceeq'] = float(field.max())
    out['mean_ceeq'] = float(field.mean())
    out['p95_ceeq'] = float(np.percentile(field, 95))
    out['hotspot_element'] = int(np.argmax(field))
    out['hotspot_value'] = float(field.max())
    out['centroids'] = _mesh(Rm, Ro, w).tolist()
    return out


def get_hotspot(field):
    a = np.asarray(field)
    top5 = np.argsort(a)[-5:][::-1]
    return {'hotspot_element': int(top5[0]), 'value': float(a[top5[0]]),
            'top5_elements': [int(i) for i in top5],
            'top5_values': [float(a[i]) for i in top5]}


def predict_time_series(T, P, Rm, Ro, w, t_grid=None):
    if t_grid is None:
        t_grid = [1, 3, 10, 30, 100, 300, 500, 750, 1000, 3000]
    out = []
    for t in t_grid:
        r = predict_field(T, P, t, Rm, Ro, w)
        out.append({'t': t, 'validity': r['validity'],
                    'max_ceeq': r['max_ceeq'], 'field': r['ceeq_field']})
    maxima = [o['max_ceeq'] for o in out if o['validity'] == 'VALID' and o['max_ceeq']]
    mono = all(maxima[i + 1] >= maxima[i] for i in range(len(maxima) - 1)) if len(maxima) > 1 else True
    return {'series': out, 'max_ceeq_vs_t': maxima, 't_monotonic': bool(mono)}


if __name__ == '__main__':
    import sys
    T, P, t, Rm, Ro, w = map(float, sys.argv[1:7])
    r = predict_field(T, P, t, Rm, Ro, w)
    print(json.dumps({k: v for k, v in r.items() if k != 'ceeq_field' and k != 'centroids'},
                     indent=1, default=str))
    print('field[0:3]:', r['ceeq_field'][:3] if r['ceeq_field'] else None)
