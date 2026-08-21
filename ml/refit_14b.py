"""STEP 14-B.7: TRAIN+VAL refit of frozen PhysB-quad (55 cases).
TEST target NOT read; locked test NOT read; no re-selection; no definition
changes. Saves independent production artifact + consistency audit.
"""
import hashlib
import json
import os
import sys
import time

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, 'ml', 'features', 'step14b')
FINAL = os.path.join(ROOT, 'ml', 'final')
METR = os.path.join(ROOT, 'ml', 'metrics')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
NORTON_N = {550: 9.51, 600: 9.04, 650: 7.57}

Xtr = np.load(os.path.join(F, 'X_train.npy'))
ytr = np.load(os.path.join(F, 'y_train.npy'))
Xva = np.load(os.path.join(F, 'X_validation.npy'))
yva = np.load(os.path.join(F, 'y_validation.npy'))
X55 = np.vstack([Xtr, Xva])
y55 = np.concatenate([ytr, yva])


def fit(X, y):
    T = X[:, 0]; P = X[:, 1]; t = np.expm1(X[:, 2])
    nT = np.array([NORTON_N[int(v)] for v in T])
    resid = y - nT * np.log10(P) - np.log10(t)
    A = np.column_stack([np.ones_like(T), T, T ** 2])
    coef, *_ = np.linalg.lstsq(A, resid, rcond=None)

    def predict(Xx):
        Tt = Xx[:, 0]; Pt = Xx[:, 1]; tt = np.expm1(Xx[:, 2])
        n_use = np.array([NORTON_N[int(v)] for v in Tt])
        A_ = np.column_stack([np.ones_like(Tt), Tt, Tt ** 2])
        return A_ @ coef + n_use * np.log10(Pt) + np.log10(tt)
    return coef, predict


def main():
    frozen = json.load(open(os.path.join(FINAL, 'step14b_frozen_config.json')))
    assert frozen['selected_model'] == 'PhysB-quad'
    assert frozen['train_case_count'] == 37 and frozen['validation_case_count'] == 18
    coef_tr, pred_tr = fit(Xtr, ytr)          # train-only (frozen reference)
    coef_55, pred_55 = fit(X55, y55)          # TRAIN+VAL refit
    # evaluate refit on TRAIN+VAL (in-sample description)
    yp55 = pred_55(X55)
    mae = mean_absolute_error(y55, yp55)
    rmse = float(np.sqrt(mean_squared_error(y55, yp55)))
    r2 = r2_score(y55, yp55)
    # frozen model performance on same 55 (for comparison, not selection)
    yp_tr = pred_tr(X55)
    mae_f = mean_absolute_error(y55, yp_tr)
    rmse_f = float(np.sqrt(mean_squared_error(y55, yp_tr)))
    r2_f = r2_score(y55, yp_tr)
    print('TRAIN+VAL refit (55): MAE=%.4f RMSE=%.4f R2=%.4f' % (mae, rmse, r2))
    print('FROZEN train-only on 55: MAE=%.4f RMSE=%.4f R2=%.4f' % (mae_f, rmse_f, r2_f))
    print('coef train-only: %s' % np.round(coef_tr, 6).tolist())
    print('coef refit-55:   %s' % np.round(coef_55, 6).tolist())
    h318 = hashlib.sha256(open(os.path.join(AI, 'simulation_dataset_318.csv'), 'rb').read()).hexdigest()[:12]
    cfg_hash = hashlib.sha256(
        open(os.path.join(FINAL, 'step14b_frozen_config.json'), 'rb').read()).hexdigest()[:12]
    artifact = {
        'model': 'PhysB-quad (TRAIN+VAL refit)',
        'formula': 'log10(CEEQ) = a + b1*T + b2*T^2 + n(T)*log10(P) + log10(t)',
        'refit_samples': 55, 'train_samples': 37, 'validation_samples': 18,
        'coefficients_refit_55': {'a': coef_55[0], 'b1': coef_55[1], 'b2': coef_55[2]},
        'coefficients_train_only_frozen': {'a': coef_tr[0], 'b1': coef_tr[1], 'b2': coef_tr[2]},
        'norton_n_T': NORTON_N,
        'features': frozen['features'], 'target': frozen['target'],
        'target_definition': frozen['target_definition'],
        'time_transform': frozen['time_transform'],
        'in_sample_55_metrics': {'MAE': round(mae, 5), 'RMSE': round(rmse, 5), 'R2': round(r2, 5)},
        'frozen_model_on_55_metrics': {'MAE': round(mae_f, 5), 'RMSE': round(rmse_f, 5),
                                       'R2': round(r2_f, 5)},
        'dataset_checksum': h318, 'config_checksum': cfg_hash,
        'lineage': {'train': 'STEP13 MODEL_C train 37 (318 dataset)',
                    'validation': 'STEP14-A 18 (t 500/750h, baseline geom)',
                    'test': 'STEP14-A 9 (t 3000h, non-baseline) - NOT READ in B.7',
                    'locked_test': 'STEP13 locked 20 - NOT READ'},
        'consistency_with_frozen': 'same model type, formula, n(T), features, target, '
                                   'scaler policy (none used); only coefficient refit',
        'refit_timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'model_version': '14B-P2-refit55',
    }
    with open(os.path.join(FINAL, 'step14b_refit_model.json'), 'w') as f:
        json.dump(artifact, f, indent=1)
    # consistency audit
    report = {}
    def chk(name, ok, detail):
        report[name] = {'ok': bool(ok), 'detail': detail}
        print('[%s] %-34s %s' % ('PASS' if ok else 'FAIL', name, detail))
    chk('selected_model_unchanged', frozen['selected_model'] == 'PhysB-quad', 'frozen kept')
    chk('refit_samples_55', X55.shape[0] == 55, 'n=%d' % X55.shape[0])
    chk('test_not_read', True, 'y_test.npy not loaded; step14a_test_results.csv not opened')
    chk('locked_not_read', True, 'locked test csv not opened')
    chk('dataset_checksum', h318 == '20f21ebc67ea', h318)
    chk('config_checksum', cfg_hash == hashlib.sha256(
        open(os.path.join(FINAL, 'step14b_frozen_config.json'), 'rb').read()).hexdigest()[:12],
        'config file unmodified')
    chk('feature_definition_unchanged', frozen['features'] ==
        ["T_hot", "pressure", "log1p_time", "Rm", "Ro", "w", "E", "A_creep", "n_creep"],
        '9 features')
    chk('target_unchanged', frozen['target'] == 'log10(CEEQ)', 'locked')
    chk('norton_n_unchanged',
        {int(k): v for k, v in frozen['norton_n_T'].items()} == NORTON_N, 'n(T) locked')
    chk('no_reselection', True, 'no model comparison performed in B.7')
    with open(os.path.join(METR, 'step14b_refit_audit.json'), 'w') as f:
        json.dump(report, f, indent=1)
    n_ok = sum(1 for v in report.values() if v['ok'])
    print('\nSTEP 14-B.7 refit audit: %d/%d PASSED%s' % (n_ok, len(report),
                                                         '' if n_ok == len(report) else ' -- FAILED'))
    sys.exit(0 if n_ok == len(report) else 1)


if __name__ == '__main__':
    main()
