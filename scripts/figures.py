#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""All scientific panels are derived from saved trajectories and events."""
import sys,pathlib,json,csv
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,read_csv
from barricelli.plot import plt,PALETTE,image,save,legend,color,style,run_label,pixels
import numpy as np
OUT=ROOT/'results/figures'

def historical():
 figs=[2,5,7,8,12,18]; descriptions=['displacement without self-retention','assisted multiple copying','collective domain propagation','crossing of periodic domains','collision-generated +5','historical host-dependent pattern']
 fig,axes=plt.subplots(3,2,figsize=(15,11),facecolor='white'); sources=[]
 for ax,f,desc in zip(axes.flat,figs,descriptions):
  path=ROOT/f'results/reconstruction/figure{f:02d}'; arr=read_csv(path/'trajectory.csv'); sources.append(path/'trajectory.csv')
  image(ax,arr,f'Fig.{f}: {desc}\n'+run_label(path),historical=True)
 fig.tight_layout()
 save(fig,OUT/'historical_examples.png','Historical reconstruction: Figures 2, 5, 7, 8, 12 and 18 match Taylor fixtures exactly. Empty cells are blank, negative values underlined, and x denotes exclusion. Displacement, assisted copying, propagation, crossing and mutation are separate observations; Figure7 domain propagation does not establish detached offspring.',sources)

def gallery():
 fig,axes=plt.subplots(2,3,figsize=(14,10),facecolor=PALETTE['background']); sources=[]; values=set()
 for ax,seed in zip(axes.flat,range(2026,2032)):
  path=ROOT/('results/reconstruction' if seed==2026 else 'results/ensemble')/f'galloway{seed}'; arr=read_csv(path/'trajectory.csv'); sources.append(path/'trajectory.csv'); values.update(np.unique(arr))
  image(ax,arr,run_label(path)); ax.set_xlim(-.5,510.5); ax.set_ylim(511.5,-.5)
 legend(fig,sorted(values)); fig.subplots_adjust(bottom=.13,top=.94,hspace=.35,wspace=.27)
 save(fig,OUT/'galloway_all_runs.png','Complete six-run Galloway ensemble, seeds2026–2031, all W511 and511 updates (512 saved rows). Runs are unselected. Stable textures and moving boundaries show numerical dynamics; these panels do not identify reproducing collectives. Values outside the legacy palette remain distinct from empty cells in the research palette.',sources)
 # Full published palette behavior for FIRST predeclared seed, explicitly labeled.
 path=ROOT/'results/reconstruction/galloway2026'; arr=read_csv(path/'trajectory.csv')
 fig,axes=plt.subplots(1,2,figsize=(12,6),facecolor=PALETTE['background'])
 image(axes[0],arr,'Published rendering | '+run_label(path),legacy=True); image(axes[1],arr,'Research rendering | '+run_label(path))
 fig.tight_layout(); save(fig,OUT/'galloway_rendering_comparison.png','Selected illustration: first predeclared ensemble seed2026, identical saved511×512 values in two explicit rendering modes. Published palette defaults to white for both0 and out-of-palette values (this run generates−22). Research mapping distinguishes them; hue identifies value, not organism.',[path/'trajectory.csv'])

def discrepancy():
 new=ROOT/'results/reconstruction/figure15/trajectory.csv'; plate=ROOT/'fixtures/fig15-orig-from-lalaina-rahobisoa.csv'; arr=read_csv(new); old=read_csv(plate)
 fig,axes=plt.subplots(1,3,figsize=(13,7),facecolor=PALETTE['background'])
 image(axes[0],arr,'barricelli1954_reference | Fig15-new initial\nW83, T100 | computed, unpatched')
 image(axes[1],old,'Historical plate fixture | same initial row\nW83, T100 | Rahobisoa transcription')
 axes[2].imshow(arr!=old,cmap='cividis',interpolation='nearest',aspect='auto',origin='upper'); axes[2].set_title('Cell discrepancies | first at t8\n5,091 mismatches after divergence',fontsize=9); axes[2].set_xlabel('horizontal position x'); axes[2].set_ylabel('time t (downward)'); style(axes[2])
 legend(fig,sorted(set(np.unique(arr))|set(np.unique(old)))); fig.subplots_adjust(bottom=.12,top=.9,wspace=.4)
 save(fig,OUT/'figure15_discrepancy.png','Figure15 computed and historical-plate fixture trajectories agree through t7 (first8 rows). At t8 (generation9), positions51,56,58 first differ. Subsequent propagation of discrepancies produces5,091 unequal cells; this is not a count of hand-calculation errors. No cells were patched. Model: historical conditional norm, W83,T100, fixed Fig15 initial row.',[new,plate])

def causal():
 data=json.loads((ROOT/'results/assay/summary.json').read_text()); candidates=json.loads((ROOT/'results/assay/candidates.json').read_text())
 names=['intact','helper_removed','rescue','composition_shuffled_fixed_gaps','wrong_helper_same_occupancy','matched_delete_same_type']
 for candidate in candidates:
  fig,axes=plt.subplots(2,3,figsize=(14,7),facecolor=PALETTE['background']); sources=[]; values=set()
  for ax,name in zip(axes.flat,names):
   path=ROOT/f'results/assay/{candidate["id"]}__empty__x112__{name}'; arr=read_csv(path/'trajectory.csv'); sources.append(path/'trajectory.csv'); values.update(np.unique(arr))
   # SAME window and time axes for all paired conditions. Show complete horizon.
   image(ax,arr[:,64:152],f'{name}\nresearch/{candidate["norm"]} | saved initial x112 | W256,T48')
   ax.set_xticks([0,24,48,72]); ax.set_xticklabels([64,88,112,136])
  legend(fig,sorted(values)); fig.subplots_adjust(bottom=.12,top=.94,wspace=.28,hspace=.43)
  save(fig,OUT/(candidate['id']+'_conditions.png'),f'Selected explanatory setting: {candidate["id"]}, empty background, placement112, all six specified conditions at the same48-update horizon; shown x64–151 from width256. All other settings remain in assay aggregates. Template equality and occupied domain expansion are measured separately from detached offspring; two-cell guards outside each motif define detachment.',sources)
 # Aggregate every condition/background/placement. No standard error from timepoints.
 fig,axes=plt.subplots(1,2,figsize=(15,6),facecolor=PALETTE['background']); sources=[]
 for ax,candidate in zip(axes,candidates):
  rows=[r for r in data['rows'] if r['candidate']==candidate['id']]; names=list(candidate['conditions'])+['cleared_footprint']; keys=sorted(set((r['background'],r['placement']) for r in rows))
  matrix=np.array([[next((r['motif_persistence_last_time'] for r in rows if r['condition']==name and (r['background'],r['placement'])==key),np.nan) for name in names] for key in keys])
  im=ax.imshow(matrix,vmin=0,vmax=48,cmap='Blues',interpolation='nearest',aspect='auto'); ax.set_xticks(range(len(names))); ax.set_xticklabels(names,rotation=60,ha='right',fontsize=7); ax.set_yticks(range(len(keys))); ax.set_yticklabels([f'{bg}/x{x}' for bg,x in keys],fontsize=8); ax.set_title(candidate['id']+'\nresearch | W256,T48 | all settings',fontsize=10); ax.set_xlabel('condition'); ax.set_ylabel('paired background / placement'); style(ax)
  for (y,x),v in np.ndenumerate(matrix):
   if np.isfinite(v): ax.text(x,y,str(int(v)),ha='center',va='center',fontsize=8,color='white' if v>24 else '#143650')
  cbar=fig.colorbar(im,ax=ax,fraction=.035,pad=.02); cbar.set_label('last time with exact motif',color=PALETTE['text']); cbar.ax.tick_params(colors=PALETTE['text'])
 sources.append(ROOT/'results/assay/summary.csv'); fig.subplots_adjust(bottom=.36,top=.88,wspace=.38)
 save(fig,OUT/'assay_all_settings.png','Complete paired assay: all conditions and background/placement settings, research profiles, width256 and48 updates, fixed saved initial rows. Entries give the last time with an exact translated period-one template; a missing initial template does not automatically fail if it reappears. Empty, resident and original-ecology outcomes differ. These chosen settings support descriptive paired effects, not seed-level population uncertainty estimates.',sources)

def dependencies():
 path=ROOT/'results/assay/historical_figure7__empty__x112__intact'; arr=read_csv(path/'trajectory.csv'); events=list(csv.DictReader((path/'events.csv').open()))
 # Defined focal source: first nonzero value5 in initial motif, source112.
 events=[e for e in events if int(e['time'])==0 and int(e['source'])==112]
 fig,ax=plt.subplots(figsize=(12,5),facecolor=PALETTE['background']); crop=arr[:3,104:128]
 image(ax,crop,'research/exclusion | Figure7 motif initial x112 | W256,T48\nNumerical copying detail t0→t1 (first3 saved rows)',textual=True)
 for event in events:
  source=int(event['source'])-104; target=int(event['target'])-104
  ax.annotate('',xy=(target,.82),xytext=(source,.17),arrowprops={'arrowstyle':'->','color':PALETTE['accent'],'lw':1.7})
  for helper in event['helpers'].split(';'):
   if not helper: continue
   h=int(helper.split(':')[0])-104
   ax.annotate('',xy=(target,.83),xytext=(h,.17),arrowprops={'arrowstyle':'->','color':'#f6dd78','lw':1.2,'linestyle':'dashed'})
 ax.set_xticks(np.arange(0,24,2)); ax.set_xticklabels(np.arange(104,128,2)); ax.set_yticks([0,1,2]); ax.set_ylim(2.5,-.5)
 fig.text(.06,.02,'Cyan: copied source5 at112. Dashed gold: old-row helper−3 at117.\nTwo accepted targets:117 and109. Offsets refer to the original source; helpers do not themselves move the source cumulatively.',color=PALETTE['text'],fontsize=9)
 fig.subplots_adjust(bottom=.18,top=.8)
 save(fig,OUT/'copy_dependencies.png','Selected numerical explanation: Figure7 motif in research/exclusion, empty width256, initial placement112,48 updates. Saved first-step events record the5 at112 copying to117, then through helper−3 at117 to109 (the old-row cell109 is empty, so this chain stops). Both source and ordered numerical partners are recorded. Equal values elsewhere do not establish this ancestry.',[path/'trajectory.csv',path/'events.csv'])

def main():
 OUT.mkdir(parents=True,exist_ok=True); historical(); gallery(); discrepancy(); causal(); dependencies()
 print('figures',len(list(OUT.glob('*.png'))))
if __name__=='__main__': main()
