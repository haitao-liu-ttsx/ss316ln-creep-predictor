"""STEP 13.7: SHAP (physics sanity), Pi_yield physical plots, CEEQ exploratory.

- SHAP for von Mises final XGB (base features) and unified displacement XGB
  (all features): mean |SHAP| ranking; compare vs physics intuition.
- Pi_yield vs PEEQ / displacement / von Mises scatter (test+train).
- CEEQ exploratory: nonzero distribution, MODEL_C, time, A/n, stress level.
Figures -> ml/figures/step13_7/. No data modification.
"""
import csv
import json
import os

import numpy as np
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import shap
import xgboost as xgb

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F137 = os.path.join(ROOT, 'ml', 'features', 'step13_7')
MDIR = os.path.join(ROOT, 'ml', 'models', 'step13_7')
FIG = os.path.join(ROOT, 'ml', 'figures', 'step13_7')
AI = os.path.join(ROOT, 'data', 'ai_ready_v3')
METR = os.path.join(ROOT, 'ml', 'metrics')

plt.rcParams.update({'font.size': 9, 'figure.dpi': 130})


def load_set(sname, s):
    return np.load(os.path.join(F137, 'X_%s_%s.npy' % (sname, s)))


def main():
    os.makedirs(FIG, exist_ok=True)
    names = json.load(open(os.path.join(F137, 'feature_names.json')))
    lines = []

    # ---------------- Feature importance (SHAP substitute) ----------------
    # NOTE (documented limitation): shap 0.49.1 cannot parse xgboost 3.2 model
    # format (base_score '[9.9961E1]' -> ValueError, both sklearn wrapper and
    # booster paths). Environment not modified to force compatibility.
    # Equivalent analysis used: permutation importance (model-agnostic,
    # validation set, 10 repeats, seed 42) + xgboost gain importance.
    from sklearn.inspection import permutation_importance

    def perm_imp(model, X, y, feat_names):
        pi = permutation_importance(model, X, y, n_repeats=10, random_state=SEED, n_jobs=-1)
        return pi.importances_mean

    lines.append('=== FEATURE IMPORTANCE (permutation, validation; SHAP unavailable: '
                 'shap 0.49.1 vs xgboost 3.2 base_score parse incompatibility, documented) ===')
    m_vm = joblib.load(os.path.join(MDIR, 'vm_final_xgb.joblib'))
    Xva = load_set('base', 'validation')
    y_va = np.load(os.path.join(ROOT, 'ml', 'features', 'y_validation.npy'))[:, 1]
    imp = perm_imp(m_vm, Xva, y_va, names['sets']['base'])
    order = np.argsort(imp)[::-1]
    lines.append('  von Mises (base features):')
    for i in order:
        lines.append('    %-16s %8.4f' % (names['sets']['base'][i], imp[i]))
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.barh([names['sets']['base'][i] for i in order[::-1]], imp[order[::-1]])
    ax.set_xlabel('permutation importance (R2 drop)')
    ax.set_title('von Mises XGB (base) - permutation importance')
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'shap_vm.png')); plt.close(fig)

    m_d = joblib.load(os.path.join(MDIR, 'disp_unified_xgb.joblib'))
    Xva_a = load_set('all', 'validation')
    y_va_d = np.load(os.path.join(ROOT, 'ml', 'features', 'y_validation.npy'))[:, 0]
    imp2 = perm_imp(m_d, Xva_a, y_va_d, names['sets']['all'])
    order2 = np.argsort(imp2)[::-1]
    lines.append('  displacement unified (all features):')
    for i in order2:
        lines.append('    %-16s %8.4f' % (names['sets']['all'][i], imp2[i]))
    # xgboost gain importance (built-in)
    lines.append('  xgboost gain importance (von Mises):')
    gain = m_vm.get_booster().get_score(importance_type='gain')
    for k in sorted(gain, key=gain.get, reverse=True):
        lines.append('    f%-4s gain=%.2f' % (k, gain[k]))

    # ---------------- Pi_yield physical plots ----------------
    allrows = list(csv.DictReader(open(os.path.join(AI, 'simulation_dataset_300.csv'))))
    valid = [r for r in allrows if r['valid_for_AI'] == 'YES']
    Pi = []; PEEQ = []; disp = []; vm = []
    for r in valid:
        sy = float(r['sigma_y_MPa']) if r['sigma_y_MPa'] else float('nan')
        P = float(r['pressure']); Ro = float(r['R_outer']); w = float(r['wall_thickness'])
        pi = P * Ro / (w * sy) if sy == sy else float('nan')
        Pi.append(pi); PEEQ.append(float(r['max_PEEQ']))
        disp.append(float(r['max_displacement'])); vm.append(float(r['max_von_mises']))
    Pi = np.array(Pi); PEEQ = np.array(PEEQ); disp = np.array(disp); vm = np.array(vm)
    mask = ~np.isnan(Pi)
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, yv, yl, name in ((axes[0], PEEQ, 'max_PEEQ', 'peeq'),
                             (axes[1], disp, 'max_displacement (mm)', 'disp'),
                             (axes[2], vm, 'max_von Mises (MPa)', 'vm')):
        ax.scatter(Pi[mask], yv[mask], s=10, alpha=0.6)
        ax.axvline(1.0, color='r', ls='--', lw=0.8, label='Pi_yield=1')
        ax.set_xlabel('Pi_yield = P*Ro/(w*sy)'); ax.set_ylabel(yl)
        ax.set_title('Pi_yield vs %s' % name)
        ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'pi_yield_physics.png')); plt.close(fig)
    # Pi_yield transition stats
    lines.append('=== Pi_yield transition evidence (valid rows) ===')
    for lo, hi, tag in ((0.0, 0.5, '<0.5'), (0.5, 0.8, '0.5-0.8'), (0.8, 1.0, '0.8-1.0'),
                        (1.0, 1.5, '1.0-1.5'), (1.5, 99, '>1.5')):
        sel = mask & (Pi >= lo) & (Pi < hi)
        if sel.sum() == 0:
            lines.append('  Pi_yield %-7s n=0' % tag)
            continue
        lines.append('  Pi_yield %-7s n=%3d  PEEQ>0: %d (%.0f%%)  vm range: %.0f-%.0f MPa'
                     % (tag, sel.sum(), int((PEEQ[sel] > 1e-6).sum()),
                        100 * (PEEQ[sel] > 1e-6).mean(), vm[sel].min(), vm[sel].max()))

    # ---------------- CEEQ exploratory ----------------
    lines.append('=== CEEQ exploratory ===')
    creep = [r for r in allrows if r['model_type'] == 'MODEL_C']
    nz = [r for r in creep if float(r['max_creep_strain']) > 0]
    lines.append('  MODEL_C rows: %d, nonzero CEEQ: %d' % (len(creep), len(nz)))
    for s in ('train', 'validation', 'test'):
        rows = list(csv.DictReader(open(os.path.join(AI, s + '.csv'))))
        cr = [r for r in rows if r['model_type'] == 'MODEL_C']
        nzn = sum(1 for r in cr if float(r['max_creep_strain']) > 0)
        lines.append('  %-10s MODEL_C n=%2d nonzero=%d' % (s, len(cr), nzn))
    lines.append('  nonzero CEEQ by time:')
    for t in ('100', '300', '1000', '3000'):
        rs = [r for r in nz if r['time'] == t]
        if rs:
            vals = [float(r['max_creep_strain']) for r in rs]
            lines.append('    t=%4sh n=%2d CEEQ min=%.2e max=%.2e' %
                         (t, len(rs), min(vals), max(vals)))
    lines.append('  nonzero CEEQ vs stress level (vm ~ P*Ro/w):')
    for r in sorted(nz, key=lambda r: float(r['max_creep_strain']), reverse=True)[:8]:
        P = float(r['pressure']); Ro = float(r['R_outer']); w = float(r['wall_thickness'])
        lines.append('    %-34s T=%s P=%4s t=%6s vm~%.0f CEEQ=%.2e A=%s n=%s' % (
            r['case_id'], r['T_uniform'], r['pressure'], r['time'],
            P * Ro / w, float(r['max_creep_strain']), r['A_creep'], r['n_creep']))

    with open(os.path.join(METR, 'step13_7_analysis.txt'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print('figures ->', FIG)


if __name__ == '__main__':
    main()
