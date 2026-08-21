"""STEP 15-G: coverage audit + gap-driven data expansion design (DESIGN ONLY).
Coverage from 318 + STEP14-A 27 (345 creep-capable rows). Proposed ~30-50
cases prioritized: 3000h x non-baseline geometry > high-P creep > bridge times
> new geometry. Duplicate audit vs all historical; physics feasibility check.
"""
import csv
import itertools
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}

# ---------------- existing creep coverage (318 + STEP14-A 27) ----------------
rows = [r for r in csv.DictReader(open(os.path.join(AI, 'simulation_dataset_318.csv')))
        if r['model_type'] == 'MODEL_C']
for src in ('step14a_validation_results.csv', 'step14a_test_results.csv'):
    for r in csv.DictReader(open(os.path.join(METR, src))):
        rows.append({'T_uniform': r['T'], 'pressure': r['P'], 'time': r['t_h'],
                     'R_major': r['Rm'], 'R_outer': r['Ro'],
                     'wall_thickness': r['w']})
existing = set()
for r in rows:
    existing.add((int(float(r['T_uniform'])), float(r['pressure']),
                  int(float(r['time'])), int(float(r['R_major'])),
                  int(float(r['R_outer'])), int(float(r['wall_thickness']))))
print('existing creep rows: %d, unique keys: %d' % (len(rows), len(existing)))

# coverage per dimension
def cov(fn):
    return dict(Counter(fn(r) for r in rows))

t_cov = cov(lambda r: int(float(r['time'])))
p_cov = cov(lambda r: float(r['pressure']))
g_cov = cov(lambda r: '%s/%s/%s' % (r['R_major'], r['R_outer'], r['wall_thickness']))
print('time:', dict(sorted(t_cov.items())))
print('P:', dict(sorted(p_cov.items())))
print('n geometries:', len(g_cov), '| baseline:', g_cov.get('100/20/4', 0))

# long-time x geometry matrix (t>=1000)
ltg = {}
for r in rows:
    t = int(float(r['time']))
    if t >= 1000:
        key = '%s/%s/%s' % (r['R_major'], r['R_outer'], r['wall_thickness'])
        ltg.setdefault(key, []).append(t)
print('long-time (>=1000h) geometry coverage:')
for g, ts in sorted(ltg.items()):
    print('  %-12s t=%s' % (g, sorted(set(ts))))
print('geometries with ZERO long-time coverage:',
      sorted(set(g_cov) - set(ltg)))

# high-P creep
hp = sorted({float(r['pressure']) for r in rows if float(r['pressure']) >= 25})
print('high-P (>=25) creep present:', hp)

# ---------------- gap-driven design ----------------
DESIGN = []
NORTON_OK = {550, 600, 650}


def add(T, P, t, Rm, Ro, w, reason):
    key = (T, P, t, Rm, Ro, w)
    if key in existing:
        return
    if T not in NORTON_OK:
        return
    if not (Ro > w and Rm > 2 * Ro):
        return
    DESIGN.append({'T': T, 'P': P, 't': t, 'Rm': Rm, 'Ro': Ro, 'w': w,
                   'P_Ro_w': round(P * Ro / w, 1), 'reason': reason})


# Priority 1: 3000h x non-baseline geometries (the F-identified gap), incl. middle geoms
GEOMS = [(80, 15, 2), (120, 25, 3), (150, 20, 4), (90, 18, 3), (110, 22, 4)]
for T in (550, 600, 650):
    for P in (5, 10, 20):
        for g in GEOMS:
            add(T, P, 3000, *g, 'P1: 3000h x non-baseline geom (F gap)')
# Priority 1b: 3000h high-P x thin (stress-scale extreme)
for T in (550, 600, 650):
    for P in (25, 30):
        for g in ((80, 15, 2), (120, 25, 3)):
            add(T, P, 3000, *g, 'P1b: 3000h high-P x thin (stress extreme)')
# Priority 2: bridge 1000h x non-baseline (reduce 10x extrapolation)
for T in (550, 600, 650):
    for P in (5, 10, 20):
        for g in ((90, 18, 3), (110, 22, 4), (80, 15, 2), (120, 25, 3), (150, 20, 4)):
            add(T, P, 1000, *g, 'P2: 1000h bridge x non-baseline')
# Priority 3: high-P creep at baseline geom (P 25/30/40)
for T in (550, 600, 650):
    for P in (25, 30, 40):
        add(T, P, 100, 100, 20, 4, 'P3: high-P baseline creep 100h')
        add(T, P, 1000, 100, 20, 4, 'P3: high-P baseline creep 1000h')
# Priority 4: new representative geometries (stress-scale spread) at 300/1000h
MID = [(90, 18, 3), (110, 22, 4), (100, 25, 3), (120, 20, 3), (140, 18, 4)]
for T in (600, 650):
    for P in (10, 20):
        for g in MID:
            add(T, P, 300, *g, 'P4: new geometry coverage 300h')
            add(T, P, 1000, *g, 'P4: new geometry coverage 1000h')

print('\nproposed new cases: %d' % len(DESIGN))
from collections import Counter as _C
print('by time:', dict(_C(d['t'] for d in DESIGN)))
print('by P:', dict(sorted(_C(d['P'] for d in DESIGN).items())))
print('by T:', dict(_C(d['T'] for d in DESIGN)))
print('by reason:', dict(_C(d['reason'].split(':')[0] for d in DESIGN)))

# cap to 50 (highest priority first)
order_prio = {'P1': 0, 'P1b': 1, 'P2': 2, 'P3': 3, 'P4': 4}
DESIGN.sort(key=lambda d: (order_prio.get(d['reason'].split(':')[0], 9),
                           -d['P_Ro_w']))
if len(DESIGN) > 50:
    DESIGN = DESIGN[:50]
print('final proposed: %d' % len(DESIGN))

with open(os.path.join(METR, 'step15_g_proposed_cases.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(DESIGN[0].keys()))
    w.writeheader()
    for d in DESIGN:
        w.writerow(d)
with open(os.path.join(METR, 'step15_g_duplicate_audit.json'), 'w') as f:
    json.dump({'proposed': len(DESIGN), 'duplicates_vs_history': 0,
               'checked_against': len(existing)}, f, indent=1)
with open(os.path.join(METR, 'step15_g_physics_feasibility.json'), 'w') as f:
    json.dump({'T_set': sorted({d['T'] for d in DESIGN}),
               'norton_available': '550/600/650 only (700/750 DATA_REQUIRED, blocked)',
               'geometry_valid': all(d['Ro'] > d['w'] and d['Rm'] > 2 * d['Ro']
                                     for d in DESIGN),
               'P_Ro_w_range': [min(d['P_Ro_w'] for d in DESIGN),
                                max(d['P_Ro_w'] for d in DESIGN)]}, f, indent=1)
# coverage matrix csv (time x geometry summary)
with open(os.path.join(METR, 'step15_g_coverage_matrix.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['geometry', 't1-300', 't500-750', 't1000', 't3000', 'total'])
    for g, n in sorted(g_cov.items()):
        tcounts = {t: 0 for t in ('1-300', '500-750', '1000', '3000')}
        for r in rows:
            if '%s/%s/%s' % (r['R_major'], r['R_outer'], r['wall_thickness']) != g:
                continue
            t = int(float(r['time']))
            key = '1-300' if t <= 300 else ('500-750' if t <= 750 else
                                            ('1000' if t == 1000 else '3000'))
            tcounts[key] += 1
        w.writerow([g, tcounts['1-300'], tcounts['500-750'], tcounts['1000'],
                    tcounts['3000'], n])
with open(os.path.join(METR, 'step15_g_gap_analysis.json'), 'w') as f:
    json.dump({'time_cov': dict(sorted(t_cov.items())),
               'P_cov': dict(sorted(p_cov.items())),
               'n_geometries': len(g_cov),
               'long_time_geometries': {g: sorted(set(ts)) for g, ts in ltg.items()},
               'geometries_no_long_time': sorted(set(g_cov) - set(ltg)),
               'highP_creep_present': hp,
               'proposed_count': len(DESIGN),
               'gap_summary': 'F-gap (3000h x thin non-baseline) is priority 1; '
                              '1000h bridge priority 2; high-P priority 3; new '
                              'geometry priority 4'}, f, indent=1)
print('STEP 15-G design artifacts written')
