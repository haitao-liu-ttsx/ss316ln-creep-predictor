"""STEP 15-C.2.1/2.2: model freeze manifest + EXT 27 manifest (target NOT read)."""
import csv
import hashlib
import json
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
FINAL = os.path.join(ROOT, 'ml', 'final', 'step15_v1')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


# ---------------- C.2.1 freeze manifest ----------------
frozen = json.load(open(os.path.join(FINAL, 'step15_v1_config.json')))
c1 = json.load(open(os.path.join(FINAL, 'step15_v1_model.json')))
train_ids = c1['train_ids']
c0 = json.load(open(os.path.join(METR, 'step15_c0_split_audit.json')))
val_ids = c0['validation']['ids']
ext18 = sorted({r['case_id'] for r in
                csv.DictReader(open(os.path.join(METR, 'step14a_validation_results.csv')))})
ext9 = sorted({r['case_id'] for r in
               csv.DictReader(open(os.path.join(METR, 'step14a_test_results.csv')))})
ext_ids = ext18 + ext9
locked_ids = sorted({r['case_id'] for r in csv.DictReader(open(os.path.join(AI, 'test.csv')))
                     if r['model_type'] == 'MODEL_C'})
manifest = {
    'model_version': 'step15-v1-POD3-XGB',
    'pod_domain': 'log10(CEEQ)', 'pod_k': 3,
    'checksums': {
        'pod_basis': sha(os.path.join(FINAL, 'pod_basis.npz')),
        'model_json': sha(os.path.join(FINAL, 'step15_v1_model.json')),
        'config_json': sha(os.path.join(FINAL, 'step15_v1_config.json'))},
    'features': ['T_hot', 'pressure', 'log1p_time', 'Rm', 'Ro', 'w', 'E', 'A_creep', 'n_creep'],
    'time_transform': 'log1p(time)',
    'scaler': 'StandardScaler (TRAIN-only fit, frozen)',
    'reconstruction': 'log_field = mean_log + sum(c_i * mode_i); CEEQ = 10**log_field',
    'positivity': 'exp10 reconstruction guarantees CEEQ >= 0',
    'train_case_ids': train_ids, 'validation_case_ids': val_ids,
    'ext_case_ids': ext_ids, 'locked_case_ids': locked_ids,
    'dataset_checksum': sha(os.path.join(AI, 'simulation_dataset_318.csv'))[:12],
    'locked_checksum': sha(os.path.join(AI, 'test.csv'))[:12],
    'freeze_timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'ext_target_status': 'NOT_READ',
}
with open(os.path.join(FINAL, 'STEP15_C2_FREEZE_MANIFEST.json'), 'w') as f:
    json.dump(manifest, f, indent=1)
print('FREEZE manifest written; ext_target_status = NOT_READ')
print('checksums:', {k: v[:12] for k, v in manifest['checksums'].items()})

# ---------------- C.2.2 EXT manifest ----------------
ext_rows = []
for cid in ext_ids:
    r = None
    for src in ('step14a_validation_results.csv', 'step14a_test_results.csv'):
        for rr in csv.DictReader(open(os.path.join(METR, src))):
            if rr['case_id'] == cid:
                r = rr
                break
        if r:
            break
    odb_p = None
    for d in (os.path.join(ROOT, 'simulation', 'generated_cases_step14a_ceeq', 'validation'),
              os.path.join(ROOT, 'simulation', 'generated_cases_step14a_ceeq', 'test')):
        p = os.path.join(d, cid + '.odb')
        if os.path.exists(p):
            odb_p = p
            break
    ext_rows.append({'case_id': cid, 'T': r['T'], 'P': r['P'], 't': r['t_h'],
                     'Rm': r['Rm'], 'Ro': r['Ro'], 'w': r['w'],
                     'geometry_group': '%s/%s/%s' % (r['Rm'], r['Ro'], r['w']),
                     'split': 'ext_val' if cid in ext18 else 'ext_test',
                     'odb_path': odb_p or '', 'target_status': 'NOT_READ'})
with open(os.path.join(METR, 'step15_c2_ext_manifest.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(ext_rows[0].keys()))
    w.writeheader()
    for r in ext_rows:
        w.writerow(r)
ids = [r['case_id'] for r in ext_rows]
overlap = set(ids) & (set(train_ids) | set(val_ids) | set(locked_ids))
print('EXT manifest: %d rows, unique=%s, overlap_with_train/val/locked=%s, odb_missing=%d'
      % (len(ext_rows), len(set(ids)) == 27, sorted(overlap),
         sum(1 for r in ext_rows if not r['odb_path'])))
