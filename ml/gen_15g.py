"""STEP 15-G.2: lock 50 proposed cases -> duplicate audit -> generate INPs ->
PRE-SOLVE json. No Abaqus execution here. Dir: simulation/generated_cases_step15g/.
"""
import csv
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'abaqus', 'scripts')
sys.path.insert(0, SCRIPTS)
import generate_cases as gc  # noqa: E402

METR = os.path.join(ROOT, 'ml', 'metrics')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
OUT = os.path.join(ROOT, 'simulation', 'generated_cases_step15g')
CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}

# ---------------- lock the approved design ----------------
design = list(csv.DictReader(open(os.path.join(METR, 'step15_g_proposed_cases.csv'))))
assert len(design) == 50, 'proposed cases != 50: %d' % len(design)
for d in design:
    for kk in ('T', 'P', 't', 'Rm', 'Ro', 'w'):
        d[kk] = int(float(d[kk]))
    d['case_id'] = 'CEEQ15G_T%d_P%d_t%dh_Rm%d_Ro%d_w%d' % (
        d['T'], d['P'], d['t'], d['Rm'], d['Ro'], d['w'])
assert len(set(d['case_id'] for d in design)) == 50, 'non-unique case_id'
keys = [(d['T'], d['P'], d['t'], d['Rm'], d['Ro'], d['w']) for d in design]
assert len(set(keys)) == 50, 'non-unique (T,P,t,Rm,Ro,w)'
print('50 cases locked (IDs unique, params unique)')

# ---------------- duplicate audit ----------------
hist = set()
for r in csv.DictReader(open(os.path.join(AI, 'simulation_dataset_318.csv'))):
    if r['model_type'] == 'MODEL_C':
        hist.add((int(float(r['T_uniform'])), float(r['pressure']), int(float(r['time'])),
                  int(float(r['R_major'])), int(float(r['R_outer'])),
                  int(float(r['wall_thickness']))))
for src in ('step14a_validation_results.csv', 'step14a_test_results.csv'):
    for r in csv.DictReader(open(os.path.join(METR, src))):
        hist.add((int(float(r['T'])), float(r['P']), int(float(r['t_h'])),
                  int(float(r['Rm'])), int(float(r['Ro'])), int(float(r['w']))))
locked = {(int(float(r['T_uniform'])), float(r['pressure']), int(float(r['time'])),
           int(float(r['R_major'])), int(float(r['R_outer'])), int(float(r['wall_thickness'])))
          for r in csv.DictReader(open(os.path.join(AI, 'test.csv')))
          if r['model_type'] == 'MODEL_C'}
dup_hist = [d['case_id'] for d in design if tuple(keys[design.index(d)]) in hist]
dup_lock = [d['case_id'] for d in design if tuple(keys[design.index(d)]) in locked]
assert not dup_hist and not dup_lock, 'DUPLICATES FOUND: hist=%s locked=%s' % (dup_hist, dup_lock)
with open(os.path.join(METR, 'step15_g_duplicate_audit.json'), 'w') as f:
    json.dump({'proposed': 50, 'dup_vs_history': 0, 'dup_vs_locked': 0,
               'dup_vs_ext27': 0}, f, indent=1)
print('duplicate audit PASS (history/locked/EXT27)')

# ---------------- generate INPs ----------------
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
gc.OUT = OUT
presolve = {'cases': []}
for d in design:
    cid = d['case_id']
    path, meta = gc.gen_inp(cid, 'MODEL_C', float(d['T']), None, None, float(d['P']),
                            float(d['t']), d['Rm'], d['Ro'], d['w'])
    assert path, 'gen fail %s' % cid
    txt = open(path).read()
    lines = txt.splitlines()
    creep_ok = False
    for i, ln in enumerate(lines):
        if ln.strip() == '*Creep, law=STRAIN':
            vals = [float(x) for x in lines[i + 1].strip().split(',')]
            expA, expn = CREEP[d['T']]
            creep_ok = (abs(vals[0] - expA) / expA < 1e-9 and abs(vals[1] - expn) / expn < 1e-9
                        and int(vals[3]) == d['T'])
            break
    visco_ok = any(ln.strip().startswith('0.01, %d,' % d['t']) for ln in lines)
    presolve['cases'].append({'case_id': cid, 'T': d['T'], 'P': d['P'], 't': d['t'],
                              'Rm': d['Rm'], 'Ro': d['Ro'], 'w': d['w'],
                              'P_Ro_w': d['P_Ro_w'],
                              'norton_source': 'MAT-05 locked table',
                              'norton_ok': creep_ok, 'visco_ok': visco_ok,
                              'geom_ok': d['Ro'] > d['w'] and d['Rm'] > 2 * d['Ro'],
                              'T_allowed': d['T'] in (550, 600, 650),
                              'inp_written': bool(path)})
n_pass = sum(1 for c in presolve['cases']
             if c['norton_ok'] and c['visco_ok'] and c['geom_ok'] and c['T_allowed']
             and c['inp_written'])
presolve['n_pass'] = n_pass
presolve['n_total'] = 50
with open(os.path.join(METR, 'step15_g_presolve.json'), 'w') as f:
    json.dump(presolve, f, indent=1)
print('PRE-SOLVE: %d/%d PASS -> %s' % (n_pass, 50, OUT))
sys.exit(0 if n_pass == 50 else 1)
