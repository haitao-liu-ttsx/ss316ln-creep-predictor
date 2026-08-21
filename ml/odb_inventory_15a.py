"""STEP 15-A: batch ODB metadata extraction (Abaqus python).

For each of 318 ODBs: readable?, steps, frames, final frame time, frame time
series, node count, element count, instances, sets count, field keys per final
frame. Writes ml/metrics/step15_odb_raw.json (per-case dict).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = json.load(open(os.path.join(ROOT, 'ml', 'metrics', 'step15_odb_paths.json')))
paths = MAP['paths']

out = {}
n_ok = 0
n_fail = 0
for cid, p in sorted(paths.items()):
    rec = {'case_id': cid, 'odb_path': p, 'readable': False}
    try:
        from odbAccess import openOdb
        odb = openOdb(p, readOnly=True)
        rec['readable'] = True
        rec['instances'] = list(odb.rootAssembly.instances.keys())
        rec['node_count'] = sum(len(i.nodes) for i in odb.rootAssembly.instances.values())
        rec['element_count'] = sum(len(i.elements) for i in odb.rootAssembly.instances.values())
        nset = sum(len(v.nodeSets) for v in odb.rootAssembly.instances.values())
        eset = sum(len(v.elementSets) for v in odb.rootAssembly.instances.values())
        rec['node_sets'] = nset
        rec['element_sets'] = eset
        steps = {}
        for sname, st in odb.steps.items():
            frames = []
            for fr in st.frames:
                frames.append({'t': float(fr.frameValue),
                               'fields': sorted(fr.fieldOutputs.keys())})
            steps[sname] = {'frames_n': len(frames),
                            'final_time': frames[-1]['t'] if frames else None,
                            'time_series': [f['t'] for f in frames],
                            'field_keys_final': frames[-1]['fields'] if frames else [],
                            'all_field_keys': sorted({k for f in frames for k in f['fields']})}
        rec['steps'] = steps
        rec['final_frame_time'] = list(steps.values())[-1]['final_time'] if steps else None
        n_ok += 1
        odb.close()
    except Exception as e:
        rec['error'] = str(e)[:200]
        n_fail += 1
    out[cid] = rec
    if (n_ok + n_fail) % 50 == 0:
        print('progress: ok=%d fail=%d' % (n_ok, n_fail), flush=True)

with open(os.path.join(ROOT, 'ml', 'metrics', 'step15_odb_raw.json'), 'w') as f:
    json.dump({'n_ok': n_ok, 'n_fail': n_fail, 'odb': out}, f)
print('DONE: readable=%d fail=%d' % (n_ok, n_fail))
