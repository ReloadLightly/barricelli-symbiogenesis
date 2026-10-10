#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Reanalyze saved trajectories, preserving every original analysis in place."""
import json,pathlib,sys,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
from barricelli.run import ROOT,read_csv,sha,save_json
from barricelli.descriptors import describe,coverage,mean_nearest_diversity,bootstrap_mean_ci
BASE=ROOT/'results/corrections/descriptor_v2'

def main():
 start=time.perf_counter(); records={}; deltas=[]; cache_valid={}
 previous_damage={r['id']:r for r in json.loads((BASE/'heterogeneity_summary.json').read_text())['damage']} if (BASE/'heterogeneity_summary.json').exists() else {}
 cached_version=json.loads((BASE/'summary.json').read_text()).get('descriptor_sha256') if (BASE/'summary.json').exists() else None
 paths=[p.parent for folder in ['search','search_confirmation','heterogeneity'] for p in (ROOT/'results'/folder).rglob('provenance.json')]
 paths += [p.parent for p in (ROOT/'results/descriptor_controls').glob('*/config.json')]
 for path in sorted(paths):
  original=path/'search_record.json' if (path/'search_record.json').exists() else path/'descriptors.json'
  if not original.exists() and not (path/'damage_outcome.json').exists(): continue
  c=json.loads((path/'config.json').read_text()); boundary=c.get('boundary','ring' if c['model']=='descriptor_control' else None)
  if boundary is None: raise ValueError('undeclared boundary')
  stats=json.loads((path/'statistics.json').read_text()) if (path/'statistics.json').exists() else None
  out=BASE/'runs'/path.relative_to(ROOT/'results'); saved=out/'analysis.json'
  prior=json.loads(saved.read_text()) if saved.exists() else None
  valid=bool(prior and cached_version==sha(ROOT/'barricelli/descriptors.py') and prior['trajectory_sha256']==sha(path/'trajectory.csv') and prior['boundary']==boundary)
  cache_valid[str(path.relative_to(ROOT))]=valid
  desc=prior['descriptors'] if valid else describe(read_csv(path/'trajectory.csv'),stats,boundary=boundary)
  old=json.loads(original.read_text()) if original.exists() else json.loads((path/'damage_outcome.json').read_text())['damaged']
  previous=old.get('descriptors',old); ident=str(path.relative_to(ROOT))
  changed={k:{'original':previous[k],'corrected':v} for k,v in desc.items() if k in previous and k!='descriptor_seconds' and previous[k]!=v}
  record={'source_run':ident,'trajectory_sha256':sha(path/'trajectory.csv'),'boundary':boundary,'descriptors':desc,
          'original_analysis':str(original.relative_to(ROOT)) if original.exists() else str((path/'damage_outcome.json').relative_to(ROOT)),'changes':changed}
  if 'method' in old: record.update({k:old[k] for k in ['method','repeat','trial','space_index','theta','seed','path','engine_seconds','process_seconds','max_rss_kib']})
  out=BASE/'runs'/path.relative_to(ROOT/'results'); out.mkdir(parents=True,exist_ok=True); save_json(out/'analysis.json',record)
  records[ident]=record; deltas.append({'run':ident,'changed_fields':list(changed)})
 methods=['random','novelty_archive','codex_feedback']; searches=[]
 for method in methods:
  for repeat in range(4):
   h=sorted([r for r in records.values() if r.get('method')==method and r.get('repeat')==repeat],key=lambda r:r['trial'])
   searches.append({'method':method,'repeat':repeat,'archive_coverage':coverage(h),'nearest_diversity':mean_nearest_diversity(h),'evaluations':len(h)})
 aggregate={m:{'coverage':bootstrap_mean_ci([r['archive_coverage'] for r in searches if r['method']==m]),'diversity':bootstrap_mean_ci([r['nearest_diversity'] for r in searches if r['method']==m])} for m in methods}
 paired={m:bootstrap_mean_ci([next(r['archive_coverage'] for r in searches if r['method']==m and r['repeat']==i)-next(r['archive_coverage'] for r in searches if r['method']=='random' and r['repeat']==i) for i in range(4)]) for m in methods[1:]}
 save_json(BASE/'search_summary.json',{'searches':searches,'aggregate':aggregate,'paired_coverage_difference_vs_random':paired,'policy_scope':'Reanalysis of originally selected runs; adaptive choices were based on original descriptors. This is not a rerun of corrected adaptive policies.'})
 original_environment=json.loads((ROOT/'results/heterogeneity/summary.json').read_text()); rows=[]
 for old in original_environment['rows']:
  row=dict(old); row.update(records[old['path']]['descriptors']); rows.append(row)
 contrasts=[]
 for cohort in ['exploration','confirmation']:
  for norm in ['galloway_AB_halves','galloway_AB_quarters','galloway_AB_temporal']:
   metrics={}
   for metric in ['tail_activity','tail_repeated4_fraction','retained_repeated4_signatures','tail_new4_signatures']:
    diffs=[]
    for seed in sorted({r['seed'] for r in rows if r['cohort']==cohort}):
     g={r['norm']:r for r in rows if r['cohort']==cohort and r['seed']==seed}; diffs.append(g[norm][metric]-.5*(g['galloway_A'][metric]+g['galloway_B'][metric]))
    metrics[metric]=bootstrap_mean_ci(diffs)
   contrasts.append({'cohort':cohort,'treatment':norm,'metrics':metrics})
 damage=[]
 for old in original_environment['damage']:
  path=ROOT/'results/heterogeneity'/old['id']; desc=records[str(path.relative_to(ROOT))]['descriptors']
  baseline=ROOT/'results/heterogeneity'/old['id'].removesuffix('__damage')
  control=previous_damage[old['id']]['undamaged_saved_window'] if old['id'] in previous_damage and cache_valid[str(baseline.relative_to(ROOT))] else describe(read_csv(baseline/'trajectory.csv')[256:385],boundary='ring')
  damage.append({**old,'damaged':desc,'undamaged_saved_window':control,'occupancy_difference':desc['tail_occupancy']-control['tail_occupancy'],'repeated4_difference':desc['tail_repeated4_fraction']-control['tail_repeated4_fraction']})
 save_json(BASE/'heterogeneity_summary.json',{'rows':rows,'contrasts':contrasts,'damage':damage,'scope':'saved baseline and matched-damage histories; original analyses remain preserved'})
 save_json(BASE/'summary.json',{'descriptor_version':2,'runs_reanalyzed':len(records),'runs_with_changes':sum(bool(r['changed_fields']) for r in deltas),'deltas':deltas,'elapsed_seconds':time.perf_counter()-start,'new_scientific_simulations':0,'descriptor_sha256':sha(ROOT/'barricelli/descriptors.py'),'original_archive_sha256':sha(BASE/'original_analyses.tar.gz'),'boundary_for_old_synthetic_controls':'ring explicitly assigned on correction: their imposed translation was generated with np.roll; this was absent from original control configs','original_search_means':{m:json.loads((ROOT/'results/search/summary.json').read_text())['aggregate'][m]['coverage']['mean'] for m in methods},'corrected_search_means':{m:aggregate[m]['coverage']['mean'] for m in methods},'adaptive_policy_limit':'Corrected historical summaries do not estimate what adaptive policies would have chosen under corrected feedback.'})
 print('corrected',len(records),'saved analyses; means',[aggregate[m]['coverage']['mean'] for m in methods])
if __name__=='__main__': main()
