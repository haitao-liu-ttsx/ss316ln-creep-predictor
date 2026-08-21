"""STEP 13.6: figures for baseline report (matplotlib, seed 42).
Figures -> ml/figures/. No data modification.
"""
import csv
import json
import os

import numpy as np
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SEED = 42
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEAT = os.path.join(ROOT, 'ml', 'features')
MODELS_DIR = os.path.join(ROOT, 'ml', 'models')
FIG = os.path.join(ROOT, 'ml', 'figures')
AI = os.path.join(ROOT, 'data', 'ai_ready_v3')

plt.rcParams.update({'font.size': 9, 'figure.dpi': 130})


def load():
    X, extra, meta, ids = {}, {}, {}, {}
    for s in ('train', 'validation', 'test'):
        X[s] = np.load(os.path.join(FEAT, 'X_%s.npy' % s))
        extra[s] = json.load(open(os.path.join(FEAT, 'y_%s_extra.json' % s)))
        ids[s] = json.load(open(os.path.join(FEAT, 'case_ids_%s.json' % s)))
        meta[s] = {r['case_id']: r for r in
                   csv.DictReader(open(os.path.join(AI, s + '.csv')))}
    return X, extra, meta, ids


def ap(ax, yt, yp, c, label):
    ax.scatter(yt, yp, s=14, alpha=0.65, color=c, label=label)
    lim = [min(yt.min(), yp.min()), max(yt.max(), yp.max())]
    ax.plot(lim, lim, 'k--', lw=0.8)


def main():
    os.makedirs(FIG, exist_ok=True)
    X, extra, meta, ids = load()

    # ---- 1/2. actual vs predicted (vm xgb; displacement linear) ----
    for tcol, tag, logscale in (('max_von_mises', 'xgb_von_mises_raw', False),
                                ('max_displacement', 'linear_displacement_raw', True)):
        model = joblib.load(os.path.join(MODELS_DIR, tag + '.joblib'))
        fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
        for i, s in enumerate(('train', 'validation', 'test')):
            yt = np.asarray(extra[s][tcol], float)
            yp = model.predict(X[s])
            if logscale:
                ax[i].set_xscale('log'); ax[i].set_yscale('log')
            ap(ax[i], yt, yp, 'C%d' % i, s)
            ax[i].set_title('%s (%s): %s' % (tcol, tag.split('_')[0], s))
            ax[i].set_xlabel('actual'); ax[i].set_ylabel('predicted')
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, 'avp_%s_%s.png' % (tag, tcol.split('_')[1])))
        plt.close(fig)

    # ---- 3-6. residual vs T/P/Rm/time (vm xgb, test) ----
    model = joblib.load(os.path.join(MODELS_DIR, 'xgb_von_mises_raw.joblib'))
    yt = np.asarray(extra['test']['max_von_mises'], float)
    yp = model.predict(X['test'])
    resid = yt - yp
    dims = [('T', lambda r: float(r['T_uniform'] or r['T_inner'] or 0)),
            ('P', lambda r: float(r['pressure'])),
            ('Rm', lambda r: float(r['R_major'])),
            ('time', lambda r: float(r['time'] or 0))]
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.4))
    for ax, (dn, f) in zip(axes, dims):
        xv = np.array([f(meta['test'][c]) for c in ids['test']])
        ax.scatter(xv, resid, s=14, alpha=0.7, c='C1')
        ax.axhline(0, color='k', lw=0.6, ls='--')
        ax.set_xlabel(dn); ax.set_ylabel('residual (MPa)')
        ax.set_title('vm residual vs %s (test)' % dn)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'residual_dims_vm.png'))
    plt.close(fig)

    # ---- 7. model comparison (test R2) ----
    metrics = list(csv.DictReader(open(os.path.join(ROOT, 'ml', 'metrics', 'baseline_metrics.csv'))))
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    for i, (tname, trf) in enumerate((('displacement', 'raw'), ('von_mises', 'raw'))):
        rows = [r for r in metrics if r['target'] == tname and r['transform'] == trf and r['split'] == 'test']
        names = [r['model'] for r in rows]
        r2 = [float(r['R2']) for r in rows]
        ax[i].bar(names, r2, color=['C3' if v < 0 else 'C0' for v in r2])
        ax[i].set_title('test R2: %s (%s)' % (tname, trf))
        ax[i].set_ylim(-1.2, 1.05)
        ax[i].tick_params(axis='x', rotation=30)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'model_comparison_test_r2.png'))
    plt.close(fig)

    # ---- 8. extrapolation summary ----
    fig, ax = plt.subplots(figsize=(7, 3.8))
    bins = ['T<=700', 'T=750', 'P<=20', 'P=25', 'P>=30', 'Rm<=120', 'Rm=150', 'CT<=300', 'CT=1000', 'CT=3000']
    r2v = [0.840, 0.872, 0.929, 0.453, -0.267, 0.798, 0.890, 0.841, 0.813, 0.999]
    ax.bar(range(len(bins)), r2v, color=['C0' if v >= 0 else 'C3' for v in r2v])
    ax.set_xticks(range(len(bins))); ax.set_xticklabels(bins, rotation=30)
    ax.axhline(0, color='k', lw=0.6)
    ax.set_ylabel('test R2 (von Mises, XGB)')
    ax.set_title('extrapolation bins')
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'extrapolation_summary.png'))
    plt.close(fig)
    print('figures written to', FIG)


if __name__ == '__main__':
    main()
