"""STEP 13.6A: independent metric recomputation + displacement decomposition.

1. Recompute MAE/RMSE/R2 from saved per-case predictions (formula-level, no
   sklearn metric calls for the headline numbers): assert RMSE >= MAE for all
   normal regression results, compare against baseline_metrics.csv.
2. Displacement case-level decomposition: MODEL_B/C x elastic/plastic x
   PEEQ=0/>0 x T/P/Rm/wall/time bins -> n/MAE/RMSE/R2/median_AE/max_AE.
3. Extreme-displacement physical audit (test top-10 by displacement).
4. Physics-derived feature exploratory correlations (P/sy, Ro/wall, Rm/wall,
   sy/E, P*Ro/(wall*sy)) vs targets.
"""
import csv
import json
import math
import os
from collections import Counter

import numpy as np
import joblib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRED = os.path.join(ROOT, 'ml', 'predictions')
METRICS = os.path.join(ROOT, 'ml', 'metrics')
AI = os.path.join(ROOT, 'data', 'ai_ready_v3')


def mae(y, yp):
    return float(np.mean(np.abs(y - yp)))


def rmse(y, yp):
    return float(np.sqrt(np.mean((y - yp) ** 2)))


def r2(y, yp):
    sst = float(np.sum((y - np.mean(y)) ** 2))
    if sst == 0:
        return float('nan')
    return float(1 - np.sum((y - yp) ** 2) / sst)


def load_preds():
    out = {}
    for f in os.listdir(PRED):
        if not f.startswith('predictions_') or not f.endswith('.csv'):
            continue
        tag = f[len('predictions_'):-len('.csv')]
        rows = list(csv.DictReader(open(os.path.join(PRED, f))))
        out[tag] = rows
    return out


def main():
    lines = []
    preds = load_preds()
    # ---------------- 1. independent metric recomputation ----------------
    lines.append('=== 1. independent metric recomputation (from per-case predictions) ===')
    issues = []
    reported = {}
    for r in csv.DictReader(open(os.path.join(METRICS, 'baseline_metrics.csv'))):
        reported[(r['model'], r['target'], r['transform'], r['split'])] = r
    for tag, rows in sorted(preds.items()):
        mname, tname, trf = tag.split('_')[0], tag.split('_')[1], tag.split('_')[2]
        for s in ('train', 'validation', 'test'):
            rs = [r for r in rows if r['split'] == s]
            y = np.array([float(r['y_true']) for r in rs])
            yp = np.array([float(r['y_pred']) for r in rs])
            a, r_, r2v = mae(y, yp), rmse(y, yp), r2(y, yp)
            # assertion
            if r_ < a - 1e-9:
                issues.append((tag, s, 'RMSE<MAE', a, r_))
            # compare with reported
            key = (mname, tname, trf, s)
            if key in reported:
                rep = reported[key]
                if abs(a - float(rep['MAE'])) > 1e-3 * max(1, abs(a)) or \
                   abs(r_ - float(rep['RMSE'])) > 1e-3 * max(1, abs(r_)):
                    issues.append((tag, s, 'mismatch vs csv', a, float(rep['MAE'])))
    lines.append('prediction files: %d, (model,target,transform,split) combos: %d'
                 % (len(preds), len(reported)))
    lines.append('RMSE>=MAE violations: %d; csv-mismatch violations: %d' %
                 (sum(1 for i in issues if i[2] == 'RMSE<MAE'),
                  sum(1 for i in issues if i[2] != 'RMSE<MAE')))
    for i in issues[:10]:
        lines.append('  ISSUE %s' % (i,))
    # headline table (test, all 6 models, both raw targets)
    lines.append('\nrecomputed TEST metrics (MAE / RMSE / R2):')
    for tname in ('displacement', 'von_mises'):
        for mname in ('dummy', 'linear', 'ridge', 'rf', 'histgb', 'xgb'):
            tag = '%s_%s_raw' % (mname, tname)
            if tag not in preds:
                continue
            rs = [r for r in preds[tag] if r['split'] == 'test']
            y = np.array([float(r['y_true']) for r in rs])
            yp = np.array([float(r['y_pred']) for r in rs])
            lines.append('  %-10s %-14s MAE=%9.3f RMSE=%9.3f R2=%7.3f'
                         % (mname, tname, mae(y, yp), rmse(y, yp), r2(y, yp)))

    # ---------------- 2. displacement decomposition ----------------
    dataset = {r['case_id']: r for r in
               csv.DictReader(open(os.path.join(AI, 'simulation_dataset_300.csv')))}
    tag = 'linear_displacement_raw'
    rows = preds[tag]
    lines.append('\n=== 2. displacement decomposition (model=%s, test) ===' % tag)
    meta = {r['case_id']: dataset[r['case_id']] for r in rows if r['split'] == 'test'}

    def report_group(name, rs):
        if len(rs) < 2:
            lines.append('  %-38s n=%d (too few)' % (name, len(rs)))
            return
        y = np.array([float(r['y_true']) for r in rs])
        yp = np.array([float(r['y_pred']) for r in rs])
        ae = np.abs(y - yp)
        lines.append('  %-38s n=%3d MAE=%9.3f RMSE=%9.3f R2=%7.3f medAE=%7.3f maxAE=%8.2f'
                     % (name, len(rs), mae(y, yp), rmse(y, yp), r2(y, yp),
                        float(np.median(ae)), float(ae.max())))

    for dim, keyfn in (
            ('model', lambda r: 'MODEL_C' if meta[r['case_id']]['model_type'] == 'MODEL_C' else 'MODEL_B'),
            ('plasticity', lambda r: 'plastic(PEEQ>0)' if float(meta[r['case_id']]['max_PEEQ']) > 1e-6 else 'elastic(PEEQ=0)'),
            ('T', lambda r: 'T<=700' if float(meta[r['case_id']]['T_uniform'] or meta[r['case_id']]['T_inner'] or 0) <= 700 else 'T=750'),
            ('P', lambda r: 'P<=20' if float(meta[r['case_id']]['pressure']) <= 20 else ('P=25' if float(meta[r['case_id']]['pressure']) == 25 else 'P>=30')),
            ('Rm', lambda r: 'Rm<=120' if float(meta[r['case_id']]['R_major']) <= 120 else ('Rm=150' if float(meta[r['case_id']]['R_major']) == 150 else 'Rm=130/140')),
            ('wall', lambda r: 'w=2' if float(meta[r['case_id']]['wall_thickness']) == 2 else 'w>=3'),
            ('time', lambda r: 'MODEL_C t>=1000' if (meta[r['case_id']]['model_type'] == 'MODEL_C' and float(meta[r['case_id']]['time'] or 0) >= 1000) else ('MODEL_C t<=300' if meta[r['case_id']]['model_type'] == 'MODEL_C' else 'MODEL_B'))):
        lines.append('  -- by %s --' % dim)
        groups = {}
        for r in rows:
            if r['split'] != 'test':
                continue
            groups.setdefault(keyfn(r), []).append(r)
        for g, rs in sorted(groups.items()):
            report_group(g, rs)

    # ---------------- 3. extreme displacement audit ----------------
    lines.append('\n=== 3. extreme displacement physical audit (test top-10) ===')
    test_rows = [r for r in rows if r['split'] == 'test']
    test_rows.sort(key=lambda r: float(r['y_true']), reverse=True)
    lines.append('  %-30s %4s %5s %4s %5s %5s %8s %10s %9s %6s %7s' %
                 ('case_id', 'T', 'P', 'w', 'Rm', 'sy', 'E', 'vm', 'disp', 'PEEQ', 'model'))
    for r in test_rows[:10]:
        m = meta[r['case_id']]
        lines.append('  %-30s %4s %5s %4s %5s %5s %8s %10.3f %9.3f %6.2f %7s' % (
            r['case_id'], m['T_uniform'] or m['T_inner'], m['pressure'], m['wall_thickness'],
            m['R_major'], m['sigma_y_MPa'] or '-', m['E_GPa'],
            float(m['max_von_mises']), float(m['max_displacement']),
            float(m['max_PEEQ']), m['model_type']))
    n_p30 = sum(1 for r in test_rows[:10] if float(meta[r['case_id']]['pressure']) >= 30)
    n_thin = sum(1 for r in test_rows[:10] if float(meta[r['case_id']]['wall_thickness']) == 2)
    n_plast = sum(1 for r in test_rows[:10] if float(meta[r['case_id']]['max_PEEQ']) > 1e-6)
    n_sat = sum(1 for r in test_rows[:10]
                if float(meta[r['case_id']]['max_von_mises']) >=
                (float(meta[r['case_id']]['sigma_y_MPa']) * 0.98 if meta[r['case_id']]['sigma_y_MPa'] else 1e9))
    lines.append('  top-10: P>=30=%d, wall=2=%d, PEEQ>0=%d, vm>=0.98sy=%d' %
                 (n_p30, n_thin, n_plast, n_sat))

    # ---------------- 4. physics-derived features exploratory ----------------
    lines.append('\n=== 4. physics-derived features: Pearson r vs targets (all valid rows) ===')
    valid = [m for m in dataset.values() if m['valid_for_AI'] == 'YES']
    X = {k: [] for k in ['P_sy', 'Ro_w', 'Rm_w', 'sy_E', 'P_Ro_w_sy']}
    yv = {k: [] for k in ['max_displacement', 'max_von_mises', 'max_PEEQ']}
    for m in valid:
        P = float(m['pressure']); Ro = float(m['R_outer']); w = float(m['wall_thickness'])
        Rm = float(m['R_major']); sy = float(m['sigma_y_MPa']) if m['sigma_y_MPa'] else float('nan')
        E = float(m['E_GPa']) * 1000.0
        T = float(m['T_uniform'] or m['T_inner'] or 0)
        X['P_sy'].append(P / sy if sy == sy else float('nan'))
        X['Ro_w'].append(Ro / w)
        X['Rm_w'].append(Rm / w)
        X['sy_E'].append(sy / E if sy == sy else float('nan'))
        X['P_Ro_w_sy'].append(P * Ro / (w * sy) if sy == sy else float('nan'))
        for t in yv:
            yv[t].append(float(m[t]))
    for k, xs in X.items():
        xa = np.array(xs, float)
        for t in yv:
            ya = np.array(yv[t], float)
            mask = ~(np.isnan(xa) | np.isnan(ya))
            if mask.sum() < 10:
                continue
            xv, y2 = xa[mask], ya[mask]
            if xv.std() == 0:
                continue
            corr = float(np.corrcoef(xv, np.log1p(y2))[0, 1])
            lines.append('  %-14s vs %-18s r=%7.3f (n=%d, log1p(target))' % (k, t, corr, mask.sum()))

    with open(os.path.join(METRICS, 'audit_metrics_report.txt'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print('\nRMSE>=MAE violations: %d (must be 0)' % sum(1 for i in issues if i[2] == 'RMSE<MAE'))
    print('csv mismatch violations: %d (must be 0)' % sum(1 for i in issues if i[2] != 'RMSE<MAE'))


if __name__ == '__main__':
    main()
