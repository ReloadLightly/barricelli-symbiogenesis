#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Illustrate measured R8 outcomes, retaining all unselected runs separately."""
import json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
from barricelli.run import ROOT,read_csv
from barricelli.plot import plt,PALETTE,style,image,save
BASE=ROOT/'results/discovery_art'; FIG=ROOT/'results/figures'
def main():
 s=json.loads((BASE/'summary.json').read_text()); colors=['#60e6ed','#dfacff','#ffe19c']; names=['random','novelty_archive','codex_feedback']
 fig,axes=plt.subplots(1,2,figsize=(11,4),facecolor=PALETTE['background'])
 for m,col in zip(names,colors):
  rows=[r for r in s['searches'] if r['method']==m]; ys=np.array([r['coverage_by_trial'] for r in rows])
  axes[0].plot(np.arange(1,17),ys.mean(axis=0),label=m,color=col); axes[0].fill_between(np.arange(1,17),ys.min(axis=0),ys.max(axis=0),alpha=.1,color=col)
  i=names.index(m); v=[r['coverage'] for r in rows]; a=s['aggregate'][m]['coverage']; lo,hi=a['ci95_percentile']; axes[1].bar(i,a['mean'],color=col,width=.55,alpha=.65)
  axes[1].errorbar(i,a['mean'],yerr=[[a['mean']-lo],[hi-a['mean']]],fmt='none',ecolor=PALETTE['text']); axes[1].scatter(i+np.linspace(-.12,.12,4),v,color=col,edgecolors='#080f1c')
 axes[0].set(xlabel='evaluations per search (identical update budget)',ylabel='occupied descriptor archive bins',title='R8 / complete search learning curves'); axes[0].legend(fontsize=8,facecolor=PALETTE['background'],labelcolor=PALETTE['text'])
 axes[1].set(xticks=range(3),xticklabels=['Random','Novelty','Codex'],ylabel='final archive coverage',title='Four search units; exploratory bootstrap 95% CI')
 for ax in axes: style(ax)
 save(fig,FIG/'discovery_broader_comparison.png','R8:192 retained searches in1,024 declared configurations;16 evaluations per repeated search, four repeats/method. Bands span search minima/maxima; points are search units. Codex used its own saved visuals and numerical feedback. Descriptor coverage is not life or aesthetic quality.',[BASE/'summary.json'])
 study=BASE/'investigation/summary.json'
 if not study.exists(): return
 d=json.loads(study.read_text()); fig,axes=plt.subplots(1,2,figsize=(10,4),facecolor=PALETTE['background'])
 for ci in range(3):
  rows=[r['descriptors'] for r in d['confirmation'] if r['candidate']==ci]
  for ax,key in zip(axes,['retained_repeated4_signatures','tail_new4_signatures']): ax.scatter(ci+np.linspace(-.12,.12,4),[r[key] for r in rows],color=colors[ci],s=36)
 for ax,title in zip(axes,['Retained signatures at1536 updates','New signatures in final32 rows']):
  ax.set(xticks=range(3),xticklabels=['Random case','Novelty case','Codex case'],ylabel='number of exact four-cell signatures',title=title); style(ax)
 save(fig,FIG/'discovery_reserved_checks.png','Four unseen seeds per scientifically selected rule/configuration;1536 updates. These cases were selected by retained signatures, not art. Counts are exact short templates; recurrence and mutation ambiguity remain separate evidence.',[study])
 design=json.loads((BASE/'investigation/design.json').read_text()); sources=[]
 fig,axes=plt.subplots(3,4,figsize=(12,10),facecolor=PALETTE['background'])
 for ci,candidate in enumerate(design['candidates']):
  for j,condition in enumerate(['whole','focal_only','adjacent_removed','matched_damage_elsewhere']):
   p=BASE/'investigation'/f'case{ci}'/condition/'trajectory.csv'; sources.append(p)
   image(axes[ci,j],read_csv(p),f'Case{ci} / {condition.replace("_"," ")}')
 save(fig,FIG/'discovery_interventions.png','Saved R8 causal-assay histories. Component extraction/removal and matched damage are imposed before assay t0, from discovery t192. Appearance, persistence, exact template spread and certified ancestry are distinct. All shuffles, restoration and constituent rules are retained in the complete experiment.',sources)
 curation=BASE/'curation.json'
 if curation.exists():
  c=json.loads(curation.read_text()); fig,axes=plt.subplots(1,3,figsize=(13,4.8),facecolor=PALETTE['background']); sources=[]
  for ax,w in zip(axes,c['works']):
   source=ROOT/w['source_run']/'trajectory.csv'; sources.append(source); image(ax,read_csv(source),w['title'])
  save(fig,FIG/'discovery_art_series.png','Interfaces / R8: three aesthetic selections from actual saved trajectories. Full scientific outcomes are retained; these chosen works are not representative sampling and do not support a model-performance or biological claim.',sources)
  fig,axes=plt.subplots(1,3,figsize=(13,5),facecolor=PALETTE['background'])
  for ax,w in zip(axes,c['works']):
   a=read_csv(ROOT/w['source_run']/'trajectory.csv'); image(ax,a[184:196,72:84],w['title']+' / x72–83, t184–195',textual=True)
   ax.set_xlabel('position x −72'); ax.set_ylabel('time t −184 (downward)')
  save(fig,FIG/'discovery_numeric_closeups.png','Exact integer cutouts, x72–83 and t184–195, from each curated source. Local axes carry the explicitly stated offsets; colors encode values, not individual organisms. Enlarged atlas close-ups use the same integers.',sources)
if __name__=='__main__': main()
