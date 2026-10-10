# SPDX-License-Identifier: GPL-3.0-only
"""Adversarial tests of the independent source-specific dyad audit."""
import csv
import pathlib
import tempfile
import unittest

import numpy as np

from barricelli.dyad import audit_first_step


class IndependentDyadAudit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = pathlib.Path(self.temp.name)
        self.rows = np.zeros((2, 32), dtype=np.int32)
        self.rows[0, [12, 16]] = [4, -4]
        self.rows[1, [8, 12, 16, 20]] = [4, -4, 4, -4]
        self.events = [
            [0, 12, 16, 1, 4, 0, 4, 'copy', -1, ''],
            [0, 12, 8, 2, 4, 0, 4, 'copy', -1, '16:-4'],
            [0, 16, 12, 1, -4, 0, -4, 'copy', -1, ''],
            [0, 16, 20, 2, -4, 0, -4, 'copy', -1, '12:4'],
        ]

    def audit(self):
        np.savetxt(self.path / 'initial.csv', self.rows[:1], fmt='%d', delimiter=',')
        np.savetxt(self.path / 'trajectory.csv', self.rows, fmt='%d', delimiter=',')
        with (self.path / 'events.csv').open('w') as stream:
            writer = csv.writer(stream)
            writer.writerow(['time', 'source', 'target', 'depth', 'value', 'before', 'after', 'outcome', 'previous_writer', 'helpers'])
            writer.writerows(self.events)
        return audit_first_step(self.path, 12, 4)

    def test_source_specific_four_edge_fixture(self):
        result = self.audit()
        self.assertEqual(result['children'], [8, 16])
        self.assertEqual(result['helper_enabled_edges'], 2)

    def test_missing_enabling_partner_rejected_even_with_same_numbers(self):
        self.events[1][-1] = ''
        with self.assertRaises(ValueError): self.audit()

    def test_equal_valued_external_source_is_not_founder(self):
        self.rows[0, 13] = 4
        self.events[0][1] = 13
        with self.assertRaises(ValueError): self.audit()

    def test_wrong_write_order_rejected(self):
        self.events[0], self.events[1] = self.events[1], self.events[0]
        with self.assertRaises(ValueError): self.audit()

    def test_incomplete_trace_rejected(self):
        self.events.pop()
        with self.assertRaises(ValueError): self.audit()

    def test_occupied_guard_rejected(self):
        self.rows[0, 9] = self.rows[1, 9] = 1
        self.events.append([0, 9, 9, 1, 1, 0, 1, 'copy', -1, ''])
        with self.assertRaises(ValueError): self.audit()


if __name__ == '__main__': unittest.main()
