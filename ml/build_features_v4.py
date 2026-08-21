"""STEP 13.9: feature rebuild on the 318-row dataset (seed 42).

Same 16-feature set as STEP 13.7 'all' (base 12 + Pi_yield + Ro_over_w +
P_over_sy + sy_over_E) + regression labels + PEEQ nonzero flags.
Outputs: ml/features/v4/ (X_<split>.npy, y_<split>.npy, extras, names).
"""
import json
import os

import numpy as np
import pandas as pd

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
OUT = os.path.join(ROOT, 'ml', 'features', 'v4')

FEATURES = ['R_major', 'R_outer', 'wall_thickness', 'pressure', 'log1p_time',
            'T_hot', 'Delta_T', 'E_GPa', 'sigma_y_MPa', 'A_creep', 'n_creep',
            'model_type_C', 'Pi_yield', 'Ro_over_w', 'P_over_sy', 'sy_over_E']
TARGETS = ['max_displacement', 'max_von_mises', 'max_thermal_strain',
           'max_PEEQ', 'max_creep_strain']


def build(df):
    df = df.copy()
    df['T_hot'] = pd.to_numeric(df['T_uniform']).fillna(pd.to_numeric(df['T_inner']))
    df['log1p_time'] = np.log1p(pd.to_numeric(df['time']).fillna(0.0))
    df['Delta_T'] = pd.to_numeric(df['Delta_T']).fillna(0.0)
    for c in ['R_major', 'R_outer', 'wall_thickness', 'pressure', 'E_GPa']:
        df[c] = pd.to_numeric(df[c])
    df['sigma_y_MPa'] = pd.to_numeric(df['sigma_y_MPa']).fillna(0.0)
    df['A_creep'] = pd.to_numeric(df['A_creep']).fillna(0.0)
    df['n_creep'] = pd.to_numeric(df['n_creep']).fillna(0.0)
    df['model_type_C'] = (df['model_type'] == 'MODEL_C').astype(float)
    sy = df['sigma_y_MPa']; E_MPa = df['E_GPa'] * 1000.0
    P, Ro, w = df['pressure'], df['R_outer'], df['wall_thickness']
    df['Pi_yield'] = np.where(sy > 0, P * Ro / (w * sy), 0.0)
    df['Ro_over_w'] = Ro / w
    df['P_over_sy'] = np.where(sy > 0, P / sy, 0.0)
    df['sy_over_E'] = np.where(sy > 0, sy / E_MPa, 0.0)
    X = df[FEATURES].astype(float).values
    ys = {}
    for t in TARGETS:
        v = pd.to_numeric(df[t], errors='coerce')
        ys[t] = v.values
        ys[t + '_nonzero'] = (v.fillna(0.0) > 1e-12).astype(int).values
        if t in ('max_displacement', 'max_thermal_strain'):
            ys['log1p_' + t] = np.log1p(np.clip(v.fillna(0.0), 0, None)).values
    return X, ys, df['case_id'].tolist()


def main():
    os.makedirs(OUT, exist_ok=True)
    n = {}
    for s in ('train', 'validation', 'test'):
        df = pd.read_csv(os.path.join(AI, s + '.csv'))
        X, ys, ids = build(df)
        n[s] = len(df)
        np.save(os.path.join(OUT, 'X_%s.npy' % s), X)
        np.save(os.path.join(OUT, 'y_%s.npy' % s), np.column_stack([ys[t] for t in TARGETS]))
        with open(os.path.join(OUT, 'y_%s_extra.json' % s), 'w') as f:
            json.dump({k: [None if (isinstance(v, float) and v != v) else v
                           for v in vals.tolist()] for k, vals in ys.items()}, f)
        with open(os.path.join(OUT, 'case_ids_%s.json' % s), 'w') as f:
            json.dump(ids, f)
        print('%s: %d rows' % (s, len(df)))
    with open(os.path.join(OUT, 'feature_names.json'), 'w') as f:
        json.dump({'features': FEATURES, 'targets': TARGETS, 'seed': SEED,
                   'n': n}, f, indent=1)
    print('features/v4 written:', n)


if __name__ == '__main__':
    main()
