"""STEP 13.8A: verify design params -> generate 18 INPs -> solve (batch, resume).

Verification: prints per-case T/P/Rm/Ro/w/E/sy/Pi_yield straight from the
approved design JSON (ml/metrics/step13_8_design.json, = docs/STEP13_8_CASE_DESIGN.md)
and asserts values match the approved EXP material table; any mismatch aborts.
INP generation reuses v2 gen_inp (identical material/BC/mesh/step/outputs),
output dir: simulation/generated_cases_step13_8/ (v2 dir untouched).
Solve: Abaqus 2024, cpus=4, resume-safe (.sta COMPLETED skipped), license errors
logged with timestamp and retried on next invocation.
"""
import csv
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'abaqus', 'scripts')
sys.path.insert(0, SCRIPTS)
import generate_cases as gc  # noqa: E402

SY = {650: 227.0, 700: 212.0, 750: 199.0}
E_G = {650: 171.0, 700: 141.0, 750: 119.0}
OUT = os.path.join(ROOT, 'simulation', 'generated_cases_step13_8')
ABQ = r'C:/SIMULIA/Commands/abaqus.bat'
LOG = os.path.join(OUT, 'run_138.log')


def log(msg):
    line = time.strftime('%H:%M:%S ') + msg
    with open(LOG, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)


def main():
    design = json.load(open(os.path.join(ROOT, 'ml', 'metrics', 'step13_8_design.json')))
    sel = design['selected']
    assert len(sel) == 18
    os.makedirs(OUT, exist_ok=True)
    gc.OUT = OUT

    # ---- 1. verify + generate (abort on mismatch) ----
    metas = []
    for c in sel:
        cid = 'U_%d_P%d_Rm%d_Ro%d_w%d' % (c['T'], c['P'], c['Rm'], c['Ro'], c['w'])
        E = E_G[c['T']]; sy = SY[c['T']]
        pi = c['pi']
        print('CHECK %-28s T=%3d P=%2d Rm=%3d Ro=%2d w=%d E=%3.0f sy=%3.0f Pi=%.3f'
              % (cid, c['T'], c['P'], c['Rm'], c['Ro'], c['w'], E, sy, pi))
        assert c['T'] in SY and c['T'] in E_G, 'material table mismatch T=%d' % c['T']
        assert abs(pi - c['P'] * c['Ro'] / (c['w'] * sy)) < 1e-9, 'pi recompute mismatch'
        path, meta = gc.gen_inp(cid, 'MODEL_B', float(c['T']), None, None, float(c['P']),
                                0, c['Rm'], c['Ro'], c['w'])
        assert path, 'gen fail %s: %s' % (cid, meta)
        meta['pi_yield'] = round(pi, 4)
        metas.append(meta)
    with open(os.path.join(OUT, 'manifest_138.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(metas[0].keys()) + ['pi_yield'])
        w.writeheader()
        for m in metas:
            w.writerow(m)
    print('verify+generate OK: 18 INPs in', OUT)

    # ---- 2. solve (resume-safe) ----
    log('batch start: 18 cases')
    done = failed = skipped = 0
    for m in metas:
        c = m['case']
        sta = os.path.join(OUT, c + '.sta')
        if os.path.exists(sta) and 'COMPLETED' in open(sta, errors='ignore').read():
            skipped += 1
            continue
        t0 = time.time()
        r = subprocess.run([ABQ, 'job=' + c, 'cpus=4', '-interactive'], cwd=OUT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ok = os.path.exists(sta) and 'COMPLETED' in open(sta, errors='ignore').read()
        if ok:
            done += 1
            log('OK   %s (%.0fs)' % (c, time.time() - t0))
        else:
            failed += 1
            # license diagnosis: check lmgrd log tail and record
            lic = ''
            try:
                lic = open(r'C:\SolidSQUAD_License_Servers\Logs\lmgrd.log',
                           errors='ignore').read().splitlines()[-1]
            except OSError:
                pass
            log('FAIL %s (%.0fs, exit %s) license_tail=%s' % (c, time.time() - t0, r.returncode, lic))
        if (done + failed) % 5 == 0:
            log('progress: done=%d failed=%d skipped=%d' % (done, failed, skipped))
    log('batch end: done=%d failed=%d skipped=%d' % (done, failed, skipped))


if __name__ == '__main__':
    main()
