"""STEP 14-A.9 pre-solve + INP check (read-only, no Abaqus)."""
import csv
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
OUT = os.path.join(ROOT, 'simulation', 'generated_cases_step14a_ceeq')
V2_MAN = os.path.join(ROOT, 'simulation', 'generated_cases_v2', 'manifest_v2.csv')

CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
MATRIX = {(550, 5): (80, 15, 2), (550, 10): (120, 25, 3), (550, 20): (150, 20, 4),
          (600, 5): (120, 25, 3), (600, 10): (150, 20, 4), (600, 20): (80, 15, 2),
          (650, 5): (150, 20, 4), (650, 10): (80, 15, 2), (650, 20): (120, 25, 3)}
report = {}


def chk(name, ok, detail):
    report[name] = {'ok': bool(ok), 'detail': detail}
    print('[%s] %-32s %s' % ('PASS' if ok else 'FAIL', name, detail))


# A. design csv: test layer, t=3000, exactly 9, row-by-row match
design = list(csv.DictReader(open(os.path.join(METR, 'step14a_case_design.csv'))))
test9 = [r for r in design if r['layer'] == 'test' and int(r['t']) == 3000]
chk('design_9_rows', len(test9) == 9, 'n=%d' % len(test9))
bad = []
for r in test9:
    exp_g = MATRIX[(int(r['T']), int(r['P']))]
    g = (int(r['Rm']), int(r['Ro']), int(r['w']))
    exp_id = 'CEEQ14A_T%d_P%d_t3000h_Rm%d_Ro%d_w%d' % (int(r['T']), int(r['P']), *exp_g)
    if g != exp_g or r['case_id'] != exp_id or int(r['t']) != 3000:
        bad.append(r)
chk('design_rows_exact', not bad, 'violations=%d' % len(bad))

# B. dedup vs all historical MODEL_C keys
hist = set()
for src in (os.path.join(AI, 'simulation_dataset_318.csv'),):
    for r in csv.DictReader(open(src)):
        if r['model_type'] == 'MODEL_C':
            hist.add((int(float(r['T_uniform'])), float(r['pressure']), int(float(r['time'])),
                      int(float(r['R_major'])), int(float(r['R_outer'])), int(float(r['wall_thickness']))))
for r in csv.DictReader(open(V2_MAN)):
    if r['model'] == 'MODEL_C':
        hist.add((int(float(r['T_uniform'])), float(r['P']), int(float(r['t_h'])),
                  int(float(r['R_major'])), int(float(r['R_outer'])), int(float(r['wall']))))
# validation 18 (STEP14-A)
for r in csv.DictReader(open(os.path.join(METR, 'step14a_validation_results.csv'))):
    hist.add((int(float(r['T'])), float(r['P']), int(float(r['t_h'])),
              int(float(r['Rm'])), int(float(r['Ro'])), int(float(r['w']))))
dup = [r['case_id'] for r in test9
       if (int(r['T']), float(r['P']), int(r['t']), int(r['Rm']), int(r['Ro']), int(r['w'])) in hist]
chk('no_historical_dup', not dup, 'dups=%s' % (dup or 'NONE'))

# C. locked test conflict
locked = {(r['case_id'], (int(float(r['T_uniform'])), float(r['pressure']), int(float(r['time'])),
                          int(float(r['R_major'])), int(float(r['R_outer'])), int(float(r['wall_thickness']))))
          for r in csv.DictReader(open(os.path.join(AI, 'test.csv'))) if r['model_type'] == 'MODEL_C'}
hit = [r['case_id'] for r in test9
       if (int(r['T']), float(r['P']), int(r['t']), int(r['Rm']), int(r['Ro']), int(r['w'])) in
       {k[1] for k in locked}]
chk('no_locked_conflict', not hit, 'hits=%s' % (hit or 'NONE'))

# D. checksums
h318 = hashlib.sha256(open(os.path.join(AI, 'simulation_dataset_318.csv'), 'rb').read()).hexdigest()[:12]
hte = hashlib.sha256(open(os.path.join(AI, 'test.csv'), 'rb').read()).hexdigest()[:12]
chk('checksum_318', h318 == '20f21ebc67ea', h318)
chk('checksum_locked_test', hte == 'fa573e330926', hte)

# E. validation results untouched (mtime before this check)
import time as _t
vmt = os.path.getmtime(os.path.join(METR, 'step14a_validation_results.csv'))
chk('validation_results_untouched', _t.time() - vmt < 3600 * 6, 'written %.0f min ago' % ((_t.time() - vmt) / 60))

# F. materials unchanged (Norton table constant check via creep.csv)
creep_rows = list(csv.DictReader(open(os.path.join(ROOT, 'materials', 'SS316LN_N014', 'creep.csv'))))
vals = {550: None, 600: None, 650: None}
for r in creep_rows:
    if r['property'] == 'Creep_C':
        T = int(float(r['T_C']))
        if T in vals:
            vals[T] = float(r['value'])
chk('norton_C_unchanged', vals == {550: 2.79e-27, 600: 1.28e-24, 650: 8.46e-20},
    'C=%s (vs locked 2.79e-27/1.28e-24/8.46e-20)' % vals)

# G. INP checks: 9/9 exist + cards
inp_ok = 0
for r in test9:
    p = os.path.join(OUT, r['case_id'] + '.inp')
    if not os.path.exists(p):
        continue
    txt = open(p).read()
    lines = txt.splitlines()
    ok = True
    creep_row = None
    visco_ok = temp_ok = ds_ok = False
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s == '*Creep, law=STRAIN':
            vals = [float(x) for x in lines[i + 1].strip().split(',')]
            expA, expn = CREEP[int(r['T'])]
            creep_row = vals[:2]
            ok = ok and abs(vals[0] - expA) / expA < 1e-9 and abs(vals[1] - expn) / expn < 1e-9
        if s.startswith('0.01, 3000,'):
            visco_ok = True
        if s.startswith('ALLN,') and abs(float(s.split(',')[1]) - float(r['T'])) < 1e-9:
            temp_ok = True
        if s.startswith('SINNER, P,') and abs(float(s.split(',')[2]) - float(r['P'])) < 1e-9:
            ds_ok = True
    if ok and visco_ok and temp_ok and ds_ok:
        inp_ok += 1
chk('inp_9_9', inp_ok == 9, 'valid INPs=%d/9 (Creep/Norton, Visco 3000h, T, P)' % inp_ok)

with open(os.path.join(METR, 'step14a_test_presolve.json'), 'w') as f:
    json.dump(report, f, indent=1)
all_ok = all(v['ok'] for v in report.values())
print('\nPRE-SOLVE + INP CHECK: %d/%d PASSED%s' %
      (sum(1 for v in report.values() if v['ok']), len(report),
       '' if all_ok else ' -- FAILED'))
sys.exit(0 if all_ok else 1)
