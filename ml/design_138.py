"""STEP 13.8: physics-transition case design (12-18 cases, DESIGN ONLY, no solve).

Target: cover Pi_yield = P*Ro/(w*sy) in {0.7, 0.85, 1.0, 1.15, 1.3, 1.5} across
T = {650, 700, 750} (sy = 227/212/199 MPa, E = 171/141/119 GPa - approved EXP data).
Constraints: >=4 cases wall=2, >=4 cases P>=30, Rm in {80,100,120} (train-domain
geometry, avoids new Rm-150 test-zone entanglement), geometry rules
(Rm>2Ro, Ro>w), NO duplicate (T,P,Rm,Ro,w) vs 300-case dataset + all 298 v2
candidates. Compatibility: same material/BC/mesh(medium)/step/outputs as v2
generator (MODEL_B uniform). Regime labels are PRE-SOLVE predictions only.
"""
import csv
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI = os.path.join(ROOT, 'data', 'ai_ready_v3')
V2_MAN = os.path.join(ROOT, 'simulation', 'generated_cases_v2', 'manifest_v2.csv')

SY = {650: 227.0, 700: 212.0, 750: 199.0}
E_G = {650: 171.0, 700: 141.0, 750: 119.0}
PI_TARGETS = [0.7, 0.85, 1.0, 1.15, 1.3, 1.5]
TS = [650, 700, 750]
PS = list(range(15, 41))
RMS = [80, 100, 120]
ROS = [15, 20, 25]
WS = [2, 3]


def existing_keys():
    keys = set()
    for r in csv.DictReader(open(os.path.join(AI, 'simulation_dataset_300.csv'))):
        if r['model_type'] == 'MODEL_B' and r['T_uniform'] not in ('', 'nan'):
            keys.add((int(float(r['T_uniform'])), int(float(r['pressure'])),
                      int(float(r['R_major'])), int(float(r['R_outer'])),
                      int(float(r['wall_thickness']))))
    for r in csv.DictReader(open(V2_MAN)):
        if r['model'] == 'MODEL_B' and r['T_uniform'] not in ('', 'nan'):
            keys.add((int(float(r['T_uniform'])), int(float(r['P'])),
                      int(float(r['R_major'])), int(float(r['R_outer'])),
                      int(float(r['wall']))))
    return keys


def pi_of(P, Ro, w, T):
    return P * Ro / (w * SY[T])


def main():
    ex = existing_keys()
    cand = []
    for T in TS:
        for P in PS:
            for Rm in RMS:
                for Ro in ROS:
                    for w in WS:
                        if Ro <= w or Rm <= 2 * Ro:
                            continue
                        k = (T, P, Rm, Ro, w)
                        if k in ex:
                            continue
                        pi = pi_of(P, Ro, w, T)
                        cand.append({'T': T, 'P': P, 'Rm': Rm, 'Ro': Ro, 'w': w,
                                     'pi': pi, 'key': k})
    # greedy with Rm rotation (80/100/120 per slot) for geometric diversity:
    # for each (T, target) slot pick the closest unused candidate with the
    # slot-assigned Rm; fall back to global nearest if slot Rm exhausted.
    selected = []
    used = set()
    slot = 0
    for T in TS:
        for tgt in PI_TARGETS:
            rm_slot = RMS[slot % 3]
            slot += 1
            pool = [c for c in cand if c['T'] == T and c['key'] not in used]
            if not pool:
                print('WARN no candidate for T=%d pi=%.2f' % (T, tgt))
                continue
            best = min(pool, key=lambda c: abs(c['pi'] - tgt))
            # prefer the assigned Rm within 15% pi tolerance
            same_rm = [c for c in pool if c['Rm'] == rm_slot and abs(c['pi'] - tgt) < 0.15]
            if same_rm:
                best = min(same_rm, key=lambda c: abs(c['pi'] - tgt))
            selected.append(best)
            used.add(best['key'])
    # constraints check
    n_w2 = sum(1 for c in selected if c['w'] == 2)
    n_p30 = sum(1 for c in selected if c['P'] >= 30)
    print('selected: %d, wall=2: %d, P>=30: %d' % (len(selected), n_w2, n_p30))
    print('%-4s %4s %4s %5s %4s %4s %7s' % ('T', 'P', 'Rm', 'Ro', 'w', 'Pi', 'regime'))
    for c in sorted(selected, key=lambda c: (c['T'], c['pi'])):
        pi = c['pi']
        regime = 'elastic' if pi < 0.8 else ('near_transition' if pi <= 1.2 else 'plastic_candidate')
        print('%-4d %4d %4d %5d %4d %7.3f  %s' % (c['T'], c['P'], c['Rm'], c['Ro'], c['w'], pi, regime))
    with open(os.path.join(ROOT, 'ml', 'metrics', 'step13_8_design.json'), 'w') as f:
        json.dump({'selected': selected, 'n_w2': n_w2, 'n_p30': n_p30,
                   'existing_combo_count': len(ex)}, f, indent=1)


if __name__ == '__main__':
    main()
