#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Three cumulative stills from each frozen world; never calls the simulator."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT, read_csv, save_json, sha
from barricelli.plot import PALETTE
from art import font, rgb
from PIL import Image, ImageDraw
import numpy as np

OUT = ROOT / 'results/art/temporal'
DESCRIPTIONS = ROOT / 'configs/temporal_art.json'
STAGES = ('early', 'middle', 'late')


def protected_files(design):
    for name, digest in design['protected_files_sha256'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Protected original changed: ' + name)


def preview(path, dimensions):
    with Image.open(path) as image:
        image.thumbnail(dimensions, Image.Resampling.NEAREST)
        target = path.with_name(path.stem + '.preview.png')
        image.save(target)
    return str(target.relative_to(ROOT))


def export(world, design, observations):
    source = ROOT / world['source_run']
    for file, field in [('trajectory.csv', 'trajectory_sha256'), ('initial.csv', 'initial_sha256'),
                        ('config.json', 'config_sha256'), ('provenance.json', 'provenance_sha256')]:
        if sha(source / file) != world[field]:
            raise ValueError('Frozen world mismatch: ' + str(source / file))
    if sha(ROOT / design['fixed_presentation']['palette_file']) != design['fixed_presentation']['palette_sha256']:
        raise ValueError('Frozen palette changed')
    original_recipe = ROOT / 'results/art' / (world['slug'] + '.recipe.json')
    if sha(original_recipe) != world['original_recipe_sha256']:
        raise ValueError('Original print recipe changed')
    original = json.loads(original_recipe.read_text())
    config = json.loads((source / 'config.json').read_text())
    provenance = json.loads((source / 'provenance.json').read_text())
    versions = {str(p.relative_to(ROOT)): sha(p) for p in [pathlib.Path(__file__), ROOT / 'scripts/art.py',
                ROOT / 'barricelli/plot.py', ROOT / 'barricelli/run.py', DESCRIPTIONS, OUT / 'design.json']}
    versions[original['font_file']] = sha(original['font_file'])
    folder = OUT / world['slug']
    folder.mkdir(exist_ok=True)
    recipe_path = folder / 'series.recipe.json'
    if recipe_path.exists():
        cached = json.loads(recipe_path.read_text())
        outputs = [*cached['panels'], cached['triptych']]
        if (cached['renderer_inputs_sha256'] == versions and cached['world'] == world
                and all((ROOT / item['file']).is_file() and (ROOT / item['preview_file']).is_file() and
                        sha(ROOT / item['file']) == item['sha256'] and
                        sha(ROOT / item['preview_file']) == item['preview_sha256'] for item in outputs)):
            return cached
    array = read_csv(source / 'trajectory.csv')
    np.testing.assert_array_equal(array[:1], read_csv(source / 'initial.csv'))
    assert array.shape == (world['updates'] + 1, original['width']) == (512, 511)
    scale = original['print']['integer_scale']
    dimensions = original['print']['dimensions']
    assert dimensions == design['fixed_presentation']['canvas_dimensions']
    assert scale == design['fixed_presentation']['integer_cell_scale']
    x, y = design['fixed_presentation']['numerical_origin']
    w, h = array.shape[1] * scale, array.shape[0] * scale
    assert [w, h] == design['fixed_presentation']['full_numeric_extent']
    numeric = rgb(array)
    panels = []
    for stage, step in zip(STAGES, design['elapsed_steps']):
        canvas = Image.new('RGB', tuple(dimensions), PALETTE['background'])
        draw = ImageDraw.Draw(canvas)
        draw.text((x, 45), world['title'], font=font(44), fill=PALETTE['text'])
        label = f'{stage.upper()} / ELAPSED STEP {step} OF {world["updates"]}'
        draw.text((dimensions[0] - x - draw.textlength(label, font=font(24)), 60),
                  label, font=font(24), fill=PALETTE['accent'])
        draw.text((x, 110), f'{config["model"]} / {config["norm"]} | seed {config["seed"]} | W{config["width"]} · T{config["steps"]}',
                  font=font(24), fill=PALETTE['accent'])
        # Crop before resizing: every reached row keeps exactly nine pixels.
        reached = numeric.crop((0, 0, array.shape[1], step + 1))
        enlarged = reached.resize((w, (step + 1) * scale), Image.Resampling.NEAREST)
        canvas.paste(enlarged, (x, y))
        reached.close(); enlarged.close()
        draw.text((x, h + 220), 'POSITION x 0–510 →     TIME t 0–511 ↓     /     FUTURE TIME BLANK',
                  font=font(26), fill=PALETTE['text'])
        draw.text((x, h + 268), 'Value colors; no organism identities. Source ' + world['trajectory_sha256'][:20],
                  font=font(22), fill=PALETTE['accent'])
        path = folder / (stage + '.png')
        canvas.save(path, dpi=(300, 300)); canvas.close()
        preview_file = preview(path, (980, 1000))
        row = array[step]
        panel = {'stage': stage, 'elapsed_step': step, 'included_rows': [0, step],
                 'unreached_rows': [step + 1, world['updates']] if step < world['updates'] else None,
                 'file': str(path.relative_to(ROOT)), 'sha256': sha(path),
                 'preview_file': preview_file, 'preview_sha256': sha(ROOT / preview_file),
                 'dimensions': dimensions, 'numerical_crop': [x, y, x + w, y + h],
                 'integer_cell_scale': scale, 'observation': observations[stage],
                 'elapsed_row_counts': {'nonzero_cells': int(np.count_nonzero(row)),
                                        'distinct_nonzero_values': int(len(np.unique(row[row != 0])))} }
        panels.append(panel)
        save_json(folder / (stage + '.recipe.json'), {'world': world, 'panel': panel,
                  'fixed_presentation': design['fixed_presentation'], 'renderer_inputs_sha256': versions,
                  'simulation_source_version': provenance['repository_head'],
                  'simulation_binary_sha256': provenance['binary_sha256'],
                  'source_provenance': world['source_run'] + '/provenance.json'})
        print(world['slug'], stage, step, dimensions, flush=True)
    numeric.close()
    # Hold one panel at a time, never three decoded high-resolution sources.
    composed = Image.new('RGB', (dimensions[0] * 3, dimensions[1]), PALETTE['background'])
    for index, panel in enumerate(panels):
        with Image.open(ROOT / panel['file']) as image:
            composed.paste(image, (dimensions[0] * index, 0))
    path = folder / 'triptych.png'
    composed.save(path, dpi=(300, 300)); composed.close()
    preview_file = preview(path, (2400, 1000))
    triptych = {'file': str(path.relative_to(ROOT)), 'sha256': sha(path),
               'preview_file': preview_file, 'preview_sha256': sha(ROOT / preview_file),
               'dimensions': [dimensions[0] * 3, dimensions[1]], 'resampling': 'none',
               'panel_origins': [[dimensions[0] * i, 0] for i in range(3)], 'order': list(STAGES)}
    result = {'title': world['title'], 'slug': world['slug'], 'world': world, 'configuration': config,
              'source_run': world['source_run'], 'source_provenance': world['source_run'] + '/provenance.json',
              'simulation_source_version': provenance['repository_head'],
              'simulation_source_tree_sha256': provenance['source_tree_sha256'],
              'simulation_binary_sha256': provenance['binary_sha256'],
              'renderer_inputs_sha256': versions, 'palette_sha256': original['palette_sha256'],
              'fixed_presentation': design['fixed_presentation'], 'panels': panels, 'triptych': triptych,
              'recipe_file': str(recipe_path.relative_to(ROOT)),
              'interpretation': 'Cumulative aesthetic observations; no metric or claim of increasing complexity.',
              'interventions': config.get('modifications', []),
              'presentation_only': 'Mask future rows with background; no simulated intervention or altered history.'}
    save_json(recipe_path, result)
    print(world['slug'], 'triptych', triptych['dimensions'], flush=True)
    return result


def main():
    design = json.loads((OUT / 'design.json').read_text())
    protected_files(design)
    descriptions = {work['slug']: work['observations'] for work in json.loads(DESCRIPTIONS.read_text())['works']}
    series = [export(world, design, descriptions[world['slug']]) for world in design['worlds']]
    protected_files(design)
    save_json(OUT / 'manifest.json', {'design_file': 'results/art/temporal/design.json',
              'series': series, 'stage_panels': 9, 'triptychs': 3,
              'new_simulations': 0, 'new_model_api_calls': 0, 'animation_frames_exported': 0})


if __name__ == '__main__':
    main()
