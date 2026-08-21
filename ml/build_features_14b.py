"""STEP 14-B.2/3: build CEEQ 9-feature datasets (TRAIN/VAL/TEST-X).

Locked feature order:
  ["T_hot", "pressure", "log1p_time", "Rm", "Ro", "w", "E", "A_creep", "n_creep"]
time transform = log1p(time) (STEP13-identical; NOT log10).
TRAIN: from STEP13 MODEL_C train rows (features/v4 effective subset).
VAL/TEST: from STEP14-A results (T/P/t/Rm/Ro/w + material table lookup).
TEST target y is NOT loaded here (quarantine: test y only used at final eval).
"""
import csv
import json
import math
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
F = os.path.join(ROOT, 'ml', 'features', 'v4')
METR = os.path.join(ROOT, 'ml', 'metrics')
OUT = os.path.join(ROOT, 'ml', 'features', 'step14b')

FEATURES = ["T_hot", "pressure", "log1p_time", "Rm", "Ro", "w", "E", "A_creep", "n_creep"]
E_T = {550: 155020.0, 600: 150780.0, 650: 171000.0}   # RCCMR@550/600, EXP@650 (STEP13 MODEL_C)
CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}


def build_train():
    rows = [r for r in csv.DictReader(open(os.path.join(AI, 'train.csv')))
            if r['model_type'] == 'MODEL_C']
    X, y, ids = [], [], []
    for r in rows:
        T = int(float(r['T_uniform']))
        X.append([T, float(r['pressure']), math.log1p(float(r['time'])),
                  float(r['R_major']), float(r['R_outer']), float(r['wall_thickness']),
                  E_T[T], CREEP[T][0], CREEP[T][1]])
        y.append(math.log10(float(r['max_creep_strain'])))
        ids.append(r['case_id'])
    return np.array(X), np.array(y), ids


def build_valtest(layer):
    rows = list(csv.DictReader(open(os.path.join(METR, 'step14a_%s_results.csv' % layer))))
    X, ids = [], []
    for r in rows:
        T = int(float(r['T']))
        X.append([T, float(r['P']), math.log1p(float(r['t_h'])),
                  float(r['Rm']), float(r['Ro']), float(r['w']),
                  E_T[T], CREEP[T][0], CREEP[T][1]])
        ids.append(r['case_id'])
    return np.array(X), ids


def main():
    os.makedirs(OUT, exist_ok=True)
    Xtr, ytr, id_tr = build_train()
    Xva, id_va = build_valtest('validation')
    Xte, id_te = build_valtest('test')
    # validation y from results (allowed for evaluation, not selection-tuning here)
    yva = np.array([math.log10(float(r['CEEQ_max']))
                    for r in csv.DictReader(open(os.path.join(METR, 'step14a_validation_results.csv')))])
    np.save(os.path.join(OUT, 'X_train.npy'), Xtr)
    np.save(os.path.join(OUT, 'y_train.npy'), ytr)
    np.save(os.path.join(OUT, 'X_validation.npy'), Xva)
    np.save(os.path.join(OUT, 'y_validation.npy'), yva)
    np.save(os.path.join(OUT, 'X_test.npy'), Xte)   # no y_test saved (quarantine)
    with open(os.path.join(OUT, 'case_ids.json'), 'w') as f:
        json.dump({'train': id_tr, 'validation': id_va, 'test': id_te}, f)
    with open(os.path.join(OUT, 'feature_names.json'), 'w') as f:
        json.dump({'features': FEATURES,
                   'time_transform': 'log1p(time)',
                   'target': 'log10(CEEQ) nonzero domain, no epsilon',
                   'test_y_loaded': False}, f, indent=1)
    print('step14b features: train %s, validation %s, test-X %s (test y NOT loaded)'
          % (Xtr.shape, Xva.shape, Xte.shape))


if __name__ == '__main__':
    main()
