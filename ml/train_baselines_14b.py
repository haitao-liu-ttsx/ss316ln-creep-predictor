"""STEP 14-B.2/3: feature-target audit JSON + physics/ML baselines with 5-fold CV
and validation-only independent evaluation. TEST target NEVER read here.
"""
import csv
import json
import math
import os

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, 'ml', 'features', 'step14b')
METR = os.path.join(ROOT, 'ml', 'metrics')
FEATS = ["T_hot", "pressure", "log1p_time", "Rm", "Ro", "w", "E", "A_creep", "n_creep"]
np.random.seed(SEED)

Xtr = np.load(os.path.join(F, 'X_train.npy'))
ytr = np.load(os.path.join(F, 'y_train.npy'))
Xva = np.load(os.path.join(F, 'X_validation.npy'))
yva = np.load(os.path.join(F, 'y_validation.npy'))


def met(y, yp):
    return (mean_absolute_error(y, yp), float(np.sqrt(mean_squared_error(y, yp))),
            r2_score(y, yp))


def cv_report(model, X, y):
    kf = KFold(n_splits=5, shuffle=True, random_state=SEED)
    yp = cross_val_predict(model, X, y, cv=kf)
    mae, rmse, r2 = met(y, yp)
    return {'MAE': mae, 'RMSE': rmse, 'R2': r2, 'max_err': float(np.max(np.abs(y - yp)))}, yp


# ---------------- physics baselines ----------------
def physics_baseline(fixed_n=False):
    """log10(CEEQ) - n*log10(P) - log10(t) = a + b1*T (+ b2*T^2) via OLS on residual."""
    T = Xtr[:, 0]; P = Xtr[:, 1]; t = np.expm1(Xtr[:, 2])
    results = []
    for deg, tag in ((1, 'lin'), (2, 'quad')):
        if fixed_n:
            nT = np.array([9.51, 9.04, 7.57])[np.searchsorted([550, 600, 650], T)]
        else:
            nT = 0.0  # fitted below
        resid = ytr - nT * np.log10(P) - np.log10(t)
        if fixed_n:
            A = np.column_stack([np.ones_like(T), T] + ([T ** 2] if deg == 2 else []))
            coef, *_ = np.linalg.lstsq(A, resid, rcond=None)
        else:
            A = np.column_stack([np.ones_like(T), T] + ([T ** 2] if deg == 2 else []) +
                                [np.log10(P)])
            coef, *_ = np.linalg.lstsq(A, ytr - np.log10(t), rcond=None)
            nT = coef[-1]
            coef = coef[:-1]
        # predictions
        def predict(Xx):
            Tt = Xx[:, 0]; Pt = Xx[:, 1]; tt = np.expm1(Xx[:, 2])
            n_use = (np.array([9.51, 9.04, 7.57])[np.searchsorted([550, 600, 650], Tt)]
                     if fixed_n else nT * np.ones_like(Tt))
            A_ = np.column_stack([np.ones_like(Tt), Tt] + ([Tt ** 2] if deg == 2 else []))
            return A_ @ coef + n_use * np.log10(Pt) + np.log10(tt)
        yp_tr = predict(Xtr); yp_va = predict(Xva)
        results.append({'tag': 'phys%s_%s' % ('B' if fixed_n else 'A', tag),
                        'fitted_n': None if fixed_n else float(nT),
                        'coef': coef.tolist()})
        print('phys%s_%s: CV-free (analytic) train MAE=%.3f RMSE=%.3f R2=%.3f | '
              'val MAE=%.3f RMSE=%.3f R2=%.3f%s'
              % ('B' if fixed_n else 'A', tag, *met(ytr, yp_tr)[:2],
                 met(ytr, yp_tr)[2], *met(yva, yp_va)[:2], met(yva, yp_va)[2],
                 '' if fixed_n else ' (fitted n=%.2f)' % nT))
    return results


print('=== Physics baselines ===')
phys = physics_baseline(fixed_n=False)
phys_fixed = physics_baseline(fixed_n=True)

# ---------------- ML baselines ----------------
models = {
    'linear': Pipeline([('scale', StandardScaler()), ('m', LinearRegression())]),
    'poly2': Pipeline([('poly', PolynomialFeatures(2)), ('scale', StandardScaler()),
                       ('m', LinearRegression())]),
    'poly3': Pipeline([('poly', PolynomialFeatures(3)), ('scale', StandardScaler()),
                       ('m', LinearRegression())]),
    'rf': RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=-1),
    'histgb': HistGradientBoostingRegressor(random_state=SEED),
    'xgb': xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8,
                            random_state=SEED, n_jobs=-1, verbosity=0),
}
print('\n=== ML baselines: 5-fold CV (train 37) + validation ===')
cv_rows = []
comp_rows = []
for name, m in models.items():
    cv, yp_cv = cv_report(m, Xtr, ytr)
    yp_va = m.fit(Xtr, ytr).predict(Xva)
    vmae, vrmse, vr2 = met(yva, yp_va)
    comp_rows.append({'model': name, 'cv_MAE': round(cv['MAE'], 4),
                      'cv_RMSE': round(cv['RMSE'], 4), 'cv_R2': round(cv['R2'], 4),
                      'cv_max_err': round(cv['max_err'], 4),
                      'val_MAE': round(vmae, 4), 'val_RMSE': round(vrmse, 4),
                      'val_R2': round(vr2, 4),
                      'val_max_err': round(float(np.max(np.abs(yva - yp_va))), 4),
                      'note': ''})
    print('%-7s CV  MAE=%.3f RMSE=%.3f R2=%.3f max=%.3f | val MAE=%.3f RMSE=%.3f R2=%.3f max=%.3f'
          % (name, cv['MAE'], cv['RMSE'], cv['R2'], cv['max_err'], vmae, vrmse, vr2,
             float(np.max(np.abs(yva - yp_va)))))
for p in phys + phys_fixed:
    comp_rows.append({'model': p['tag'], 'cv_MAE': '', 'cv_RMSE': '', 'cv_R2': '',
                      'cv_max_err': '', 'val_MAE': '', 'val_RMSE': '', 'val_R2': '',
                      'val_max_err': '',
                      'note': 'analytic physics baseline, fitted_n=%s' % p['fitted_n']})
with open(os.path.join(METR, 'step14b_cv_results.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['model', 'MAE', 'RMSE', 'R2', 'max_err'])
    w.writeheader()
    for name, m in models.items():
        cv, _ = cv_report(m, Xtr, ytr)
        w.writerow({'model': name, 'MAE': round(cv['MAE'], 4), 'RMSE': round(cv['RMSE'], 4),
                    'R2': round(cv['R2'], 4), 'max_err': round(cv['max_err'], 4)})
with open(os.path.join(METR, 'step14b_baseline_comparison.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(comp_rows[0].keys()))
    w.writeheader()
    for r in comp_rows:
        w.writerow(r)

# ---------------- physical trend checks (validation, per model) ----------------
print('\n=== Physical trend checks (validation predictions) ===')
trend_rows = []
for name, m in models.items():
    m.fit(Xtr, ytr)
    yp = m.predict(Xva)
    # t trend: 750 vs 500 same T,P -> log10 ratio ~ log10(1.5)=0.176
    viol = []
    for T in (550, 600, 650):
        for P in (5, 10, 20):
            idx500 = [i for i in range(len(Xva)) if Xva[i, 0] == T and Xva[i, 1] == P
                      and abs(np.expm1(Xva[i, 2]) - 500) < 1]
            idx750 = [i for i in range(len(Xva)) if Xva[i, 0] == T and Xva[i, 1] == P
                      and abs(np.expm1(Xva[i, 2]) - 750) < 1]
            if idx500 and idx750:
                r = yp[idx750[0]] - yp[idx500[0]]
                if r < 0:
                    viol.append('t_down T%d P%d' % (T, P))
    # P trend: 5->10->20 monotonic per T (fixed t)
    for T in (550, 600, 650):
        vals = {}
        for i in range(len(Xva)):
            if Xva[i, 0] == T and abs(np.expm1(Xva[i, 2]) - 500) < 1:
                vals[int(Xva[i, 1])] = yp[i]
        ps = sorted(vals)
        if any(vals[ps[k + 1]] <= vals[ps[k]] for k in range(len(ps) - 1)):
            viol.append('P_nonmono T%d' % T)
    trend_rows.append({'model': name, 'violations': viol or 'NONE'})
    print('%-7s %s' % (name, viol or 'NONE (t: 750>500, P monotonic)'))
with open(os.path.join(METR, 'step14b_trend_check.json'), 'w') as f:
    json.dump(trend_rows, f, indent=1)

# ---------------- B.2 audit JSON ----------------
audit = {
    'target_name': 'log10(CEEQ)',
    'target_formula': 'log10(final-frame element-field max CEEQ)',
    'target_extraction_definition': 'final frame, element field, max, nonzero domain',
    'epsilon_used': False,
    'train_positive': '37/37', 'validation_positive': '18/18', 'test_positive': '9/9',
    'features': FEATS,
    'feature_order': FEATS,
    'time_transform': 'log1p(time)',
    'constant_features_for_MODEL_C': {
        'Delta_T': 0, 'sigma_y_MPa': 0, 'model_type_C': 1,
        'Pi_yield': 0, 'P_over_sy': 0, 'sy_over_E': 0},
    'leakage_audit': {
        'A_creep': 'material input (Norton A from MAT-05 table), pre-solve, NOT target-derived',
        'n_creep': 'material input (Norton n), pre-solve, NOT target-derived',
        'E': 'material input (RCCMR/EXP table), pre-solve, NOT target-derived',
        'all_features_pre_solve': True,
        'no_odb_output_features': True},
    'scaler_policy': 'all preprocessing inside sklearn Pipeline; scaler fit on TRAIN fold only '
                     '(KFold inside cross_val_predict); never fit on TRAIN+VAL or +TEST',
    'test_target_read': False,
}
with open(os.path.join(METR, 'step14b_feature_target_audit.json'), 'w') as f:
    json.dump(audit, f, indent=1)
print('\nB.2 audit -> ml/metrics/step14b_feature_target_audit.json')
print('B.3 done: cv + validation baselines, trend checks')
