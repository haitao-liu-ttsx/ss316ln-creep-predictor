"""STEP 15-C.2.4: FIRST read of EXT target - extract final-frame CEEQ element
fields from 27 STEP14-A ODBs (Abaqus python). Writes ext_true_fields.npz.
"""
import csv
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
OUT = os.path.join(ROOT, 'simulation', 'generated_cases_step14a_ceeq')

ext = list(csv.DictReader(open(os.path.join(METR, 'step15_c2_ext_manifest.csv'))))
fields, ids = [], []
for r in ext:
    cid = r['case_id']
    layer = 'validation' if r['split'] == 'ext_val' else 'test'
    odb_p = os.path.join(OUT, layer, cid + '.odb')
    from odbAccess import openOdb
    odb = openOdb(odb_p, readOnly=True)
    fr = list(odb.steps.values())[-1].frames[-1]
    f = np.array([v.data for v in fr.fieldOutputs['CEEQ'].values], dtype=np.float64)
    odb.close()
    fields.append(f)
    ids.append(cid)
F = np.array(fields)
np.savez(os.path.join(METR, 'step15_c2_ext_true_fields.npz'),
         case_ids=np.array(ids), fields=F)
print('EXT target FIRST READ: %d cases, field shape %s' % (len(ids), F.shape))
print('true field range: %.3e .. %.3e' % (F.min(), F.max()))
