#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Resume the predeclared R6 calibration, motif assay and reserved confirmation."""
import argparse
import datetime
import itertools
import json
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np

from barricelli.lineage import analyze
from barricelli.motifs import matches
from barricelli.run import ROOT, read_csv, run, save_json, sha

BASE = ROOT / 'results/descendant_detector'


def variants(candidate):
    motif = np.array(candidate['motif'], dtype=np.int32)
    result = {name: motif.copy() for name in (
        'intact', 'helper_removed', 'same_type_damage_elsewhere',
        'wrong_helper_same_occupancy', 'composition_shuffled_fixed_gaps', 'rescue')}
    helper = candidate['helper_offset']
    result['helper_removed'][helper] = 0
    result['same_type_damage_elsewhere'][candidate['matched_damage_offset']] = 0
    result['wrong_helper_same_occupancy'][helper] -= 1
    occupied = np.flatnonzero(motif)
    result['composition_shuffled_fixed_gaps'][occupied] = np.roll(motif[occupied], 1)
    # The exact rescue reverses the helper-removal intervention before t0.
    result['rescue'] = result['helper_removed'].copy()
    result['rescue'][helper] = motif[helper]
    return result


def freeze(path, row):
    path.mkdir(parents=True, exist_ok=True)
    frozen = path / 'frozen.csv'
    if frozen.exists():
        if not np.array_equal(read_csv(frozen)[0], row):
            raise ValueError('refusing to overwrite a different frozen initial state')
    else:
        np.savetxt(frozen, row[None, :], fmt='%d', delimiter=',')
    return str(frozen.relative_to(ROOT))


def config(norm, width, steps, initial, metadata):
    return {'model': 'research', 'variant': 'r6_' + metadata['id'], 'norm': norm,
            'width': width, 'steps': steps, 'boundary': 'open', 'iteration_order': 'ascending',
            'seed': None, 'initial_state_file': initial, 'trace_steps': steps,
            'modifications': ['R6 designed inoculation or extraction; historical numerical norm unchanged',
                              'complete observation-only event trace; external interventions specified in experiment'],
            'experiment': metadata}


def plans(design):
    result = []
    for control in design['calibration_controls']:
        row = np.zeros(control['width'], dtype=np.int32)
        for x in [control['founder'], *control['other_founders']]:
            row[x:x + len(control['motif'])] = control['motif']
        metadata = {'id': control['id'], 'stage': 'calibration', 'candidate': control['id'],
                    'condition': 'numerical_control', 'placement': control['founder']}
        path = BASE / 'runs' / control['id']
        result.append({'id': control['id'], 'path': str(path.relative_to(ROOT)),
                       'motif': control['motif'], 'founder': control['founder'],
                       'config': config(control['norm'], control['width'], control['steps'],
                                        freeze(path, row), metadata)})
    for stage in ('exploration', 'confirmation'):
        cohort = design[stage]
        for candidate, placement in itertools.product(design['candidates'], cohort['placements']):
            for condition, variant in variants(candidate).items():
                ident = f'{stage}_{candidate["id"]}_x{placement}_{condition}'
                path = BASE / 'runs' / ident
                row = np.zeros(cohort['width'], dtype=np.int32)
                row[placement:placement + len(variant)] = variant
                metadata = {'id': ident, 'stage': stage, 'candidate': candidate['id'],
                            'condition': condition, 'placement': placement,
                            'helper_offset': candidate['helper_offset']}
                result.append({'id': ident, 'path': str(path.relative_to(ROOT)),
                               'motif': candidate['motif'], 'founder': placement,
                               'config': config(candidate['norm'], cohort['width'], cohort['steps'],
                                                freeze(path, row), metadata)})
    expected = design['budget']['baseline_native_runs']
    if len(result) != expected or sum(p['config']['width'] * p['config']['steps'] for p in result) != design['budget']['baseline_cell_updates']:
        raise ValueError('plans differ from predeclared baseline budget')
    manifest = BASE / 'manifest.json'
    record = {'design_sha256': sha(BASE / 'design.json'), 'declared_before_execution': True,
              'runs': result, 'recovery_probes': 'adaptive extraction of at most the earliest two children per run; separately retained',
              'execution': 'serial native runs; numeric trajectories and ancestry evidence streamed to disk'}
    if manifest.exists() and json.loads(manifest.read_text())['design_sha256'] != record['design_sha256']:
        raise ValueError('design changed after plans were frozen; create a new experiment')
    save_json(manifest, record)
    return result


def ensure_native(conf, path):
    """Reuse only completed, hash-checked runs; preserve earlier run provenance."""
    marker = path / 'complete.json'
    if marker.exists():
        completed = json.loads(marker.read_text())
        if json.loads((path / 'config.json').read_text()) != conf:
            raise ValueError('saved run configuration differs from frozen plan')
        if completed['binary_sha256'] != sha(ROOT / 'build/simulator'):
            raise ValueError('engine changed; preserve old results and name a new experiment')
        if any(sha(path / n) != h for n, h in completed['files_sha256'].items()):
            raise ValueError('completed run artifact changed')
        return json.loads((path / 'statistics.json').read_text())
    stats = run(conf, path)
    if sha(path / 'initial.csv') != sha(ROOT / conf['initial_state_file']):
        raise ValueError('native run starting row differs from frozen inoculation')
    provenance_path = path / 'provenance.json'
    provenance = json.loads(provenance_path.read_text())
    provenance['events_sha256'] = sha(path / 'events.csv')
    save_json(provenance_path, provenance)
    names = ('initial.csv', 'trajectory.csv', 'trajectory.npz', 'events.csv',
             'config.json', 'statistics.json', 'resource.json', 'provenance.json')
    save_json(marker, {'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       'binary_sha256': sha(ROOT / 'build/simulator'),
                       'files_sha256': {n: sha(path / n) for n in names}})
    return stats


def recovery(plan, pair):
    probes = []
    source = ROOT / plan['path']
    arr = read_csv(source / 'trajectory.csv')
    for index, child in enumerate(pair['children'], start=1):
        x = child['position']
        cutout = arr[pair['time'], x:x + len(plan['motif'])]
        ident = plan['id'] + f'_child{index}'
        path = BASE / 'recovery' / ident
        row = np.zeros(256, dtype=np.int32)
        row[112:112 + len(cutout)] = cutout
        metadata = {'id': ident, 'stage': 'recovery', 'candidate': plan['config']['experiment']['candidate'],
                    'condition': 'isolated_child', 'placement': 112, 'source_run': plan['path'],
                    'source_time': pair['time'], 'source_position': x,
                    'intervention': 'extract exact child footprint; translate to x112; clear all exterior cells'}
        conf = config(plan['config']['norm'], 256, 8, freeze(path, row), metadata)
        ensure_native(conf, path)
        history = read_csv(path / 'trajectory.csv')
        probe = {'path': str(path.relative_to(ROOT)), 'source_time': pair['time'], 'source_position': x,
                 'persistent_every_saved_time': all(matches(r, plan['motif']) for r in history),
                 'source_trajectory_sha256': sha(source / 'trajectory.csv')}
        save_json(path / 'recovery.json', probe)
        probes.append(probe)
    return probes


def execute(plan):
    path = ROOT / plan['path']
    start = time.perf_counter()
    stats = ensure_native(plan['config'], path)
    detector = analyze(path, plan['motif'], plan['founder'])
    pair = detector['first_internal_helper_pair'] or detector['first_common_founder_pair']
    probes = recovery(plan, pair) if pair else []
    recovered = len(probes) == 2 and all(p['persistent_every_saved_time'] for p in probes)
    row = {'id': plan['id'], 'path': plan['path'], **plan['config']['experiment'],
           'norm': plan['config']['norm'], 'width': plan['config']['width'], 'steps': plan['config']['steps'],
           'maximum_unguarded_matches': detector['maximum_unguarded_matches'],
           'maximum_detached_matches': detector['maximum_detached_matches'],
           'common_founder_pair': detector['first_common_founder_pair'],
           'internal_helper_pair': detector['first_internal_helper_pair'],
           'both_children_recover': recovered, 'recovery_probes': probes,
           'copying_geometry_ancestry_recovery_pass': bool(pair) and recovered,
           'dependency_supported_detached_reproduction': bool(detector['first_internal_helper_pair']) and recovered,
           'events_audited': detector['events_audited'],
           'analysis_and_resume_seconds': time.perf_counter() - start,
           'native_process_seconds': stats['process_seconds'], 'native_max_rss_kib': stats['max_rss_kib']}
    save_json(path / 'result.json', row)
    print(plan['id'], 'unguarded', row['maximum_unguarded_matches'],
          'detached', row['maximum_detached_matches'], 'common-founder pair', bool(pair), flush=True)
    return row


def summarize(all_plans):
    rows = [json.loads((ROOT / p['path'] / 'result.json').read_text()) for p in all_plans
            if (ROOT / p['path'] / 'result.json').exists()]
    assays = [r for r in rows if r['stage'] != 'calibration']
    groups = []
    for stage, candidate in sorted({(r['stage'], r['candidate']) for r in assays}):
        group = [r for r in assays if r['stage'] == stage and r['candidate'] == candidate]
        groups.append({'stage': stage, 'candidate': candidate, 'worlds': len(group),
                       'common_founder_pairs': sum(r['common_founder_pair'] is not None for r in group),
                       'dependency_supported_reproduction_cases': sum(r['dependency_supported_detached_reproduction'] for r in group),
                       'maximum_unguarded_matches': max(r['maximum_unguarded_matches'] for r in group),
                       'maximum_detached_matches': max(r['maximum_detached_matches'] for r in group)})
    paired = []
    for stage, candidate, placement in sorted({(r['stage'], r['candidate'], r['placement']) for r in assays}):
        group = {r['condition']: r for r in assays
                 if (r['stage'], r['candidate'], r['placement']) == (stage, candidate, placement)}
        if set(group) != set(('intact', 'helper_removed', 'same_type_damage_elsewhere',
                              'wrong_helper_same_occupancy', 'composition_shuffled_fixed_gaps', 'rescue')):
            continue
        persistence = {}
        for condition, row in group.items():
            history = json.loads((ROOT / row['path'] / 'detector.json').read_text())['history']
            present = [h['time'] for h in history if h['unguarded_matches']]
            persistence[condition] = {'first_exact_template_time': min(present, default=None),
                                      'last_exact_template_time': max(present, default=None)}
        intact, rescued = (ROOT / group[c]['path'] for c in ('intact', 'rescue'))
        paired.append({'stage': stage, 'candidate': candidate, 'placement': placement,
                       'persistence': persistence,
                       'rescue_initial_exact': sha(intact / 'initial.csv') == sha(rescued / 'initial.csv'),
                       'rescue_trajectory_exact': sha(intact / 'trajectory.csv') == sha(rescued / 'trajectory.csv'),
                       'rescue_events_exact': sha(intact / 'events.csv') == sha(rescued / 'events.csv')})
    recovery_paths = sorted((BASE / 'recovery').glob('*/statistics.json'))
    baseline_stats = [json.loads((ROOT / r['path'] / 'statistics.json').read_text()) for r in rows]
    recovery_stats = [json.loads(p.read_text()) for p in recovery_paths]
    stats = baseline_stats + recovery_stats
    summary = {'experiment': 'R6', 'baseline_worlds_completed': len(rows),
               'baseline_worlds_planned': len(all_plans), 'recovery_probes': len(recovery_paths),
               'groups': groups, 'paired_effects': paired, 'rows': rows,
               'all_update_traces_match_saved_dynamics': True,
               'events_audited': sum(r['events_audited'] for r in rows),
               'native_process_seconds_sum': sum(s['process_seconds'] for s in stats),
               'max_native_rss_kib': max((s['max_rss_kib'] for s in stats), default=0),
               'new_model_api_calls': 0,
               'interpretation': 'Calibration copying is not partner-dependent collective reproduction; deterministic placements are robustness settings, not population samples.'}
    save_json(BASE / 'summary.json', summary)
    completed = {r['id'] for r in rows}
    save_json(BASE / 'checkpoint.json', {'updated_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                        'completed': sorted(completed), 'pending': [p['id'] for p in all_plans if p['id'] not in completed],
                                        'resume_command': '.venv/bin/python scripts/descendant_detector.py --phase all'})
    return summary


def require_calibration():
    path = BASE / 'calibration.json'
    if not path.exists():
        raise ValueError('run calibration before inspecting assay or reserved confirmation worlds')
    calibration = json.loads(path.read_text())
    if not calibration['passed'] or calibration['design_sha256'] != sha(BASE / 'design.json') or calibration['analyzer_sha256'] != sha(ROOT / 'barricelli/lineage.py'):
        raise ValueError('calibration is missing, failed or uses different detector criteria')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('calibration', 'exploration', 'confirmation', 'all'), default='all')
    args = parser.parse_args()
    design = json.loads((BASE / 'design.json').read_text())
    if not (ROOT / 'build/simulator').exists():
        subprocess.run([sys.executable, str(ROOT / 'scripts/build.py')], check=True)
    all_plans = plans(design)
    phases = ('calibration', 'exploration', 'confirmation') if args.phase == 'all' else (args.phase,)
    for phase in phases:
        if phase == 'calibration':
            with (BASE / 'test-results.txt').open('w') as output:
                subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                               cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, check=True)
        else:
            require_calibration()
        rows = []
        for plan in all_plans:
            if plan['config']['experiment']['stage'] == phase:
                rows.append(execute(plan))
                summarize(all_plans)
        if phase == 'calibration':
            by_id = {r['id']: r for r in rows}
            positive = by_id['copying_positive']
            assertions = {
                'copying_control_has_common_founder_pair_and_two_recoveries': positive['copying_geometry_ancestry_recovery_pass'],
                'copying_control_is_not_partner_supported': not positive['dependency_supported_detached_reproduction'],
                'unrelated_lookalikes_are_two_detached_matches_without_common_founder': by_id['unrelated_lookalikes']['maximum_detached_matches'] == 2 and by_id['unrelated_lookalikes']['common_founder_pair'] is None,
                'translation_is_one_detached_match_without_branch': by_id['translation_negative']['maximum_detached_matches'] == 1 and by_id['translation_negative']['common_founder_pair'] is None,
                'tiling_expands_without_detached_branch': by_id['tiling_negative']['maximum_unguarded_matches'] > 1 and by_id['tiling_negative']['common_founder_pair'] is None}
            save_json(BASE / 'calibration.json', {'passed': all(assertions.values()), 'assertions': assertions,
                                                'design_sha256': sha(BASE / 'design.json'),
                                                'analyzer_sha256': sha(ROOT / 'barricelli/lineage.py'),
                                                'test_log': str((BASE / 'test-results.txt').relative_to(ROOT)),
                                                'limitation': 'No independently known native partner-assisted detached collective positive is available; only the detector core is calibrated.'})
            if not all(assertions.values()):
                raise ValueError('calibration failed; reserved confirmation remains unexecuted')
        print(phase, 'complete', len(rows), 'baseline worlds', flush=True)
    summary = summarize(all_plans)
    print('completed', summary['baseline_worlds_completed'], 'baseline worlds and', summary['recovery_probes'], 'recovery probes', flush=True)


if __name__ == '__main__':
    main()
