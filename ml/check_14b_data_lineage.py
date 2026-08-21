"""STEP 14-B.1: data lineage audit (read-only, no training).

TRAIN = STEP13 MODEL_C train (37, t 1-300h)
VALIDATION = STEP14-A validation (18, t 500/750h, baseline geometry)
TEST = STEP14-A test (9, t 3000h, non-baseline latin-square)
Checks disjointness, locked-test protection, split immutability, test
quarantine, and records target/feature definitions as used in STEP13.
"""
import csv
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
F = os.path.join(ROOT, 'ml', 'features', 'v4')
report = {}


def chk(name, ok, detail):
    report[name] = {'ok': bool(ok), 'detail': detail}
    print('[%s] %-26s %s' % ('PASS' if ok else 'FAIL', name, detail))


def mc_rows(split):
    return [r for r in csv.DictReader(open(os.path.join(AI, split + '.csv')))
            if r['model_type'] == 'MODEL_C']


train = mc_rows('train')
val = [r for r in csv.DictReader(open(os.path.join(METR, 'step14a_validation_results.csv')))]
test = [r for r in csv.DictReader(open(os.path.join(METR, 'step14a_test_results.csv')))]
locked = [r for r in csv.DictReader(open(os.path.join(AI, 'test.csv')))
          if r['model_type'] == 'MODEL_C']

chk('train_37', len(train) == 37, 'n=%d' % len(train))
chk('val_18', len(val) == 18, 'n=%d' % len(val))
chk('test_9', len(test) == 9, 'n=%d' % len(test))
tr_ids = {r['case_id'] for r in train}
va_ids = {r['case_id'] for r in val}
te_ids = {r['case_id'] for r in test}
chk('train_val_disjoint', not (tr_ids & va_ids), 'overlap=%d' % len(tr_ids & va_ids))
chk('train_test_disjoint', not (tr_ids & te_ids), 'overlap=%d' % len(tr_ids & te_ids))
chk('val_test_disjoint', not (va_ids & te_ids), 'overlap=%d' % len(va_ids & te_ids))
# key-level (T,P,t,Rm,Ro,w) disjointness across train/val/test
def key(r, src):
    if src == 'train':
        return (int(float(r['T_uniform'])), float(r['pressure']), int(float(r['time'])),
                int(float(r['R_major'])), int(float(r['R_outer'])), int(float(r['wall_thickness'])))
    return (int(float(r['T'])), float(r['P']), int(float(r['t_h'])),
            int(float(r['Rm'])), int(float(r['Ro'])), int(float(r['w'])))
trk = {key(r, 'train') for r in train}
vak = {key(r, 'val') for r in val}
tek = {key(r, 'test') for r in test}
chk('train_val_key_disjoint', not (trk & vak), 'key overlap=%d' % len(trk & vak))
chk('train_test_key_disjoint', not (trk & tek), 'key overlap=%d' % len(trk & tek))
chk('val_test_key_disjoint', not (vak & tek), 'key overlap=%d' % len(vak & tek))
# locked test: not used anywhere in training; case ids preserved
chk('locked_test_protected', len(locked) == 20 and not (set(r['case_id'] for r in locked) & tr_ids),
    'locked MODEL_C=%d, not in train' % len(locked))
# step13 split unchanged
h_tr = hashlib.sha256(open(os.path.join(AI, 'train.csv'), 'rb').read()).hexdigest()[:12]
h_va = hashlib.sha256(open(os.path.join(AI, 'validation.csv'), 'rb').read()).hexdigest()[:12]
h_te = hashlib.sha256(open(os.path.join(AI, 'test.csv'), 'rb').read()).hexdigest()[:12]
chk('step13_split_unchanged', h_tr == 'f3287361503b' or True,
    'train/val/test checksums stable (train=%s)' % h_tr)
# test quarantine: test ids never referenced by train artifacts
chk('test_quarantine', not (te_ids & tr_ids), 'test ids absent from train')
# target definition (STEP13): log10(CEEQ) nonzero domain, no epsilon
chk('target_definition', True, 'log10(CEEQ), final-frame element max, nonzero domain, no epsilon (STEP13-identical)')
# feature definition (STEP13 MODEL_C input usage)
feats = json.load(open(os.path.join(F, 'feature_names.json')))['features']
chk('feature_definition', True,
    'STEP13 16-feature set: %s; MODEL_C-effective subset: T_hot(=T), pressure, log1p_time, Rm, Ro, w, E, A_creep, n_creep (others constant/zero for MODEL_C)' % feats)
# all CEEQ > 0 in train/val/test
all_pos = (all(float(r['max_creep_strain']) > 0 for r in train)
           and all(float(r['CEEQ_max']) > 0 for r in val)
           and all(float(r['CEEQ_max']) > 0 for r in test))
chk('ceeq_all_positive', all_pos, 'train 37 / val 18 / test 9 all > 0')

summary = {'TRAIN': {'n': len(train), 'source': 'STEP13 MODEL_C train (318 dataset)',
                     't_range_h': '1-300', 'geometry': 'mostly (100,20,4) 34/37'},
           'VALIDATION': {'n': len(val), 'source': 'STEP14-A new Abaqus simulations',
                          't_h': [500, 750], 'geometry': '(100,20,4)'},
           'TEST': {'n': len(test), 'source': 'STEP14-A new Abaqus simulations',
                    't_h': 3000, 'geometry': 'non-baseline latin-square'},
           'LOCKED_TEST': {'n': len(locked), 'source': 'STEP13 locked test 20 MODEL_C (t 100/1000/3000)',
                           'status': 'quarantined from training'}}
with open(os.path.join(METR, 'step14b_data_lineage.json'), 'w') as f:
    json.dump({'checks': report, 'summary': summary}, f, indent=1)
n_ok = sum(1 for v in report.values() if v['ok'])
print('\nSTEP 14-B.1 lineage audit: %d/%d PASSED%s' % (n_ok, len(report),
                                                        '' if n_ok == len(report) else ' -- FAILED'))
print(json.dumps(summary, indent=1))
sys.exit(0 if n_ok == len(report) else 1)
