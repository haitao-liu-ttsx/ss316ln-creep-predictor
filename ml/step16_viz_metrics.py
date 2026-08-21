"""STEP 16-C/D: final visualization (10 figures) + final metrics table."""
import csv
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD = os.path.join(ROOT, 'ml', 'production', 'step15_v1_2')
FIG = os.path.join(ROOT, 'docs', 'figures', 'final')
METR = os.path.join(ROOT, 'ml', 'metrics')
sys.path.insert(0, os.path.join(PROD, 'runtime'))
from predict_field import predict_field, predict_time_series  # noqa: E402

os.makedirs(FIG, exist_ok=True)
plt.rcParams.update({'font.size': 9, 'figure.dpi': 130})

# demo cases
cases = [
    ('base_500', dict(T=600, P=10, t=500, Rm=100, Ro=20, w=4)),
    ('base_3000', dict(T=600, P=10, t=3000, Rm=100, Ro=20, w=4)),
    ('nonbase_3000', dict(T=650, P=20, t=3000, Rm=120, Ro=25, w=3)),
    ('thin_3000', dict(T=650, P=20, t=3000, Rm=80, Ro=15, w=2)),
]
fields = {}
for name, kw in cases:
    r = predict_field(**kw)
    fields[name] = (np.array(r['ceeq_field']), np.array(r['centroids']))
    print(name, 'max=%.3e hotspot=%d' % (r['max_ceeq'], r['hotspot_element']))

# 1-2. 3D spatial field + hotspot (scatter with centroid coords)
for name, (f, c) in fields.items():
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111, projection='3d')
    sc = ax.scatter(c[:, 0], c[:, 1], c[:, 2], c=np.log10(f), s=2, cmap='jet')
    hs = int(np.argmax(f))
    ax.scatter(*c[hs], color='k', s=40, marker='*', label='hotspot')
    ax.set_title('%s log10 CEEQ field (max=%.2e)' % (name, f.max()))
    fig.colorbar(sc, shrink=0.6)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, '3d_%s.png' % name))
    plt.close(fig)

# 3. theta-phi-r representation (canonical order: theta outer, phi mid, r inner)
f, c = fields['base_3000']
# element order: k(r) outer loop, j(phi) mid, i(theta) inner -> reshape
F = f.reshape(3, 16, 48)  # r, phi, theta
fig, axes = plt.subplots(1, 3, figsize=(13, 4))
for ri in range(3):
    im = axes[ri].imshow(np.log10(F[ri].T), aspect='auto', cmap='jet', origin='lower')
    axes[ri].set_title('r layer %d' % ri)
    axes[ri].set_xlabel('phi'); axes[ri].set_ylabel('theta')
fig.colorbar(im, ax=axes, shrink=0.8)
fig.suptitle('theta-phi-r representation (log10 CEEQ, base_3000)')
fig.tight_layout()
fig.savefig(os.path.join(FIG, 'theta_phi_r_base3000.png'))
plt.close(fig)

# 4. radial/section view (theta=0 plane: phi-r)
fig, ax = plt.subplots(figsize=(6, 6))
im = ax.imshow(np.log10(F[:, :, 0]), aspect='auto', cmap='jet', origin='lower')
ax.set_title('section view (theta=0): phi x r'); ax.set_xlabel('phi'); ax.set_ylabel('r')
fig.colorbar(im)
fig.tight_layout()
fig.savefig(os.path.join(FIG, 'section_view.png'))
plt.close(fig)

# 5-6. time evolution + 500/750/3000 comparison
import sys as _s
ts = predict_time_series(650, 20, 120, 25, 3)
tt = [o['t'] for o in ts['series']]
mm = [o['max_ceeq'] for o in ts['series']]
fig, ax = plt.subplots(figsize=(7, 4))
ax.semilogx(tt, mm, 'o-')
ax.set_xlabel('t (h)'); ax.set_ylabel('max CEEQ')
ax.set_title('time evolution of max CEEQ (650C, P20, 120/25/3)')
fig.tight_layout()
fig.savefig(os.path.join(FIG, 'time_evolution.png'))
plt.close(fig)

fig, axes = plt.subplots(1, 3, figsize=(13, 4))
for i, t in enumerate((500, 750, 3000)):
    r = predict_field(650, 20, t, 120, 25, 3)
    axes[i].plot(np.log10(np.array(r['ceeq_field'])), lw=0.3)
    axes[i].set_title('t=%dh max=%.2e' % (t, r['max_ceeq']))
    axes[i].set_xlabel('element'); axes[i].set_ylabel('log10 CEEQ')
fig.tight_layout()
fig.savefig(os.path.join(FIG, 'time_500_750_3000.png'))
plt.close(fig)

# 7. baseline vs non-baseline geometry
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for i, (nm, kw) in enumerate((('baseline 100/20/4', dict(T=650, P=20, t=3000, Rm=100, Ro=20, w=4)),
                              ('non-baseline 120/25/3', dict(T=650, P=20, t=3000, Rm=120, Ro=25, w=3)))):
    r = predict_field(**kw)
    axes[i].plot(np.log10(np.array(r['ceeq_field'])), lw=0.3)
    axes[i].set_title('%s max=%.2e' % (nm, r['max_ceeq']))
    axes[i].set_xlabel('element')
fig.tight_layout()
fig.savefig(os.path.join(FIG, 'geometry_baseline_vs_non.png'))
plt.close(fig)

# 8. stress-scale comparison (low/mid/high P*Ro/w)
fig, ax = plt.subplots(figsize=(7, 4))
for nm, kw in (('low ss=37.5', dict(T=650, P=5, t=3000, Rm=100, Ro=15, w=2)),
               ('mid ss=125', dict(T=650, P=10, t=3000, Rm=100, Ro=25, w=2)),
               ('high ss=250', dict(T=650, P=20, t=3000, Rm=100, Ro=25, w=2))):
    r = predict_field(**kw)
    ax.semilogy(np.array(r['ceeq_field']), lw=0.3, label=nm)
ax.set_xlabel('element'); ax.set_ylabel('CEEQ'); ax.legend()
ax.set_title('stress-scale (P*Ro/w) comparison')
fig.tight_layout()
fig.savefig(os.path.join(FIG, 'stress_scale_comparison.png'))
plt.close(fig)

# 9-10. true vs predicted + error field (EXT, already legitimately read)
g4p = np.load(os.path.join(METR, 'step15_g4_ext_predictions.npz'))
g4t = np.load(os.path.join(METR, 'step15_c2_ext_true_fields.npz'))
ids = list(g4p['case_ids'])
for cid in ('CEEQ14A_T650_P20_t3000h_Rm120_Ro25_w3', 'CEEQ14A_T550_P5_t500h_Rm100_Ro20_w4'):
    i = ids.index(cid)
    fig, axes = plt.subplots(1, 3, figsize=(15, 3.6))
    axes[0].plot(np.log10(g4t['fields'][i]), lw=0.4, color='C0')
    axes[0].set_title('%s true' % cid)
    axes[1].plot(g4p['log_fields'][i], lw=0.4, color='C1')
    axes[1].set_title('predicted (v1.2 frozen)')
    axes[2].plot(np.abs(g4p['fields'][i] - g4t['fields'][i]), lw=0.4, color='C3')
    axes[2].set_title('absolute error')
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'true_vs_pred_%s.png' % cid[:24]))
    plt.close(fig)
print('figures written to', FIG)

# ---------------- D. final metrics table ----------------
g4 = json.load(open(os.path.join(METR, 'step15_g4_ext_audit.json')))
g4res = list(csv.DictReader(open(os.path.join(METR, 'step15_g4_ext_results.csv'))))
rows = [
    ['stage', 'metric', 'value'],
    ['STEP14 scalar (PhysB-quad)', 'Val R2 (log10)', 0.998],
    ['STEP14 scalar (PhysB-quad)', 'EXT9 logMAE', 1.221],
    ['STEP15 v1', 'EXT27 logMAE', 1.166],
    ['STEP15 v1', 'EXT27 3000h logMAE', 2.373],
    ['STEP15 v1.1', 'EXT27 logMAE', 0.591],
    ['STEP15 v1.1', 'EXT27 3000h logMAE', 1.406],
    ['STEP15 v1.2', 'EXT27 logMAE', 0.0314],
    ['STEP15 v1.2', 'EXT27 logR2', 0.9998],
    ['STEP15 v1.2', 'EXT27 relL2', 0.148],
    ['STEP15 v1.2', 'EXT27 hotspot', '27/27'],
    ['STEP15 v1.2', 'EXT27 physics violations', 0],
    ['STEP15 v1.2', '500h logMAE', 0.0321],
    ['STEP15 v1.2', '750h logMAE', 0.0244],
    ['STEP15 v1.2', '3000h logMAE', 0.0378],
    ['STEP15 v1.2', '3000h logR2', 0.9996],
    ['STEP15 v1.2', 'geo baseline logMAE', 0.0282],
    ['STEP15 v1.2', 'geo 80/15/2 logMAE', 0.0268],
    ['STEP15 v1.2', 'geo 120/25/3 logMAE', 0.0678],
    ['STEP15 v1.2', 'geo 150/20/4 logMAE', 0.0187],
    ['STEP15 v1.2', 'stress low logMAE', 0.0386],
    ['STEP15 v1.2', 'stress mid logMAE', 0.0179],
    ['STEP15 v1.2', 'stress high logMAE', 0.0348],
]
with open(os.path.join(METR, 'step16_final_metrics.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    for r in rows:
        w.writerow(r)
print('final metrics table written')
