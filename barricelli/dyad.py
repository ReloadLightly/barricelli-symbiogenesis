# SPDX-License-Identifier: GPL-3.0-only
"""Independent first-step formula audit, separate from R6 ancestry propagation.

Only the proposed opposite-sign dyad is eligible for this analytic audit. It
checks exact source-specific events, helpers and numbers, not appearance alone.
"""
import csv

import numpy as np

from .run import read_csv, sha


def formula(width, founder, d, time):
    """Analytically predicted lattice, before any boundary encounters."""
    if d < 3 or founder - d * time < 2 or founder + d * (time + 1) > width - 3:
        raise ValueError('formula outside the declared guarded, boundary-free domain')
    row = np.zeros(width, dtype=np.int32)
    for k in range(time + 1):
        x = founder - d * time + 2 * d * k
        row[x], row[x + d] = d, -d
    return row


def audit_first_step(path, founder, d):
    """Check four distinct copied roots and exactly two partner-enabled writes.

    No imports from the lineage detector, simulator adapter or its hook code.
    Extra initial cells are allowed only if none of their writes affect the
    predicted children's cells or two-cell guards.
    """
    arr = read_csv(path / 'trajectory.csv')
    if len(arr) != 2 or arr[0, founder] != d or arr[0, founder + d] != -d:
        raise ValueError('not a one-update dyad run')
    expected = [
        (founder, founder + d, 1, d, ''),
        (founder, founder - d, 2, d, f'{founder + d}:{-d}'),
        (founder + d, founder, 1, -d, ''),
        (founder + d, founder + 2 * d, 2, -d, f'{founder}:{d}'),
    ]
    actual = []
    scratch = np.zeros(arr.shape[1], dtype=np.int32)
    protected = set()
    for start in (founder - d, founder + d):
        protected.update(range(start - 2, start + d + 3))
    with (path / 'events.csv').open() as stream:
        for e in csv.DictReader(stream):
            t, source, target, depth, value, before, after = (
                int(e[k]) for k in ('time', 'source', 'target', 'depth', 'value', 'before', 'after'))
            if t != 0 or not 0 <= source < arr.shape[1] or arr[0, source] != value:
                raise ValueError('invalid first-step source or time')
            if not 0 <= target < arr.shape[1]:
                raise ValueError('unexpected out-of-bounds first-step attempt')
            if before != scratch[target] or after != value or e['outcome'] != 'copy':
                raise ValueError('first-step write is not a fresh numerical copy')
            scratch[target] = after
            if source in (founder, founder + d):
                actual.append((source, target, depth, value, e['helpers']))
            elif target in protected:
                raise ValueError('external source enters a child or its guard')
    if actual != expected:
        raise ValueError('source-specific dyad edges/helpers differ from the analytical prediction')
    if not np.array_equal(scratch, arr[1]):
        raise ValueError('ordered writes do not reconstruct the saved next row')
    local = formula(arr.shape[1], founder, d, 1)
    for start in (founder - d, founder + d):
        if not np.array_equal(arr[1, start - 2:start + d + 3], local[start - 2:start + d + 3]):
            raise ValueError('predicted child or guard differs from saved numbers')
    return {'passed': True, 'children': [founder - d, founder + d],
            'copied_edges': len(actual), 'helper_enabled_edges': sum(bool(e[-1]) for e in actual),
            'predicted_events': [list(e) for e in expected],
            'independence': 'closed-form source-specific audit; does not call R6 lineage propagation',
            'sources_sha256': {name: sha(path / name) for name in ('initial.csv', 'trajectory.csv', 'events.csv')},
            'auditor_sha256': sha(__file__)}
