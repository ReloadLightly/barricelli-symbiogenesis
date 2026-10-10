#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build an offline, data-only atlas and complete linked native-run register."""
import html,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,read_csv,sha,save_json
from barricelli.plot import color
from PIL import Image

def main():
 selections=[('results/reconstruction/galloway2026','Confluence / 2026','Selected artwork; the complete six-run display ensemble is also available below.')]
 for seed in range(2027,2032): selections.append((f'results/ensemble/galloway{seed}',f'Published world / {seed}','Unselected display ensemble member. Diagonal traces indicate motion, not established organism identities.'))
 selections.extend([('results/reconstruction/figure07','Historical collective / Figure 7','Documented eight-cell pattern under exclusion. This short historical example demonstrates collective propagation.'),('results/ensemble/conditional3002','Conditional world / 3002','Generated trajectory from which an exact four-cell candidate motif was extracted. It forms a growing alternating domain.')])
 for norm in ['A','B','AB_halves','AB_quarters','AB_temporal']:
  selections.append((f'results/heterogeneity/exploration_6100_galloway_{norm}',f'Paired environment / {norm}','Same saved initial row and 512 updates. Spatial or temporal collision norms are explicitly imposed research extensions.'))
 selections.append(('results/heterogeneity/confirmation_9200_galloway_AB_halves','Longer check / spatial A:B','Fresh seed9200, 2048 updates. A longer nonrepeating history alone does not establish sustained innovation.'))
 parent='results/search/codex_feedback/repeat3/trial07'
 selections.append((parent,'Search neighborhood / starting world','Conversational feedback proposal from the equal-budget search. Nearby configuration changes are external design interventions.'))
 for name in ['density_down','density_up','next_layout','constituent_A']:
  selections.append((f'results/nearby/{name}','Nearby / '+name.replace('_',' '),'Saved configuration neighbor of the search world. Shared seed; exact integer starting states are independently saved.'))
 r6=ROOT/'results/descendant_detector/summary.json'
 if r6.exists() and json.loads(r6.read_text())['baseline_worlds_completed']==64:
  for ident,title,caption in [
   ('copying_positive','Copying calibration / basic','Designed two-cell inoculation under the unchanged historical basic norm. Detached numerical copies recover after isolation; no partner assistance, so this is a detector calibration.'),
   ('unrelated_lookalikes','Ancestry control / lookalikes','Two deliberately inoculated equal templates remain stationary under the basic norm. Their matching values do not imply a shared founder.'),
   ('translation_negative','Motion control / translation','Designed two-cell inoculation under the historical symbiotic norm. The footprint moves while remaining one copy.'),
   ('tiling_negative','Spread control / tiled domain','Historical Figure7 motif in an empty research world. Tiled growth creates many exact matches without a detached descendant pair.'),
   ('exploration_historical_figure7_x224_intact','Descendant assay / historical motif','Selected explanatory intact setting, x224, width512 and48 updates. Full experiment includes all treatments and longer reserved checks; no detached reproduction case was found.'),
   ('exploration_generated_conditional3002_x224_intact','Descendant assay / generated motif','Selected explanatory intact setting from the generated candidate. Its expanding alternating domain is distinct from detached reproduction.')]:
   selections.append(('results/descendant_detector/runs/'+ident,title,caption))
 r7=ROOT/'results/partner_dyad/summary.json'
 if r7.exists() and json.loads(r7.read_text())['baseline_cases_completed']==31:
  for condition in ['intact','positive_removed','negative_removed','wrong_negative_same_occupancy','composition_shuffled_fixed_gaps','spacing_shift','rescue']:
   selections.append(('results/partner_dyad/runs/construction_d4_'+condition+'/continuation',
                      'Partner dyad / '+condition.replace('_',' '),
                      'R7 designed +4/−4 pair under unchanged historical symbiotic arithmetic. Initial-state treatment is externally imposed. Intact and restored pairs produce two guarded numerical copies at t1; five perturbations prevent copying. This is a constructed control, not an evolved organism.'))
  for setting in ['confirmation_d3','confirmation_d5','confirmation_long_d4']:
   selections.append(('results/partner_dyad/runs/'+setting+'_intact/continuation',
                      'Reserved dyad / '+setting.removeprefix('confirmation_').replace('_',' '),
                      'Reserved deterministic robustness setting. Every number matches the separate unchanged-source oracle. The long setting reaches97 exact dyads at t96; a regular lattice does not establish organism boundaries or open-ended evolution.'))
  for child in [1,2]:
   selections.append((f'results/partner_dyad/recovery/construction_d4_child{child}/continuation',
                      f'Isolated dyad / child {child}',
                      'Actual saved first child, externally extracted and translated to x240 with exterior cleared. It reproduces at its first update after isolation and reaches13 exact dyads at t12. Isolation is an imposed assay; original branching arose from the numerical rule.'))
 worlds=[]; values=set()
 for path,title,caption in selections:
  run=ROOT/path; c=json.loads((run/'config.json').read_text()); arr=read_csv(run/'trajectory.csv'); flat=arr.ravel().tolist(); values.update(flat)
  worlds.append({'id':path.replace('/','--'),'title':title,'caption':caption,'model':c['model']+' / '+c['norm'],'path':path,'width':c['width'],'steps':c['steps'],'seed':c.get('seed'),'initialHash':sha(run/'initial.csv'),'values':flat,'neighbors':[]})
  corrected=ROOT/'results/corrections/descriptor_v2/runs'/pathlib.Path(path).relative_to('results')/'analysis.json'
  worlds[-1]['analysisPath']=str(corrected.relative_to(ROOT)) if corrected.exists() else None
 neighbor_ids=[w['id'] for w in worlds if w['path']==parent or w['path'].startswith('results/nearby/')]
 environment_ids=[w['id'] for w in worlds if 'exploration_6100_' in w['path']]
 dyad_ids=[w['id'] for w in worlds if w['path'].startswith('results/partner_dyad/runs/construction_d4_')]
 for w in worlds:
  group=neighbor_ids if w['id'] in neighbor_ids else environment_ids if w['id'] in environment_ids else dyad_ids if w['id'] in dyad_ids else []
  w['neighbors']=[v for v in group if v!=w['id']]
 prints=[]
 for p in sorted((ROOT/'results/art').glob('*.recipe.json')):
  recipe=json.loads(p.read_text()); slug=p.name.removesuffix('.recipe.json'); recipe['slug']=slug; prints.append(recipe)
  with Image.open(p.with_name(slug+'.png')) as im:
   im.thumbnail((980,1000),Image.Resampling.NEAREST); im.save(p.with_name(slug+'.preview.png'))
 payload={'worlds':worlds,'prints':prints,'colors':{str(v):list(bytes.fromhex(color(v)[1:])) for v in sorted(values)}}
 (ROOT/'atlas/data.js').write_text('/* Generated from saved CSVs; never generated by a model. */\nwindow.ATLAS='+json.dumps(payload,separators=(',',':'))+';\n')
 save_json(ROOT/'atlas/manifest.json',{'selection':'browsable subset for illustration; complete native-run register is separate','worlds':[{'path':w['path'],'trajectory_sha256':sha(ROOT/w['path']/'trajectory.csv')} for w in worlds],'palette_sha256':sha(ROOT/'configs/palette.json'),'numeric_payload_sha256':sha(ROOT/'atlas/data.js')})
 rows=json.loads((ROOT/'results/run_register.json').read_text()); body=[]
 for r in rows:
  path=html.escape(r['path']); body.append('<tr>'+''.join('<td>'+v+'</td>' for v in [f'<a href="../{path}/trajectory.csv">{html.escape(r["id"])}</a>',html.escape(r['model']),html.escape(r['norm']),str(r['seed']),str(r['width']),str(r['steps']),f'{r["process_seconds"]:.4f}',str(r['max_rss_kib']),f'<a href="../{path}/config.json">config</a> / <a href="../{path}/provenance.json">provenance</a>'])+'</tr>')
 page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>All retained runs · Barricelli</title><link rel="stylesheet" href="style.css"><style>main{max-width:1500px}table{border-collapse:collapse;font-size:12px;width:100%}td,th{text-align:left;padding:10px;border-bottom:1px solid #243747}.overflow{overflow-x:auto}</style></head><body><header><a href="index.html">B / S · Return to atlas</a><a href="../results/run_register.csv">Download CSV</a></header><main><h1>Every retained run.</h1><p>'+str(len(rows))+' native simulation trajectories, including unsuccessful assays and unselected search outcomes. This register records retained scientific runs; oracle replays, tests, development reruns and explicitly synthetic descriptor controls are separately documented.</p><input id="filter" aria-label="Filter runs" placeholder="Filter profile, norm, seed or stage"><div class="overflow"><table><thead><tr>'+''.join('<th>'+s+'</th>' for s in ['Run / numeric data','Profile','Norm','Seed','Cells','Updates','Process s','Native KiB','Evidence'])+'</tr></thead><tbody>'+''.join(body)+'</tbody></table></div><p><a href="../results/descriptor_controls/manifest.json">Explicitly imposed descriptor controls</a> · <a href="../results/resource_summary.json">Resource summary</a></p></main><script>document.getElementById("filter").oninput=e=>{for(const row of document.querySelectorAll("tbody tr"))row.hidden=!row.textContent.toLowerCase().includes(e.target.value.toLowerCase())}</script></body></html>'
 (ROOT/'atlas/register.html').write_text(page)
 print('atlas worlds',len(worlds),'registered native runs',len(rows),'payload bytes',(ROOT/'atlas/data.js').stat().st_size)
if __name__=='__main__': main()
