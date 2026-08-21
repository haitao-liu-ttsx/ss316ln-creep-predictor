"""STEP 15-B.3: POD/PCA feasibility on 57 CEEQ field snapshots (exploratory only).

Builds snapshot matrix (final-frame CEEQ fields per case, 57 x 2304 element
field), compares raw vs log10 POD (explained variance + reconstruction),
scans k in {2,3,5,8,10,15,20,30,40}. QC: zero initial frames allowed (t~0),
nan/inf/neg must be zero. EXPLORATORY: production POD basis must later be
re-fit on TRAIN snapshots only (documented).
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'ml', 'data', 'step15_ceeq_snapshots')
METR = os.path.join(ROOT, 'ml', 'metrics')

ids = sorted(f[:-4] for f in os.listdir(DATA) if f.endswith('.npz'))
print('snapshots found:', len(ids))
F = []
for cid in ids:
    d = np.load(os.path.join(DATA, cid + '.npz'))
    ceeq = d['ceeq_frames']
    times = d['frame_times']
    # final frame field
    fin = ceeq[-1]
    assert fin.shape == (2304,)
    F.append(fin)
F = np.array(F)  # [57, 2304]
print('snapshot matrix:', F.shape)
print('QC: nan=%d inf=%d neg=%d' % (np.isnan(F).sum(), np.isinf(F).sum(), (F < 0).sum()))
print('amplitude: min=%.3e max=%.3e' % (F.min(), F.max()))


def pod(X):
    """X: [n, d]. Returns modes [d, k], coeffs [n, k], explained var, center."""
    mu = X.mean(axis=0)
    Xc = X - mu
    U, s, Vt = np.linalg.svd(Xc, full_matrices=False)
    var = s ** 2 / (Xc ** 2).sum()
    return Vt.T, U * s, np.cumsum(var), mu


def recon_err(X, modes, coeffs, mu, k):
    Xr = mu + coeffs[:, :k] @ modes[:, :k].T
    abs_err = np.abs(X - Xr)
    mae = abs_err.mean()
    rmse = float(np.sqrt((abs_err ** 2).mean()))
    max_err = float(abs_err.max())
    # log-domain error on positive entries
    mask = (X > 0) & (Xr > 0)
    lerr = np.abs(np.log10(X[mask]) - np.log10(Xr[mask]))
    log_mae = float(lerr.mean()) if lerr.size else float('nan')
    return mae, rmse, max_err, log_mae


results = {'raw': {}, 'log10': {}}
K = [2, 3, 5, 8, 10, 15, 20, 30, 40]
for name, X in (('raw', F), ('log10', np.log10(F))):
    modes, coeffs, cumvar, mu = pod(X)
    results[name]['cumvar'] = {int(k): float(cumvar[min(k, len(cumvar)) - 1])
                               for k in K}
    results[name]['recon'] = {}
    print('--- %s POD ---' % name)
    for k in K:
        mae, rmse, mx, lmae = recon_err(X, modes, coeffs, mu, k)
        results[name]['recon'][int(k)] = {'MAE': mae, 'RMSE': rmse,
                                          'max_err': mx, 'log10_MAE': lmae}
        print('  k=%2d cumvar=%.4f recon MAE=%.4e RMSE=%.4e max=%.4e log10MAE=%.4f'
              % (k, cumvar[min(k, len(cumvar)) - 1], mae, rmse, mx, lmae))
    np.save(os.path.join(METR, 'step15_pod_modes_%s.npy' % name), modes)
    np.save(os.path.join(METR, 'step15_pod_coeffs_%s.npy' % name), coeffs)

# recommendation
for name in ('raw', 'log10'):
    r = results[name]
    k99 = next((k for k in K if r['cumvar'][k] >= 0.99), None)
    print('%s: k for >=99%% var = %s' % (name, k99))
with open(os.path.join(METR, 'step15_pod_exploration.json'), 'w') as f:
    json.dump({'snapshot_matrix': list(F.shape), 'ids': ids, 'results': results,
               'note': 'EXPLORATORY: production POD basis must be re-fit on TRAIN '
                       'snapshots only after formal split; TEST fields never used '
                       'in basis fitting'}, f, indent=1)
print('pod_exploration.json written')
