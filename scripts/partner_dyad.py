#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Resume the frozen R7 construction, reserved checks and independent oracles."""
import argparse
import datetime
import json
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np

from barricelli.dyad import audit_first_step, formula
from barricelli.lineage import analyze
from barricelli.motifs import disjoint, matches
from barricelli.run import ROOT, read_csv, save_json, sha
from scripts.descendant_detector import ensure_native, freeze

BASE = ROOT / 'results/partner_dyad'
ORACLE = ROOT / 'build/symbiotic_oracle'


def make_config(ident, setting, condition, phase, initial, intervention=None):
    steps = 1 if phase == 'trace' else setting['steps']
    return {'model': 'research', 'variant': 'r7_partner_dyad', 'norm': 'symbiotic',
            'width': setting['width'], 'steps': steps, 'boundary': 'open',
            'iteration_order': 'ascending', 'seed': None, 'initial_state_file': initial,
            'trace_steps': steps if phase == 'trace' else 0,
            'modifications': ['R7 designed integer inoculation; historical symbiotic arithmetic unchanged',
                              'external causal interventions declared in frozen design; observation-only trace'],
            'experiment': {'id': ident, 'setting': setting['id'], 'stage': setting['stage'],
                           'condition': condition, 'phase': phase, 'd': setting['d'],
                           'founder': setting['founder'], 'intervention': intervention}}


def plans(design):
    cases = []
    for setting in design['settings']:
        d, x, width = (setting[k] for k in ('d', 'founder', 'width'))
        conditions = list(design['conditions'])
        if setting['stage'] == 'construction':
            conditions += ['background_intact', 'background_partner_removed', 'background_matched_damage']
        for condition in conditions:
            row = np.zeros(width, dtype=np.int32)
            row[x], row[x + d] = d, -d
            if condition.startswith('background_'): row[400] = -d
            if condition == 'positive_removed': row[x] = 0
            if condition in ('negative_removed', 'background_partner_removed'): row[x + d] = 0
            if condition == 'wrong_negative_same_occupancy': row[x + d] = -(d + 1)
            if condition == 'composition_shuffled_fixed_gaps': row[x], row[x + d] = -d, d
            if condition == 'spacing_shift': row[x + d], row[x + d + 1] = 0, -d
            if condition == 'background_matched_damage': row[400] = 0
            if condition == 'rescue': row[x + d] = 0; row[x + d] = -d
            ident = setting['id'] + '_' + condition
            path = BASE / 'runs' / ident
            initial = freeze(path, row)
            cases.append({'id': ident, 'path': str(path.relative_to(ROOT)), 'setting': setting,
                          'condition': condition, 'motif': [d] + [0] * (d - 1) + [-d],
                          'configs': {phase: make_config(ident, setting, condition, phase, initial)
                                      for phase in ('trace', 'continuation')}})
    budget = design['budgets']
    if len(cases) != budget['baseline_settings_conditions'] or sum(c['width'] * c['steps'] for p in cases for c in p['configs'].values()) != budget['baseline_cell_updates']:
        raise ValueError('plan differs from frozen budget')
    manifest = BASE / 'manifest.json'
    record = {'design_sha256': sha(BASE / 'design.json'), 'cases': cases,
              'execution': 'serial; hash-checked native cache preserves original provenance',
              'recovery_selection': 'two first children from each intact setting only; retain failures'}
    if manifest.exists() and json.loads(manifest.read_text()) != record:
        raise ValueError('frozen plan changed; preserve it and name a new experiment')
    if not manifest.exists(): save_json(manifest, record)
    return cases


def oracle_run(native, output, mode='historical'):
    output.parent.mkdir(parents=True, exist_ok=True)
    marker = output.with_suffix('.verification.json')
    c = json.loads((native / 'config.json').read_text())
    expected = {'mode': mode, 'initial_sha256': sha(native / 'initial.csv'),
                'steps': c['steps'], 'native_trajectory_sha256': sha(native / 'trajectory.csv'),
                'oracle_binary_sha256': sha(ORACLE),
                'upstream_sha256': sha(ROOT / 'engine/upstream/barricelli54.cpp'),
                'harness_sha256': sha(ROOT / 'engine/symbiotic_oracle.cpp')}
    if marker.exists():
        record = json.loads(marker.read_text())
        if record['inputs'] != expected or record['trajectory_sha256'] != sha(output):
            raise ValueError('oracle inputs/output changed; preserve prior verification')
        return record
    resource = output.with_suffix('.resource.json')
    start = time.perf_counter()
    subprocess.run(['/usr/bin/time', '-f', '{"max_rss_kib":%M,"elapsed_seconds":%e,"user_seconds":%U,"system_seconds":%S}',
                    '-o', str(resource), str(ORACLE), mode, str(c['steps']), str(native / 'initial.csv'), str(output)], check=True)
    elapsed = time.perf_counter() - start
    original, replay = read_csv(native / 'trajectory.csv'), read_csv(output)
    if original.shape != replay.shape: raise ValueError('oracle dimensions differ')
    equal = np.array_equal(original, replay)
    if mode == 'historical' and not equal: raise ValueError('unchanged-source oracle differs from native numbers')
    record = {'inputs': expected, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'trajectory_sha256': sha(output), 'cells_compared': int(original.size),
              'equal_to_native': bool(equal), 'wall_seconds': elapsed,
              'resource': json.loads(resource.read_text()),
              'scope': 'independent uninstrumented binary of retained original source' if mode == 'historical'
                       else 'externally imposed helper-recursion suppression; not historical behavior'}
    save_json(marker, record)
    return record


def run_pair(plan):
    path = ROOT / plan['path']
    stats = {}
    for phase, conf in plan['configs'].items():
        stats[phase] = ensure_native(conf, path / phase)
        oracle_run(path / phase, path / 'oracle' / (phase + '.csv'))
    if not np.array_equal(read_csv(path / 'trace/trajectory.csv'), read_csv(path / 'continuation/trajectory.csv')[:2]):
        raise ValueError('trace observation changes first update')
    s = plan['setting']; motif = plan['motif']; condition = plan['condition']
    detector = analyze(path / 'trace', motif, s['founder'])
    history = read_csv(path / 'continuation/trajectory.csv')
    counts = [len(disjoint(matches(row, motif, guard=2), len(motif))) for row in history]
    result = {'id': plan['id'], 'path': plan['path'], 'setting': s['id'], 'stage': s['stage'],
              'condition': condition, 'd': s['d'], 'detached_counts': counts,
              'first_internal_helper_pair': detector['first_internal_helper_pair'],
              'first_update_trace_complete': detector['trace_matches_every_saved_update'],
              'oracle_all_cells_equal': True, 'oracle_cells': int(history.size + 2 * s['width']),
              'native_seconds': sum(stat['process_seconds'] for stat in stats.values()),
              'cell_updates': sum(c['width'] * c['steps'] for c in plan['configs'].values()),
              'max_native_rss_kib': max(stat['max_rss_kib'] for stat in stats.values())}
    if condition in ('intact', 'rescue', 'background_intact', 'background_matched_damage', 'isolated_child'):
        result['independent_first_step'] = audit_first_step(path / 'trace', s['founder'], s['d'])
        save_json(path / 'first_step_audit.json', result['independent_first_step'])
    if condition in ('intact', 'rescue', 'background_matched_damage', 'isolated_child'):
        result['formula_matches_all_saved_rows'] = all(np.array_equal(row, formula(s['width'], s['founder'], s['d'], t)) for t, row in enumerate(history))
    if condition == 'intact':
        output = path / 'oracle/helpers_disabled.csv'
        oracle_run(path / 'continuation', output, 'helpers_disabled')
        counterfactual = read_csv(output)
        result['helpers_disabled_detached_counts'] = [len(disjoint(matches(row, motif, guard=2), len(motif))) for row in counterfactual]
        result['helpers_disabled_occupied_counts'] = np.count_nonzero(counterfactual, axis=1).tolist()
    save_json(path / 'result.json', result)
    return result


def recover(plan, result):
    pair = result['first_internal_helper_pair']
    if not pair: return []
    source = ROOT / plan['path']
    arr = read_csv(source / 'trace/trajectory.csv')
    probes = []
    for number, child in enumerate(pair['children'], 1):
        ident = plan['setting']['id'] + f'_child{number}'
        path = BASE / 'recovery' / ident
        row = np.zeros(512, dtype=np.int32)
        cutout = arr[pair['time'], child['position']:child['position'] + len(plan['motif'])]
        row[240:240 + len(cutout)] = cutout
        setting = {'id': ident, 'stage': 'recovery', 'd': plan['setting']['d'], 'width': 512, 'steps': 12, 'founder': 240}
        intervention = {'action': 'extract exact saved child; clear all exterior; translate to x240',
                        'source_run': plan['path'], 'source_time': pair['time'], 'source_position': child['position'],
                        'source_trajectory_sha256': sha(source / 'trace/trajectory.csv')}
        initial = freeze(path, row)
        probe_plan = {'id': ident, 'path': str(path.relative_to(ROOT)), 'setting': setting,
                      'condition': 'isolated_child', 'motif': plan['motif'],
                      'configs': {phase: make_config(ident, setting, 'isolated_child', phase, initial, intervention)
                                  for phase in ('trace', 'continuation')}}
        save_json(path / 'extraction.json', {'intervention': intervention, 'plan': probe_plan})
        probe = run_pair(probe_plan)
        probe['reproduces_after_isolation'] = bool(probe['first_internal_helper_pair'])
        probe['persistent_every_saved_time'] = all(probe['detached_counts'])
        save_json(path / 'recovery.json', probe)
        probes.append(probe)
    return probes


def verify_group(cases, results):
    by_setting = {}
    for result in results: by_setting.setdefault(result['setting'], {})[result['condition']] = result
    checks = []
    for setting, group in by_setting.items():
        if 'intact' not in group: continue
        intact = group['intact']
        assert intact['first_internal_helper_pair'] and intact['independent_first_step']['passed']
        assert intact['formula_matches_all_saved_rows'] and intact['detached_counts'] == list(range(1, len(intact['detached_counts']) + 1))
        assert not any(intact['helpers_disabled_detached_counts'][1:])
        assert set(intact['helpers_disabled_occupied_counts']) == {2}
        for condition in ('positive_removed', 'negative_removed', 'wrong_negative_same_occupancy', 'composition_shuffled_fixed_gaps', 'spacing_shift'):
            assert not group[condition]['first_internal_helper_pair']
            assert not any(group[condition]['detached_counts'][1:])
        a, b = ROOT / intact['path'], ROOT / group['rescue']['path']
        for phase in ('trace', 'continuation'):
            for name in ('initial.csv', 'trajectory.csv', 'events.csv'):
                assert sha(a / phase / name) == sha(b / phase / name), (setting, name)
        if 'background_intact' in group:
            assert group['background_intact']['first_internal_helper_pair']
            assert group['background_matched_damage']['first_internal_helper_pair']
            assert not group['background_partner_removed']['first_internal_helper_pair']
            assert not any(group['background_partner_removed']['detached_counts'])
        checks.append({'setting': setting, 'all_predeclared_checks_passed': True, 'rescue_identical': True})
    return checks


def summarize(cases):
    results = [json.loads((ROOT / p['path'] / 'result.json').read_text()) for p in cases if (ROOT / p['path'] / 'result.json').exists()]
    allowed_sources = {p['path'] for p in cases}
    recoveries = [json.loads(p.read_text()) for p in sorted((BASE / 'recovery').glob('*/recovery.json'))
                  if json.loads((p.parent / 'extraction.json').read_text())['intervention']['source_run'] in allowed_sources]
    checks = verify_group(cases, results)
    assert all(r['reproduces_after_isolation'] and r['persistent_every_saved_time'] and r['formula_matches_all_saved_rows'] for r in recoveries)
    oracles = [json.loads(p.read_text()) for p in sorted(BASE.glob('**/*.verification.json'))]
    summary = {'experiment': 'R7', 'baseline_cases_planned': len(cases), 'baseline_cases_completed': len(results),
               'baseline_native_runs': 2 * len(results), 'recovery_native_runs': 2 * len(recoveries),
               'cell_updates': sum(r['cell_updates'] for r in results + recoveries),
               'native_process_seconds_sum': sum(r['native_seconds'] for r in results + recoveries),
               'maximum_native_rss_kib': max(r['max_native_rss_kib'] for r in results + recoveries),
               'oracle_historical_runs': sum(r['inputs']['mode'] == 'historical' for r in oracles),
               'oracle_cells_compared': sum(r['cells_compared'] for r in oracles if r['inputs']['mode'] == 'historical'),
               'oracle_counterfactual_runs': sum(r['inputs']['mode'] == 'helpers_disabled' for r in oracles),
               'oracle_wall_seconds_sum': sum(r['wall_seconds'] for r in oracles),
               'reserved_settings_verified': sum(c['setting'].startswith('confirmation') for c in checks),
               'checks': checks, 'cases': results, 'recovery_probes': recoveries,
               'claim': 'Designed opposite-sign dyad produces two guarded, full-founder, partner-assisted numerical copies at t1. Each isolated first child reproduces. This is an operational numerical positive control, not evolved biological symbiosis.',
               'ancestry_scope': 'complete ordered native trace at t0→t1 only; longer histories verified numerically with unchanged-source oracle and formula, not full lineage reconstruction',
               'limits': json.loads((BASE / 'design.json').read_text())['limits']}
    save_json(BASE / 'summary.json', summary)
    save_json(BASE / 'checkpoint.json', {'design_sha256': sha(BASE / 'design.json'),
              'completed': [r['id'] for r in results], 'pending': [p['id'] for p in cases if p['id'] not in {r['id'] for r in results}],
              'recovery_completed': [r['id'] for r in recoveries]})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('plan', 'construction', 'confirmation', 'all', 'verify'), default='all')
    args = parser.parse_args()
    design = json.loads((BASE / 'design.json').read_text())
    cases = plans(design)
    if args.phase == 'plan': print('frozen', len(cases), 'R7 cases'); return
    if not ORACLE.exists(): raise ValueError('build the independent oracle with scripts/build.py first')
    if args.phase == 'verify':
        for plan in cases:
            result = run_pair(plan)
            if plan['condition'] == 'intact': recover(plan, result)
    for stage in ('construction', 'confirmation'):
        if args.phase not in (stage, 'all'): continue
        if stage == 'confirmation':
            gate = BASE / 'construction_verified.json'
            if not gate.exists() or json.loads(gate.read_text())['design_sha256'] != sha(BASE / 'design.json'):
                raise ValueError('verify construction before viewing reserved settings')
        for plan in cases:
            if plan['setting']['stage'] != stage: continue
            result = run_pair(plan)
            if plan['condition'] == 'intact': recover(plan, result)
            print(plan['id'], 'pair', bool(result['first_internal_helper_pair']), 'final', result['detached_counts'][-1], flush=True)
        summary = summarize([p for p in cases if p['setting']['stage'] == 'construction'] if stage == 'construction' else cases)
        if stage == 'construction':
            if len(summary['cases']) != 10 or len(summary['recovery_probes']) != 2 or not summary['checks']:
                raise ValueError('construction or recovery incomplete')
            save_json(BASE / 'construction_verified.json', {'design_sha256': sha(BASE / 'design.json'),
                       'passed': True, 'summary_at_gate': summary, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    summary = summarize(cases)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('cases', 'recovery_probes', 'limits')}, indent=2))


if __name__ == '__main__': main()
