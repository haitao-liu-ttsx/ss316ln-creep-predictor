"""STEP 15-G.2: batch solve 50 new cases (resume-safe)."""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'simulation', 'generated_cases_step15g')
ABQ = r'C:/SIMULIA/Commands/abaqus.bat'

presolve = json.load(open(os.path.join(ROOT, 'ml', 'metrics', 'step15_g_presolve.json')))
ids = [c['case_id'] for c in presolve['cases']]
log_path = os.path.join(OUT, 'run_15g.log')


def log(msg):
    line = time.strftime('%H:%M:%S ') + msg
    with open(log_path, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)


def main():
    os.chdir(OUT)
    log('batch start: 50 cases')
    done = failed = skipped = 0
    for c in ids:
        sta = os.path.join(OUT, c + '.sta')
        if os.path.exists(sta) and 'COMPLETED' in open(sta, errors='ignore').read():
            skipped += 1
            continue
        t0 = time.time()
        r = subprocess.run([ABQ, 'job=' + c, 'cpus=4', '-interactive'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ok = os.path.exists(sta) and 'COMPLETED' in open(sta, errors='ignore').read()
        if ok:
            done += 1
            log('OK   %s (%.0fs)' % (c, time.time() - t0))
        else:
            failed += 1
            lic = ''
            try:
                lic = open(r'C:\SolidSQUAD_License_Servers\Logs\lmgrd.log',
                           errors='ignore').read().splitlines()[-1]
            except OSError:
                pass
            log('FAIL %s (%.0fs) license_tail=%s' % (c, time.time() - t0, lic))
        if (done + failed) % 10 == 0:
            log('progress: done=%d failed=%d skipped=%d' % (done, failed, skipped))
    log('batch end: done=%d failed=%d skipped=%d' % (done, failed, skipped))


if __name__ == '__main__':
    main()
