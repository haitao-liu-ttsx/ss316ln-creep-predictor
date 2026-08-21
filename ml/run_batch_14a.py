"""STEP 14-A.8/9: batch solve CEEQ cases (resume-safe, per-layer manifest).
Usage: python run_batch_14a.py validation|test [--all]
Solves only the given layer's cases (validation=18 incl. 1 done, test=9).
Keeps .inp/.odb/.sta/.msg/.dat; logs to run_14a_<layer>.log.
"""
import csv
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'simulation', 'generated_cases_step14a_ceeq')
ABQ = r'C:/SIMULIA/Commands/abaqus.bat'

layer = sys.argv[1] if len(sys.argv) > 1 else 'validation'
log_path = os.path.join(OUT, 'run_14a_%s.log' % layer)


def log(msg):
    line = time.strftime('%H:%M:%S ') + msg
    with open(log_path, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)


def main():
    rows = list(csv.DictReader(open(os.path.join(OUT, layer, 'manifest.csv'))))
    if os.path.isdir(os.path.join(OUT, layer)):
        os.chdir(os.path.join(OUT, layer))
    log('%s batch start: %d cases' % (layer, len(rows)))
    done = failed = skipped = 0
    for m in rows:
        c = m['case']
        sta = os.path.join(os.getcwd(), c + '.sta')
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
            log('FAIL %s (%.0fs, exit %s) license_tail=%s' % (c, time.time() - t0,
                                                               r.returncode, lic))
        if (done + failed) % 5 == 0:
            log('progress: done=%d failed=%d skipped=%d' % (done, failed, skipped))
    log('%s batch end: done=%d failed=%d skipped=%d' % (layer, done, failed, skipped))


if __name__ == '__main__':
    main()
