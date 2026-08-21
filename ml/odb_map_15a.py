"""STEP 15-A: map 318 case_ids to ODB paths (pure python, existence check only)."""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
CAND = {
    'v1_generated': os.path.join(ROOT, 'simulation', 'generated_cases'),
    'v2_generated': os.path.join(ROOT, 'simulation', 'generated_cases_v2'),
    'step13_8': os.path.join(ROOT, 'simulation', 'generated_cases_step13_8'),
    'step14a_val': os.path.join(ROOT, 'simulation', 'generated_cases_step14a_ceeq', 'validation'),
    'step14a_test': os.path.join(ROOT, 'simulation', 'generated_cases_step14a_ceeq', 'test'),
    'step14a_root': os.path.join(ROOT, 'simulation', 'generated_cases_step14a_ceeq'),
}
OLD_PATHS = {  # v1-era extra locations for B/LHS (STEP9 thermal dir also has some)
    os.path.join(ROOT, 'simulation', 'thermal_mechanical', 'cases'),
    os.path.join(ROOT, 'abaqus', 'input'),
}

rows = list(csv.DictReader(open(os.path.join(AI, 'simulation_dataset_318.csv'))))
out = []
missing = []
for r in rows:
    cid = r['case_id']
    found = None
    # CEEQ14A cases live in validation/test subdirs (also root has master copies)
    if cid.startswith('CEEQ14A'):
        for d in (CAND['step14a_val'], CAND['step14a_test'], CAND['step14a_root']):
            p = os.path.join(d, cid + '.odb')
            if os.path.exists(p):
                found = p
                break
    else:
        for d in (CAND['v1_generated'], CAND['v2_generated'], CAND['step13_8']):
            p = os.path.join(d, cid + '.odb')
            if os.path.exists(p):
                found = p
                break
        if found is None:
            for d in OLD_PATHS:
                p = os.path.join(d, cid + '.odb')
                if os.path.exists(p):
                    found = p
                    break
    out.append({'case_id': cid, 'odb_path': found or '', 'exists': bool(found)})
    if not found:
        missing.append(cid)
with open(os.path.join(ROOT, 'ml', 'metrics', 'step15_odb_paths.json'), 'w') as f:
    json.dump({'total': len(out), 'found': len(out) - len(missing),
               'missing': missing, 'paths': {o['case_id']: o['odb_path'] for o in out}}, f, indent=1)
print('318 ODB map: found=%d missing=%d' % (len(out) - len(missing), len(missing)))
print('missing cases: %s' % missing[:20])
