"""STEP 13.7: feature sets with physics-informed candidates (seed 42).

Base 12 features (as STEP 13.5) + candidates:
  Pi_yield    = P*R_outer/(wall_thickness*sigma_y)   (first priority)
  Ro_over_w   = R_outer/wall_thickness
  P_over_sy   = P/sigma_y
  sy_over_E   = sigma_y/E  (E in MPa)
sigma_y missing (MODEL_C creep cases): physics features that require sigma_y are
0-filled (MODEL_C has no plasticity path); model_type_C already encodes the
regime identity. No test-side information used; documented in feature audit.

Feature-set variants: base(12), base+Pi, base+Pi+Ro_w, all(16).
Outputs: ml/features/step13_7/X_<set>_<split>.npy + feature_names.json.
"""
import json
import os

import numpy as np
import pandas as pd

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI = os.path.join(ROOT, 'data', 'ai_ready_v3')
OUT = os.path.join(ROOT, 'ml', 'features', 'step13_7')

BASE = ['R_major', 'R_outer', 'wall_thickness', 'pressure', 'log1p_time',
        'T_hot', 'Delta_T', 'E_GPa', 'sigma_y_MPa', 'A_creep', 'n_creep',
        'model_type_C']
PHYS = ['Pi_yield', 'Ro_over_w', 'P_over_sy', 'sy_over_E']


def build_rows():
    frames = {}
    for s in ('train', 'validation', 'test'):
        df = pd.read_csv(os.path.join(AI, s + '.csv'))
        df['T_hot'] = pd.to_numeric(df['T_uniform']).fillna(pd.to_numeric(df['T_inner']))
        df['log1p_time'] = np.log1p(pd.to_numeric(df['time']).fillna(0.0))
        df['Delta_T'] = pd.to_numeric(df['Delta_T']).fillna(0.0)
        for c in ['R_major', 'R_outer', 'wall_thickness', 'pressure', 'E_GPa']:
            df[c] = pd.to_numeric(df[c])
        df['sigma_y_MPa'] = pd.to_numeric(df['sigma_y_MPa']).fillna(0.0)
        df['A_creep'] = pd.to_numeric(df['A_creep']).fillna(0.0)
        df['n_creep'] = pd.to_numeric(df['n_creep']).fillna(0.0)
        df['model_type_C'] = (df['model_type'] == 'MODEL_C').astype(float)
        sy = df['sigma_y_MPa']
        E_MPa = df['E_GPa'] * 1000.0
        P = df['pressure']; Ro = df['R_outer']; w = df['wall_thickness']
        # physics features: 0 where sigma_y missing (MODEL_C)
        df['Pi_yield'] = np.where(sy > 0, P * Ro / (w * sy), 0.0)
        df['Ro_over_w'] = Ro / w
        df['P_over_sy'] = np.where(sy > 0, P / sy, 0.0)
        df['sy_over_E'] = np.where(sy > 0, sy / E_MPa, 0.0)
        frames[s] = df
    return frames


def main():
    os.makedirs(OUT, exist_ok=True)
    frames = build_rows()
    sets = {
        'base': BASE,
        'base_pi': BASE + ['Pi_yield'],
        'base_pi_row': BASE + ['Pi_yield', 'Ro_over_w'],
        'all': BASE + PHYS,
    }
    for sname, cols in sets.items():
        for s, df in frames.items():
            X = df[cols].astype(float).values
            np.save(os.path.join(OUT, 'X_%s_%s.npy' % (sname, s)), X)
        print('%s: %s -> shapes %s' % (sname, cols,
                                       [frames[s].shape[0] for s in ('train', 'validation', 'test')]))
    with open(os.path.join(OUT, 'feature_names.json'), 'w') as f:
        json.dump({'seed': SEED, 'sets': sets,
                   'physics_missing_policy': 'sigma_y-missing (MODEL_C) physics features 0-filled; '
                                             'model_type_C encodes regime; no test info used'}, f, indent=1)
    # audit: how many train rows have Pi_yield in key regions
    tr = frames['train']
    n_p30 = int((tr['pressure'] >= 30).sum())
    n_w2 = int((tr['wall_thickness'] == 2).sum())
    pi = tr['Pi_yield']
    n_pi_08_12 = int(((pi >= 0.8) & (pi <= 1.2)).sum())
    n_pi_gt1 = int((pi > 1.0).sum())
    print('data gap (train): P>=30: %d, wall=2: %d, Pi_yield in [0.8,1.2]: %d, Pi_yield>1: %d'
          % (n_p30, n_w2, n_pi_08_12, n_pi_gt1))


if __name__ == '__main__':
    main()
