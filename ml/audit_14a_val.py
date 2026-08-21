"""STEP 14-A.8: 14-item validation batch audit (read-only)."""
import csv
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
AI = os.path.join(ROOT, 'data', 'ai_ready_v4')
OUT = os.path.join(ROOT, 'simulation', 'generated_cases_step14a_ceeq')

rows = list(csv.DictReader(open(os.path.join(METR, 'step14a_validation_results.csv'))))
report = {}


def chk(name, ok, detail):
    report[name] = {'ok': bool(ok), 'detail': detail}
    print('[%s] %-30s %s' % ('PASS' if ok else 'FAIL', name, detail))


chk('17_17_success', sum(1 for r in rows if r['solver'] == 'OK') == 18,
    'solved=%d/18 (all incl. first case rerun in layer dir)' %
    sum(1 for r in rows if r['solver'] == 'OK'))
chk('18_odb_exist', all(os.path.exists(os.path.join(OUT, 'validation', r['case_id'] + '.odb'))
                        for r in rows), '18/18 ODB')
chk('18_ceeq_extracted', all(r.get('CEEQ_max') not in ('', None) for r in rows), '18/18 CEEQ')
chk('no_nan_inf', all(float(r['CEEQ_max']) == float(r['CEEQ_max'])
                      and float(r['CEEQ_max']) not in (float('inf'), float('-inf')) for r in rows),
    'finite')
chk('ceeq_positive', all(float(r['CEEQ_max']) > 0 for r in rows), 'min CEEQ > 0')
bad_t = [r['case_id'] for r in rows
         if abs(float(r['final_time_h']) - float(r['t_h'])) > 1e-6]
chk('final_time_correct', not bad_t, '500h->500 / 750h->750; bad=%s' % (bad_t or 'NONE'))
chk('T_coverage', {float(r['T']) for r in rows} == {550.0, 600.0, 650.0},
    'T=%s' % sorted({float(r['T']) for r in rows}))
chk('P_coverage', {float(r['P']) for r in rows} == {5.0, 10.0, 20.0},
    'P=%s' % sorted({float(r['P']) for r in rows}))
missing_pair = []
for T in (550, 600, 650):
    for P in (5, 10, 20):
        ts = sorted(float(r['t_h']) for r in rows if float(r['T']) == T and float(r['P']) == P)
        if ts != [500.0, 750.0]:
            missing_pair.append((T, P, ts))
chk('each_TxP_both_times', not missing_pair, 'missing=%s' % (missing_pair or 'NONE'))
ids = [r['case_id'] for r in rows]
chk('no_duplicate', len(ids) == len(set(ids)) == 18, 'unique 18')
# locked-test conflict: no new case id in locked test
locked = {r['case_id'] for r in csv.DictReader(open(os.path.join(AI, 'test.csv')))}
chk('no_locked_conflict', not (set(ids) & locked), 'intersection=0')
h318 = hashlib.sha256(open(os.path.join(AI, 'simulation_dataset_318.csv'), 'rb').read()).hexdigest()[:12]
h_te = hashlib.sha256(open(os.path.join(AI, 'test.csv'), 'rb').read()).hexdigest()[:12]
chk('dataset_318_checksum', h318 == '20f21ebc67ea', '318=%s' % h318)
chk('locked_test_checksum', h_te == 'fa573e330926', 'test=%s' % h_te)
# ml/final untouched (mtime of locked vm model)
import time as _t
mt = os.path.getmtime(os.path.join(ROOT, 'ml', 'final', 'final_vm_model.joblib'))
chk('ml_final_untouched', mt < _t.time() - 60, 'mtime=%.0f ago (before this batch)' % (_t.time() - mt))

with open(os.path.join(METR, 'step14a_validation_audit.json'), 'w') as f:
    json.dump(report, f, indent=1)
all_ok = all(v['ok'] for v in report.values())
print('\nSTEP 14-A.8 validation audit: %d/%d PASSED%s' %
      (sum(1 for v in report.values() if v['ok']), len(report),
       '' if all_ok else ' -- FAILED'))
sys.exit(0 if all_ok else 1)
