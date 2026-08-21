"""STEP 13.8A: postprocess 18 ODBs (Abaqus python) + transition/coverage analysis.

Run via abaqus.bat python (odbAccess). Extracts T_max/HFL/vm/U/PEEQ/EE/CEEQ
(same metrics as v1/v3), writes ml/metrics/step13_8a_results.csv, then a
combined analysis vs the 300-row dataset (Pi_yield bins, elastic/plastic
separation, transition region, joint coverage plots).
"""
import math
import os
import sys
import csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'simulation', 'generated_cases_step13_8')
METR = os.path.join(ROOT, 'ml', 'metrics')
FIG = os.path.join(ROOT, 'ml', 'figures', 'step13_8a')


def vm(s):
    a, b, c, d, e, f = s
    return math.sqrt(((a - b) ** 2 + (b - c) ** 2 + (c - a) ** 2
                      + 6 * (d ** 2 + e ** 2 + f ** 2)) / 2.0)


def extract(case):
    from odbAccess import openOdb
    odb = openOdb(os.path.join(OUT, case + '.odb'), readOnly=True)
    st = list(odb.steps.values())[-1]
    fr = st.frames[-1]
    NT = fr.fieldOutputs['NT11']
    ts = [v.data for v in NT.values]
    hf = 0.0
    if 'HFL' in fr.fieldOutputs:
        hf = max(math.hypot(v.data[0], v.data[1], v.data[2])
                 for v in fr.fieldOutputs['HFL'].values)
    vms = [vm(v.data) for v in fr.fieldOutputs['S'].values]
    U = fr.fieldOutputs['U']
    umax = max(math.hypot(v.data[0], v.data[1], v.data[2]) for v in U.values)
    peeq = ee = ceeq = 0.0
    if 'PEEQ' in fr.fieldOutputs:
        peeq = max(v.data for v in fr.fieldOutputs['PEEQ'].values)
    if 'EE' in fr.fieldOutputs:
        ee = max(max(v.data) for v in fr.fieldOutputs['EE'].values)
    if 'CEEQ' in fr.fieldOutputs:
        ceeq = max(v.data for v in fr.fieldOutputs['CEEQ'].values)
    odb.close()
    return {'T_max': max(ts), 'HFL_max': hf, 'vm_max': max(vms),
            'U_max': umax, 'PEEQ_max': peeq, 'EE_max': ee, 'CEEQ_max': ceeq}


def main():
    os.makedirs(METR, exist_ok=True)
    import json
    SY = {650: 227.0, 700: 212.0, 750: 199.0}
    EG = {650: 171.0, 700: 141.0, 750: 119.0}
    design = json.load(open(os.path.join(ROOT, 'ml', 'metrics', 'step13_8_design.json')))
    sel = {('U_%d_P%d_Rm%d_Ro%d_w%d' % (c['T'], c['P'], c['Rm'], c['Ro'], c['w'])): c
           for c in design['selected']}
    for c in sel.values():
        c['E'] = EG[c['T']]
        c['sy'] = SY[c['T']]
    rows = []
    for cid, c in sorted(sel.items()):
        sta = os.path.join(OUT, cid + '.sta')
        ok = os.path.exists(sta) and 'COMPLETED' in open(sta, errors='ignore').read()
        r = extract(cid) if ok else {}
        rows.append({'case_id': cid, 'T': c['T'], 'P': c['P'], 'Rm': c['Rm'],
                     'Ro': c['Ro'], 'wall': c['w'], 'E_GPa': c.get('E', ''),
                     'sigma_y': c.get('sy', ''), 'pi_yield': round(c['pi'], 4),
                     'solver': 'OK' if ok else 'FAIL',
                     'vm_max': round(r.get('vm_max', ''), 3) if r else '',
                     'U_max': round(r.get('U_max', ''), 5) if r else '',
                     'PEEQ_max': round(r.get('PEEQ_max', ''), 6) if r else '',
                     'EE_max': r.get('EE_max', '') if r else '',
                     'CEEQ_max': r.get('CEEQ_max', '') if r else '',
                     'T_max': r.get('T_max', '') if r else ''})
    with open(os.path.join(METR, 'step13_8a_results.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print('step13_8a_results.csv: %d rows' % len(rows))
    for r in rows:
        print('  %-28s Pi=%.3f vm=%s PEEQ=%s U=%s' %
              (r['case_id'], r['pi_yield'], r['vm_max'], r['PEEQ_max'], r['U_max']))


if __name__ == '__main__':
    main()
