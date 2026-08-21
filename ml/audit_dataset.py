"""
STEP 13.1: full data audit of the 300-case dataset (read-only, no training).

Reports: schema (33 fields), types, missing/unique counts, numeric stats,
categorical uniques, train/validation/test consistency, duplicate/cross-set
checks, target-candidate analysis (completeness, zeros, magnitude span, log fit).
Pure stdlib + numpy (no pandas/sklearn dependency).
"""
import csv
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI = os.path.join(ROOT, 'data', 'ai_ready_v3')
FILES = ['simulation_dataset_300.csv', 'train.csv', 'validation.csv', 'test.csv']

NUMERIC_HINTS = ['R_major', 'R_outer', 'wall_thickness', 'R_inner', 'T_uniform',
                 'T_inner', 'T_outer', 'Delta_T', 'pressure', 'time', 'E_GPa',
                 'sigma_y_MPa', 'A_creep', 'n_creep', 'rho_kgm3', 'k_WmK',
                 'Cp_JkgK', 'CTE_1e6', 'max_temperature', 'max_heat_flux',
                 'max_displacement', 'max_von_mises', 'max_PEEQ',
                 'max_thermal_strain', 'max_creep_strain', 'max_creep_rate',
                 'N_content']


def load(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fmt(x):
    if x is None:
        return '-'
    if isinstance(x, float):
        return '%.4g' % x
    return str(x)


def main():
    out = {}
    data = {f: load(os.path.join(AI, f)) for f in FILES}
    main_rows = data['simulation_dataset_300.csv']
    out['rows'] = {f: len(rows) for f, rows in data.items()}

    # ---------------- 1. schema ----------------
    fields = list(main_rows[0].keys())
    out['n_fields'] = len(fields)
    out['fields'] = []
    for col in fields:
        vals = [r.get(col, '') for r in main_rows]
        missing = sum(1 for v in vals if v in ('', None))
        uniq_set = set(vals)
        uniq = len(uniq_set)
        rec = {'field': col, 'missing': missing, 'missing_pct': round(100.0 * missing / len(vals), 1),
               'unique': uniq}
        if col in NUMERIC_HINTS or all(num(v) is not None for v in vals if v != ''):
            nums = [num(v) for v in vals if v not in ('', None)]
            if nums:
                rec['type'] = 'numeric'
                rec['min'] = fmt(min(nums)); rec['max'] = fmt(max(nums))
                n = len(nums)
                mean = sum(nums) / n
                var = sum((x - mean) ** 2 for x in nums) / (n - 1) if n > 1 else 0.0
                rec['mean'] = fmt(mean); rec['std'] = fmt(math.sqrt(var))
        else:
            rec['type'] = 'categorical'
            rec['unique_values'] = sorted(str(v) for v in uniq_set)[:20]
        out['fields'].append(rec)

    # ---------------- 2. split consistency ----------------
    tr, va, te = data['train.csv'], data['validation.csv'], data['test.csv']
    fields_s = set(fields)
    out['split_consistency'] = {
        'train_fields_match': set(tr[0].keys()) == fields_s,
        'validation_fields_match': set(va[0].keys()) == fields_s,
        'test_fields_match': set(te[0].keys()) == fields_s,
        'train_rows': len(tr), 'validation_rows': len(va), 'test_rows': len(te),
    }
    def dup_keys(rows):
        return [r['case_id'] for r in rows if sum(1 for x in rows if x['case_id'] == r['case_id']) > 1]
    out['split_consistency']['train_dup_case_ids'] = sorted(set(dup_keys(tr)))
    out['split_consistency']['validation_dup_case_ids'] = sorted(set(dup_keys(va)))
    out['split_consistency']['test_dup_case_ids'] = sorted(set(dup_keys(te)))
    tr_ids, va_ids, te_ids = set(r['case_id'] for r in tr), set(r['case_id'] for r in va), set(r['case_id'] for r in te)
    out['split_consistency']['case_id_cross_set'] = {
        'train_and_validation': sorted(tr_ids & va_ids),
        'train_and_test': sorted(tr_ids & te_ids),
        'validation_and_test': sorted(va_ids & te_ids),
    }
    # exact row duplicates (full content) within each set
    def full_dups(rows):
        seen, dups = set(), []
        for r in rows:
            k = tuple(sorted(r.items()))
            if k in seen:
                dups.append(r['case_id'])
            seen.add(k)
        return sorted(set(dups))
    out['split_consistency']['exact_duplicate_rows'] = {
        'train': full_dups(tr), 'validation': full_dups(va), 'test': full_dups(te)}
    # exact copies of train samples inside test/validation
    tr_full = {tuple(sorted(r.items())) for r in tr}
    out['split_consistency']['train_copy_in_test'] = [r['case_id'] for r in te if tuple(sorted(r.items())) in tr_full]
    out['split_consistency']['train_copy_in_validation'] = [r['case_id'] for r in va if tuple(sorted(r.items())) in tr_full]

    # ---------------- 3. target candidates ----------------
    out['targets'] = []
    for col in ['max_displacement', 'max_von_mises', 'max_PEEQ', 'max_thermal_strain',
                'max_creep_strain', 'max_creep_rate', 'max_temperature', 'max_heat_flux']:
        vals = [num(r.get(col, '')) for r in main_rows]
        n = len(vals)
        present = [v for v in vals if v is not None]
        missing = n - len(present)
        nz = sum(1 for v in present if abs(v) > 1e-12)
        zeros = len(present) - nz
        rec = {'target': col, 'missing': missing,
               'missing_pct': round(100.0 * missing / n, 1),
               'non_zero_pct': round(100.0 * nz / n, 1),
               'zero_pct': round(100.0 * zeros / n, 1)}
        if present:
            lo = min(present); hi = max(present)
            rec['min'] = fmt(lo); rec['max'] = fmt(hi)
            rec['span_orders_of_magnitude'] = round(math.log10(hi / lo), 1) if lo > 0 else 'inf (contains 0)'
            rec['log_transform_recommended'] = (lo > 0 and math.log10(hi / lo) > 3) or zeros > 0
            pos = [v for v in present if v > 0]
            rec['positive_fraction'] = round(len(pos) / n, 3)
        out['targets'].append(rec)

    # ---------------- 4. leakage pre-screen ----------------
    # features = inputs (T/P/geometry/time/material); anything max_* is output.
    out['leakage_prescreen'] = {
        'input_candidate_fields': [c for c in fields if not c.startswith('max_') and c not in
                                   ('case_id', 'quality_grade', 'valid_for_AI',
                                    'valid_for_physics_reference', 'solver_status', 'notes')],
        'output_fields': [c for c in fields if c.startswith('max_')],
        'flag_fields': ['quality_grade', 'valid_for_AI', 'valid_for_physics_reference',
                        'solver_status', 'notes', 'converged'],
    }

    with open(os.path.join(ROOT, 'ml', 'metrics', 'audit_dataset.json'), 'w') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print('audit done -> ml/metrics/audit_dataset.json')
    print('rows:', out['rows'])
    print('targets:')
    for t in out['targets']:
        print('  %-22s missing=%-4s zero=%-4s span=%s log_reco=%s' % (
            t['target'], t['missing_pct'], t['zero_pct'], t.get('span_orders_of_magnitude'),
            t.get('log_transform_recommended')))
    print('split:', out['split_consistency'])


if __name__ == '__main__':
    os.makedirs(os.path.join(ROOT, 'ml', 'metrics'), exist_ok=True)
    main()
