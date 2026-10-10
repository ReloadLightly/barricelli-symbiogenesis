#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Complete native-run register, including assays and unselected explorations."""
import csv,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,save_json

def main():
 rows=[]
 for p in sorted((ROOT/'results').rglob('provenance.json')):
  path=p.parent; c=json.loads((path/'config.json').read_text()); s=json.loads((path/'statistics.json').read_text()); prov=json.loads(p.read_text())
  rows.append({'id':str(path.relative_to(ROOT/'results')),'path':str(path.relative_to(ROOT)),'stage':path.relative_to(ROOT/'results').parts[0],'model':c['model'],'variant':c.get('variant',c['norm']),'norm':c['norm'],'seed':c.get('seed'),'width':c['width'],'steps':c['steps'],'cell_updates':c['width']*c['steps'],
   'engine_seconds':s['engine_seconds'],'process_seconds':s['process_seconds'],'max_rss_kib':s['max_rss_kib'],'attempted_copies':s['attempted_copies'],'accepted_outcomes':s['accepted_outcomes'],'collisions':s['collisions'],'newly_produced_values':s['newly_produced_values'],'erasures':s['erasures'],
   'initial_sha256':prov['initial_sha256'],'trajectory_sha256':prov['trajectory_sha256'],'source_tree_sha256':prov['source_tree_sha256']})
 for row in rows:
  corrected=ROOT/'results/corrections/descriptor_v2/runs'/pathlib.Path(row['path']).relative_to('results')/'analysis.json'
  row['analysis_file']=str(corrected.relative_to(ROOT)) if corrected.exists() else None
 save_json(ROOT/'results/run_register.json',rows)
 with (ROOT/'results/run_register.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
 summary={'native_runs':len(rows),'cell_updates':sum(r['cell_updates'] for r in rows),'engine_seconds_sum':sum(r['engine_seconds'] for r in rows),'process_seconds_sum':sum(r['process_seconds'] for r in rows),'max_native_rss_kib':max(r['max_rss_kib'] for r in rows),'count_by_stage':{stage:sum(r['stage']==stage for r in rows) for stage in sorted(set(r['stage'] for r in rows))},'excluded_from_counts':['original executable fixture-oracle replays','temporary Java source-level oracle replays','separate unchanged-source symbiotic oracle replays and helpers-disabled counterfactuals','synthetic descriptor-control histories','development reruns and tests','compressed earlier metadata and incomplete-attempt archives'],'budget_scope':'retained scientific native trajectories, not all development compute'}
 save_json(ROOT/'results/resource_summary.json',summary); print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
