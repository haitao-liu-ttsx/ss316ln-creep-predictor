"""STEP 14-A.8/9: extract CEEQ for all solved cases in a layer (Abaqus python).

STEP13-identical extraction: final frame, element-field CEEQ max/mean/min,
log10(max) on nonzero domain, no epsilon. Also vm_max/U_max/T for sanity.
Usage: abaqus python extract_14a.py validation|test [--all]
Writes ml/metrics/step14a_<layer>_results.csv.
"""
import csv
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'simulation', 'generated_cases_step14a_ceeq')
METR = os.path.join(ROOT, 'ml', 'metrics')

layer = sys.argv[1] if len(sys.argv) > 1 else 'validation'
L = os.path.join(OUT, layer)


def vm(s):
    a, b, c, d, e, f = s
    return math.sqrt(((a - b) ** 2 + (b - c) ** 2 + (c - a) ** 2
                      + 6 * (d ** 2 + e ** 2 + f ** 2)) / 2.0)


def main():
    from odbAccess import openOdb
    metas = {r['case']: r for r in
             csv.DictReader(open(os.path.join(L, 'manifest.csv')))}
    rows = []
    for cid, m in sorted(metas.items()):
        sta = os.path.join(L, cid + '.sta')
        ok = os.path.exists(sta) and 'COMPLETED' in open(sta, errors='ignore').read()
        row = {'case_id': cid, 'T': m['T_uniform'], 'P': m['P'], 't_h': m['t_h'],
               'Rm': m['R_major'], 'Ro': m['R_outer'], 'w': m['wall'],
               'solver': 'OK' if ok else 'FAIL/PD'}
        if ok:
            odb = openOdb(os.path.join(L, cid + '.odb'), readOnly=True)
            fr = list(odb.steps.values())[-1].frames[-1]
            row['final_time_h'] = float(fr.frameValue)
            S = fr.fieldOutputs['S']
            vms = [vm(v.data) for v in S.values]
            row['vm_max'] = round(float(max(vms)), 3)
            U = fr.fieldOutputs['U']
            row['U_max'] = round(float(max(math.hypot(v.data[0], v.data[1], v.data[2])
                                           for v in U.values)), 6)
            ceeq = [float(v.data) for v in fr.fieldOutputs['CEEQ'].values]
            row['CEEQ_max'] = max(ceeq)
            row['CEEQ_mean'] = sum(ceeq) / len(ceeq)
            row['CEEQ_min'] = min(ceeq)
            row['log10_CEEQ'] = math.log10(max(ceeq)) if max(ceeq) > 0 else None
            row['n_elements'] = len(ceeq)
            odb.close()
        rows.append(row)
    out = os.path.join(METR, 'step14a_%s_results.csv' % layer)
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    n_ok = sum(1 for r in rows if r['solver'] == 'OK')
    print('%s: %d rows, %d solved -> %s' % (layer, len(rows), n_ok, out))
    for r in rows:
        print('  %-36s t=%s CEEQ=%s log10=%s' %
              (r['case_id'], r['t_h'], r.get('CEEQ_max'), r.get('log10_CEEQ')))


if __name__ == '__main__':
    main()
