# SPDX-License-Identifier: GPL-3.0-only
"""Conservative numerical copying support from ordered native event traces.

Roots are occupied cells at t0, not organisms. Same-value arrivals add possible
copying parents. Erasure removes support; replacement resets it; mutations have
unknown copying origins. This is an operational audit, not biological ancestry.
"""
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .motifs import disjoint, matches
from .run import read_csv, save_json, sha

EXCLUSION = 99999


@dataclass(frozen=True)
class CellLineage:
    roots: int = 0
    dependencies: int = 0
    helpers: int = 0
    unknown: bool = False
    dependency_unknown: bool = False


def root_positions(mask):
    positions = []
    while mask:
        bit = mask & -mask
        positions.append(bit.bit_length() - 1)
        mask ^= bit
    return positions


def initial_lineages(row):
    return [CellLineage(1 << x, 1 << x) if v not in (0, EXCLUSION)
            else CellLineage() for x, v in enumerate(row)]


def propagate_step(old, expected, previous, events):
    """Audit one complete update, retaining only final surviving parent edges.

    Mutational nearest-neighbor inputs are not fully traced by the current
    engine. Their unknown origins are excluded from certified copying paths.
    """
    width = len(old)
    scratch = np.zeros(width, dtype=np.int32)
    current = [CellLineage() for _ in range(width)]
    parents = [set() for _ in range(width)]
    same_arrivals = [0] * width
    count = 0
    for event in events:
        count += 1
        source, target = int(event['source']), int(event['target'])
        value, before, after = (int(event[k]) for k in ('value', 'before', 'after'))
        if not 0 <= source < width or int(old[source]) != value:
            raise ValueError('trace source differs from saved old row')
        helpers = []
        for item in event['helpers'].split(';'):
            if item:
                x, v = map(int, item.split(':'))
                if not 0 <= x < width or int(old[x]) != v:
                    raise ValueError('trace helper differs from saved old row')
                helpers.append(x)
        outcome = event['outcome']
        if not 0 <= target < width:
            if outcome not in ('out_of_bounds', 'depth_cap'):
                raise ValueError('unsupported out-of-bounds event')
            continue
        if int(scratch[target]) != before:
            raise ValueError('trace before-value differs from ordered writes')
        if outcome == 'depth_cap':
            if before != after:
                raise ValueError('depth cap changes numerical state')
            continue
        source_state = previous[source]
        dependencies = source_state.dependencies
        helper_roots = source_state.helpers
        dependency_unknown = source_state.dependency_unknown
        edges = {(source, 'copy')}
        for x in helpers:
            dependencies |= previous[x].dependencies
            helper_roots |= previous[x].roots
            dependency_unknown |= previous[x].dependency_unknown
            edges.add((x, 'helper'))
        if outcome in ('copy', 'same'):
            if after != value or after in (0, EXCLUSION):
                raise ValueError('accepted trace event has invalid after-value')
            copied = CellLineage(source_state.roots, dependencies,
                                 helper_roots, source_state.unknown, dependency_unknown)
            if outcome == 'same':
                if before != after:
                    raise ValueError('same-value event changes state')
                prior = current[target]
                copied = CellLineage(prior.roots | copied.roots,
                                     prior.dependencies | copied.dependencies,
                                     prior.helpers | copied.helpers,
                                     prior.unknown or copied.unknown,
                                     prior.dependency_unknown or copied.dependency_unknown)
                edges.discard((source, 'copy'))
                edges.add((source, 'same_value_alternative'))
                parents[target].update(edges)
                same_arrivals[target] += 1
            else:
                parents[target] = edges
                same_arrivals[target] = 0
            current[target] = copied
        elif outcome == 'excluded':
            if after not in (0, EXCLUSION):
                raise ValueError('exclusion leaves a valid numerical value')
            current[target] = CellLineage()
            parents[target].clear()
            same_arrivals[target] = 0
        elif outcome == 'mutation':
            # A newly produced value is not a copied identity, even when it
            # happens to equal an integer occurring elsewhere in the world.
            current[target] = (CellLineage(0, current[target].dependencies | dependencies,
                                          helper_roots, True, True)
                               if after not in (0, EXCLUSION) else CellLineage())
            parents[target] = {(source, 'mutation_input')} if after not in (0, EXCLUSION) else set()
            same_arrivals[target] = 0
        else:
            raise ValueError('unsupported trace outcome: ' + outcome)
        scratch[target] = after
    if not np.array_equal(scratch, expected):
        raise ValueError('trace is incomplete or differs from saved numerical update')
    return current, parents, same_arrivals, count


def child_support(states, x, motif, founder_mask):
    roots = guaranteed_roots = dependencies = helpers = 0
    unknown = False
    dependency_unknown = False
    for offset, value in enumerate(motif):
        if value:
            node = states[x + offset]
            roots |= node.roots
            # A union of alternative origins only shows possible coverage.
            # Require every founding component to occur as an unambiguous
            # initial-cell origin somewhere in each descendant footprint.
            if node.roots.bit_count() == 1 and not node.unknown:
                guaranteed_roots |= node.roots
            dependencies |= node.dependencies
            helpers |= node.helpers
            unknown |= node.unknown or not node.roots
            dependency_unknown |= node.dependency_unknown
    return {
        'position': x,
        'copy_roots': root_positions(roots),
        'guaranteed_copy_roots': root_positions(guaranteed_roots),
        'dependency_roots': root_positions(dependencies),
        'helper_roots': root_positions(helpers),
        'unknown_copy_origin': unknown,
        'unknown_dependency_origin': dependency_unknown,
        'exclusive_full_founder_copying': not unknown and roots == founder_mask and guaranteed_roots == founder_mask,
        'dependencies_confined_to_founder': not dependency_unknown and not (dependencies & ~founder_mask),
        'internal_helper_support': bool(helpers & founder_mask),
    }


def analyze(run_path, motif, founder):
    """Stream events and lineage evidence; scan exact saved numerical matches."""
    path = Path(run_path)
    config = json.loads((path / 'config.json').read_text())
    if config.get('trace_steps', 0) < config['steps']:
        raise ValueError('complete update trace required for ancestry audit')
    arr = read_csv(path / 'trajectory.csv')
    if arr.shape != (config['steps'] + 1, config['width']):
        raise ValueError('saved trajectory dimensions differ from configuration')
    motif = list(map(int, motif))
    if not motif or not any(motif) or EXCLUSION in motif:
        raise ValueError('motif must contain valid nonzero founding cells')
    if not 0 <= founder <= config['width'] - len(motif):
        raise ValueError('founder outside world')
    founder_mask = sum(1 << (founder + i) for i, v in enumerate(arr[0, founder:founder + len(motif)])
                       if v not in (0, EXCLUSION))
    states = initial_lineages(arr[0])
    history = []
    first_pair = first_internal_pair = None
    total_events = ambiguous_cells = 0
    with (path / 'events.csv').open() as event_stream, \
            (path / 'lineage_nodes.csv').open('w') as node_stream, \
            (path / 'lineage_edges.csv').open('w') as edge_stream:
        events = iter(csv.DictReader(event_stream))
        pending = next(events, None)
        nodes = csv.writer(node_stream)
        nodes.writerow(['time', 'x', 'value', 'copy_roots', 'dependency_roots', 'helper_roots',
                        'unknown_copy_origin', 'unknown_dependency_origin', 'same_value_arrivals'])
        edges = csv.writer(edge_stream)
        edges.writerow(['parent_time', 'parent_x', 'child_time', 'child_x', 'kind'])
        for t, row in enumerate(arr):
            parents = [set() for _ in row]
            same = [0] * len(row)
            if t:
                def step_events():
                    nonlocal pending
                    while pending is not None and int(pending['time']) == t - 1:
                        item = pending
                        pending = next(events, None)
                        yield item
                    if pending is not None and int(pending['time']) < t:
                        raise ValueError('event times are unordered')
                states, parents, same, count = propagate_step(arr[t - 1], row, states, step_events())
                total_events += count
            for x, value in enumerate(row):
                if value in (0, EXCLUSION):
                    continue
                cell = states[x]
                ambiguous_cells += cell.roots.bit_count() > 1
                nodes.writerow([t, x, int(value), ';'.join(map(str, root_positions(cell.roots))),
                                ';'.join(map(str, root_positions(cell.dependencies))),
                                ';'.join(map(str, root_positions(cell.helpers))), cell.unknown,
                                cell.dependency_unknown, same[x]])
                for parent_x, kind in sorted(parents[x]):
                    edges.writerow([t - 1, parent_x, t, x, kind])
            unguarded = disjoint(matches(row, motif), len(motif))
            guarded = disjoint(matches(row, motif, guard=2), len(motif))
            children = [child_support(states, x, motif, founder_mask) for x in guarded]
            qualified = [c for c in children if c['exclusive_full_founder_copying']]
            internal = [c for c in qualified if c['dependencies_confined_to_founder'] and c['internal_helper_support']]
            history.append({'time': t, 'unguarded_matches': len(unguarded), 'detached_matches': len(guarded),
                            'full_founder_descendants': len(qualified), 'internal_helper_descendants': len(internal)})
            if t and len(qualified) >= 2 and first_pair is None:
                first_pair = {'time': t, 'children': qualified[:2]}
            if t and len(internal) >= 2 and first_internal_pair is None:
                first_internal_pair = {'time': t, 'children': internal[:2]}
        if pending is not None:
            raise ValueError('trace contains events beyond saved horizon')
    result = {
        'motif': motif, 'founder_position': founder, 'founder_cells': root_positions(founder_mask),
        'trace_matches_every_saved_update': True, 'events_audited': total_events,
        'ambiguous_cell_times': ambiguous_cells,
        'maximum_unguarded_matches': max(h['unguarded_matches'] for h in history),
        'maximum_detached_matches': max(h['detached_matches'] for h in history),
        'first_common_founder_pair': first_pair,
        'first_internal_helper_pair': first_internal_pair,
        'history': history,
        'interpretation': 'set-valued operational numerical copying support; no biological ancestry claim',
        'sources_sha256': {n: sha(path / n) for n in ('initial.csv', 'trajectory.csv', 'events.csv')},
        'analyzer_sha256': sha(Path(__file__)),
    }
    save_json(path / 'detector.json', result)
    return result
