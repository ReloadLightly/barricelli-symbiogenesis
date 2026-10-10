# SPDX-License-Identifier: GPL-3.0-only
"""Renderer consumes saved data only. Historical and research styles explicit."""
import argparse, colorsys, csv, json, pathlib, os,sys
import numpy as np
os.environ.setdefault('MPLCONFIGDIR','/tmp/barricelli-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from .run import ROOT,read_csv,save_json,sha
PALETTE=json.loads((ROOT/'configs/palette.json').read_text())

def color(value,legacy=False):
 value=int(value)
 if legacy: return PALETTE['legacy_galloway'].get(str(value),'#ffffff')
 if value==0: return PALETTE['background']
 if value==99999: return PALETTE['exclusion']
 spec=PALETTE['research']; h=((value*spec['multiplier'])%(2**32))/(2**32)
 rgb=colorsys.hsv_to_rgb(h,spec['saturation'],spec['value'])
 return '#'+''.join(f'{int(round(v*255)):02x}' for v in rgb)
def pixels(arr,legacy=False):
 from matplotlib.colors import to_rgb
 out=np.empty((*arr.shape,3))
 for v in np.unique(arr): out[arr==v]=to_rgb(color(v,legacy))
 return out

def style(ax,historical=False):
 if historical: return
 ax.set_facecolor(PALETTE['background']); ax.tick_params(colors=PALETTE['text'],labelsize=8)
 for spine in ax.spines.values(): spine.set_color('#345574')
 for element in [ax.xaxis.label,ax.yaxis.label,ax.title]: element.set_color(PALETTE['text'])

def image(ax,arr,title,legacy=False,textual=False,historical=False):
 if historical:
  ax.set_facecolor('white'); ax.set_xlim(-.5,arr.shape[1]-.5); ax.set_ylim(arr.shape[0]-.5,-.5)
  for t,x in np.argwhere(arr!=0):
   v=int(arr[t,x]); ax.text(x,t,'x' if v==99999 else str(abs(v)),ha='center',va='center',fontsize=7,color='black')
   if v<0: ax.plot([x-.27,x+.27],[t+.3,t+.3],color='black',lw=.8)
  ax.set_xticks(np.arange(-.5,arr.shape[1],1),minor=True); ax.set_yticks(np.arange(-.5,arr.shape[0],1),minor=True)
  ax.grid(which='minor',color='#dddddd',lw=.25); ax.tick_params(which='minor',length=0)
 else: ax.imshow(pixels(arr,legacy),origin='upper',interpolation='nearest',aspect='auto')
 ax.set_xlabel('horizontal position x'); ax.set_ylabel('time t (downward)'); ax.set_title(title,fontsize=9)
 style(ax,historical)
 if textual and not historical:
  for t,x in np.argwhere(arr!=0):
   v=int(arr[t,x]); ax.text(x,t,'x' if v==99999 else str(v),ha='center',va='center',fontsize=8,color='white',bbox={'facecolor':'#080f1c','alpha':.75,'pad':.1,'edgecolor':'none'})

def run_label(path):
 c=json.loads((path/'config.json').read_text()); ref=f"seed{c['seed']}" if c.get('seed') is not None else pathlib.Path(c['initial_state_file']).name
 return f"{c['model']} | {ref} | W={c['width']}, T={c['steps']}"

def save(fig,path,caption,sources):
 path=pathlib.Path(path); path.parent.mkdir(parents=True,exist_ok=True)
 axes=[{'horizontal':ax.get_xlabel(),'vertical':ax.get_ylabel()} for ax in fig.axes]
 render_files=[pathlib.Path(__file__).resolve()]; driver=pathlib.Path(sys.argv[0]).resolve()
 if driver.is_file() and ROOT in driver.parents: render_files.append(driver)
 fig.savefig(path,dpi=180,facecolor=fig.get_facecolor(),bbox_inches='tight'); plt.close(fig)
 records=[]
 for source in sources:
  source=pathlib.Path(source); records.append({'file':str(source.relative_to(ROOT)),'sha256':sha(source)})
 save_json(path.with_suffix('.json'),{'caption':caption,'data_sources':records,'renderer_files_sha256':{str(p.relative_to(ROOT)):sha(p) for p in render_files},'palette':'configs/palette.json','palette_sha256':sha(ROOT/'configs/palette.json'),'axes':axes,'cell_rendering':'discrete unsmoothed pixels or numerical text when trajectories are shown'})
 path.with_suffix('.caption.md').write_text(caption+'\n')

def legend(fig,values):
 handles=[Patch(facecolor=color(v),label='empty' if v==0 else 'exclusion x' if v==99999 else str(v)) for v in values]
 lg=fig.legend(handles=handles,loc='lower center',ncol=min(14,len(values)),fontsize=7,frameon=False)
 for t in lg.get_texts(): t.set_color(PALETTE['text'])

def main():
 p=argparse.ArgumentParser(); p.add_argument('run'); p.add_argument('--mode',choices=['historical','research'],default='research'); p.add_argument('--output',required=True); a=p.parse_args()
 path=pathlib.Path(a.run).resolve(); arr=read_csv(path/'trajectory.csv'); c=json.loads((path/'config.json').read_text())
 fig,ax=plt.subplots(figsize=(9,6),facecolor='white' if a.mode=='historical' else PALETTE['background'])
 hist=a.mode=='historical' and c['model']!='galloway_published'; legacy=a.mode=='historical' and c['model']=='galloway_published'
 image(ax,arr,run_label(path),legacy=legacy,historical=hist)
 if a.mode=='research': legend(fig,sorted(np.unique(arr))); fig.subplots_adjust(bottom=.18)
 save(fig,a.output,'Saved numerical trajectory; colors identify values. No reproductive identity follows from a colored domain.',[path/'trajectory.csv'])
if __name__=='__main__': main()
