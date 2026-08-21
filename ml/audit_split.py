"""STEP 13.5: full split audit after Problem-A fix (7 checks). Read-only."""
import csv
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI = os.path.join(ROOT, 'data', 'ai_ready_v3')
sys.path.insert(0, os.path.join(ROOT, 'postprocess'))
import coverage_split_v3 as cs


def load(p):
    return list(csv.DictReader(open(p, encoding='utf-8-sig')))


tr, va, te = load(os.path.join(AI, 'train.csv')), load(os.path.join(AI, 'validation.csv')), load(os.path.join(AI, 'test.csv'))
allrows = load(os.path.join(AI, 'simulation_dataset_300.csv'))
print('1) v1 150-case classification change:')
old = {}
for f, s in (('train', 'train'), ('validation', 'validation'), ('test', 'test')):
    for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'ai_ready', f + '.csv'))):
        old[r['case_id']] = s
v1valid = {r['case_id'] for r in allrows if r['valid_for_AI'] == 'YES' and cs.is_v1_case(r['case_id'])}
changed = []
for cid in v1valid:
    r = next(r for r in allrows if r['case_id'] == cid)
    s = cs.hard_rule_override(r, cs.classify(r))
    if s != old[cid]:
        changed.append((cid, old[cid], s))
print('   v1 valid cases=%d, changed=%d %s' % (len(v1valid), len(changed), changed[:5]))

print('2) new split sizes: train=%d validation=%d test=%d (sum=%d, valid=%d)'
      % (len(tr), len(va), len(te), len(tr) + len(va) + len(te), len(v1valid) + 74))

print('3) Rm=150 placement:')
for name, rows in (('train', tr), ('validation', va), ('test', te)):
    rm150 = [r['case_id'] for r in rows if float(r['R_major']) == 150.0]
    print('   %-10s Rm150=%d %s' % (name, len(rm150), sorted(rm150)))

print('4) extrapolation ladders:')
def temp(r):
    return r['T_uniform'] or r['T_inner']
for name, rows in (('train', tr), ('validation', va), ('test', te)):
    T = sorted(set(int(float(temp(r))) for r in rows))
    P = sorted(set(int(float(r['pressure'])) for r in rows))
    Rm = sorted(set(int(float(r['R_major'])) for r in rows))
    t = sorted(set(int(float(r['time'] or 0)) for r in rows))
    print('   %-10s T=%s P=%s Rm=%s t=%s' % (name, T, P, Rm, t))

print('5) train/test same-key combos after fix:')
def key4(r):
    return (r['T_uniform'], r['Delta_T'], r['pressure'], r['R_major'])
trk = {key4(r) for r in tr}
tek = {key4(r) for r in te}
ov = sorted(trk & tek)
print('   overlap combos=%d' % len(ov))
for k in ov:
    trc = [r['case_id'] for r in tr if key4(r) == k]
    tec = [r['case_id'] for r in te if key4(r) == k]
    print('   %s | train:%s | test:%s' % (k, trc[:3], tec[:3]))

print('6) anomalies:')
ids = set()
for name, rows in (('train', tr), ('validation', va), ('test', te)):
    dups = [c for c in set(r['case_id'] for r in rows) if sum(1 for r in rows if r['case_id'] == c) > 1]
    if dups:
        print('   %s internal dup: %s' % (name, dups))
    ids.update(r['case_id'] for r in rows)
print('   cross-set overlap: %d (must be 0)' % (len(tr) + len(va) + len(te) - len(ids)))
print('   valid total consistency: %d' % (len(tr) + len(va) + len(te)))

print('7) v1 case split preservation vs v1 files:')
for f, s in (('train', 'train'), ('validation', 'validation'), ('test', 'test')):
    v1c = {r['case_id'] for r in load(os.path.join(ROOT, 'data', 'ai_ready', f + '.csv'))}
    v3c = {r['case_id'] for r in load(os.path.join(AI, f + '.csv')) if cs.is_v1_case(r['case_id'])}
    diff = v1c ^ v3c
    print('   v1 %s: old=%d new=%d diff=%s' % (s, len(v1c), len(v3c), sorted(diff)[:6]))
print('   MODEL_C in validation: %d (structure note: was 0 before fix)' %
      sum(1 for r in va if r['model_type'] == 'MODEL_C'))
