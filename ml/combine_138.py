"""STEP 13.8A: transition analysis + joint coverage (18 new + 300 historical).

- Pi_yield bins (0.7-0.8/0.8-0.9/0.9-1.0/1.0-1.1/1.1-1.2/1.2-1.5): n, PEEQ>0,
  PEEQ=0, max PEEQ, max U, max vm (18-case subset + 300-row joint).
- Sanity: vm vs P*Ro/w elastic trend; vm vs sigma_y saturation.
- Quality grading per v1 rules (uniform T>=650 -> A if solver OK).
- Joint coverage plots: Pi_yield vs PEEQ/displacement/vm/T/P.
"""
import csv
import json
import os

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METR = os.path.join(ROOT, 'ml', 'metrics')
FIG = os.path.join(ROOT, 'ml', 'figures', 'step13_8a')
AI = os.path.join(ROOT, 'data', 'ai_ready_v3')

plt.rcParams.update({'font.size': 9, 'figure.dpi': 130})
os.makedirs(FIG, exist_ok=True)

BINS = [(0.7, 0.8), (0.8, 0.9), (0.9, 1.0), (1.0, 1.1), (1.1, 1.2), (1.2, 1.5)]


def load_18():
    rows = list(csv.DictReader(open(os.path.join(METR, 'step13_8a_results.csv'))))
    for r in rows:
        for k in ('T', 'P', 'Rm', 'Ro', 'wall', 'pi_yield', 'vm_max', 'U_max', 'PEEQ_max'):
            r[k] = float(r[k]) if r[k] not in ('', 'None') else 0.0
    return rows


def load_300():
    rows = list(csv.DictReader(open(os.path.join(AI, 'simulation_dataset_300.csv'))))
    out = []
    for r in rows:
        if r['model_type'] != 'MODEL_B' or r['T_uniform'] in ('', 'nan'):
            continue
        sy = float(r['sigma_y_MPa']) if r['sigma_y_MPa'] not in ('', 'nan') else None
        if sy is None:
            continue
        pi = float(r['pressure']) * float(r['R_outer']) / (
            float(r['wall_thickness']) * sy)
        out.append({'case_id': r['case_id'], 'T': float(r['T_uniform']),
                    'P': float(r['pressure']), 'Rm': float(r['R_major']),
                    'Ro': float(r['R_outer']), 'w': float(r['wall_thickness']),
                    'pi': pi, 'vm': float(r['max_von_mises']),
                    'U': float(r['max_displacement']),
                    'PEEQ': float(r['max_PEEQ']),
                    'valid': r['valid_for_AI']})
    return out


def bin_table(rows, label):
    print('=== %s: Pi_yield bins ===' % label)
    print('  %-8s %4s %8s %8s %10s %10s %10s' %
          ('bin', 'n', 'PEEQ>0', 'PEEQ=0', 'maxPEEQ', 'maxU', 'maxvm'))
    for lo, hi in BINS:
        sel = [r for r in rows if lo <= float(r.get('pi', r.get('pi_yield', 0))) < hi]
        if not sel:
            print('  %-8s n=0' % ('%.1f-%.1f' % (lo, hi)))
            continue
        n_pl = sum(1 for r in sel if float(r.get('PEEQ', r.get('PEEQ_max', 0))) > 1e-6)
        print('  %-8s %4d %8d %8d %10.4g %10.4g %10.2f' % (
            '%.1f-%.1f' % (lo, hi), len(sel), n_pl, len(sel) - n_pl,
            max(float(r.get('PEEQ', r.get('PEEQ_max', 0))) for r in sel),
            max(float(r.get('U', r.get('U_max', 0))) for r in sel),
            max(float(r.get('vm', r.get('vm_max', 0))) for r in sel)))


def main():
    r18 = load_18()
    r300 = load_300()
    # sanity: elastic trend vm ~ P*Ro/w and saturation at sy
    print('=== sanity: vm vs P*Ro/w (18 cases) ===')
    for r in sorted(r18, key=lambda r: r['pi_yield']):
        prw = r['P'] * r['Ro'] / r['wall']
        sy = {'650': 227.0, '700': 212.0, '750': 199.0}[str(int(r['T']))]
        sat = 'SAT' if r['vm_max'] >= 0.98 * sy else ('near' if r['vm_max'] >= 0.9 * sy else 'elas')
        print('  %-28s Pi=%.3f vm=%7.2f P*Ro/w=%6.1f sy=%3.0f %s' %
              (r['case_id'], r['pi_yield'], r['vm_max'], prw, sy, sat))
    # transition bins (18 only)
    bin_table(r18, '18 new cases')
    # joint bins (18 + 300 valid MODEL_B uniform with sy)
    joint = [dict(r, pi=r['pi'], vm=r['vm'], U=r['U'], PEEQ=r['PEEQ']) for r in r300]
    for r in r18:
        joint.append({'case_id': r['case_id'], 'T': r['T'], 'P': r['P'],
                      'Rm': r['Rm'], 'Ro': r['Ro'], 'w': r['wall'],
                      'pi': r['pi_yield'], 'vm': r['vm_max'],
                      'U': r['U_max'], 'PEEQ': r['PEEQ_max'], 'valid': 'NEW'})
    joint = [dict(r, P=float(r['P']), Ro=float(r['Ro']), w=float(r['w']),
                  T=float(r['T']), pi=float(r['pi']), vm=float(r['vm']),
                  U=float(r['U']), PEEQ=float(r['PEEQ'])) for r in joint]
    bin_table(joint, 'joint (300 historical + 18 new)')
    # quality grading (v1 rules: uniform T>=650, solver OK -> A)
    print('=== quality grade (v1 rules) ===')
    grades = {}
    for r in r18:
        g = 'A' if r['solver'] == 'OK' else 'D'
        grades[r['case_id']] = g
        print('  %-28s solver=%s grade=%s' % (r['case_id'], r['solver'], g))
    # plots
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, (key, yl, nm) in zip(axes, (('PEEQ', 'max_PEEQ', 'peeq'),
                                        ('U', 'max_displacement (mm)', 'disp'),
                                        ('vm', 'max_von Mises (MPa)', 'vm'))):
        ax.scatter([r['pi'] for r in joint], [r[key] for r in joint], s=8, alpha=0.6)
        ax.axvline(1.0, color='r', ls='--', lw=0.8)
        ax.set_xlabel('Pi_yield'); ax.set_ylabel(yl)
        ax.set_title('Pi_yield vs %s (joint 318)' % nm)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'joint_pi_physics.png')); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    for ax, (key, yl, nm) in zip(axes, (('T', 'T (C)', 'T'), ('P', 'P (MPa)', 'P'))):
        ax.scatter([r['pi'] for r in joint], [r[key] for r in joint], s=8, alpha=0.6)
        ax.axvline(1.0, color='r', ls='--', lw=0.8)
        ax.set_xlabel('Pi_yield'); ax.set_ylabel(yl)
        ax.set_title('Pi_yield vs %s (joint 318)' % nm)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'joint_pi_tp.png')); plt.close(fig)
    print('plots ->', FIG)


if __name__ == '__main__':
    main()
