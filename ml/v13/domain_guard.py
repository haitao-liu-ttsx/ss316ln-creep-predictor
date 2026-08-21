"""V1.3 Domain Guard (self-contained; frozen TRAIN coverage inlined).
Three-level status: SAFE / WARNING / OUT_OF_DOMAIN.
All boundaries from TRAIN 157 cases actual coverage (frozen 2026-08-21).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- frozen TRAIN coverage (157 cases; built from v13_prepared manifest) ----
COVERAGE = {
    'T_range': [550.0, 750.0], 'P_range': [2.5, 30.0], 't_range': [1.0, 3000.0],
    'Rm_range': [80.0, 150.0], 'Ro_range': [15.0, 25.0], 'w_range': [2.0, 5.0],
    'ss_range': [50.0, 250.0],
    'geoms': [[80, 15, 2], [90, 18, 3], [100, 20, 4], [110, 22, 4], [120, 25, 3], [150, 20, 4]],
    'geom_count': {'100.20.4': 77, '110.22.4': 9, '90.18.3': 10, '80.15.2': 11,
                   '150.20.4': 39, '120.25.3': 11},
    'tgeom_count': {'550.100.20.4': 15, '600.100.20.4': 16, '650.100.20.4': 14,
                    '550.110.22.4': 3, '550.90.18.3': 3, '600.80.15.2': 5,
                    '600.150.20.4': 3, '650.110.22.4': 4, '650.150.20.4': 3,
                    '650.90.18.3': 4, '550.80.15.2': 3, '550.120.25.3': 4,
                    '550.150.20.4': 1, '600.110.22.4': 2, '600.120.25.3': 5,
                    '600.90.18.3': 3, '650.120.25.3': 2, '650.80.15.2': 3,
                    '700.100.20.4': 16, '700.150.20.4': 16,
                    '750.100.20.4': 16, '750.150.20.4': 16},
    'n_train': 157,
}


class DomainGuard:
    def __init__(self):
        C = COVERAGE
        self.T_range = tuple(C['T_range'])
        self.P_range = tuple(C['P_range'])
        self.t_range = tuple(C['t_range'])
        self.Rm_range = tuple(C['Rm_range'])
        self.Ro_range = tuple(C['Ro_range'])
        self.w_range = tuple(C['w_range'])
        self.ss_range = tuple(C['ss_range'])
        self.geoms = [tuple(g) for g in C['geoms']]
        self.geom_count = {tuple(int(x) for x in k.split('.')): v for k, v in C['geom_count'].items()}
        self.tgeom_count = {tuple(int(x) for x in k.split('.')): v for k, v in C['tgeom_count'].items()}

    def check(self, T, P, t, Rm, Ro, w):
        reasons = []
        status = 'SAFE'

        def degrade(level, msg):
            nonlocal status
            reasons.append(msg)
            if level == 'OUT' and status != 'OUT_OF_DOMAIN':
                status = 'OUT_OF_DOMAIN'
            elif level == 'WARN' and status == 'SAFE':
                status = 'WARNING'

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
        if not (self.T_range[0] <= T <= self.T_range[1]):
            degrade('OUT', 'T=%g outside TRAIN [%g,%g]' % (T, self.T_range[0], self.T_range[1]))
        elif T not in (550, 600, 650, 700, 750):
            degrade('WARN', 'T=%g not a calibrated temperature point' % T)
        if not (self.P_range[0] <= P <= self.P_range[1]):
            degrade('OUT', 'P=%g outside TRAIN [%g,%g]' % (P, self.P_range[0], self.P_range[1]))
        ss = P * Ro / w
        if ss > self.ss_range[1]:
            degrade('OUT' if ss > self.ss_range[1] * 1.1 else 'WARN',
                    'P*Ro/w=%g > TRAIN max %g' % (ss, self.ss_range[1]))
        if t < self.t_range[0] or t > self.t_range[1]:
            degrade('WARN', 't=%g outside TRAIN [%g,%g]' % (t, self.t_range[0], self.t_range[1]))
        elif t <= 100 and gk not in self.geoms:
            degrade('WARN', 'short time t=%g with non-TRAIN geometry (CEEQ low confidence)' % t)
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
