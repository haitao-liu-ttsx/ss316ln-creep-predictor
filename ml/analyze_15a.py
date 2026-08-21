"""STEP 15-A: synthesize inventory, completeness classes, coverage, mesh
unification feasibility, POD feasibility, gap analysis (pure python, no ODB)."""
import csv
import hashlib
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')

raw = json.load(open(os.path.join(METR, 'step15_odb_raw.json')))
odb = raw['odb']
rows = list(csv.DictReader(open(os.path.join(AI, 'simulation_dataset_318.csv'))))
meta = {r['case_id']: r for r in rows}
TARGET_FIELDS = ['CEEQ', 'S', 'E', 'EE', 'TEMP', 'NT11', 'U', 'RF']

inv = []
classes = Counter()
for r in rows:
    cid = r['case_id']
    o = odb.get(cid, {})
    rec = {'case_id': cid, 'odb_path': o.get('odb_path', ''),
           'odb_readable': o.get('readable', False),
           'T': r['T_uniform'] or r['T_inner'], 'P': r['pressure'],
           'time': r['time'], 'Rm': r['R_major'], 'Ro': r['R_outer'],
           'w': r['wall_thickness'],
           'node_count': o.get('node_count', ''), 'element_count': o.get('element_count', ''),
           'frame_count': '', 'final_frame_time': '',
           'field_keys': '', 'status': '', 'failure_reason': ''}
    if o.get('readable'):
        steps = o.get('steps', {})
        rec['frame_count'] = sum(v['frames_n'] for v in steps.values())
        rec['final_frame_time'] = o.get('final_frame_time', '')
        keys = []
        for v in steps.values():
            keys += v['all_field_keys']
        keys = sorted(set(keys))
        rec['field_keys'] = '|'.join(keys)
        for f in TARGET_FIELDS:
            rec['has_' + f] = f in keys
        n = int(rec['node_count']); e = int(rec['element_count'])
        rec['mesh_signature'] = 'n%d_e%d' % (n, e)
        rec['geometry_signature'] = '%s/%s/%s' % (rec['Rm'], rec['Ro'], rec['w'])
        rec['material_signature'] = r['material_id']
        # completeness class
        missing_targets = [f for f in ('CEEQ', 'S', 'EE', 'U') if not rec.get('has_' + f)]
        if not missing_targets:
            cls = 'A'
        else:
            cls = 'B'
        rec['status'] = cls
        classes[cls] += 1
    else:
        rec['status'] = 'C'
        rec['failure_reason'] = o.get('error', 'unreadable')
        classes['C'] += 1
    inv.append(rec)

with open(os.path.join(METR, 'step15_odb_inventory.csv'), 'w', newline='') as f:
    cols = list(inv[0].keys())
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for rec in inv:
        w.writerow(rec)
print('inventory written; classes:', dict(classes))

# ---------------- field inventory ----------------
field_inv = {'target_fields': TARGET_FIELDS, 'has_by_field': {}}
for f in TARGET_FIELDS:
    n_have = sum(1 for rec in inv if rec.get('has_' + f))
    field_inv['has_by_field'][f] = n_have
    print('has_%-6s: %d/318' % (f, n_have))
# class A only
field_inv['class_A_has_by_field'] = {f: sum(1 for rec in inv
                                            if rec['status'] == 'A' and rec.get('has_' + f))
                                     for f in TARGET_FIELDS}

# ---------------- mesh unification ----------------
mesh_counter = Counter(rec['mesh_signature'] for rec in inv if rec['odb_readable'])
print('mesh signatures:', dict(mesh_counter))
# node coordinate identity check (per geometry group) - compare first-case node coords
import numpy as np
# we do NOT re-read ODBs here; use mesh_signature + geometry + frame counts
geom_mesh = {}
for rec in inv:
    if rec['odb_readable']:
        geom_mesh.setdefault(rec['geometry_signature'], set()).add(rec['mesh_signature'])
print('geometry->mesh mapping:')
for g, ms in sorted(geom_mesh.items()):
    print('  geo %-14s meshes=%s' % (g, sorted(ms)))
frame_counter = Counter(rec['frame_count'] for rec in inv if rec['odb_readable'])
print('frame counts:', dict(frame_counter))

# ---------------- time coverage ----------------
time_cov = Counter()
for rec in inv:
    if rec['odb_readable']:
        time_cov[rec['time']] += 1
print('time layers:', dict(sorted(time_cov.items(), key=lambda x: float(x[0]))))
# time series uniformity (within creep cases)
ts_sets = Counter()
for cid, o in odb.items():
    if o.get('readable'):
        for st in o.get('steps', {}).values():
            ts_sets[tuple(round(t, 2) for t in st['time_series'])] += 1
            break  # single step TM
print('distinct time-series shapes:', len(ts_sets))
for ts, n in ts_sets.most_common(6):
    print('  n=%3d times=%s' % (n, list(ts)[:12]))

# ---------------- geometry coverage ----------------
geo_cov = Counter(rec['geometry_signature'] for rec in inv if rec['odb_readable'])
print('geometry coverage:', dict(geo_cov))
# per-geometry T/P/time coverage
geo_detail = {}
for rec in inv:
    g = rec['geometry_signature']
    d = geo_detail.setdefault(g, {'T': set(), 'P': set(), 't': set(), 'n': 0})
    d['T'].add(rec['T']); d['P'].add(rec['P']); d['t'].add(rec['time']); d['n'] += 1
geo_rows = []
for g, d in sorted(geo_detail.items()):
    geo_rows.append({'geometry': g, 'n': d['n'],
                     'T': sorted(d['T']), 'P': sorted(d['P'], key=float),
                     't': sorted(d['t'], key=float)})
    print('geo %-12s n=%-3d T=%s P=%s t=%s' % (g, d['n'], sorted(d['T']),
                                               sorted(d['P'], key=float),
                                               sorted(d['t'], key=float)))
with open(os.path.join(METR, 'step15_geometry_coverage.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['geometry', 'n', 'T', 'P', 't'])
    w.writeheader()
    for r in geo_rows:
        w.writerow(r)
with open(os.path.join(METR, 'step15_time_coverage.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['time_h', 'n_cases'])
    for t, n in sorted(time_cov.items(), key=lambda x: float(x[0])):
        w.writerow([t, n])

# ---------------- design space ----------------
ds = {}
for var, key in (('T', 'T_uniform'), ('P', 'pressure'), ('t', 'time'), ('Rm', 'R_major'),
                 ('Ro', 'R_outer'), ('w', 'wall_thickness')):
    vals = sorted({float(r[key]) for r in rows if r[key] not in ('', 'nan')}, key=float)
    ds[var] = {'min': min(vals), 'max': max(vals), 'unique': vals}
print('design space:', json.dumps(ds, indent=0))
with open(os.path.join(METR, 'step15_design_space.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['variable', 'min', 'max', 'unique_values'])
    for var, d in ds.items():
        w.writerow([var, d['min'], d['max'], d['unique']])

# ---------------- gap: creep-capable (has CEEQ) coverage ---------------
creep_cases = [rec for rec in inv if rec.get('has_CEEQ')]
print('cases with CEEQ field: %d' % len(creep_cases))
for T in (550, 600, 650, 700, 750):
    ts = sorted({rec['time'] for rec in creep_cases if rec['T'] == str(T)}, key=float)
    print('  T=%s times=%s' % (T, ts))

# ---------------- checksums ----------------
h318 = hashlib.sha256(open(os.path.join(AI, 'simulation_dataset_318.csv'), 'rb').read()).hexdigest()[:12]
hte = hashlib.sha256(open(os.path.join(AI, 'test.csv'), 'rb').read()).hexdigest()[:12]
print('checksums: 318=%s locked_test=%s' % (h318, hte))

geo_json = {g: {'n': d['n'], 'T': sorted(d['T']), 'P': sorted(d['P'], key=float),
                't': sorted(d['t'], key=float)} for g, d in geo_detail.items()}
json.dump({'classes': dict(classes), 'field_inv': field_inv,
           'mesh_counter': dict(mesh_counter), 'frame_counter': dict(frame_counter),
           'time_layers': dict(time_cov), 'geometry': geo_json,
           'design_space': ds, 'checksums': {'318': h318, 'locked_test': hte},
           'creep_case_count': len(creep_cases)},
          open(os.path.join(METR, 'step15_field_inventory.json'), 'w'), indent=1)
print('field_inventory.json written')
