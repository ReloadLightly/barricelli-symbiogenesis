#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Figures for complete search, environment and diagnostic-control outcomes."""
import json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,read_csv
from barricelli.plot import plt,PALETTE,style,save,image,run_label,legend
from search import records,METHODS
import numpy as np
OUT=ROOT/'results/figures'
LABELS=['Random','Novelty archive','Codex feedback']

def search():
 d=json.loads((ROOT/'results/search/summary.json').read_text()); fig,axes=plt.subplots(1,2,figsize=(12,5),facecolor=PALETTE['background']); colors=['#7da8bd','#39d5ee','#bfa9ff']
 for m,label,col in zip(METHODS,LABELS,colors):
  histories=[records(m,i) for i in range(4)]; curves=[ [len({tuple(r['descriptors']['archive_bin']) for r in h[:t]}) for t in range(1,13)] for h in histories]
  for c in curves: axes[0].plot(range(1,13),c,color=col,alpha=.22,lw=1)
  axes[0].plot(range(1,13),np.mean(curves,axis=0),color=col,lw=2,label=label)
 for i,m in enumerate(METHODS):
  rows=[r for r in d['searches'] if r['method']==m]; a=d['aggregate'][m]['coverage']; lo,hi=a['ci95_percentile']
  axes[1].errorbar(i,a['mean'],yerr=[[a['mean']-lo],[hi-a['mean']]],fmt='o',color=colors[i],capsize=6)
  axes[1].scatter(np.full(4,i)+np.linspace(-.12,.12,4),[r['archive_coverage'] for r in rows],color=colors[i],s=16,alpha=.5)
 axes[0].set(xlabel='Simulation evaluations per search',ylabel='Occupied descriptor bins',ylim=(0,7),title='Complete learning curves / four searches per method'); axes[0].legend(facecolor=PALETTE['background'],labelcolor=PALETTE['text'],fontsize=9)
 axes[1].set(xticks=range(3),xticklabels=LABELS,ylabel='Final archive coverage',ylim=(0,7),title='Search-unit means and exploratory bootstrap intervals')
 for ax in axes: style(ax)
 fig.tight_layout(); sources=[ROOT/r['path']/'search_record.json' for m in METHODS for i in range(4) for r in records(m,i)]
 save(fig,OUT/'search_comparison.png','All144 discovery evaluations: research/galloway_B, W128,T256; four repeated12-evaluation searches per method, same48-configuration space and matched seed schedule4100+100r+trial. Thin lines and points retain all search outcomes. Thick curves show search-unit means; bars are95% seed/search-level percentile bootstrap intervals. Codex proposals use shared conversation context and are not independent model sessions; these exploratory results do not establish a general LLM advantage. Sources include every saved run reference and descriptor record.',sources)

def heterogeneity():
 d=json.loads((ROOT/'results/heterogeneity/summary.json').read_text()); norms=['galloway_A','galloway_B','galloway_AB_halves','galloway_AB_quarters','galloway_AB_temporal']; names=['A','B','A:B halves','A:B:A:B quarters','A/B temporal']
 fig,axes=plt.subplots(2,2,figsize=(13,8),facecolor=PALETTE['background'])
 for row,cohort in enumerate(['exploration','confirmation']):
  group=[r for r in d['rows'] if r['cohort']==cohort]; seeds=sorted({r['seed'] for r in group}); horizon=512 if row==0 else 2048
  for seed in seeds:
   g={r['norm']:r for r in group if r['seed']==seed}
   # Right-censored nonrecurrence is shown at the horizon with a triangle.
   y=[g[n]['recurrence']['return_time'] if g[n]['recurrence'] else horizon for n in norms]
   axes[row,0].plot(range(5),y,color=PALETTE['accent'],alpha=.25,lw=1)
   for i,n in enumerate(norms): axes[row,0].scatter(i,y[i],marker='o' if g[n]['recurrence'] else '^',s=25,color=PALETTE['accent'])
   axes[row,1].plot(range(5),[g[n]['tail_new4_signatures'] for n in norms],color='#bfa9ff',alpha=.25,lw=1)
   axes[row,1].scatter(range(5),[g[n]['tail_new4_signatures'] for n in norms],color='#bfa9ff',s=20)
  axes[row,0].set(ylabel='First recurrence return time\n▲ = no recurrence by horizon',title=f'{cohort}: paired seeds, T{horizon}',ylim=(0,horizon*1.06))
  axes[row,1].set(ylabel='New four-cell signatures\nin final32 saved rows',title=f'{cohort}: local novelty, T{horizon}',ylim=(-8,240))
  for ax in axes[row]: ax.set_xticks(range(5)); ax.set_xticklabels(names,rotation=18,ha='right',fontsize=8); style(ax)
 fig.tight_layout(); sources=[ROOT/r['path']/'descriptors.json' for r in d['rows']]
 save(fig,OUT/'heterogeneity_comparison.png','Complete60 baseline worlds: research profiles, W128, shared initial rows within each seed; exploration6100–6107,T512 and confirmation9200–9203,T2048. Full-world recurrence includes environment phase for temporal A/B. Triangles are right-censored, not exact recurrence events. Some mixed environments have late local novelty at512 updates; every longer confirmation has zero unseen four-cell signatures in its final32-row window. Local sequences are not inherited collective variants.',sources)
 fig,axes=plt.subplots(1,5,figsize=(15,6),facecolor=PALETTE['background']); sources=[]; values=set()
 for ax,n,name in zip(axes,norms,names):
  path=ROOT/f'results/heterogeneity/exploration_6100_{n}'; arr=read_csv(path/'trajectory.csv'); sources.append(path/'trajectory.csv'); values.update(np.unique(arr)); image(ax,arr,name+'\n'+run_label(path))
 legend(fig,sorted(values)); fig.subplots_adjust(bottom=.15,top=.88,wspace=.4)
 save(fig,OUT/'heterogeneity_paired_worlds.png','Selected explanatory seed6100: five research collision environments, identical saved128-cell initial row and512 updates. Axes and research palette match. A andB settle into simple recurrent domains; this seed’s spatial halves treatment retains a nonrepeating transient. All other seeds are included in aggregate results. Time increases downward.',sources)

def controls():
 d=json.loads((ROOT/'results/descriptor_controls/summary.json').read_text()); fig,axes=plt.subplots(2,3,figsize=(12,7),facecolor=PALETTE['background']); sources=[]; values=set()
 for ax,r in zip(axes.flat,d):
  p=ROOT/'results/descriptor_controls'/r['id']; arr=read_csv(p/'trajectory.csv'); sources.append(p/'trajectory.csv'); values.update(np.unique(arr)); image(ax,arr[:48],r['id']+'\nIMPOSED control / seed7711 / W128,T256\nfirst48 rows; activity'+f"{r['tail_activity']:.2f}, repeat4 {r['tail_repeated4_fraction']:.2f}")
 axes.flat[-1].axis('off'); legend(fig,sorted(values)); fig.subplots_adjust(bottom=.15,top=.93,wspace=.4,hspace=.5)
 save(fig,OUT/'descriptor_controls.png','Five explicitly imposed numerical histories, not simulated discoveries: W128,T256, RNG seed7711 for IID noise. Activity equals1 for the period-two and translation controls; IID noise has high entropy but zero retained repeated signatures. Repetition, motion, persistence and entropy therefore require separate interpretations. Every panel derives from saved control CSVs; time increases downward.',sources)

def helper():
 conditions=['direct_helper_removed','rescue','same_type_damage_elsewhere','wrong_helper_same_occupancy']; fig,axes=plt.subplots(1,4,figsize=(14,5),facecolor=PALETTE['background']); sources=[]; values=set()
 labels=['Direct helper removed','Exact rescue','Same type, other site','Wrong helper, same occupancy']
 for ax,name,label in zip(axes,conditions,labels):
  p=ROOT/f'results/partner_followup/empty__x112__{name}'
  if not p.exists(): p=next((ROOT/'results/partner_followup').glob('*empty*x112*'+name))
  arr=read_csv(p/'trajectory.csv'); values.update(np.unique(arr)); sources.append(p/'trajectory.csv'); image(ax,arr[:,64:152],label+'\nresearch / exclusion\nx112 · W256 · T48'); ax.set_xticks([0,24,48,72]); ax.set_xticklabels([64,88,112,136])
 legend(fig,sorted(values)); fig.subplots_adjust(bottom=.15,top=.8,wspace=.4)
 save(fig,OUT/'partner_specificity.png','Exploratory dependency-directed follow-up, selected empty-background placement112; all24 follow-up runs remain registered. Historical Figure7 motif, research/exclusion,W256,T48, x64–151 shown. Removing its direct helper at offset5 or changing−3 to−4 prevents exact-motif recovery; removal of the same type at offset1 permits recovery; exact rescue restores the intact trajectory. This tests partner arrangement for propagation; no additional detached collective reproduction was detected.',sources)

if __name__=='__main__': OUT.mkdir(exist_ok=True); search(); heterogeneity(); controls(); helper()
