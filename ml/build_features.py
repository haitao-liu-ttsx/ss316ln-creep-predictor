"""STEP 13.5: feature pipeline (reproducible, seed 42).

Features (13): R_major, R_outer, wall_thickness, pressure, log1p(time),
T_hot (= T_uniform or T_inner), Delta_T, E_GPa, sigma_y_MPa (0-filled for
MODEL_C with has_sy indicator removed: has_sy == model_type, collinear),
A_creep (0-filled, has_creep indicator also collinear with model_type -> dropped),
n_creep (0-filled), model_type (MODEL_C=1).

Targets (raw + log1p where applicable): max_displacement, max_von_mises,
max_thermal_strain, max_PEEQ, max_creep_strain.
Zero-inflated targets (PEEQ/CEEQ) additionally get binary flags for 2-stage
exploratory modelling (y_*_nonzero).

Outputs: ml/features/{X_train,X_val,X_test}.npy + feature_names.json +
y_train.json etc. (values per target). No Abaqus data is modified.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI = os.path.join(ROOT, 'data', 'ai_ready_v3')
OUT = os.path.join(ROOT, 'ml', 'features')

FEATURES = ['R_major', 'R_outer', 'wall_thickness', 'pressure', 'log1p_time',
            'T_hot', 'Delta_T', 'E_GPa', 'sigma_y_MPa', 'A_creep', 'n_creep',
            'model_type_C']
TARGETS = ['max_displacement', 'max_von_mises', 'max_thermal_strain',
           'max_PEEQ', 'max_creep_strain']


def build(rows):
    df = pd.DataFrame(rows)
    # CSV missing values arrive as string 'nan' -> pandas NaN via read_csv;
    # use isna() (NOT != '') for structural-missing handling.
    df['T_hot'] = pd.to_numeric(df['T_uniform']).fillna(pd.to_numeric(df['T_inner']))
    df['T_outer_f'] = pd.to_numeric(df['T_outer']).fillna(df['T_hot'])
    df['Delta_T'] = pd.to_numeric(df['Delta_T']).fillna(0.0)
    df['log1p_time'] = np.log1p(pd.to_numeric(df['time']).fillna(0.0))
    for c in ['R_major', 'R_outer', 'wall_thickness', 'pressure', 'E_GPa']:
        df[c] = pd.to_numeric(df[c])
    df['sigma_y_MPa'] = pd.to_numeric(df['sigma_y_MPa']).fillna(0.0)   # MODEL_C -> 0
    df['A_creep'] = pd.to_numeric(df['A_creep']).fillna(0.0)           # MODEL_B -> 0
    df['n_creep'] = pd.to_numeric(df['n_creep']).fillna(0.0)
    df['model_type_C'] = (df['model_type'] == 'MODEL_C').astype(float)
    X = df[FEATURES].astype(float).values
    ys = {}
    for t in TARGETS:
        v = pd.to_numeric(df[t], errors='coerce')
        ys[t] = v.values
        ys[t + '_nonzero'] = (v.fillna(0.0) > 1e-12).astype(int).values
        if t in ('max_displacement', 'max_thermal_strain'):
            ys['log1p_' + t] = np.log1p(np.clip(v.fillna(0.0), 0, None)).values
        if t == 'max_creep_strain':
            nz = v.fillna(0.0) > 1e-12
            ylog = np.full(len(v), np.nan)
            ylog[nz] = np.log(v[nz].values)
            ys['log_' + t] = ylog  # only nonzero entries; NaN elsewhere
    return X, ys


def main():
    os.makedirs(OUT, exist_ok=True)
    splits = {}
    for s in ('train', 'validation', 'test'):
        rows = pd.read_csv(os.path.join(AI, s + '.csv'))
        X, ys = build(rows)
        splits[s] = (X, ys, rows['case_id'].tolist())
        np.save(os.path.join(OUT, 'X_%s.npy' % s), X)
        np.save(os.path.join(OUT, 'y_%s.npy' % s),
                np.column_stack([ys[t] for t in TARGETS]))
        with open(os.path.join(OUT, 'y_%s_extra.json' % s), 'w') as f:
            json.dump({k: [None if (isinstance(v, float) and v != v) else v
                           for v in vals.tolist()] for k, vals in ys.items()}, f)
        with open(os.path.join(OUT, 'case_ids_%s.json' % s), 'w') as f:
            json.dump(rows['case_id'].tolist(), f)
    with open(os.path.join(OUT, 'feature_names.json'), 'w') as f:
        json.dump({'features': FEATURES, 'targets': TARGETS,
                   'seed': SEED, 'n_train': len(splits['train'][0]),
                   'n_validation': len(splits['validation'][0]),
                   'n_test': len(splits['test'][0])}, f, indent=1)
    print('features written to', OUT)
    for s, (X, ys, _) in splits.items():
        print('%s: X shape %s' % (s, X.shape))
    # quick sanity: zero fractions of targets in each split
    for t in TARGETS:
        zf = [round(100.0 * (1 - float(np.nanmean(ys[t + '_nonzero']))), 1)
              for _, ys, _ in splits.values()]
        print('%-22s zero%% train/val/test = %s' % (t, zf))


if __name__ == '__main__':
    main()
