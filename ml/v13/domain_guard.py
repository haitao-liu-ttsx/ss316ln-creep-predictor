"""STEP21-D: V1.3 Domain Guard.
Three-level status: SAFE / WARNING / OUT_OF_DOMAIN.
All boundaries computed from TRAIN 157 cases (actual coverage, not hand-set).
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
V13 = os.path.join(ROOT, 'simulation', 'v13_prepared')


class DomainGuard:
    def __init__(self):
        # frozen coverage data lives in ml/v13 (deployment-safe); rebuilt from
        # manifest when present locally
        frozen = os.path.join(HERE, 'domain_guard_train_coverage.json')
        if os.path.exists(frozen) and not os.path.exists(os.path.join(V13, 'manifest.csv')):
            data = json.load(open(frozen))
            self.T_range = tuple(data['T_range'])
            self.P_range = tuple(data['P_range'])
            self.t_range = tuple(data['t_range'])
            self.Rm_range = tuple(data['Rm_range'])
            self.Ro_range = tuple(data['Ro_range'])
            self.w_range = tuple(data['w_range'])
            self.ss_range = tuple(data['ss_range'])
            self.geoms = [tuple(int(x) for x in g) for g in data['train_geometries']]
            self.geom_count = {tuple(int(x) for x in k.split('.')): v for k, v in data['geom_count'].items()}
            self.tgeom_count = {tuple(int(x) for x in k.split('.')): v for k, v in data['tgeom_count'].items()}
            self._coverage_source = 'frozen'
            return
        man = list(csv.DictReader(open(os.path.join(V13, 'manifest.csv'), encoding='utf-8')))
        train = [r for r in man if r['status'] == 'OK' and r['split'] == 'TRAIN']
        T = [float(r['temperature']) for r in train]
        P = [float(r['pressure']) for r in train]
        t = [float(r['time_h']) for r in train]
        Rm = [float(r['Rm']) for r in train]
        Ro = [float(r['Ro']) for r in train]
        w = [float(r['w']) for r in train]
        ss = [p * o / ww for p, o, ww in zip(P, Ro, w)]
        self.T_range = (min(T), max(T))
        self.P_range = (min(P), max(P))
        self.t_range = (min(t), max(t))
        self.Rm_range = (min(Rm), max(Rm))
        self.Ro_range = (min(Ro), max(Ro))
        self.w_range = (min(w), max(w))
        self.ss_range = (min(ss), max(ss))
        self.geoms = sorted({(int(r['Rm']), int(r['Ro']), int(r['w'])) for r in train})
        self.geom_count = {}
        self.tgeom_count = {}
        for r in train:
            gk = (int(r['Rm']), int(r['Ro']), int(r['w']))
            self.geom_count[gk] = self.geom_count.get(gk, 0) + 1
            tk = (int(round(float(r['temperature']))),) + gk
            self.tgeom_count[tk] = self.tgeom_count.get(tk, 0) + 1
        self._coverage_source = 'manifest'
        self._store()

    def _store(self):
        data = {'T_range': list(self.T_range), 'P_range': list(self.P_range),
                't_range': list(self.t_range), 'Rm_range': list(self.Rm_range),
                'Ro_range': list(self.Ro_range), 'w_range': list(self.w_range),
                'ss_range': list(self.ss_range), 'train_geometries': self.geoms,
                'geom_count': {'.'.join(map(str, k)): v for k, v in self.geom_count.items()},
                'tgeom_count': {'.'.join(map(str, k)): v for k, v in self.tgeom_count.items()},
                'n_train': 157}
        with open(os.path.join(HERE, 'domain_guard_train_coverage.json'), 'w') as f:
            json.dump(data, f, indent=1)

    def check(self, T, P, t, Rm, Ro, w):
        """Return (status, reasons). Never blocks stress output; CEEQ confidence derived."""
        reasons = []
        status = 'SAFE'

        def degrade(level, msg):
            nonlocal status
            reasons.append(msg)
            if level == 'OUT' and status != 'OUT_OF_DOMAIN':
                status = 'OUT_OF_DOMAIN'
            elif level == 'WARN' and status == 'SAFE':
                status = 'WARNING'

        # geometry membership + temperature x geometry joint coverage (primary)
        gk = (int(round(Rm)), int(round(Ro)), int(round(w)))
        tk = (int(round(T)),) + gk
        if gk not in self.geoms:
            near = any(abs(Rm - g[0]) <= 20 and abs(Ro - g[1]) <= 5 and abs(w - g[2]) <= 1
                       for g in self.geoms)
            degrade('OUT' if not near else 'WARN',
                    'geometry (Rm,Ro,w)=(%g,%g,%g) %s TRAIN geometries' % (
                        Rm, Ro, w, 'not near any' if not near else 'near'))
        elif tk in self.tgeom_count:
            n = self.tgeom_count[tk]
            if n < 3:
                degrade('WARN', 'T=%g x geometry %s sparse TRAIN coverage (n=%d)' % (T, gk, n))
        else:
            degrade('WARN', 'T=%g x geometry %s not jointly in TRAIN (combination extrapolation)' % (T, gk))
        # temperature
        if not (self.T_range[0] <= T <= self.T_range[1]):
            degrade('OUT', 'T=%g outside TRAIN [%g,%g]' % (T, self.T_range[0], self.T_range[1]))
        elif T not in (550, 600, 650, 700, 750):
            degrade('WARN', 'T=%g not a calibrated temperature point' % T)
        # pressure / stress scale
        if not (self.P_range[0] <= P <= self.P_range[1]):
            degrade('OUT', 'P=%g outside TRAIN [%g,%g]' % (P, self.P_range[0], self.P_range[1]))
        ss = P * Ro / w
        if ss > self.ss_range[1]:
            degrade('OUT' if ss > self.ss_range[1] * 1.1 else 'WARN',
                    'P*Ro/w=%g > TRAIN max %g' % (ss, self.ss_range[1]))
        # time
        if t < self.t_range[0] or t > self.t_range[1]:
            degrade('WARN', 't=%g outside TRAIN [%g,%g]' % (t, self.t_range[0], self.t_range[1]))
        elif t <= 100 and (int(round(Rm)), int(round(Ro)), int(round(w))) not in self.geoms:
            degrade('WARN', 'short time t=%g with non-TRAIN geometry (CEEQ low confidence)' % t)
        # geometry ranges
        for name, v, rng in (('Rm', Rm, self.Rm_range), ('Ro', Ro, self.Ro_range),
                             ('w', w, self.w_range)):
            if not (rng[0] <= v <= rng[1]):
                degrade('OUT', '%s=%g outside TRAIN [%g,%g]' % (name, v, rng[0], rng[1]))
        return status, reasons


if __name__ == '__main__':
    g = DomainGuard()
    for args in [(700, 20, 1000, 100, 20, 4), (700, 20, 100, 120, 25, 3), (800, 10, 100, 100, 20, 4)]:
        s, r = g.check(*args)
        print(args, '->', s, r)
