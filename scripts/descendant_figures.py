#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Illustrate R6 using saved integer histories and observed copying edges only."""
import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT, read_csv, save_json
from barricelli.plot import PALETTE, image, plt, save

BASE = ROOT / 'results/descendant_detector'
OUT = ROOT / 'results/figures'


def panel(ax, path, title, left, right, last=None):
    arr = read_csv(path / 'trajectory.csv')
    shown = arr[:last, left:right]
    image(ax, shown, title)
    tick_positions = list(range(0, right - left, max(1, (right - left) // 4)))
    ax.set_xticks(tick_positions)
    ax.set_xticklabels([left + x for x in tick_positions])
    return {'run': str(path.relative_to(ROOT)), 'columns': [left, right],
            'saved_times': [0, len(shown) - 1], 'interpolation': 'nearest',
            'horizontal_axis': 'saved global position x', 'vertical_axis': 'time t downward'}


def controls():
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), facecolor=PALETTE['background'])
    specs = [
        ('copying_positive', 'Basic copying control\nTwo recovered children share one founder; no helpers', 56, 208),
        ('unrelated_lookalikes', 'Unrelated lookalikes\nTwo identical templates; distinct founders', 56, 160),
        ('translation_negative', 'Translation control\nOne persistent moving footprint; no branching', 56, 160),
        ('tiling_negative', 'Historical motif under exclusion\n25 unguarded matches; no detached branch', 64, 480),
    ]
    sources, panels = [], []
    for ax, (ident, title, left, right) in zip(axes.flat, specs):
        path = BASE / 'runs' / ident
        panels.append(panel(ax, path, title, left, right))
        sources.extend([path / 'trajectory.csv', path / 'detector.json'])
    # Arrows come from surviving t0 -> t1 numerical copying parents, including
    # both destinations of each founding component. They are explanations,
    # not scripted trajectories or organism motion.
    edge_path = BASE / 'runs/copying_positive/lineage_edges.csv'
    with edge_path.open() as stream:
        for edge in csv.DictReader(stream):
            if int(edge['child_time']) == 1 and edge['kind'] == 'copy':
                axes.flat[0].annotate('', xy=(int(edge['child_x']) - 56, .86),
                                      xytext=(int(edge['parent_x']) - 56, .15),
                                      arrowprops={'arrowstyle': '->', 'color': PALETTE['accent'], 'lw': 1.2})
    sources.extend([edge_path, BASE / 'calibration.json'])
    fig.subplots_adjust(left=.07, right=.98, top=.9, bottom=.1, wspace=.25, hspace=.42)
    fig.text(.07, .025, 'Every panel is a saved native trajectory. Cyan arrows: recorded copying edges, t0 → t1.\n'
             'Basic copying is a numerical calibration; it does not establish partner-dependent collective reproduction.',
             color=PALETTE['text'], fontsize=9)
    save(fig, OUT / 'descendant_detector_controls.png',
         'R6 native numerical detector controls, fixed integer inoculations. The basic two-cell [8,8] founder '
         'branches into detached copied footprints and both selected children persist after isolation. The basic '
         '[1000,1000] lookalikes remain unrelated, the symbiotic [5,5] motif translates without branching, and '
         'the exclusion Figure7 motif expands a tiled domain. All controls were predeclared; plots are explicit '
         'spatial crops of complete saved horizons. Time increases downward. Arrows are observed copying parents.', sources)
    save_json(OUT / 'descendant_detector_controls.recipe.json', {'panels': panels,
               'overlays': {'source': str(edge_path.relative_to(ROOT)), 'selection': 'child_time=1, kind=copy'}})


def assays():
    conditions = ['intact', 'helper_removed', 'same_type_damage_elsewhere',
                  'wrong_helper_same_occupancy', 'composition_shuffled_fixed_gaps', 'rescue']
    candidates = ['historical_figure7', 'generated_conditional3002']
    fig, axes = plt.subplots(2, 6, figsize=(19, 8), facecolor=PALETTE['background'])
    sources, panels = [BASE / 'summary.json'], []
    for row, candidate in enumerate(candidates):
        for col, condition in enumerate(conditions):
            path = BASE / 'runs' / f'exploration_{candidate}_x224_{condition}'
            title = candidate.replace('_', ' ') + '\n' + condition.replace('_', ' ')
            panels.append(panel(axes[row, col], path, title, 64, 480))
            sources.extend([path / 'trajectory.csv', path / 'detector.json'])
    fig.subplots_adjust(left=.045, right=.995, top=.88, bottom=.12, wspace=.4, hspace=.4)
    fig.text(.045, .025, 'Selected explanatory placement x224; W512, 48 updates; identical axes and empty exterior backgrounds.\n'
             'Complete aggregate: 36 exploratory and 24 reserved longer treatment worlds; zero detached common-founder pairs.',
             color=PALETTE['text'], fontsize=10)
    save(fig, OUT / 'descendant_detector_assays.png',
         'R6 treatment trajectories for both recorded motifs, selected explanatory placement224. All six '
         'predeclared treatments use width512 and48 updates, shown positions64–479 with time increasing downward. '
         'Numerical dynamics generate every form; inoculation, ablation, wrong-value replacement, shuffle '
         'and exact rescue are externally imposed interventions. Full outcomes include all60 treatment worlds. '
         'No detached common-founder pair occurs, including the reserved width1024/96-update cohort.', sources)
    save_json(OUT / 'descendant_detector_assays.recipe.json', {'panels': panels,
               'selection': 'both motifs, every declared condition, exploratory placement224; illustrative selection, not aggregate evidence'})


def main():
    summary = json.loads((BASE / 'summary.json').read_text())
    if summary['baseline_worlds_completed'] != summary['baseline_worlds_planned']:
        raise ValueError('finish the predeclared experiment before rendering its final figures')
    controls()
    assays()
    print('R6 figures rendered from saved trajectories and lineage evidence')


if __name__ == '__main__':
    main()
