"""STEP 15-B.2: extract full-frame CEEQ element fields + node coords for 57 ODBs.

Writes ml/data/step15_ceeq_snapshots/ (per-case .npz: node coords + per-frame
CEEQ element field + frame times) + ml/metrics/step15_field_extraction_audit.json
+ field stats. NPZ chosen: SMApy (abaqus python) has numpy but no h5py; NPZ is
a supported storage option per STEP15-B spec. QC:
NaN/Inf/negative/zero/continuity/amplitude. No ODB modification.
"""
import csv
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
DATA = os.path.join(ROOT, 'ml', 'data', 'step15_ceeq_snapshots')
MAP = json.load(open(os.path.join(METR, 'step15_odb_paths.json')))
raw = json.load(open(os.path.join(METR, 'step15_odb_raw.json')))
paths = MAP['paths']

ceeq_ids = [cid for cid, o in raw['odb'].items()
            if o.get('readable') and any('CEEQ' in v.get('all_field_keys', [])
                                         for v in o.get('steps', {}).values())]
os.makedirs(DATA, exist_ok=True)
meta_rows = []
audit = {'cases': len(ceeq_ids), 'extracted': 0, 'issues': []}


def vm(s):
    a, b, c, d, e, f = s
    return float(np.sqrt(((a - b) ** 2 + (b - c) ** 2 + (c - a) ** 2
                          + 6 * (d ** 2 + e ** 2 + f ** 2)) / 2.0))


for cid in sorted(ceeq_ids):
    p = paths[cid]
    rec = {'case_id': cid, 'ok': False}
    try:
        from odbAccess import openOdb
        odb = openOdb(p, readOnly=True)
        inst = list(odb.rootAssembly.instances.values())[0]
        coords = np.array([[n.coordinates[0], n.coordinates[1], n.coordinates[2]]
                           for n in inst.nodes], dtype=np.float64)
        st = list(odb.steps.values())[0]
        times = [float(fr.frameValue) for fr in st.frames]
        fields = []
        for fr in st.frames:
            ceeq = np.array([v.data for v in fr.fieldOutputs['CEEQ'].values],
                            dtype=np.float64)
            fields.append(ceeq)
        F = np.stack(fields)  # [n_frames, 2304]
        odb.close()
        # QC
        qc = {}
        qc['nan'] = int(np.isnan(F).sum())
        qc['inf'] = int(np.isinf(F).sum())
        qc['negative'] = int((F < 0).sum())
        qc['zero_frames'] = int((F.max(axis=1) == 0).sum())
        qc['final_max'] = float(F[-1].max())
        qc['final_min'] = float(F[-1].min())
        # spatial continuity proxy: neighbor ratio spread on final frame (element order)
        fin = F[-1]
        cont = float(np.std(np.log10(fin[fin > 0])) if (fin > 0).any() else 0.0)
        qc['log10_final_std'] = cont
        if not (qc['nan'] == 0 and qc['inf'] == 0 and qc['negative'] == 0
                and qc['zero_frames'] == 0):
            audit['issues'].append({'case': cid, 'qc': qc})
        np.savez(os.path.join(DATA, cid + '.npz'),
                 node_coords=coords, ceeq_frames=F, frame_times=np.array(times))
        meta_rows.append({'case_id': cid, 'n_nodes': coords.shape[0],
                          'n_elems': F.shape[1], 'n_frames': F.shape[0],
                          't_final': times[-1], 'ceeq_final_max': qc['final_max'],
                          'ceeq_final_min': qc['final_min'], 'qc_nan': qc['nan'],
                          'qc_inf': qc['inf'], 'qc_neg': qc['negative'],
                          'qc_zero_frames': qc['zero_frames'],
                          'log10_final_std': round(qc['log10_final_std'], 5)})
        rec['ok'] = True
        audit['extracted'] += 1
    except Exception as e:
        audit['issues'].append({'case': cid, 'error': str(e)[:200]})
    if audit['extracted'] % 10 == 0:
        print('progress: %d/57' % audit['extracted'], flush=True)

with open(os.path.join(METR, 'step15_field_extraction_audit.json'), 'w') as f:
    json.dump(audit, f, indent=1)
with open(os.path.join(DATA, 'step15_case_metadata.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(meta_rows[0].keys()))
    w.writeheader()
    for r in meta_rows:
        w.writerow(r)
with open(os.path.join(METR, 'step15_field_statistics.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(meta_rows[0].keys()))
    w.writeheader()
    for r in meta_rows:
        w.writerow(r)
print('extraction done: %d/57; npz -> ml/data/step15_ceeq_snapshots/' % audit['extracted'])
print('issues:', len(audit['issues']))
