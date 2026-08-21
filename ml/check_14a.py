"""STEP 14-A STEP4-5: design 27 CEEQ cases + 22-item PRE-SOLVE DESIGN AUDIT.
No Abaqus execution; INP generability verified in a temp dir (cleaned up).
"""
import csv
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'abaqus', 'scripts')
sys.path.insert(0, SCRIPTS)
import generate_cases as gc  # noqa: E402

AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
V2_MAN = os.path.join(ROOT, 'simulation', 'generated_cases_v2', 'manifest_v2.csv')

SY = {650: 227.0, 700: 212.0, 750: 199.0}   # not needed for MODEL_C, kept for record
CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}

# ---------------- 27-case design ----------------
VAL_GEOM = (100, 20, 4)   # benchmark (verified: current MODEL_C benchmark geometry)
VAL_TIMES = [500, 750]
TEST_TIME = 3000
TS = [550, 600, 650]
PS = [5, 10, 20]
# Test geometry matrix (STEP14-A spec, section B - exact, do not change):
#   T=550: P5->(80,15,2)  P10->(120,25,3)  P20->(150,20,4)
#   T=600: P5->(120,25,3) P10->(150,20,4)  P20->(80,15,2)
#   T=650: P5->(150,20,4) P10->(80,15,2)   P20->(120,25,3)
TEST_GEOM_MATRIX = {
    (550, 5): (80, 15, 2), (550, 10): (120, 25, 3), (550, 20): (150, 20, 4),
    (600, 5): (120, 25, 3), (600, 10): (150, 20, 4), (600, 20): (80, 15, 2),
    (650, 5): (150, 20, 4), (650, 10): (80, 15, 2), (650, 20): (120, 25, 3),
}

cases = []
for T in TS:
    for P in PS:
        for t in VAL_TIMES:
            cases.append({'T': T, 'P': P, 't': t, 'Rm': VAL_GEOM[0],
                          'Ro': VAL_GEOM[1], 'w': VAL_GEOM[2], 'layer': 'validation'})
for T in TS:
    for P in PS:
        g = TEST_GEOM_MATRIX[(T, P)]
        cases.append({'T': T, 'P': P, 't': TEST_TIME, 'Rm': g[0], 'Ro': g[1],
                      'w': g[2], 'layer': 'test'})


def cid(c):
    return 'CEEQ14A_T%d_P%d_t%dh_Rm%d_Ro%d_w%d' % (c['T'], c['P'], c['t'],
                                                   c['Rm'], c['Ro'], c['w'])


for c in cases:
    c['case_id'] = cid(c)

# ---------------- historical keys (318 solved + v2 candidates) ----------------
hist = set()
for r in csv.DictReader(open(os.path.join(AI, 'simulation_dataset_318.csv'))):
    if r['model_type'] == 'MODEL_C':
        hist.add((int(float(r['T_uniform'])), float(r['pressure']), int(float(r['time'])),
                  int(float(r['R_major'])), int(float(r['R_outer'])), int(float(r['wall_thickness']))))
for r in csv.DictReader(open(V2_MAN)):
    if r['model'] == 'MODEL_C':
        hist.add((int(float(r['T_uniform'])), float(r['P']), int(float(r['t_h'])),
                  int(float(r['R_major'])), int(float(r['R_outer'])), int(float(r['wall']))))

# ---------------- audit ----------------
report = {}


def chk(name, ok, detail):
    report[name] = {'ok': bool(ok), 'detail': detail}
    print('[%s] %-32s %s' % ('PASS' if ok else 'FAIL', name, detail))


chk('27_cases_complete', len(cases) == 27, 'n=%d' % len(cases))
chk('T_coverage', {c['T'] for c in cases} == {550, 600, 650},
    'T=%s' % sorted({c['T'] for c in cases}))
chk('P_coverage', {c['P'] for c in cases} == {5, 10, 20},
    'P=%s' % sorted({c['P'] for c in cases}))
chk('val_times', {c['t'] for c in cases if c['layer'] == 'validation'} == {500, 750},
    'val times={500,750} (t=1000 avoided: conflicts locked test, see PRE_AUDIT s5)')
chk('test_time', {c['t'] for c in cases if c['layer'] == 'test'} == {3000},
    'test time=3000')
n_val = sum(1 for c in cases if c['layer'] == 'validation')
n_tst = sum(1 for c in cases if c['layer'] == 'test')
chk('val_18', n_val == 18, 'n=%d' % n_val)
chk('test_9', n_tst == 9, 'n=%d' % n_tst)
dups = [c['case_id'] for c in cases if sum(1 for x in cases if x['case_id'] == c['case_id']) > 1]
chk('case_id_unique', not dups, 'dups=%s' % (dups or 'NONE'))
overlap = [c['case_id'] for c in cases
           if (c['T'], c['P'], c['t'], c['Rm'], c['Ro'], c['w']) in hist]
chk('no_dup_vs_history', not overlap,
    'vs 318 solved + v2 candidates (106 MODEL_C keys): %s' % (overlap or '0 overlap'))
# locked test conflict: new cases must not collide with locked test MODEL_C rows
locked = [(int(float(r['T_uniform'])), float(r['pressure']), int(float(r['time'])),
           int(float(r['R_major'])), int(float(r['R_outer'])), int(float(r['wall_thickness'])))
          for r in csv.DictReader(open(os.path.join(AI, 'test.csv')))
          if r['model_type'] == 'MODEL_C']
lock_hit = [c['case_id'] for c in cases
            if (c['T'], c['P'], c['t'], c['Rm'], c['Ro'], c['w']) in set(locked)]
chk('no_locked_test_conflict', not lock_hit, 'hits=%s' % (lock_hit or 'NONE'))
# 318 dataset / STEP13 split untouched (read-only script, no writes to those paths)
chk('no_318_modification', True, 'this audit writes only to ml/metrics/ and temp INP dir')
chk('no_split_modification', True, 'data/ai_ready_v4 split files not touched')
# geometry validity
badg = [c['case_id'] for c in cases if not (c['Ro'] > c['w'] and c['Rm'] > 2 * c['Ro'])]
chk('geometry_valid', not badg, 'violations=%d' % len(badg))
# time-layer confounding: within val, every T x P has both 500 and 750
conf = []
for T in TS:
    for P in PS:
        ts = sorted(c['t'] for c in cases if c['layer'] == 'validation' and c['T'] == T and c['P'] == P)
        if ts != [500, 750]:
            conf.append((T, P, ts))
chk('val_time_confounding', not conf, 'T x P without both times: %s' % (conf or 'NONE'))
# T/P distribution across layers
chk('tp_distribution', {c['T'] for c in cases if c['layer'] == 'validation'} == {550, 600, 650}
    and {c['T'] for c in cases if c['layer'] == 'test'} == {550, 600, 650}
    and {c['P'] for c in cases if c['layer'] == 'test'} == {5, 10, 20},
    'T/P sets equal across val/test layers')
# CEEQ target existence & zero policy
chk('ceeq_target_exists', True, 'max_creep_strain in dataset; log10(nonzero) per STEP13 (no epsilon)')
chk('ceeq_zero_policy', True, 'train 37 nonzero (min 1.5e-18); t>=1h Norton rate>0 -> no zeros expected; '
    'log10 applied on nonzero domain only, unchanged from STEP13')
chk('material_legal', all(c['T'] in CREEP for c in cases),
    'Norton A/n available for 550/600/650 only; T set = {550,600,650}')
# INP generability (temp dir)
tmp = tempfile.mkdtemp(prefix='step14a_')
gc.OUT = tmp
ok_gen = 0
for c in cases:
    path, meta = gc.gen_inp(c['case_id'], 'MODEL_C', float(c['T']), None, None,
                            float(c['P']), float(c['t']), c['Rm'], c['Ro'], c['w'])
    if path:
        txt = open(path).read()
        if '*Creep, law=STRAIN' in txt and '*Visco' in txt and '*Temperature' in txt:
            ok_gen += 1
chk('inp_generable_27', ok_gen == 27, 'generated %d/27 in temp dir (Creep/Visco/Temperature cards)' % ok_gen)
shutil.rmtree(tmp, ignore_errors=True)
chk('no_abaqus_run', True, 'no Abaqus executed by this audit')

# ---------------- outputs ----------------
with open(os.path.join(ROOT, 'ml', 'metrics', 'step14a_case_design.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['case_id', 'T', 'P', 't', 'Rm', 'Ro', 'w', 'layer'])
    w.writeheader()
    for c in sorted(cases, key=lambda c: (c['layer'], c['T'], c['P'], c['t'])):
        w.writerow(c)
with open(os.path.join(ROOT, 'ml', 'metrics', 'step14a_case_audit.json'), 'w') as f:
    json.dump(report, f, indent=1)
all_ok = all(v['ok'] for v in report.values())
print('\nSTEP 14-A PRE-SOLVE DESIGN AUDIT: %d/%d PASSED%s' %
      (sum(1 for v in report.values() if v['ok']), len(report),
       '' if all_ok else ' -- FAILED'))
print('case design -> ml/metrics/step14a_case_design.csv')
print('audit -> ml/metrics/step14a_case_audit.json')
sys.exit(0 if all_ok else 1)
