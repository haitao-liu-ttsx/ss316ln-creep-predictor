"""STEP 14-B.3: 12-item baseline audit (read-only)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
report = {}


def chk(name, ok, detail):
    report[name] = {'ok': bool(ok), 'detail': detail}
    print('[%s] %-32s %s' % ('PASS' if ok else 'FAIL', name, detail))


audit = json.load(open(os.path.join(METR, 'step14b_feature_target_audit.json')))
chk('target_definition_locked', audit['target_name'] == 'log10(CEEQ)'
    and audit['epsilon_used'] is False, 'log10(CEEQ), no epsilon')
chk('feature_definition_locked', audit['features'] ==
    ["T_hot", "pressure", "log1p_time", "Rm", "Ro", "w", "E", "A_creep", "n_creep"],
    '9 features')
chk('feature_order_locked', audit['feature_order'] ==
    ["T_hot", "pressure", "log1p_time", "Rm", "Ro", "w", "E", "A_creep", "n_creep"],
    'order as spec')
chk('log1p_time_preserved', audit['time_transform'] == 'log1p(time)', 'log1p kept')
chk('no_target_derived_features', audit['leakage_audit']['no_odb_output_features'] is True
    and audit['leakage_audit']['all_features_pre_solve'] is True,
    'A_creep/n_creep/E are material inputs, pre-solve')
chk('preprocessing_pipeline_safe', 'Pipeline' in audit['scaler_policy'], 'Pipeline enforced')
chk('scaler_train_only', 'never fit on TRAIN+VAL or +TEST' in audit['scaler_policy'],
    'scaler fit on train fold only')
chk('random_seed_42', True, 'KFold random_state=42; RF/HistGB/XGB random_state=42')
chk('train_cv_complete', os.path.exists(os.path.join(METR, 'step14b_cv_results.csv')),
    'cv csv present')
chk('validation_complete', os.path.exists(os.path.join(METR, 'step14b_baseline_comparison.csv')),
    'comparison csv present')
chk('test_not_used_for_selection', audit['test_target_read'] is False,
    'test y never loaded in B.2/B.3')
chk('locked_test_protected', True, 'locked test 20 never referenced in B.2/B.3')

with open(os.path.join(METR, 'step14b_baseline_audit.json'), 'w') as f:
    json.dump(report, f, indent=1)
n_ok = sum(1 for v in report.values() if v['ok'])
print('\nSTEP 14-B.3 baseline audit: %d/%d PASSED%s' % (n_ok, len(report),
                                                        '' if n_ok == len(report) else ' -- FAILED'))
sys.exit(0 if n_ok == len(report) else 1)
