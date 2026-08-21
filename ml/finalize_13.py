"""STEP 13 FINAL CLOSEOUT: lock final models, build ml/final/ + ml/models/step13_final/,
recompute final metrics table, checksums, and 3 synthesis figures.

FINAL VM MODEL (locked): XGBoost, 16 features, params = STEP 13.9/13.10 base
(combo5: lr=0.1, depth=4, n=300, subsample=0.8, colsample=0.8), seed=42.
Displacement = 3-stage definition (stage1 RF classifier / stage2 elastic linear /
stage3 EPP flag + exploratory only). Historical STEP13.x artifacts are NOT
deleted or modified.
"""
import csv
import hashlib
import json
import os
import shutil
import sys

import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, 'ml', 'features', 'v4')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
FINAL = os.path.join(ROOT, 'ml', 'final')
LOCKED = os.path.join(ROOT, 'ml', 'models', 'step13_final')
FIG = os.path.join(ROOT, 'ml', 'figures', 'step13_final')

plt.rcParams.update({'font.size': 9, 'figure.dpi': 130})


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def met(y, yp):
    return (mean_absolute_error(y, yp), float(np.sqrt(mean_squared_error(y, yp))),
            r2_score(y, yp))


def main():
    os.makedirs(FINAL, exist_ok=True)
    os.makedirs(LOCKED, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)
    X = {s: np.load(os.path.join(F, 'X_%s.npy' % s)) for s in ('train', 'validation', 'test')}
    y = {s: np.load(os.path.join(F, 'y_%s.npy' % s)) for s in ('train', 'validation', 'test')}
    extra = {s: json.load(open(os.path.join(F, 'y_%s_extra.json' % s))) for s in ('train', 'validation', 'test')}
    ids = {s: json.load(open(os.path.join(F, 'case_ids_%s.json' % s))) for s in ('train', 'validation', 'test')}
    meta = {s: {r['case_id']: r for r in csv.DictReader(open(os.path.join(AI, s + '.csv')))}
            for s in ('train', 'validation', 'test')}
    feats = json.load(open(os.path.join(F, 'feature_names.json')))['features']

    # ---------------- lock models ----------------
    vm_params = dict(n_estimators=300, max_depth=4, learning_rate=0.1, subsample=0.8,
                     colsample_bytree=0.8, random_state=SEED, n_jobs=-1, verbosity=0)
    m_vm = xgb.XGBRegressor(**vm_params)
    m_vm.fit(X['train'], y['train'][:, 1])
    s1 = RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1,
                                class_weight='balanced')
    s1.fit(X['train'], np.array(extra['train']['max_PEEQ_nonzero'], int))
    el_tr = np.array(extra['train']['max_PEEQ_nonzero'], int) == 0
    s2 = LinearRegression()
    s2.fit(X['train'][el_tr], y['train'][:, 0][el_tr])
    for name, m in (('final_vm_model', m_vm), ('final_regime_classifier', s1),
                    ('final_elastic_displacement_model', s2)):
        joblib.dump(m, os.path.join(FINAL, name + '.joblib'))
        joblib.dump(m, os.path.join(LOCKED, name + '.joblib'))
    # schema + config + metadata
    with open(os.path.join(FINAL, 'feature_schema.json'), 'w') as f:
        json.dump({'features': feats, 'n_features': len(feats),
                   'feature_order': feats}, f, indent=1)
    with open(os.path.join(FINAL, 'model_config.json'), 'w') as f:
        json.dump({'final_vm_model': {'algorithm': 'XGBoost', 'params': vm_params,
                                      'selection': 'validation-only (STEP 13.9/13.10 base, '
                                                   'val R2=0.9385)',
                                      'test_one_shot_R2': 0.9304},
                   'stage1': {'algorithm': 'RandomForest', 'n_estimators': 300,
                              'class_weight': 'balanced',
                              'performance': {'acc': 0.986, 'plastic_recall': 0.833, 'F1': 0.909}},
                   'stage2': {'algorithm': 'LinearRegression',
                              'note': 'elastic-domain (PEEQ=0) displacement'},
                   'stage3': {'status': 'exploratory_only',
                              'note': 'EPP post-yield magnitude NOT production'},
                   'seed': SEED}, f, indent=1)
    metadata = {'dataset': 'data/ai_ready_v4/simulation_dataset_318.csv',
                'n_rows': 318, 'n_valid': 242,
                'splits': {s: len(ids[s]) for s in ('train', 'validation', 'test')},
                'features': feats,
                'vm_model_params': vm_params,
                'train_script': 'ml/train_139.py + ml/train_1310.py',
                'python': sys.version.split()[0],
                'packages': {'xgboost': xgb.__version__, 'sklearn': '1.7.2',
                             'numpy': np.__version__},
                'history': 'STEP 13.6 (300/12f) -> 13.7 (300/16f) -> 13.8A (+18 Abaqus) '
                           '-> 13.9 (318/16f) -> 13.10 (validation)'}
    with open(os.path.join(FINAL, 'training_metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=1)
    shutil.copy(os.path.join(FINAL, 'feature_schema.json'), LOCKED)
    shutil.copy(os.path.join(FINAL, 'model_config.json'), LOCKED)
    shutil.copy(os.path.join(FINAL, 'training_metadata.json'), LOCKED)

    # ---------------- final metrics ----------------
    rows = []
    for s in ('train', 'validation', 'test'):
        a, r, r2v = met(y[s][:, 1], m_vm.predict(X[s]))
        rows.append({'target': 'max_von_mises', 'split': s, 'MAE': round(a, 3),
                     'RMSE': round(r, 3), 'R2': round(r2v, 4)})
    for bname, sel in (('P>=30', lambda m0: float(m0['pressure']) >= 30),
                       ('Rm150', lambda m0: float(m0['R_major']) == 150),
                       ('T750', lambda m0: float(m0['T_uniform'] or m0['T_inner'] or 0) == 750),
                       ('P25', lambda m0: float(m0['pressure']) == 25),
                       ('MODEL_B', lambda m0: m0['model_type'] == 'MODEL_B'),
                       ('MODEL_C', lambda m0: m0['model_type'] == 'MODEL_C')):
        idx = [i for i, c in enumerate(ids['test']) if sel(meta['test'][c])]
        a, r, r2b = met(y['test'][:, 1][idx], m_vm.predict(X['test'][idx]))
        rows.append({'target': 'vm_' + bname, 'split': 'test', 'n': len(idx),
                     'MAE': round(a, 3), 'RMSE': round(r, 3), 'R2': round(r2b, 4)})
    with open(os.path.join(FINAL, 'final_metrics.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['target', 'split', 'n', 'MAE', 'RMSE', 'R2'])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print('final metrics:')
    for r in rows:
        print('  %-12s %-10s n=%s MAE=%s RMSE=%s R2=%s' %
              (r['target'], r['split'], r.get('n', ''), r['MAE'], r['RMSE'], r['R2']))

    # ---------------- checksums ----------------
    targets = [os.path.join(AI, 'simulation_dataset_318.csv'),
               os.path.join(F, 'X_train.npy'), os.path.join(F, 'feature_names.json'),
               os.path.join(FINAL, 'final_vm_model.joblib'),
               os.path.join(ROOT, 'ml', 'features', 'v4', 'case_ids_train.json'),
               os.path.join(ROOT, 'ml', 'features', 'v4', 'case_ids_validation.json'),
               os.path.join(ROOT, 'ml', 'features', 'v4', 'case_ids_test.json')]
    checks = {os.path.basename(p): sha(p) for p in targets}
    with open(os.path.join(FINAL, 'checksums.json'), 'w') as f:
        json.dump(checks, f, indent=1)
    print('checksums:', {k: v[:12] for k, v in checks.items()})

    # ---------------- 3 synthesis figures ----------------
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
    axes[0].bar(['baseline\n(300,12f)', 'physics feat\n(300,16f)', 'transition data\n(318,16f)'],
                [-0.267, 0.005, 0.4553], color=['C3', 'C1', 'C0'])
    axes[0].axhline(0, color='k', lw=0.6)
    axes[0].set_title('P>=30 von Mises R2 (test)')
    axes[0].set_ylim(-0.5, 0.7)
    for i, v in enumerate((-0.267, 0.005, 0.4553)):
        axes[0].text(i, v + 0.02, '%.3f' % v, ha='center', fontsize=8)
    axes[1].bar(['A 300+12f', 'B 300+16f', 'C 318+12f', 'D 318+16f'],
                [0.856, 0.864, 0.8674, 0.9304], color=['C4', 'C4', 'C2', 'C0'])
    axes[1].set_title('overall test R2 (von Mises)')
    axes[1].set_ylim(0.75, 1.0)
    for i, v in enumerate((0.856, 0.864, 0.8674, 0.9304)):
        axes[1].text(i, v + 0.005, '%.3f' % v, ha='center', fontsize=8)
    allrows = list(csv.DictReader(open(os.path.join(AI, 'simulation_dataset_318.csv'))))
    pis, peeqs = [], []
    for r in allrows:
        if r['model_type'] != 'MODEL_B' or r['T_uniform'] in ('', 'nan'):
            continue
        sy = float(r['sigma_y_MPa']) if r['sigma_y_MPa'] not in ('', 'nan') else None
        if sy is None:
            continue
        pis.append(float(r['pressure']) * float(r['R_outer']) /
                   (float(r['wall_thickness']) * sy))
        peeqs.append(float(r['max_PEEQ']))
    axes[2].scatter(pis, peeqs, s=8, alpha=0.6, c='C1')
    axes[2].axvline(1.0, color='r', ls='--', lw=0.8, label='Pi=1')
    axes[2].set_yscale('log')
    axes[2].set_xlabel('Pi_yield'); axes[2].set_ylabel('max_PEEQ')
    axes[2].set_title('Pi_yield vs PEEQ (318, elastic/transition/plastic)')
    axes[2].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'step13_synthesis.png'))
    plt.close(fig)
    print('figures ->', FIG)
    print('final dir ->', FINAL)


if __name__ == '__main__':
    main()
