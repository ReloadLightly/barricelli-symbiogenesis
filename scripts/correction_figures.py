#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
import json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,save_json
from barricelli.plot import plt,PALETTE,style,save
import numpy as np
BASE=ROOT/'results/corrections/descriptor_v2'; OUT=ROOT/'results/figures'
def main():
 d=json.loads((BASE/'search_summary.json').read_text()); fig,axes=plt.subplots(1,2,figsize=(12,5),facecolor=PALETTE['background'])
 methods=['random','novelty_archive','codex_feedback']; colors=['#7da8bd','#39d5ee','#bfa9ff']; sources=[BASE/'search_summary.json']
 for method,color in zip(methods,colors):
  for repeat in range(4):
   paths=sorted((BASE/'runs/search'/method/f'repeat{repeat}').glob('*/analysis.json')); records=[json.loads(p.read_text()) for p in paths]; sources+=paths
   curve=[len({tuple(r['descriptors']['archive_bin']) for r in records[:t]}) for t in range(1,13)]
   axes[0].plot(range(1,13),curve,color=color,alpha=.45)
 for i,m in enumerate(methods):
  values=[r['archive_coverage'] for r in d['searches'] if r['method']==m]
  axes[1].scatter(np.full(4,i)+np.linspace(-.12,.12,4),values,color=colors[i]); axes[1].scatter(i,np.mean(values),color=colors[i],marker='D',s=70)
 axes[0].set(xlabel='Evaluations',ylabel='Corrected descriptor bins',title='Saved searches; boundary-aware reanalysis')
 axes[1].set(xticks=range(3),xticklabels=['Random','Novelty','Codex'],ylabel='Coverage',title='Four search units; diamonds = means')
 for ax in axes: style(ax)
 fig.tight_layout(); save(fig,OUT/'search_comparison_corrected.png','Correction C1: all144 saved discovery trajectories reanalyzed using ring-aware four-cell windows. Original policy choices remain frozen; this does not reconstruct what corrected adaptive policies would choose. Original analyses and figure remain preserved.',sources)
 rows=[]
 for name in ['static_periodic','period_two','translation','iid_noise','empty']:
  old=json.loads((ROOT/'results/descriptor_controls'/name/'descriptors.json').read_text()); new=json.loads((BASE/'runs/descriptor_controls'/name/'analysis.json').read_text())['descriptors']; rows.append((name,old,new))
 fig,ax=plt.subplots(figsize=(11,5),facecolor=PALETTE['background']); x=np.arange(5)
 ax.bar(x-.25,[r[1]['exact_translation_fraction'] for r in rows],width=.25,color='#7da8bd',label='Original reported translation')
 ax.bar(x,[r[2]['exact_translation_fraction'] for r in rows],width=.25,color=PALETTE['accent'],label='Unique exact motion, corrected')
 ax.bar(x+.25,[r[2]['ambiguous_translation_fraction'] for r in rows],width=.25,color='#bfa9ff',label='Ambiguous periodic shifts')
 ax.set(xticks=x,xticklabels=[r[0].replace('_',' ') for r in rows],ylabel='Fraction of final-window updates',title='Saved imposed controls: stationary equality and periodic aliases'); style(ax); ax.legend(facecolor=PALETTE['background'],labelcolor=PALETTE['text']); fig.tight_layout()
 save(fig,OUT/'motion_detection_correction.png','Correction C1 on original saved synthetic control histories. Stationary and empty rows are not motion. Period-two and spatially periodic shifting rows admit several exact shifts and are reported as ambiguous, not uniquely identified motion. All are explicitly imposed controls, not discovered organisms.',[ROOT/'results/descriptor_controls/summary.json',*[BASE/'runs/descriptor_controls'/r[0]/'analysis.json' for r in rows]])
if __name__=='__main__': main()
