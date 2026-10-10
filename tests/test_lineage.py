# SPDX-License-Identifier: GPL-3.0-only
"""Native adversarial traces validate surviving ancestry and missing-data errors."""
import csv
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np

from barricelli.lineage import CellLineage, analyze, child_support, initial_lineages, propagate_step, root_positions
from barricelli.run import ROOT, read_csv


class Lineage(unittest.TestCase):
    def simulate(self, row, norm, steps=1):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name)
        np.savetxt(path / 'initial.csv', np.array(row)[None, :], fmt='%d', delimiter=',')
        subprocess.run([str(ROOT / 'build/simulator'), 'research', norm, str(steps),
                        str(path / 'initial.csv'), str(path / 'trajectory.csv'),
                        str(path / 'statistics.json'), str(path / 'events.csv'), str(steps)], check=True)
        (path / 'config.json').write_text(json.dumps({'steps': steps, 'width': len(row), 'trace_steps': steps}))
        return path

    def test_native_common_founder_copying_and_no_helper_claim(self):
        row = np.zeros(128, dtype=int)
        row[32:34] = 8
        result = analyze(self.simulate(row, 'basic'), [8, 8], 32)
        self.assertEqual([c['position'] for c in result['first_common_founder_pair']['children']], [32, 40])
        self.assertTrue(all(c['copy_roots'] == [32, 33] for c in result['first_common_founder_pair']['children']))
        self.assertIsNone(result['first_internal_helper_pair'])

    def test_unrelated_equal_templates_do_not_share_founder(self):
        row = np.zeros(128, dtype=int)
        row[32:34] = row[80:82] = 1000
        result = analyze(self.simulate(row, 'basic', 3), [1000, 1000], 32)
        self.assertEqual(result['maximum_detached_matches'], 2)
        self.assertIsNone(result['first_common_founder_pair'])

    def step(self, row, norm):
        path = self.simulate(row, norm)
        arr = read_csv(path / 'trajectory.csv')
        with (path / 'events.csv').open() as stream:
            events = list(csv.DictReader(stream))
        return propagate_step(arr[0], arr[1], initial_lineages(arr[0]), events), arr, events

    def test_equal_arrivals_preserve_alternative_roots(self):
        row = np.zeros(32, dtype=int)
        row[10:12] = 1
        (states, parents, same, _), _, _ = self.step(row, 'basic')
        self.assertEqual(root_positions(states[11].roots), [10, 11])
        self.assertEqual(same[11], 1)
        self.assertEqual(parents[11], {(10, 'copy'), (11, 'same_value_alternative')})

    def test_overwrite_removes_prior_root(self):
        row = np.zeros(32, dtype=int)
        row[8], row[11] = 2, -1
        (states, parents, _, _), arr, _ = self.step(row, 'symbiotic')
        self.assertEqual(arr[1, 10], -1)
        self.assertEqual(root_positions(states[10].roots), [11])
        self.assertEqual(parents[10], {(11, 'copy')})

    def test_erasure_and_later_reuse_remove_prior_roots(self):
        row = np.zeros(32, dtype=int)
        row[8:12] = [2, 1, 7, -1]
        (states, parents, _, _), arr, _ = self.step(row, 'galloway_B')
        self.assertEqual(arr[1, 10], -1)
        self.assertEqual(root_positions(states[10].roots), [11])
        self.assertEqual(parents[10], {(11, 'copy')})

    def test_mutation_does_not_invent_copied_ancestry(self):
        row = np.zeros(32, dtype=int)
        row[8], row[11] = 2, -1
        (states, _, _, _), arr, _ = self.step(row, 'galloway_B')
        self.assertEqual(arr[1, 10], -2)
        self.assertEqual(states[10].roots, 0)
        self.assertTrue(states[10].unknown)

    def test_incomplete_and_corrupted_trace_rejected(self):
        row = np.zeros(32, dtype=int)
        row[8] = 2
        _, arr, events = self.step(row, 'symbiotic')
        with self.assertRaises(ValueError):
            propagate_step(arr[0], arr[1], initial_lineages(arr[0]), [])
        events[0]['before'] = '3'
        with self.assertRaises(ValueError):
            propagate_step(arr[0], arr[1], initial_lineages(arr[0]), events)

    def test_helper_sites_are_separate_from_copying_parents(self):
        row = np.zeros(64, dtype=int)
        row[24:32] = [5, -3, 1, -3, 0, -3, 1, 0]
        (states, parents, _, _), _, _ = self.step(row, 'exclusion')
        self.assertEqual(root_positions(states[21].roots), [24])
        self.assertEqual(root_positions(states[21].helpers), [29])
        self.assertEqual(root_positions(states[21].dependencies), [24, 29])
        self.assertEqual(parents[21], {(24, 'copy'), (29, 'helper')})

    def test_full_horizon_is_required(self):
        row = np.zeros(32, dtype=int)
        row[8] = 2
        path = self.simulate(row, 'symbiotic', 2)
        config = json.loads((path / 'config.json').read_text())
        config['trace_steps'] = 1
        (path / 'config.json').write_text(json.dumps(config))
        with self.assertRaises(ValueError):
            analyze(path, [2], 8)

    def test_untraced_mutation_helper_prevents_dependency_certificate(self):
        row = np.zeros(32, dtype=int)
        row[8], row[10] = 2, -1
        _, arr, events = self.step(row, 'galloway_B')
        previous = initial_lineages(arr[0])
        previous[10] = CellLineage(0, 1 << 10, 0, True, True)
        states, _, _, _ = propagate_step(arr[0], arr[1], previous, events)
        self.assertFalse(states[7].unknown)
        self.assertTrue(states[7].dependency_unknown)

    def test_possible_root_coverage_does_not_guarantee_all_components(self):
        ambiguous = [CellLineage(3, 3), CellLineage(3, 3)]
        support = child_support(ambiguous, 0, [8, 8], 3)
        self.assertEqual(support['copy_roots'], [0, 1])
        self.assertEqual(support['guaranteed_copy_roots'], [])
        self.assertFalse(support['exclusive_full_founder_copying'])


if __name__ == '__main__':
    unittest.main()
