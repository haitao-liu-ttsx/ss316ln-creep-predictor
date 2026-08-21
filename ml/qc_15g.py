"""STEP 15-G.2: ODB QC + CEEQ field extraction for 50 new cases (Abaqus python).
Same field definition as STEP15-B: element centroid CEEQ, 2304 dims, final frame.
"""
import csv
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'simulation', 'generated_cases_step15g')
METR = os.path.join(ROOT, 'ml', 'metrics')
DATA = os.path.join(ROOT, 'ml', 'data', 'step15g_snapshots')
os.makedirs(DATA, exist_ok=True)

presolve = json.load(open(os.path.join(METR, 'step15_g_presolve.json')))
rows = []
ok_odb = ok_ceeq = 0
topology_ok = True
for c in presolve['cases']:
    cid = c['case_id']
    sta = os.path.join(OUT, cid + '.sta')
    solved = os.path.exists(sta) and 'COMPLETED' in open(sta, errors='ignore').read()
    rec = dict(c)
    rec['solver'] = 'OK' if solved else 'FAIL'
    if not solved:
        rows.append(rec)
        continue
    from odbAccess import openOdb
    odb = openOdb(os.path.join(OUT, cid + '.odb'), readOnly=True)
    fr = list(odb.steps.values())[-1].frames[-1]
    inst = list(odb.rootAssembly.instances.values())[0]
    n_nodes = len(inst.nodes)
    n_elems = len(inst.elements)
    if n_nodes != 3072 or n_elems != 2304:
        topology_ok = False
    f = np.array([v.data for v in fr.fieldOutputs['CEEQ'].values], dtype=np.float64)
    rec['final_time'] = float(fr.frameValue)
    rec['node_count'] = n_nodes
    rec['elem_count'] = n_elems
    rec['CEEQ_max'] = float(f.max())
    rec['CEEQ_min'] = float(f.min())
    rec['CEEQ_mean'] = float(f.mean())
    rec['CEEQ_nan'] = int(np.isnan(f).sum())
    rec['CEEQ_inf'] = int(np.isinf(f).sum())
    rec['CEEQ_neg'] = int((f < 0).sum())
    rec['CEEQ_zero'] = int((f == 0).sum())
    rec['hotspot_elem'] = int(np.argmax(f))
    odb.close()
    np.savez(os.path.join(DATA, cid + '.npz'), ceeq_field=f)
    ok_odb += 1
    ok_ceeq += 1 if rec['CEEQ_nan'] == 0 and rec['CEEQ_inf'] == 0 and rec['CEEQ_neg'] == 0 else 0
    rows.append(rec)

with open(os.path.join(METR, 'step15_g_odb_qc.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow(r)
with open(os.path.join(METR, 'step15_g_field_statistics.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow(r)
print('ODB readable: %d/50, CEEQ clean: %d/50, topology 3072/2304: %s' %
      (ok_odb, ok_ceeq, topology_ok))
for r in rows[:6]:
    print('  %s t=%s CEEQ max=%.3e min=%.3e' % (r['case_id'], r['t'], r['CEEQ_max'], r['CEEQ_min']))
