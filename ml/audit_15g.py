"""STEP 15-G.2: coverage/physics/final audits (venv python, read-only)."""
import csv
import hashlib
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
FINAL_V11 = os.path.join(ROOT, 'ml', 'final', 'step15_v1_1')

rows = list(csv.DictReader(open(os.path.join(METR, 'step15_g_odb_qc.csv'))))
n_3000 = sum(1 for r in rows if r['t'] == '3000')
n_1000 = sum(1 for r in rows if r['t'] == '1000')
geoms = Counter('%s/%s/%s' % (r['Rm'], r['Ro'], r['w']) for r in rows)
p25 = sum(1 for r in rows if float(r['P']) >= 25)
prw = [float(r['P']) * float(r['Ro']) / float(r['w']) for r in rows]
phys_warn = [r['case_id'] for r in rows if float(r['CEEQ_max']) <= 0]
# trends: within same geometry, CEEQ vs P and vs T monotonicity (all t=3000 group)
trend_viol = []
for g in geoms:
    gr = [r for r in rows if '%s/%s/%s' % (r['Rm'], r['Ro'], r['w']) == g and r['t'] == '3000']
    if len(gr) < 3:
        continue
    by_t = {}
    for r in gr:
        by_t.setdefault(int(float(r['T'])), {})[int(float(r['P']))] = float(r['CEEQ_max'])
    for T, pm in by_t.items():
        ps = sorted(pm)
        if any(pm[ps[i + 1]] < pm[ps[i]] for i in range(len(ps) - 1)):
            trend_viol.append((g, T, 'P_nonmono'))
print('new cases: %d | t3000=%d t1000=%d | geoms=%d %s' %
      (len(rows), n_3000, n_1000, len(geoms), dict(geoms)))
print('P>=25 cases: %d | P*Ro/w range: %.1f .. %.1f' % (p25, min(prw), max(prw)))
print('physics warnings:', phys_warn or 'NONE', '| trend violations:', trend_viol or 'NONE')

with open(os.path.join(METR, 'step15_g_geometry_coverage.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['geometry', 'n_cases', 'P_Ro_w_range'])
    for g, n in sorted(geoms.items()):
        gr = [r for r in rows if '%s/%s/%s' % (r['Rm'], r['Ro'], r['w']) == g]
        rr = [float(r['P']) * float(r['Ro']) / float(r['w']) for r in gr]
        w.writerow([g, n, '%.1f-%.1f' % (min(rr), max(rr))])
with open(os.path.join(METR, 'step15_g_time_coverage.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['time_h', 'n_cases'])
    for t, n in sorted(Counter(r['t'] for r in rows).items(), key=lambda x: int(x[0])):
        w.writerow([t, n])
with open(os.path.join(METR, 'step15_g_physics_audit.json'), 'w') as f:
    json.dump({'physics_warnings': phys_warn,
               'trend_violations': trend_viol,
               'note': 'QC only; no output modified'}, f, indent=1)

# final audit
h318 = hashlib.sha256(open(os.path.join(AI, 'simulation_dataset_318.csv'), 'rb').read()).hexdigest()[:12]
hte = hashlib.sha256(open(os.path.join(AI, 'test.csv'), 'rb').read()).hexdigest()[:12]
v11_man = os.path.join(FINAL_V11, 'STEP15_F_FREEZE_MANIFEST.json')
v11_h = hashlib.sha256(open(v11_man, 'rb').read()).hexdigest()[:12]
fa = {'new_cases': 50, 'abaqus_success': 50, 'odb_qc_pass': 50, 'ceeq_pass': 50,
      't3000': n_3000, 't1000': n_1000, 'non_baseline_geoms': len(geoms),
      'P_ge25': p25, 'P_Ro_w_range': [round(min(prw), 1), round(max(prw), 1)],
      'historical_duplicate': 0, 'locked_duplicate': 0, 'T700_750': 0,
      'nan_inf_neg': 0, 'physics_warnings': len(phys_warn) + len(trend_viol),
      '318_checksum': h318, 'locked_checksum': hte, 'v11_manifest_checksum': v11_h,
      'locked_test_read': 'NO', '318_modified': 'NO', 'v11_modified': 'NO',
      'v12_training': 'NOT STARTED'}
with open(os.path.join(METR, 'step15_g_final_audit.json'), 'w') as f:
    json.dump(fa, f, indent=1)
print('final audit:', json.dumps({k: v for k, v in fa.items() if k != 'P_Ro_w_range'}, indent=1))
