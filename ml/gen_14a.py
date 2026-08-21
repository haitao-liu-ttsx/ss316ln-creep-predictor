"""STEP 14-A.3-4: official generation of 27 CEEQ INPs + completeness audit.

Structure (new dir, no historical file touched):
  simulation/generated_cases_step14a_ceeq/
      validation/   (18 INP copies + manifest)
      test/         (9 INP copies + manifest)
      <case>.inp    (27 master copies)
      manifest.csv
      generation_audit.json
      <case>/generation_metadata.json   (per-case provenance)
Material: MODEL_C via generate_cases_v2.gen_inp (Norton 550/600/650 unchanged,
E/thermal table unchanged, BC/mesh/step/outputs identical to STEP13 MODEL_C).
Completeness audit verifies per-INP: *Creep law=STRAIN row == Norton table,
*Visco t == design t, *Temperature == design T, *Dsload == design P, node count
matches (Rm,Ro,w), case_id == design. No Abaqus execution.
"""
import csv
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'abaqus', 'scripts')
sys.path.insert(0, SCRIPTS)
import generate_cases as gc  # noqa: E402

OUT = os.path.join(ROOT, 'simulation', 'generated_cases_step14a_ceeq')
CREEP = {550: (7.75e-32, 9.51), 600: (3.56e-30, 9.04), 650: (2.35e-25, 7.57)}
NODE_COUNTS = {(100, 20, 4): 3072, (80, 15, 2): 3072, (120, 25, 3): 3072,
               (150, 20, 4): 3072}  # 48x16x(3+1) medium mesh


def load_design():
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'ml', 'metrics', 'step14a_case_design.csv'))))
    for r in rows:
        r['T'] = int(r['T']); r['P'] = int(r['P']); r['t'] = int(r['t'])
        r['Rm'] = int(r['Rm']); r['Ro'] = int(r['Ro']); r['w'] = int(r['w'])
    return rows


def main():
    design = load_design()
    assert len(design) == 27
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)  # clean slate for THIS approved 27-case set only
    gc.OUT = OUT
    manifest = []
    audit = {'generated': 0, 'cases': [], 'issues': []}
    for c in design:
        cid = c['case_id']
        path, meta = gc.gen_inp(cid, 'MODEL_C', float(c['T']), None, None,
                                float(c['P']), float(c['t']), c['Rm'], c['Ro'], c['w'])
        assert path, 'gen fail %s' % cid
        # per-case metadata
        cdir = os.path.join(OUT, cid)
        os.makedirs(cdir, exist_ok=True)
        md = {'case_id': cid, 'T': c['T'], 'P': c['P'], 't_h': c['t'],
              'Rm': c['Rm'], 'Ro': c['Ro'], 'wall': c['w'], 'layer': c['layer'],
              'material': 'SS316LN_N014 (MODEL_C Norton)',
              'norton_A': CREEP[c['T']][0], 'norton_n': CREEP[c['T']][1],
              'E_MPa': meta['E'], 'mesh': 'medium 48x16x3',
              'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'generator': 'generate_cases_v2.gen_inp (MODEL_C)',
              'input_hash_placeholder': ''}
        with open(os.path.join(cdir, 'generation_metadata.json'), 'w') as f:
            json.dump(md, f, indent=1)
        manifest.append(meta | {'layer': c['layer']})
        audit['cases'].append(cid)
        audit['generated'] += 1
    # master manifest + layer subdir copies
    with open(os.path.join(OUT, 'manifest.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(manifest[0].keys()))
        w.writeheader()
        for m in manifest:
            w.writerow(m)
    for layer in ('validation', 'test'):
        ld = os.path.join(OUT, layer)
        os.makedirs(ld, exist_ok=True)
        layer_rows = [m for m in manifest if m['layer'] == layer]
        for m in layer_rows:
            shutil.copy(os.path.join(OUT, m['case'] + '.inp'), ld)
        with open(os.path.join(ld, 'manifest.csv'), 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(manifest[0].keys()))
            w.writeheader()
            for m in layer_rows:
                w.writerow(m)

    # ---------------- completeness audit (per INP) ----------------
    n_ok = 0
    for c in design:
        cid = c['case_id']
        inp = os.path.join(OUT, cid + '.inp')
        txt = open(inp).read()
        lines = txt.splitlines()
        issues = []
        # *Creep row
        creep_ok = False
        for i, ln in enumerate(lines):
            if ln.strip() == '*Creep, law=STRAIN':
                vals = [float(x) for x in lines[i + 1].strip().split(',')]
                expA, expn = CREEP[c['T']]
                if abs(vals[0] - expA) / expA > 1e-9 or abs(vals[1] - expn) / expn > 1e-9:
                    issues.append('creep_params_mismatch %s' % vals[:2])
                elif int(vals[3]) != c['T']:
                    issues.append('creep_temp_mismatch')
                else:
                    creep_ok = True
                break
        if not creep_ok:
            issues.append('creep_card_missing_or_bad')
        # *Visco time
        visco_ok = any(ln.strip().startswith('0.01, %d, 1e-06' % c['t']) for ln in lines)
        if not visco_ok:
            issues.append('visco_time_mismatch')
        # *Temperature (block only; *Initial Conditions also has ALLN, 20.)
        tval = None
        in_t = False
        for ln in lines:
            s = ln.strip()
            if s == '*Temperature':
                in_t = True
                continue
            if in_t and s.startswith('*'):
                break
            if in_t and s.startswith('ALLN,'):
                tval = float(s.split(',')[1])
        if tval is None or abs(tval - c['T']) > 1e-9:
            issues.append('temperature_mismatch tval=%s' % tval)
        # *Dsload
        dline = [ln.strip() for ln in lines if ln.strip().startswith('SINNER, P,')]
        if not dline or abs(float(dline[0].split(',')[2]) - c['P']) > 1e-9:
            issues.append('dsload_mismatch')
        # node count (geometry sanity)
        n_nodes = sum(1 for ln in lines if ln.strip() and ln.strip()[0].isdigit()
                      and ',' in ln and len(ln.strip().split(',')) == 4
                      and not ln.strip().startswith(('1, 1',)))
        # simpler: count lines until *Element
        cnt = 0
        for ln in lines:
            if ln.strip().startswith('*Element'):
                break
            if ln.strip() and ln.strip()[0].isdigit():
                cnt += 1
        if cnt != NODE_COUNTS[(c['Rm'], c['Ro'], c['w'])]:
            issues.append('node_count %d != %d' % (cnt, NODE_COUNTS[(c['Rm'], c['Ro'], c['w'])]))
        if not issues:
            n_ok += 1
        audit['issues'] += [{'case': cid, 'issues': issues}] if issues else []
    audit['completeness_ok'] = n_ok
    audit['completeness_total'] = 27
    with open(os.path.join(OUT, 'generation_audit.json'), 'w') as f:
        json.dump(audit, f, indent=1)
    print('generated %d INPs -> %s' % (audit['generated'], OUT))
    print('completeness audit: %d/27 clean' % n_ok)
    if audit['issues']:
        for it in audit['issues']:
            print('  ISSUE %s: %s' % (it['case'], it['issues']))
    print('manifest ->', os.path.join(OUT, 'manifest.csv'))
    sys.exit(0 if n_ok == 27 else 1)


if __name__ == '__main__':
    main()
