#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Independently check cumulative raster pixels, composition and preservation."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT, read_csv, save_json, sha
from barricelli.plot import color, PALETTE
import numpy as np
from PIL import Image


def check():
    directory = ROOT / 'results/art/temporal'
    manifest = json.loads((directory / 'manifest.json').read_text())
    design = json.loads((directory / 'design.json').read_text())
    assert manifest['new_simulations'] == manifest['new_model_api_calls'] == manifest['animation_frames_exported'] == 0
    assert len(manifest['series']) == manifest['triptychs'] == 3
    assert sum(len(s['panels']) for s in manifest['series']) == manifest['stage_panels'] == 9
    background = np.array(list(bytes.fromhex(PALETTE['background'][1:])), dtype=np.uint8)
    checked = []
    for series, world in zip(manifest['series'], design['worlds']):
        assert series['world'] == world
        source = ROOT / world['source_run']
        for file, key in [('trajectory.csv', 'trajectory_sha256'), ('initial.csv', 'initial_sha256'),
                          ('config.json', 'config_sha256'), ('provenance.json', 'provenance_sha256')]:
            assert sha(source / file) == world[key], str(source / file)
        assert series['configuration'] == json.loads((source / 'config.json').read_text())
        assert series == json.loads((ROOT / series['recipe_file']).read_text())
        assert series['fixed_presentation'] == design['fixed_presentation']
        for path, digest in series['renderer_inputs_sha256'].items():
            assert sha(ROOT / path) == digest, path
        assert sha(ROOT / design['fixed_presentation']['palette_file']) == series['palette_sha256']
        arr = read_csv(source / 'trajectory.csv')
        np.testing.assert_array_equal(arr[:1], read_csv(source / 'initial.csv'))
        assert arr.shape == (512, 511)
        colors = np.zeros((*arr.shape, 3), dtype=np.uint8)
        for value in np.unique(arr):
            colors[arr == value] = list(bytes.fromhex(color(value)[1:]))
        assert [p['elapsed_step'] for p in series['panels']] == [170, 341, 511]
        for panel in series['panels']:
            assert panel['dimensions'] == [4919, 4968]
            assert panel['integer_cell_scale'] == 9
            assert panel['numerical_crop'] == [160, 180, 4759, 4788]
            assert panel['included_rows'] == [0, panel['elapsed_step']]
            assert panel['unreached_rows'] == ([panel['elapsed_step'] + 1, 511] if panel['elapsed_step'] < 511 else None)
            stage_recipe = json.loads((directory / world['slug'] / (panel['stage'] + '.recipe.json')).read_text())
            assert stage_recipe['world'] == world and stage_recipe['panel'] == panel
            assert stage_recipe['renderer_inputs_sha256'] == series['renderer_inputs_sha256']
            assert sha(ROOT / panel['file']) == panel['sha256']
            assert sha(ROOT / panel['preview_file']) == panel['preview_sha256']
            expected_cells = colors.copy()
            expected_cells[panel['elapsed_step'] + 1:] = background
            # Whole numerical raster, in short strips; no huge comparison arrays.
            with Image.open(ROOT / panel['file']) as image:
                assert list(image.size) == panel['dimensions'] and image.mode == 'RGB'
                assert all(abs(dpi - 300) < .01 for dpi in image.info['dpi'])
                for row in range(0, arr.shape[0], 16):
                    last = min(row + 16, arr.shape[0])
                    expected = np.repeat(np.repeat(expected_cells[row:last], 9, axis=0), 9, axis=1)
                    actual = np.array(image.crop((160, 180 + row * 9, 4759, 180 + last * 9)))
                    np.testing.assert_array_equal(actual, expected, err_msg=panel['file'])
        triptych = series['triptych']
        assert triptych['dimensions'] == [14757, 4968]
        assert triptych['panel_origins'] == [[0, 0], [4919, 0], [9838, 0]]
        assert triptych['resampling'] == 'none' and triptych['order'] == ['early', 'middle', 'late']
        assert sha(ROOT / triptych['file']) == triptych['sha256']
        assert sha(ROOT / triptych['preview_file']) == triptych['preview_sha256']
        with Image.open(ROOT / triptych['file']) as composed:
            assert list(composed.size) == triptych['dimensions']
            for index, panel in enumerate(series['panels']):
                with Image.open(ROOT / panel['file']) as image:
                    for y in range(0, 4968, 64):
                        bottom = min(y + 64, 4968)
                        actual = np.array(composed.crop((index * 4919, y, (index + 1) * 4919, bottom)))
                        expected = np.array(image.crop((0, y, 4919, bottom)))
                        np.testing.assert_array_equal(actual, expected, err_msg=triptych['file'])
        checked.append({'world': world['source_run'], 'seed': world['seed'],
                        'elapsed_steps': [170, 341, 511], 'all_reached_and_blank_future_pixels_exact': True,
                        'triptych_all_pixels_equal_panels': True, 'one_saved_world_and_fixed_scales': True})
        print(world['slug'], 'all stage and triptych pixels exact', flush=True)
    for name, digest in design['protected_files_sha256'].items():
        assert sha(ROOT / name) == digest, 'Protected original changed: ' + name
    atlas = json.loads((ROOT / 'atlas/manifest.json').read_text())
    if 'temporal_series' in atlas:
        assert len(atlas['temporal_series']) == 3
        for item in atlas['temporal_series']:
            assert sha(ROOT / item['recipe_file']) == item['recipe_sha256']
    report = {'series': checked, 'panels': 9, 'triptychs': 3,
              'numerical_panel_pixels_checked': 9 * 4599 * 4608,
              'composed_triptych_pixels_checked': 3 * 14757 * 4968,
              'protected_original_files': len(design['protected_files_sha256']),
              'protected_original_hashes_exact': True, 'no_reruns_or_animation_exports': True}
    save_json(directory / 'checks.json', report)
    return report


if __name__ == '__main__':
    check()
