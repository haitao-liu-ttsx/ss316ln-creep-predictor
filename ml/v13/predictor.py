"""STEP21-D: V1.3 unified prediction API.
Input: T(°C), P(MPa), t(h), Rm/Ro/w(mm). Output: 7 fields (2304) + von Mises
+ centroids + summary + domain status. Models loaded once (module cache).
All fitting artifacts are FROZEN (TRAIN-only); inference only.
"""
import json
import os
import sys
import time

import joblib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, 'models')
TARGETS = ['Srr', 'Stt', 'Szz', 'Srt', 'Srz', 'Stz', 'CEEQ']

E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0, 700: 141000.0, 750: 119000.0}
CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57),
         700: (2.92e-22, 6.97), 750: (2.78e-18, 5.56)}

_cache = {'models': None, 'guard': None, 'mesh': None}


_global_ranges_cache = None


def _global_ranges():
    """Frozen per-field global value ranges over all 230 cases (absolute-scale colormap).
    Loaded once; not part of model math."""
    global _global_ranges_cache
    if _global_ranges_cache is None:
        with open(os.path.join(HERE, 'global_ranges.json')) as f:
            _global_ranges_cache = json.load(f)
    return _global_ranges_cache


def _load():
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    if _cache['models'] is None:
        _cache['models'] = {t: joblib.load(os.path.join(MODELS, 'model_%s.joblib' % t)) for t in TARGETS}
    if _cache['guard'] is None:
        from domain_guard import DomainGuard
        _cache['guard'] = DomainGuard()
    if _cache['mesh'] is None:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'production', 'step15_v1_2', 'runtime'))
        from predict_field import _mesh
        _cache['mesh'] = _mesh
    return _cache['models'], _cache['guard'], _cache['mesh']


def _validate(T, P, t, Rm, Ro, w):
    errs = []
    for name, v in (('T', T), ('P', P), ('t', t), ('Rm', Rm), ('Ro', Ro), ('w', w)):
        if not isinstance(v, (int, float)) or not np.isfinite(v):
            errs.append('%s non-finite' % name)
    if P <= 0:
        errs.append('P must be > 0')
    if w <= 0:
        errs.append('w must be > 0')
    if not (Ro > w and Rm > 2 * Ro):
        errs.append('invalid geometry (need Ro>w and Rm>2Ro)')
    if int(round(T)) not in E_T:
        errs.append('T=%g not in material table (550/600/650/700/750)' % T)
    return errs


def _features(T, P, t, Rm, Ro, w):
    T_int = int(round(T))
    if T_int not in E_T:
        raise ValueError('T=%g: no material table (support 550/600/650/700/750)' % T)
    ss = P * Ro / w
    A, n = CREEP[T_int]
    return np.array([[T, P, np.log1p(t), Rm, Ro, w, E_T[T_int], A, n, np.log10(max(ss, 1e-9))]])


def predict(T, P, t, Rm, Ro, w):
    """Unified prediction. Returns dict (JSON-serializable with numpy arrays)."""
    models, guard, mesh = _load()
    errs = _validate(T, P, t, Rm, Ro, w)
    if errs:
        return {'status': 'INPUT_INVALID', 'errors': errs}
    domain_status, domain_reasons = guard.check(T, P, t, Rm, Ro, w)
    X = _features(T, P, t, Rm, Ro, w)
    out = {}
    for f in TARGETS:
        m = models[f]
        C = np.stack([reg.predict(X) for reg in m['regs']], axis=1)
        Yp = (C @ m['basis'].T) * m['sd'] + m['mu']
        if f == 'CEEQ':
            Yp = 10 ** Yp
        out[f] = Yp[0]
    # von Mises from predicted tensor (never loaded)
    a, b, c = out['Srr'], out['Stt'], out['Szz']
    d, e, f2 = out['Srt'], out['Srz'], out['Stz']
    vm = np.sqrt(((a - b) ** 2 + (b - c) ** 2 + (c - a) ** 2 + 6 * (d * d + e * e + f2 * f2)) / 2.0)
    if np.any(vm < 0) or not np.all(np.isfinite(vm)):
        return {'status': 'PREDICTION_ERROR', 'errors': ['von Mises non-finite/negative']}
    centroids = mesh(Rm, Ro, w)
    summary = {}
    for f in TARGETS + ['von_mises']:
        v = out[f] if f != 'von_mises' else vm
        summary[f] = {'min': float(v.min()), 'max': float(v.max()),
                      'mean': float(v.mean()), 'p95': float(np.percentile(v, 95))}
    return {
        'status': 'OK', 'model_version': 'V1.3', 'schema_version': 'v13.1',
        'inputs': {'T': T, 'P': P, 't': t, 'Rm': Rm, 'Ro': Ro, 'w': w,
                   'P_Ro_w': P * Ro / w},
        'global_ranges': _global_ranges(),
        'derived_features': {'log1p_t': float(np.log1p(t)), 'E': E_T[int(round(T))],
                             'A_creep': CREEP[int(round(T))][0], 'n_creep': CREEP[int(round(T))][1]},
        'domain_status': domain_status, 'domain_reasons': domain_reasons,
        'centroids': centroids,
        'fields': {f: out[f] for f in TARGETS} | {'von_mises': vm},
        'summary': summary,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
    }


def predict_serializable(T, P, t, Rm, Ro, w):
    """JSON-friendly wrapper (lists instead of arrays)."""
    r = predict(T, P, t, Rm, Ro, w)
    if r['status'] != 'OK':
        return r
    r['centroids'] = r['centroids'].tolist()
    r['fields'] = {k: v.tolist() for k, v in r['fields'].items()}
    return r


if __name__ == '__main__':
    import sys
    T, P, t, Rm, Ro, w = map(float, sys.argv[1:7])
    res = predict(T, P, t, Rm, Ro, w)
    print(json.dumps({k: v for k, v in res.items() if k != 'fields' and k != 'centroids'}, indent=1))
    if res['status'] == 'OK':
        print('Srr shape:', res['fields']['Srr'].shape, '| vm max: %.2f' % res['summary']['von_mises']['max'])
