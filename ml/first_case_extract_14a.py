"""STEP 14-A.6: extract first-case ODB, list actual output variables, CEEQ.
Abaqus python (run via abaqus.bat python). Mirrors STEP13 extraction:
final frame, max over element values, raw CEEQ + log10(CEEQ), no epsilon.
"""
import math
import os
import sys

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'simulation', 'generated_cases_step14a_ceeq')
CASE = 'CEEQ14A_T550_P5_t500h_Rm100_Ro20_w4'


def vm(s):
    a, b, c, d, e, f = s
    return math.sqrt(((a - b) ** 2 + (b - c) ** 2 + (c - a) ** 2
                      + 6 * (d ** 2 + e ** 2 + f ** 2)) / 2.0)


def main():
    from odbAccess import openOdb
    odb_path = os.path.join(OUT, CASE + '.odb')
    print('odb exists:', os.path.exists(odb_path))
    odb = openOdb(odb_path, readOnly=True)
    st = list(odb.steps.values())[-1]
    print('step:', st.name, 'frames:', len(st.frames))
    fr = st.frames[-1]
    print('final frame time: %.4f (expected 500 h)' % fr.frameValue)
    print('field outputs present: %s' % sorted(fr.fieldOutputs.keys()))
    for k in sorted(fr.fieldOutputs.keys()):
        fv = fr.fieldOutputs[k]
        vals = [x.data for x in fv.values]
        if isinstance(vals[0], (int, float)):
            print('  %-8s n=%d max=%.6g min=%.6g' % (k, len(vals), max(vals), min(vals)))
    NT = fr.fieldOutputs['NT11']
    ts = [v.data for v in NT.values]
    S = fr.fieldOutputs['S']
    vms = [vm(v.data) for v in S.values]
    U = fr.fieldOutputs['U']
    umax = max(math.hypot(v.data[0], v.data[1], v.data[2]) for v in U.values)
    peeq = 0.0
    if 'PEEQ' in fr.fieldOutputs:
        peeq = max(v.data for v in fr.fieldOutputs['PEEQ'].values)
    ee = 0.0
    if 'EE' in fr.fieldOutputs:
        ee = max(max(v.data) for v in fr.fieldOutputs['EE'].values)
    if 'CEEQ' in fr.fieldOutputs:
        ceeq_vals = [v.data for v in fr.fieldOutputs['CEEQ'].values]
        ceeq_max = max(ceeq_vals)
        ceeq_mean = sum(ceeq_vals) / len(ceeq_vals)
        ceeq_min = min(ceeq_vals)
    else:
        ceeq_max = ceeq_mean = ceeq_min = None
    print('T_max=%.2f T_min=%.2f vm_max=%.4f U_max=%.6f PEEQ_max=%.4g EE_max=%.4g'
          % (max(ts), min(ts), max(vms), umax, peeq, ee))
    if ceeq_max is not None:
        print('CEEQ max=%.6g mean=%.6g min=%.6g (element field, final frame)' %
              (ceeq_max, ceeq_mean, ceeq_min))
        print('log10(CEEQ_max) = %.4f' % math.log10(ceeq_max))
    # capture record BEFORE closing odb (odb references die on close)
    import json
    rec = {'case': CASE, 'odb_exists': os.path.exists(odb_path),
           'step': st.name, 'final_frame_time_h': float(fr.frameValue),
           'output_variables': sorted(fr.fieldOutputs.keys()),
           'T_max': float(max(ts)), 'T_min': float(min(ts)),
           'vm_max': float(max(vms)), 'U_max': float(umax),
           'PEEQ_max': float(peeq), 'EE_max': float(ee),
           'CEEQ_max': float(ceeq_max) if ceeq_max is not None else None,
           'CEEQ_mean': float(ceeq_mean) if ceeq_mean is not None else None,
           'CEEQ_min': float(ceeq_min) if ceeq_min is not None else None,
           'log10_CEEQ_max': float(math.log10(ceeq_max)) if ceeq_max and ceeq_max > 0 else None}
    odb.close()
    with open(os.path.join(OUT, 'first_case_extract.json'), 'w') as f:
        json.dump(rec, f, indent=1)
    print('wrote first_case_extract.json')


if __name__ == '__main__':
    main()
