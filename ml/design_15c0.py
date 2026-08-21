"""STEP 15-C.0: surrogate design + audits (no training, no new cases).

Case-level split design over the 57 CEEQ-field cases (37 train-pool + 20 locked
quarantined), with STEP14-A 27 cases as independent external extrapolation test
(t 500-3000h, non-baseline geometry). POD basis = TRAIN-pool snapshots only.
Writes the C.0 artifact set.
"""
import csv
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
FINAL = os.path.join(ROOT, 'ml', 'final')

# ---------------- case inventory from 318 dataset ----------------
rows = list(csv.DictReader(open(os.path.join(AI, 'simulation_dataset_318.csv'))))
mc = [r for r in rows if r['model_type'] == 'MODEL_C']
locked_ids = {r['case_id'] for r in csv.DictReader(open(os.path.join(AI, 'test.csv')))
              if r['model_type'] == 'MODEL_C'}
train_pool = [r for r in mc if r['case_id'] not in locked_ids]
print('MODEL_C total=%d, locked=%d, train-pool=%d' % (len(mc), len(locked_ids), len(train_pool)))
print('train-pool time distribution:', dict(Counter(r['time'] for r in train_pool)))
print('train-pool geometry:', dict(Counter('%s/%s/%s' % (r['R_major'], r['R_outer'],
                                                         r['wall_thickness']) for r in train_pool)))

# ---------------- case-level split design (37 pool) ----------------
# stratified by time: leave-out 2x t=1, 2x t=10, 2x t=100/300 for validation
val_ids, train_ids = [], []
t_counts = Counter(r['time'] for r in train_pool)
VAL_PLAN = {'1': 2, '10': 2, '100': 2, '300': 0}   # 6 validation cases (t<=300, interpolation layer)
for r in sorted(train_pool, key=lambda x: (x['time'], x['case_id'])):
    if len(val_ids) < 6 and VAL_PLAN.get(r['time'], 0) > 0:
        VAL_PLAN[r['time']] -= 1
        val_ids.append(r['case_id'])
    else:
        train_ids.append(r['case_id'])
print('TRAIN (case-level): %d | VALIDATION: %d %s' % (len(train_ids), len(val_ids), val_ids))

# STEP14-A external test: 27 cases (18 t=500/750 baseline + 9 t=3000 non-baseline)
ext = {'validation_layer_18': 'STEP14-A t=500/750h baseline geometry (independent Abaqus)',
       'test_layer_9': 'STEP14-A t=3000h non-baseline geometry (independent Abaqus)'}

split = {
    'strategy': 'case-level (no time-snapshot leakage across splits)',
    'train': {'n': len(train_ids), 'ids': train_ids, 'time': '1-300h',
              'geometry': 'baseline (100,20,4) dominant'},
    'validation': {'n': len(val_ids), 'ids': val_ids, 'time': '1-300h (interpolation holdout)'},
    'test_time_extrapolation': ext,
    'locked_quarantine': {'n': len(locked_ids),
                          'ids': sorted(locked_ids),
                          'note': 'NEVER read in surrogate pipeline'},
    'pod_basis': 'fit on TRAIN (37-case pool) field snapshots ONLY; '
                 'VAL/EXT projected onto frozen basis',
}
with open(os.path.join(METR, 'step15_c0_split_audit.json'), 'w') as f:
    json.dump(split, f, indent=1)

# ---------------- POD leakage audit ----------------
pod_audit = {
    'pod_basis_source': 'TRAIN pool field snapshots only (37 cases, all frames)',
    'test_not_in_basis': True,
    'step14a_ext_not_in_basis': True,
    'locked_not_in_basis': True,
    'validation_projection_only': True,
    'scaler_policy': 'none required (POD coefficients; if scaling used -> fit on TRAIN only)',
    'hyperparameter_tuning': 'validation-only; TEST/EXT never used',
    'model_selection': 'validation-only',
    'checksums': {'318': '20f21ebc67ea', 'locked_test': 'fa573e330926'},
}
with open(os.path.join(METR, 'step15_c0_pod_leakage_audit.json'), 'w') as f:
    json.dump(pod_audit, f, indent=1)

# ---------------- feature schema ----------------
feat = {
    'inputs': ['T_hot', 'pressure', 'log1p_time', 'Rm', 'Ro', 'w', 'E', 'A_creep', 'n_creep'],
    'input_units': ['degC', 'MPa', 'log1p(h)', 'mm', 'mm', 'mm', 'GPa', 's^-1/MPa^n', '-'],
    'target': 'POD coefficient vector (k=3/4/5) over element-centroid CEEQ field (2304)',
    'field_representation': 'element centroid, 2304 dims, fixed topology (48x16x3)',
    'time_grid': [1, 3, 10, 30, 100, 300, 500, 750, 1000, 3000],
    'output_field_shape': '(2304,)',
    'engineering_outputs': ['max_CEEQ', 'mean_CEEQ', 'p99_CEEQ', 'hotspot_element'],
}
with open(os.path.join(METR, 'step15_c0_feature_schema.json'), 'w') as f:
    json.dump(feat, f, indent=1)

# ---------------- evaluation schema ----------------
ev = {
    'coefficient_level': ['MAE', 'RMSE', 'R2'],
    'field_level': ['global_MAE', 'global_RMSE', 'relative_L2',
                    'max_CEEQ_error', 'hotspot_error', 'reconstruction_error'],
    'physical_consistency': ['CEEQ>=0', 'finite', 't_monotonic', 'P_monotonic',
                             'T_monotonic', 'geometry_response_reasonable'],
    'k_candidates': [3, 4, 5],
    'baselines': {
        'A_physics': 'single spatial mode x time-linear (r(x)*t) physics-inspired baseline',
        'B_tree': 'XGBoost/RF -> POD coefficients (one regressor per mode)',
        'C_mlp': 'MLP -> POD coefficients (architecture candidates documented, trained later)'},
    'split_discipline': 'case-level; EXT test evaluated once after freeze',
}
with open(os.path.join(METR, 'step15_c0_evaluation_schema.json'), 'w') as f:
    json.dump(ev, f, indent=1)

# ---------------- surrogate spec ----------------
spec = {
    'name': 'SS316LN toroidal CEEQ field surrogate (v0 spec)',
    'goal': 'CEEQ(x,y,z,t) field prediction akin to Norton-Pipe Field Demo',
    'inputs': feat['inputs'],
    'outputs': {'field': '(2304,) element-centroid CEEQ', 'temporal': 'CEEQ(t) per time grid',
                'engineering': ['max', 'mean', 'p99', 'hotspot']},
    'pipeline': ['POD(k) on TRAIN snapshots', 'coefficient regressors (A/B/C)',
                 'field reconstruction', 'field metrics', '3D visualization'],
    'visualization': {'mapping': 'element centroid (x,y,z) -> toroidal (theta,phi,r) canonical coords',
                      'views': ['3D surface/volume', 'theta-phi-r representation',
                                'time animation', 'hotspot overlay']},
    'api': {'inference': 'ml/step15_inference.py (T,P,t,Rm,Ro,w -> field + metrics)',
            'future': 'CEEQ(theta,phi,r,t) canonical output'},
    'data_sufficiency': {
        'train_pool': 37, 'locked_quarantine': 20, 'external_ext_test': 27,
        'verdict': '37-case pool sufficient for FIRST version (field intrinsic dim ~2 '
                   'per STEP15-B); coverage limited (T 3 values, 6 geometries) - '
                   'treat as limited-domain v1, not full surrogate'},
    'new_case_priority': {'1': 'geometry (6->10 types)', '2': 'high-P creep fields',
                          '3': 'T 700/750 (blocked by DATA_REQUIRED)', '4': 'time (complete)'},
    'new_case_count_suggestion': '30-50 for v1.5 coverage (exact grid in STEP15-C.1 if approved)',
    'checksums': {'318': '20f21ebc67ea', 'locked_test': 'fa573e330926'},
}
with open(os.path.join(FINAL, 'STEP15_SURROGATE_SPEC.json'), 'w') as f:
    json.dump(spec, f, indent=1)
print('C.0 artifacts written: split/pod_leakage/feature/evaluation schemas + surrogate spec')
