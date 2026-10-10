#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""R7 figures: saved native integers and recorded edges, no model imagery."""
import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.plot import PALETTE, image, plt, save
from barricelli.run import ROOT, read_csv, save_json

BASE = ROOT / 'results/partner_dyad'
OUT = ROOT / 'results/figures'


def panel(ax, trajectory, title, left, right, textual=False):
    arr = read_csv(trajectory)[:, left:right]
    image(ax, arr, title, textual=textual)
    tick = list(range(0, right - left, max(1, (right - left) // 4)))
    ax.set_xticks(tick); ax.set_xticklabels([left + x for x in tick])
    return {'trajectory': str(trajectory.relative_to(ROOT)), 'columns': [left, right],
            'saved_times': [0, len(arr) - 1], 'horizontal_axis': 'global position x',
            'vertical_axis': 'time t downward', 'cell_rendering': 'nearest, unsmoothed; integers when noted'}


def first_generation():
    path = BASE / 'runs/construction_d4_intact'
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), facecolor=PALETTE['background'])
    panels = [panel(axes[0], path / 'trace/trajectory.csv',
                    'One founder → two first-generation dyads\nFour recorded copies; two require a partner', 232, 253, True),
              panel(axes[1], path / 'continuation/trajectory.csv',
                    'Saved 12-update continuation\nA regular lattice grows to 13 exact dyads', 184, 305)]
    events = path / 'trace/events.csv'
    with events.open() as stream:
        for edge in csv.DictReader(stream):
            if edge['outcome'] == 'copy':
                axes[0].annotate('', xy=(int(edge['target']) - 232, .84),
                                 xytext=(int(edge['source']) - 232, .16),
                                 arrowprops={'arrowstyle': '->', 'color': PALETTE['accent'],
                                             'lw': 1.6, 'linestyle': '--' if edge['helpers'] else '-'})
    axes[0].set_yticks([0, 1]); axes[0].set_ylim(1.5, -.5)
    fig.subplots_adjust(left=.065, right=.985, bottom=.2, top=.85, wspace=.24)
    fig.text(.065, .055, 'Designed t0 inoculation: +4 at x240, −4 at x244. Historical symbiotic arithmetic is unchanged.\n'
             'Cyan arrows follow saved native copying events; dashed arrows have an old-row helper. Time increases downward.',
             color=PALETTE['text'], fontsize=9)
    save(fig, OUT / 'partner_dyad_first_generation.png',
         'R7 designed partner-assisted numerical copying control. Saved t0 cells +4 at240 and−4 at244 '
         'produce dyads beginning236 and244 at t1. Every component retains its distinct original copying root. '
         'Four source-specific copy events, including two helper-enabled events, are independently audited; '
         'arrows show those recorded edges only. The right panel is a saved numerical continuation, with13 '
         'exact dyads at t12. Its repeated lattice does not establish evolved symbiosis or organism boundaries. '
         'Initial arrangement is imposed; every later displayed value comes from the unchanged historical norm. Time increases downward.',
         [path / 'trace/trajectory.csv', path / 'continuation/trajectory.csv', events,
          path / 'trace/detector.json', path / 'first_step_audit.json', path / 'oracle/continuation.verification.json'])
    save_json(OUT / 'partner_dyad_first_generation.recipe.json', {'panels': panels,
              'overlays': {'source': str(events.relative_to(ROOT)), 'selection': 'copy events at time0',
                           'solid': 'direct copy', 'dashed': 'helper-enabled copy'}})


def interventions():
    conditions = ['intact', 'positive_removed', 'negative_removed', 'wrong_negative_same_occupancy',
                  'composition_shuffled_fixed_gaps', 'spacing_shift', 'rescue', 'helpers_disabled']
    fig, axes = plt.subplots(2, 4, figsize=(15, 9), facecolor=PALETTE['background'])
    panels, sources = [], [BASE / 'design.json']
    for ax, condition in zip(axes.flat, conditions):
        path = BASE / 'runs' / ('construction_d4_' + ('intact' if condition == 'helpers_disabled' else condition))
        trajectory = path / ('oracle/helpers_disabled.csv' if condition == 'helpers_disabled' else 'continuation/trajectory.csv')
        title = condition.replace('_', ' ')
        if condition == 'helpers_disabled': title += '\nImposed rule counterfactual'
        else: title += '\nImposed initial-state treatment' if condition != 'intact' else '\nDesigned inoculation'
        panels.append(panel(ax, trajectory, title, 184, 305))
        sources.append(trajectory)
    fig.subplots_adjust(left=.06, right=.99, bottom=.13, top=.88, wspace=.35, hspace=.4)
    fig.text(.06, .03, 'Same axes, dimensions and 12-update budget. Removing either partner leaves one translating cell.\n'
             'Background matched-damage controls and all reserved settings remain in the complete numerical record.',
             color=PALETTE['text'], fontsize=9)
    save(fig, OUT / 'partner_dyad_interventions.png',
         'R7 construction causal controls, saved integer histories. Component deletions, wrong negative value, '
         'occupied-site shuffle and one-cell spacing shift eliminate exact dyad copying. Exact restoration '
         'recovers the intact history. The helpers-disabled panel is a separately saved, explicitly imposed '
         'rule intervention computed by the independent oracle: only direct copying remains. Every panel '
         'shows global positions184–304 and times0–12, downward. These are explanatory selected construction '
         'histories; all matched background controls and reserved confirmations are retained separately.', sources)
    save_json(OUT / 'partner_dyad_interventions.recipe.json', {'panels': panels,
              'selection': 'all seven empty-background construction conditions plus declared rule counterfactual'})


def confirmation():
    path = BASE / 'runs/confirmation_long_d4_intact'
    fig, axes = plt.subplots(1, 3, figsize=(16, 6), facecolor=PALETTE['background'])
    panels = [panel(axes[0], path / 'continuation/trajectory.csv',
                    'Reserved longer setting\n97 exact dyads at t96; regular lattice', 600, 1401)]
    sources = [path / 'continuation/trajectory.csv', BASE / 'summary.json']
    for index, ax in enumerate(axes[1:], 1):
        probe = BASE / 'recovery' / f'construction_d4_child{index}'
        panels.append(panel(ax, probe / 'continuation/trajectory.csv',
                            f'First child {index}, isolated\nReproduces again; 13 dyads at t12', 184, 305))
        sources.extend([probe / 'continuation/trajectory.csv', probe / 'extraction.json', probe / 'trace/detector.json'])
    fig.subplots_adjust(left=.055, right=.99, bottom=.19, top=.84, wspace=.3)
    fig.text(.055, .045, 'Left: saved W2048, T96 continuation; no boundary encounter. Right: externally imposed isolation and translation of actual saved children.\n'
             'Ancestry is audited at t0 → t1 only. Long histories match an uninstrumented unchanged-source oracle and the predeclared lattice formula.',
             color=PALETTE['text'], fontsize=9)
    save(fig, OUT / 'partner_dyad_confirmation.png',
         'R7 reserved 96-update numerical confirmation and actual first-child isolation assays. The longer '
         'dyad grows to97 exact guarded footprints before boundary encounters, matching the analytical lattice '
         'and every cell of Taylor unchanged-source oracle. The two actual first children of the construction '
         'are separately extracted, translated to240 in empty width512 worlds, and both produce two '
         'partner-assisted dyads at their first update and13 at update12. Extraction and clearing are '
         'external interventions, not spontaneous additional copying. Full lineage claims are limited to '
         'the traced first update; regular spatial partition does not establish biological organism boundaries. Time increases downward.', sources)
    save_json(OUT / 'partner_dyad_confirmation.recipe.json', {'panels': panels,
              'selection': 'reserved long intact setting and both construction children; aggregate results in experiment summary'})


def main():
    summary = json.loads((BASE / 'summary.json').read_text())
    if summary['baseline_cases_completed'] < 10: raise ValueError('finish construction before rendering')
    first_generation(); interventions()
    if summary['baseline_cases_completed'] == 31: confirmation()
    print('R7 figures rendered from saved numerical histories')


if __name__ == '__main__': main()
